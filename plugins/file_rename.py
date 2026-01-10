from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InputMediaDocument, Message
from PIL import Image
from datetime import datetime
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import ZoroBhaiya
from config import Config
import os
import time
import re
import asyncio
import traceback
import math
import logging

logger = logging.getLogger(__name__)

# --- QUEUE SYSTEM GLOBALS ---
PROCESSING_SEMAPHORE = asyncio.Semaphore(3)  # 3 parallel processes
QUEUE = asyncio.Queue()
QUEUE_TASK_RUNNING = False
# ----------------------------

renaming_operations = {}

# ============================================
# FIXED REGEX PATTERNS - ORDER MATTERS
# ============================================
# Pattern to extract episode number - IMPROVED
EPISODE_PATTERNS = [
    re.compile(r'[\s\-_](\d{3,4})[\s\-_\[]', re.IGNORECASE),  # Space before/after: " 1155 " or " 1155["
    re.compile(r'^(\d{3,4})[\s\-_\[]', re.IGNORECASE),  # Start of string: "1155 " or "1155["
    re.compile(r'[\]\)][\s\-_]?(\d{3,4})[\s\-_\[]', re.IGNORECASE),  # After bracket: "] 1155 "
    re.compile(r'[Ee][Pp]?[\s\-_]?(\d+)', re.IGNORECASE),  # EP123, E123, ep 123
    re.compile(r'[Ee]pisode[\s\-_]?(\d+)', re.IGNORECASE),  # Episode 123
    re.compile(r'S\d+[Ee](\d+)', re.IGNORECASE),  # S01E12
    re.compile(r'[\-_\s](\d{1,4})[\.\-_\s]*(?:v\d+)?$', re.IGNORECASE),  # End: "- 05" or " 05.mkv"
]

# Pattern to extract season number
SEASON_PATTERNS = [
    re.compile(r'[Ss]eason[\s\-_]?(\d+)', re.IGNORECASE),  # Season 1
    re.compile(r'[Ss](\d+)[Ee]\d+', re.IGNORECASE),  # S01E12
    re.compile(r'[\s\-_][Ss](\d+)[\s\-_\[]', re.IGNORECASE),  # " S1 " or " S1["
]

# Pattern to extract quality - FIXED
QUALITY_PATTERNS = [
    re.compile(r'\[(\d{3,4}[pP])\]', re.IGNORECASE),  # [480p], [1080p]
    re.compile(r'\((\d{3,4}[pP])\)', re.IGNORECASE),  # (480p), (1080p)
    re.compile(r'[\s\-_](\d{3,4}[pP])[\s\-_\[]', re.IGNORECASE),  # 480p , 1080p[
    re.compile(r'\b(\d{3,4}[pP])\b', re.IGNORECASE),  # 480p, 1080p (word boundary)
    re.compile(r'\b(4[Kk])\b', re.IGNORECASE),  # 4K
    re.compile(r'\b(2[Kk])\b', re.IGNORECASE),  # 2K
    re.compile(r'\b([Hh][Dd][Rr][Ii][Pp])\b', re.IGNORECASE),  # HDRIP
    re.compile(r'\b(4[Kk][Xx]26[45])\b', re.IGNORECASE),  # 4Kx264, 4Kx265
]

def extract_metadata_fast(filename):
    """
    OPTIMIZED: Extract all metadata in ONE pass
    Returns: (episode, season, quality)
    """
    # Remove file extension for cleaner parsing
    name_only = os.path.splitext(filename)[0]
    
    episode = None
    season = None
    quality = None
    
    # Extract episode number - try patterns in order
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(name_only)
        if match:
            episode = match.group(1)
            break
    
    # Extract season number
    for pattern in SEASON_PATTERNS:
        match = pattern.search(name_only)
        if match:
            season = match.group(1)
            break
    
    # Extract quality
    for pattern in QUALITY_PATTERNS:
        match = pattern.search(name_only)
        if match:
            quality = match.group(1)
            # Normalize quality format
            if quality.lower() in ['4k', '2k']:
                quality = quality.upper()
            elif 'p' in quality.lower():
                quality = quality.lower()  # 480p, 1080p
            elif 'hdrip' in quality.lower():
                quality = 'HDRIP'
            break
    
    # Set defaults for missing values
    if not quality:
        quality = 'Unknown'
    
    logger.info(f"Extracted from '{filename}': episode={episode}, season={season}, quality={quality}")
    
    return episode, season, quality

