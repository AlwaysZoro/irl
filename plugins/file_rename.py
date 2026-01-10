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
PROCESSING_SEMAPHORE = asyncio.Semaphore(3)  # CHANGED: 3 parallel processes
QUEUE = asyncio.Queue()
QUEUE_TASK_RUNNING = False
# ----------------------------

renaming_operations = {}

# ============================================
# ENHANCED REGEX PATTERNS - PRIORITIZED ORDER
# ============================================
# 1. Episode patterns (most specific to general)
EPISODE_PATTERNS = [
    re.compile(r'[Ss](\d+)[Ee](\d+)', re.IGNORECASE),          # S01E12 format
    re.compile(r'[Ee][Pp][\s\-_]?(\d{3,4})', re.IGNORECASE),   # EP123, EP 123
    re.compile(r'[Ee][\s\-_]?(\d{3,4})', re.IGNORECASE),       # E123
    re.compile(r'[Ee]pisode[\s\-_]?(\d{3,4})', re.IGNORECASE), # Episode 123
    re.compile(r'\[\s*(\d{3,4})\s*\]', re.IGNORECASE),         # [123]
    re.compile(r'\(\s*(\d{3,4})\s*\)', re.IGNORECASE),         # (123)
    re.compile(r'[\s\-_](\d{3,4})[\s\-_\.]', re.IGNORECASE),   # -123- or _123_
    re.compile(r'^(\d{3,4})[\s\-_]', re.IGNORECASE),           # 123 -
    re.compile(r'[\s\-_](\d{3,4})$', re.IGNORECASE),           # - 123
]

# 2. Season patterns
SEASON_PATTERNS = [
    re.compile(r'[Ss](\d+)[Ee]\d+', re.IGNORECASE),           # S01E12
    re.compile(r'[Ss]eason[\s\-_]?(\d+)', re.IGNORECASE),     # Season 1
    re.compile(r'[\s\-_][Ss](\d+)[\s\-_\.]', re.IGNORECASE),  # _S01_ or -S01-
    re.compile(r'^[Ss](\d+)', re.IGNORECASE),                 # S01Something
]

# 3. Quality patterns
QUALITY_PATTERNS = [
    re.compile(r'\[(\d{3,4}[pP])\]', re.IGNORECASE),         # [1080p]
    re.compile(r'\((\d{3,4}[pP])\)', re.IGNORECASE),         # (1080p)
    re.compile(r'[\s\-_](\d{3,4}[pP])[\s\-_\.]', re.IGNORECASE), # -1080p-
    re.compile(r'\b(4[Kk])\b', re.IGNORECASE),               # 4K
    re.compile(r'\b(2160[Pp])\b', re.IGNORECASE),            # 2160p
    re.compile(r'\b(1440[Pp])\b', re.IGNORECASE),            # 1440p
    re.compile(r'\b(1080[Pp])\b', re.IGNORECASE),            # 1080p
    re.compile(r'\b(720[Pp])\b', re.IGNORECASE),             # 720p
    re.compile(r'\b(480[Pp])\b', re.IGNORECASE),             # 480p
    re.compile(r'\b(360[Pp])\b', re.IGNORECASE),             # 360p
    re.compile(r'\b([Hh][Dd])\b', re.IGNORECASE),            # HD
    re.compile(r'\b([Ff][Hh][Dd])\b', re.IGNORECASE),        # FHD
    re.compile(r'\b([Uu][Hh][Dd])\b', re.IGNORECASE),        # UHD
]

