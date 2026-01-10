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
PROCESSING_SEMAPHORE = asyncio.Semaphore(2)
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
    
    if position > 2:
        await message.reply_text(
            f"**⏳ Added to Queue**\n"
            f"**Position:** {position - 2}\n"
            f"**Status:** Waiting for processing slot...\n"
            f"**Currently Processing:** 2 files"
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
    
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8', errors='ignore').strip()
        
        if "time=" in line_str and duration > 0:
            current_time = time.time()
            if current_time - last_update > 3:
                try:
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line_str)
                    if time_match:
                        h, m, s = map(int, time_match.groups())
                        seconds_done = h*3600 + m*60 + s
                        percentage = min(int((seconds_done / duration) * 100), 100)
                        
                        bar_len = 20
                        filled = int((percentage / 100) * bar_len)
                        bar = "■ " * filled + "□" * (bar_len - filled)
                        
                        await download_msg.edit(
                            f"**⚙️ {operation}...**\n\n"
                            f"{bar}\n"
                            f"**Progress:** {percentage}%\n"
                            f"**Time Processed:** {seconds_done}/{int(duration)}s"
                        )
                        last_update = current_time
                except Exception as e:
                    logger.debug(f"Progress update error: {e}")

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
        
        logger.info(f"Original: {file_name}")
        logger.info(f"Renamed: {renamed_file_name}")
        
        # Create directories
        os.makedirs("downloads", exist_ok=True)
        
        # FIXED: No timestamp prefix in final filename
        timestamp = int(time.time())
        download_path = f"downloads/{timestamp}_{file_name}"  # Temp download path
        output_path = f"downloads/output_{timestamp}{file_extension}"  # Final output path
        
        download_msg = await message.reply_text("🚀 **Starting Download...**")

        # Download file
        await client.download_media(
            message,
            file_name=download_path,
            progress=progress_for_pyrogram,
            progress_args=("**📥 Downloading...**", download_msg, time.time()),
        )
        
        if not os.path.exists(download_path):
            logger.error(f"Download failed: File not found at {download_path}")
            return await download_msg.edit("❌ **Download Failed:** File not found.")

        logger.info(f"Downloaded: {download_path} ({file_size} bytes)")

        # Check if video processing needed
        is_video = media_type == "video" or file_extension.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v']
        
        if duration == 0 and is_video:
            duration = await get_video_duration(download_path)
            logger.info(f"Detected video duration: {duration}s")
        
        await download_msg.edit("**⚙️ Processing: Adding Metadata & Watermark...**")

        # ============================================
        # FIXED: ONE PASS FFMPEG - METADATA + WATERMARK
        # NO DOUBLE ENCODING - OPTIMIZED SIZE
        # ============================================
        
        # Find ZURAMBI font
        font_path = None
        font_paths_to_try = [
            "/usr/share/fonts/truetype/custom/zurambi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        ]
        for fp in font_paths_to_try:
            if os.path.exists(fp):
                font_path = fp
                logger.info(f"Using font: {font_path}")
                break
        
        if not font_path:
            font_path = "/helper/ZURAMBI.ttf"
            logger.warning(f"ZURAMBI font not found, using fallback: {font_path}")
        
        # ============================================
        # FIXED WATERMARK: ZURAMBI, WHITE, BOLD, SMALL, TOP-LEFT
        # Position: x=10, y=10 (stuck to top-left corner)
        # Size: 20 (small)
        # ============================================
        watermark_text = "ANIME ATLAS"
        drawtext_filter = (
            f"drawtext=text='{watermark_text}':"
            f"fontfile={font_path}:"
            f"fontsize=20:"
            f"fontcolor=white:"
            f"x=10:"
            f"y=10:"
            f"borderw=2:"
            f"bordercolor=black"
        )

        # Build FFmpeg command - ONE PASS ONLY
        cmd = ['ffmpeg', '-i', download_path]
        
        if is_video:
            # ============================================
            # FIXED: OPTIMIZED ENCODING - PREVENT FILE BLOAT
            # CRF 27: Good quality, smaller file size
            # Preset veryfast: Fast encoding
            # Audio: Copy (no re-encode)
            # ============================================
            cmd.extend([
                '-vf', drawtext_filter,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '27',
                '-c:a', 'copy',
                '-c:s', 'copy',
                '-map', '0',
                '-movflags', '+faststart',
                '-max_muxing_queue_size', '9999',
                # Metadata
                '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
                '-metadata', 'artist=Anime Atlas',
                '-metadata', 'author=Anime Atlas',
                '-metadata:s:v', 'title=Join Anime Atlas',
                '-metadata:s:a', 'title=Anime Atlas',
            ])
        else:
            # Non-video: just copy and add metadata
            cmd.extend([
                '-c', 'copy',
                '-map', '0',
                '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
                '-metadata', 'artist=Anime Atlas',
                '-metadata', 'author=Anime Atlas',
            ])
        
        cmd.extend(['-y', '-progress', 'pipe:2', output_path])

        logger.info(f"FFmpeg command: {' '.join(cmd)}")

        # Run FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        if is_video and duration > 0:
            progress_task = asyncio.create_task(
                monitor_ffmpeg_progress(process, download_msg, duration, "Processing")
            )
        
        await process.wait()
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode()
            logger.error(f"FFmpeg error (code {process.returncode}): {error_msg}")
            
            if not os.path.exists(output_path):
                if os.path.exists(download_path):
                    logger.warning("FFmpeg failed, using original file")
                    output_path = download_path
                else:
                    return await download_msg.edit(
                        f"**❌ Processing Failed**\n"
                        f"FFmpeg error code: {process.returncode}"
                    )

        logger.info(f"FFmpeg completed: {output_path}")
        
        final_file_size = os.path.getsize(output_path)
        logger.info(f"Original size: {humanbytes(file_size)}, Final size: {humanbytes(final_file_size)}")

        # Check file size limit
        if final_file_size > 2000 * 1024 * 1024:
            return await download_msg.edit(
                "**❌ File too large (>2GB)**\n"
                "Telegram has a file size limit of 2GB."
            )

        # Get caption and thumbnail
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

        # Upload
        await download_msg.edit("**📤 Uploading...**")
        
        try:
            upload_start = time.time()
            
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=output_path,
                    thumb=thumb_path,
                    caption=caption,
                    file_name=renamed_file_name,  # FIXED: Use clean filename
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
                    file_name=renamed_file_name,  # FIXED: Use clean filename
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
                    file_name=renamed_file_name,  # FIXED: Use clean filename
                    duration=int(duration),
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            
            await download_msg.delete()
            logger.info(f"Upload completed: {renamed_file_name}")
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            traceback.print_exc()
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            await download_msg.edit(f"**❌ Upload Failed:** {error_msg}")

    except Exception as e:
        logger.error(f"Processing error: {e}")
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
                    logger.info(f"Cleaned up: {path}")
                except Exception as e:
                    logger.error(f"Cleanup error for {path}: {e}")