def apply_rename_template(template, episode, season, quality):
    """
    FIXED: Apply template with proper placeholder replacement
    """
    result = template
    
    # Replace {episode} - keep as-is if found, otherwise remove placeholder
    if '{episode}' in result:
        if episode:
            result = result.replace('{episode}', episode)
        else:
            # Remove placeholder if no episode found
            result = result.replace('{episode}', 'XX')
    
    # Replace {season} - keep as-is if found, otherwise use default
    if '{season}' in result:
        if season:
            result = result.replace('{season}', season.zfill(2))
        else:
            result = result.replace('{season}', '01')
    
    # Replace {quality}
    if '{quality}' in result:
        result = result.replace('{quality}', quality)
    
    return result

async def queue_processor(client):
    """Background task that processes queue"""
    global QUEUE_TASK_RUNNING
    QUEUE_TASK_RUNNING = True
    
    while True:
        try:
            message = await QUEUE.get()
            async with PROCESSING_SEMAPHORE:
                await start_processing(client, message)
            QUEUE.task_done()
        except Exception as e:
            logger.error(f"Queue processor error: {e}")
            traceback.print_exc()

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    """Main handler for incoming files"""
    global QUEUE_TASK_RUNNING
    
    user_id = message.from_user.id
    
    try:
        format_template = await ZoroBhaiya.get_format_template(user_id)
        logger.info(f"User {user_id} format template: {format_template}")
    except Exception as e:
        logger.error(f"Error fetching format for user {user_id}: {e}")
        format_template = None
    
    if not format_template or not format_template.strip():
        logger.warning(f"User {user_id} has no format template set")
        return await message.reply_text(
            "**❌ Please Set An Auto Rename Format First!**\n\n"
            "**Use:** `/autorename [format]`\n\n"
            "**Example:**\n"
            "`/autorename [@Anime_Atlas] {episode} - One Piece [{quality}] [Sub]`\n\n"
            "**Available Placeholders:**\n"
            "• `{episode}` - Episode number\n"
            "• `{season}` - Season number\n"
            "• `{quality}` - Video quality\n\n"
        )

    if not QUEUE_TASK_RUNNING:
        asyncio.create_task(queue_processor(client))
    
    await QUEUE.put(message)
    position = QUEUE.qsize()
    
    if position > 3:
        await message.reply_text(
            f"**⏳ Added to Queue**\n"
            f"**Position:** {position - 3}\n"
            f"**Status:** Waiting for processing slot...\n"
            f"**Currently Processing:** 3 files"
        )

async def get_video_duration(file_path):
    """Get video duration using ffprobe"""
    try:
        process = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", 
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        duration = float(stdout.decode().strip())
        return duration if duration > 0 else 0
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return 0

async def monitor_ffmpeg_progress(process, download_msg, duration, operation="Processing"):
    """Monitor FFmpeg progress in real-time"""
    last_update = 0
    
    try:
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8', errors='ignore').strip()
            
            # Look for time information
            if "time=" in line_str and duration > 0:
                current_time = time.time()
                if current_time - last_update > 2:  # Update every 2 seconds
                    try:
                        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line_str)
                        if time_match:
                            h, m, s = map(int, time_match.groups())
                            seconds_done = h*3600 + m*60 + s
                            percentage = min(int((seconds_done / duration) * 100), 100)
                            
                            bar_len = 20
                            filled = int((percentage / 100) * bar_len)
                            bar = "■ " * filled + "□" * (bar_len - filled)
                            
                            try:
                                await download_msg.edit(
                                    f"**⚙️ {operation}**\n\n"
                                    f"{bar}\n"
                                    f"**Progress:** {percentage}%\n"
                                    f"**Time Processed:** {seconds_done}/{int(duration)}s"
                                )
                                last_update = current_time
                            except Exception as edit_error:
                                # Message edit failed, continue monitoring
                                logger.debug(f"Edit failed: {edit_error}")
                                pass
                    except Exception as e:
                        logger.debug(f"Progress update error: {e}")
    except Exception as e:
        logger.error(f"Monitor error: {e}")