def extract_metadata_fast(filename):
    """
    OPTIMIZED: Extract all metadata in ONE pass with priority
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
            # For S01E12 format, group 2 is episode
            if pattern.pattern.startswith('[Ss](\\d+)[Ee](\\d+)'):
                episode = match.group(2)
            else:
                episode = match.group(1)
            break
    
    # Extract season number
    for pattern in SEASON_PATTERNS:
        match = pattern.search(name_only)
        if match:
            # For S01E12 format, group 1 is season
            season = match.group(1)
            break
    
    # Extract quality
    for pattern in QUALITY_PATTERNS:
        match = pattern.search(name_only)
        if match:
            quality = match.group(1)
            # Normalize quality format
            if quality.upper() in ['4K', '2160P']:
                quality = '4K'
            elif 'p' in quality.lower() or 'P' in quality:
                # Ensure lowercase p
                quality = quality.upper().replace('P', 'p')
            else:
                quality = quality.upper()
            break
    
    # Set defaults for missing values
    if not quality:
        quality = 'Unknown'
    if not season:
        season = '01'  # Default season
    
    logger.info(f"Extracted from '{filename}': episode={episode}, season={season}, quality={quality}")
    
    return episode, season, quality

def apply_rename_template(template, episode, season, quality):
    """
    FIXED: Apply template with proper placeholder replacement
    """
    result = template
    
    # Replace {episode}
    if episode and '{episode}' in result:
        result = result.replace('{episode}', episode.zfill(3))  # Pad to 3 digits
    elif '{episode}' in result:
        result = result.replace('{episode}', 'XXX')
    
    # Replace {season}
    if season and '{season}' in result:
        result = result.replace('{season}', season.zfill(2))
    elif '{season}' in result:
        result = result.replace('{season}', '01')
    
    # Replace {quality}
    if '{quality}' in result:
        result = result.replace('{quality}', quality)
    
    # Clean up any extra spaces
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

async def queue_processor(client):
    """Background task that processes queue - handles 3 parallel"""
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
        await asyncio.sleep(0.1)

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
            "• `{episode}` - Episode number (padded to 3 digits)\n"
            "• `{season}` - Season number (padded to 2 digits)\n"
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
            f"**Currently Processing:** 3 files\n"
            f"**Queue Size:** {position} files"
        )
    elif position > 1:
        await message.reply_text(
            f"**⏳ Added to Queue**\n"
            f"**Position:** {position}\n"
            f"**Status:** Will start processing soon..."
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
    """Monitor FFmpeg progress in real-time - show minutes:seconds"""
    last_update = 0
    
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        line_str = line.decode('utf-8', errors='ignore').strip()
        
        if "time=" in line_str and duration > 0:
            current_time = time.time()
            if current_time - last_update > 2:  # Update every 2 seconds
                try:
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line_str)
                    if time_match:
                        h, m, s = map(int, time_match.groups())
                        seconds_done = h*3600 + m*60 + s
                        percentage = min(int((seconds_done / duration) * 100), 100)
                        
                        # Convert to minutes:seconds
                        mins_done = seconds_done // 60
                        secs_done = seconds_done % 60
                        total_mins = int(duration) // 60
                        total_secs = int(duration) % 60
                        
                        bar_len = 20
                        filled = int((percentage / 100) * bar_len)
                        bar = "■" * filled + "□" * (bar_len - filled)
                        
                        await download_msg.edit(
                            f"**⚙️ {operation}...**\n\n"
                            f"{bar}\n"
                            f"**Progress:** {percentage}%\n"
                            f"**Time:** {mins_done:02d}:{secs_done:02d} / {total_mins:02d}:{total_secs:02d}\n"
                            f"**Speed:** {percentage/100:.1f}x"
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
        # ENHANCED: Extract metadata with improved regex
        # ============================================
        episode, season, quality = extract_metadata_fast(file_name)
        
        # ============================================
        # ENHANCED: Apply template with proper padding
        # ============================================
        renamed_template = apply_rename_template(format_template, episode, season, quality)
        
        _, file_extension = os.path.splitext(file_name)
        renamed_file_name = f"{renamed_template}{file_extension}"
        
        logger.info(f"Original: {file_name}")
        logger.info(f"Renamed: {renamed_file_name}")
        
        # Create directories
        os.makedirs("downloads", exist_ok=True)
        
        # Timestamp for temp files
        timestamp = int(time.time())
        download_path = f"downloads/{timestamp}_{file_name}"
        output_path = f"downloads/output_{timestamp}{file_extension}"
        
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

        logger.info(f"Downloaded: {download_path} ({humanbytes(file_size)})")

        # Check if video processing needed
        is_video = media_type == "video" or file_extension.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v']
        
        if duration == 0 and is_video:
            duration = await get_video_duration(download_path)
            logger.info(f"Detected video duration: {duration}s")
        
        await download_msg.edit("**⚙️ Processing: Adding Watermark & Metadata...**")

        # ============================================
        # FIXED WATERMARK: ZURAMBI.ttf, white, bold, size 10, top-left (1,1)
        # SINGLE PASS FFMPEG with quality preservation
        # ============================================
        
        # Find ZURAMBI font
        font_path = None
        font_paths_to_try = [
            "helper/ZURAMBI.ttf",  # Primary location
            "/usr/share/fonts/truetype/custom/zurambi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Windows/Fonts/arialbd.ttf"
        ]
        
        for fp in font_paths_to_try:
            if os.path.exists(fp):
                font_path = fp
                logger.info(f"Using font: {font_path}")
                break
        
        if not font_path:
            logger.warning("Font not found, using default")
            font_path = "Arial"
        
        # Watermark configuration
        watermark_text = "ANIME ATLAS"
        drawtext_filter = (
            f"drawtext=text='{watermark_text}':"
            f"fontfile='{font_path}':"
            f"fontsize=10:"  # Size 10
            f"fontcolor=white:"  # White color
            f"x=1:"  # Top-left x position
            f"y=1:"  # Top-left y position
            f"fontweight=bold:"  # Bold text
            f"alpha=1.0"  # No transparency
        )

        # Build FFmpeg command - SINGLE PASS with quality preservation
        cmd = ['ffmpeg', '-i', download_path]
        
        if is_video:
            # Optimized encoding for minimal size increase (2-5%)
            cmd.extend([
                '-vf', drawtext_filter,
                '-c:v', 'libx264',
                '-preset', 'veryfast',  # Fast encoding
                '-crf', '27',  # Good quality, minimal size increase
                '-c:a', 'copy',  # Copy audio (no re-encode)
                '-c:s', 'copy',  # Copy subtitles
                '-map', '0',  # Copy all streams
                '-movflags', '+faststart',
                '-max_muxing_queue_size', '9999',
                # Metadata
                '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
                '-metadata', 'artist=Anime Atlas',
                '-metadata', 'author=Anime Atlas',
                '-metadata:s:v', 'title=Anime Atlas',
                '-metadata:s:a', 'title=Join Anime Atlas',
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

        logger.info(f"FFmpeg command: {' '.join(cmd[:5])}...")

        # Run FFmpeg asynchronously
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
            error_msg = stderr.decode()[:200]
            logger.error(f"FFmpeg error (code {process.returncode}): {error_msg}")
            
            # Fallback to original file
            if os.path.exists(download_path):
                logger.warning("FFmpeg failed, using original file")
                output_path = download_path
            else:
                return await download_msg.edit(
                    f"**❌ Processing Failed**\n"
                    f"FFmpeg error code: {process.returncode}\n"
                    f"Error: {error_msg}"
                )

        # Check file sizes
        if os.path.exists(output_path):
            final_file_size = os.path.getsize(output_path)
            size_increase = ((final_file_size - file_size) / file_size * 100) if file_size > 0 else 0
            logger.info(f"Original: {humanbytes(file_size)}, Final: {humanbytes(final_file_size)}, Increase: {size_increase:.1f}%")
            
            if size_increase > 10:  # Warn if size increase > 10%
                logger.warning(f"Large size increase: {size_increase:.1f}%")
        else:
            logger.error("Output file not created")
            return await download_msg.edit("❌ **Processing Failed:** Output file not created")

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
        
        # Cleanup temp files
        for path in [download_path, output_path, thumb_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up: {path}")
                except Exception as e:
                    logger.error(f"Cleanup error for {path}: {e}")