async def start_processing(client, message):
    """Main processing function for files"""
    user_id = message.from_user.id
    download_path = None
    output_path = None
    thumb_path = None
    download_msg = None
    
    try:
        # Get user settings
        try:
            format_template = await ZoroBhaiya.get_format_template(user_id)
            logger.info(f"Processing file for user {user_id} with format: {format_template}")
        except Exception as e:
            logger.error(f"Error fetching format during processing for user {user_id}: {e}")
            format_template = None
        
        if not format_template or not format_template.strip():
            logger.error(f"Format lost during processing for user {user_id}")
            return await message.reply_text(
                "**❌ Error:** Format template lost during processing. Please set it again with `/autorename`"
            )
        
        media_preference = await ZoroBhaiya.get_media_preference(user_id)

        # Get file info
        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name
            file_size = message.document.file_size
            media_type = media_preference or "document"
            duration = 0
        elif message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or f"video_{int(time.time())}.mp4"
            file_size = message.video.file_size
            media_type = media_preference or "video"
            duration = message.video.duration or 0
        elif message.audio:
            file_id = message.audio.file_id
            file_name = message.audio.file_name or f"audio_{int(time.time())}.mp3"
            file_size = message.audio.file_size
            media_type = media_preference or "audio"
            duration = message.audio.duration or 0
        else:
            return

        if file_id in renaming_operations:
            return

        renaming_operations[file_id] = datetime.now()

        # ============================================
        # FIXED: Extract metadata ONCE - FAST
        # ============================================
        episode, season, quality = extract_metadata_fast(file_name)
        
        # ============================================
        # FIXED: Apply template correctly - NO CORRUPTION
        # ============================================
        renamed_template = apply_rename_template(format_template, episode, season, quality)
        
        _, file_extension = os.path.splitext(file_name)
        renamed_file_name = f"{renamed_template}{file_extension}"
        
        logger.info(f"📄 Original: {file_name}")
        logger.info(f"📝 Renamed: {renamed_file_name}")
        
        # Create directories
        os.makedirs("downloads", exist_ok=True)
        
        # Safe temp file paths
        timestamp = int(time.time())
        download_path = f"downloads/input_{timestamp}{file_extension}"
        output_path = f"downloads/output_{timestamp}{file_extension}"
        
        download_msg = await message.reply_text("🚀 **Starting Download...**")

        # ============================================
        # DOWNLOAD WITH VERIFICATION (3 ATTEMPTS)
        # ============================================
        max_download_attempts = 3
        download_success = False
        
        for attempt in range(1, max_download_attempts + 1):
            try:
                logger.info(f"📥 Download attempt {attempt}/{max_download_attempts}")
                
                actual_path = await client.download_media(
                    message,
                    file_name=download_path,
                    progress=progress_for_pyrogram,
                    progress_args=("**📥 Downloading...**", download_msg, time.time()),
                )
                
                # Verify download
                if actual_path and os.path.exists(actual_path):
                    downloaded_size = os.path.getsize(actual_path)
                    
                    if downloaded_size > 0:
                        logger.info(f"✅ Downloaded: {humanbytes(downloaded_size)}")
                        
                        # Update path if pyrogram saved elsewhere
                        if actual_path != download_path:
                            download_path = actual_path
                        
                        download_success = True
                        break
                    else:
                        logger.error(f"❌ Downloaded file is 0 bytes")
                        try:
                            os.remove(actual_path)
                        except:
                            pass
                else:
                    logger.error(f"❌ Download returned invalid path")
                
                if attempt < max_download_attempts:
                    await asyncio.sleep(3)
                    
            except Exception as e:
                logger.error(f"❌ Download exception: {e}")
                if attempt < max_download_attempts:
                    await asyncio.sleep(3)
        
        if not download_success:
            logger.error("❌ Download failed after all attempts")
            return await download_msg.edit(
                "❌ **Download Failed**\n"
                "Telegram failed to download the file.\n"
                "Please resend the file or try again later."
            )

        # Check if video processing needed
        is_video = media_type == "video" or file_extension.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v']
        
        if duration == 0 and is_video:
            duration = await get_video_duration(download_path)
            logger.info(f"⏱️ Detected video duration: {duration}s")
        
        await download_msg.edit("**⚙️ Processing: Adding Metadata & Watermark...**")

        # ============================================
        # FIND FONT - WITH MULTIPLE FALLBACKS
        # ============================================
        font_path = None
        font_paths_to_try = [
            "helper/ZURAMBI.ttf",
            "/app/helper/ZURAMBI.ttf",
            "/usr/share/fonts/truetype/custom/zurambi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        for fp in font_paths_to_try:
            if os.path.exists(fp):
                font_path = fp
                logger.info(f"✅ Using font: {font_path}")
                break
        
        # ============================================
        # WATERMARK SETTINGS - ESCAPE SPECIAL CHARS
        # ============================================
        watermark_text = "ANIME ATLAS"
        
        # Build drawtext filter only if we have a font
        drawtext_filter = None
        if font_path:
            # Escape the font path for FFmpeg
            escaped_font_path = font_path.replace('\\', '\\\\').replace(':', '\\:')
            drawtext_filter = (
                f"drawtext=text='{watermark_text}':"
                f"fontfile='{escaped_font_path}':"
                f"fontsize=10:"
                f"fontcolor=white:"
                f"x=1:"
                f"y=1"
            )
            logger.info(f"🎨 Watermark enabled with font: {font_path}")
        else:
            logger.warning("⚠️ No font found - proceeding without watermark")

        # ============================================
        # OPTIMIZED FFMPEG SETTINGS - PROGRESSIVE FALLBACK
        # Strategy 1: Best quality (CRF 18)
        # Strategy 2: Balanced (CRF 23)
        # Strategy 3: Simple copy with metadata only
        # ============================================
        
        encoding_strategies = []
        
        if is_video:
            # Strategy 1: Near-lossless with watermark (if font available)
            if drawtext_filter:
                encoding_strategies.append({
                    'name': 'Near-Lossless + Watermark',
                    'params': [
                        '-vf', drawtext_filter,
                        '-c:v', 'libx264',
                        '-preset', 'ultrafast',
                        '-crf', '18',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy',
                        '-c:s', 'copy',
                        '-map', '0',
                        '-movflags', '+faststart',
                        '-max_muxing_queue_size', '9999',
                    ]
                })
            
            # Strategy 2: Balanced quality with watermark
            if drawtext_filter:
                encoding_strategies.append({
                    'name': 'Balanced + Watermark',
                    'params': [
                        '-vf', drawtext_filter,
                        '-c:v', 'libx264',
                        '-preset', 'ultrafast',
                        '-crf', '23',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy',
                        '-c:s', 'copy',
                        '-map', '0',
                        '-movflags', '+faststart',
                    ]
                })
            
            # Strategy 3: Copy streams (no re-encoding, no watermark)
            encoding_strategies.append({
                'name': 'Stream Copy (No Watermark)',
                'params': [
                    '-c', 'copy',
                    '-map', '0',
                ]
            })
        else:
            # Non-video: just copy
            encoding_strategies.append({
                'name': 'Stream Copy',
                'params': [
                    '-c', 'copy',
                    '-map', '0',
                ]
            })
        
        # Metadata to add
        metadata_params = [
            '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
            '-metadata', 'artist=Anime Atlas',
            '-metadata', 'author=Anime Atlas',
            '-metadata:s:v', 'title=Join Anime Atlas',
            '-metadata:s:a', 'title=Anime Atlas',
            '-metadata:s:s', 'title=Anime Atlas',
        ]

        # ============================================
        # TRY EACH ENCODING STRATEGY UNTIL ONE WORKS
        # ============================================
        ffmpeg_success = False
        
        for strategy_num, strategy in enumerate(encoding_strategies, 1):
            logger.info(f"🎬 Trying Strategy {strategy_num}/{len(encoding_strategies)}: {strategy['name']}")
            
            # Build command
            cmd = ['ffmpeg', '-i', download_path]
            cmd.extend(strategy['params'])
            cmd.extend(metadata_params)
            cmd.extend(['-y', output_path])
            
            logger.info(f"Command: {' '.join(cmd)}")
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                # ALWAYS monitor progress for video files
                progress_task = None
                if is_video and duration > 0:
                    logger.info(f"📊 Starting progress monitor for {duration}s video")
                    progress_task = asyncio.create_task(
                        monitor_ffmpeg_progress(process, download_msg, duration, f"Processing ({strategy['name']})")
                    )
                
                # Wait for FFmpeg to complete
                await process.wait()
                
                # Cancel progress monitoring if it's still running
                if progress_task and not progress_task.done():
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        pass
                
                # Check if successful
                if process.returncode == 0 and os.path.exists(output_path):
                    output_size = os.path.getsize(output_path)
                    if output_size > 0:
                        logger.info(f"✅ Strategy '{strategy['name']}' succeeded: {humanbytes(output_size)}")
                        ffmpeg_success = True
                        break
                    else:
                        logger.error(f"❌ Strategy '{strategy['name']}' produced 0-byte file")
                else:
                    stderr = await process.stderr.read()
                    error_msg = stderr.decode()[:500]
                    logger.error(f"❌ Strategy '{strategy['name']}' failed: {error_msg}")
                
                # Clean up failed output
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                
            except Exception as e:
                logger.error(f"❌ Strategy '{strategy['name']}' exception: {e}")
                traceback.print_exc()
        
        # If all strategies failed, show detailed error
        if not ffmpeg_success:
            logger.error("❌ All encoding strategies failed")
            return await download_msg.edit(
                "**❌ Processing Failed**\n"
                "All encoding attempts failed. This could be due to:\n"
                "• Corrupted input file\n"
                "• Missing FFmpeg installation\n"
                "• Incompatible video codec\n\n"
                "Please try a different file or contact support."
            )

        # ============================================
        # FINAL VERIFICATION
        # ============================================
        if not os.path.exists(output_path):
            logger.error("❌ Output file missing")
            return await download_msg.edit("❌ **Processing Error:** Output file missing.")
        
        final_file_size = os.path.getsize(output_path)
        if final_file_size == 0:
            logger.error("❌ Output file is 0 bytes")
            return await download_msg.edit("❌ **Processing Error:** Output file is empty.")
        
        logger.info(f"✅ Final output verified: {humanbytes(final_file_size)}")
        
        # Log size comparison
        size_increase = final_file_size - file_size
        size_ratio = (final_file_size / file_size) * 100
        logger.info(f"📊 Size: {humanbytes(file_size)} → {humanbytes(final_file_size)} (+{humanbytes(size_increase)}, {size_ratio:.1f}%)")

        # Check file size limit (4GB)
        if final_file_size > 4000 * 1024 * 1024:
            return await download_msg.edit(
                "**❌ File too large (>4GB)**\n"
                "Telegram has a file size limit of 4GB."
            )

        # ============================================
        # PREPARE CAPTION AND THUMBNAIL
        # ============================================
        await download_msg.edit("**📤 Uploading...**")
        
        c_caption = await ZoroBhaiya.get_caption(message.chat.id)
        c_thumb = await ZoroBhaiya.get_thumbnail(message.chat.id)

        caption = (
            c_caption.format(
                filename=renamed_file_name,
                filesize=humanbytes(final_file_size),
                duration=convert(int(duration)),
            )
            if c_caption
            else f"**{renamed_file_name}**"
        )

        # Prepare thumbnail
        if c_thumb:
            try:
                thumb_path = await client.download_media(c_thumb)
                if thumb_path:
                    img = Image.open(thumb_path).convert("RGB")
                    img = img.resize((320, 320))
                    img.save(thumb_path, "JPEG")
            except Exception as e:
                logger.error(f"Thumbnail processing error: {e}")
                thumb_path = None
        elif is_video and message.video and message.video.thumbs:
            try:
                thumb_path = await client.download_media(message.video.thumbs[0].file_id)
            except Exception as e:
                logger.error(f"Thumbnail extraction error: {e}")
                thumb_path = None

        # ============================================
        # UPLOAD WITH CORRECT FILENAME
        # ============================================
        try:
            upload_start = time.time()
            
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=output_path,
                    thumb=thumb_path,
                    caption=caption,
                    file_name=renamed_file_name,
                    force_document=True,
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            elif media_type == "video":
                await client.send_video(
                    message.chat.id,
                    video=output_path,
                    caption=caption,
                    thumb=thumb_path,
                    file_name=renamed_file_name,
                    duration=int(duration),
                    supports_streaming=True,
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            elif media_type == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=output_path,
                    caption=caption,
                    thumb=thumb_path,
                    file_name=renamed_file_name,
                    duration=int(duration),
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            
            await download_msg.delete()
            logger.info(f"✅ Upload completed: {renamed_file_name}")
            
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            traceback.print_exc()
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            await download_msg.edit(f"**❌ Upload Failed:** {error_msg}")

    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        traceback.print_exc()
        if download_msg:
            try:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                await download_msg.edit(f"**❌ An error occurred:** {error_msg}")
            except:
                pass

    finally:
        if file_id in renaming_operations:
            del renaming_operations[file_id]
        
        # Cleanup
        for path in [download_path, output_path, thumb_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"🗑️ Cleaned up: {path}")
                except Exception as e:
                    logger.error(f"Cleanup error for {path}: {e}")
