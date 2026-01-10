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
PROCESSING_SEMAPHORE = asyncio.Semaphore(3)  # Fixed: 3 concurrent
QUEUE = asyncio.Queue()
QUEUE_TASK_RUNNING = False
# ----------------------------

renaming_operations = {}

# ============================================
# FIXED REGEX PATTERNS - ORDER MATTERS
# ============================================
EPISODE_PATTERNS = [
    re.compile(r'[\s\-_](\d{3,4})[\s\-_\[]', re.IGNORECASE),
    re.compile(r'^(\d{3,4})[\s\-_\[]', re.IGNORECASE),
    re.compile(r'[\]\)][\s\-_]?(\d{3,4})[\s\-_\[]', re.IGNORECASE),
    re.compile(r'[Ee][Pp]?[\s\-_]?(\d+)', re.IGNORECASE),
    re.compile(r'[Ee]pisode[\s\-_]?(\d+)', re.IGNORECASE),
    re.compile(r'S\d+[Ee](\d+)', re.IGNORECASE),
    re.compile(r'[\-_\s](\d{1,4})[\.\-_\s]*(?:v\d+)?$', re.IGNORECASE),
]

SEASON_PATTERNS = [
    re.compile(r'[Ss]eason[\s\-_]?(\d+)', re.IGNORECASE),
    re.compile(r'[Ss](\d+)[Ee]\d+', re.IGNORECASE),
    re.compile(r'[\s\-_][Ss](\d+)[\s\-_\[]', re.IGNORECASE),
]

QUALITY_PATTERNS = [
    re.compile(r'\[(\d{3,4}[pP])\]', re.IGNORECASE),
    re.compile(r'\((\d{3,4}[pP])\)', re.IGNORECASE),
    re.compile(r'[\s\-_](\d{3,4}[pP])[\s\-_\[]', re.IGNORECASE),
    re.compile(r'\b(\d{3,4}[pP])\b', re.IGNORECASE),
    re.compile(r'\b(4[Kk])\b', re.IGNORECASE),
    re.compile(r'\b(2[Kk])\b', re.IGNORECASE),
    re.compile(r'\b([Hh][Dd][Rr][Ii][Pp])\b', re.IGNORECASE),
    re.compile(r'\b(4[Kk][Xx]26[45])\b', re.IGNORECASE),
]

def extract_metadata_fast(filename):
    """Extract metadata from filename"""
    name_only = os.path.splitext(filename)[0]
    
    episode = None
    season = None
    quality = None
    
    # Extract episode
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(name_only)
        if match:
            episode = match.group(1)
            break
    
    # Extract season
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
            if quality.lower() in ['4k', '2k']:
                quality = quality.upper()
            elif 'p' in quality.lower():
                quality = quality.lower()
            elif 'hdrip' in quality.lower():
                quality = 'HDRIP'
            break
    
    # Defaults
    if not season:
        season = '1'
    if not quality:
        quality = 'Unknown'
    
    logger.info(f"Extracted: episode={episode}, season={season}, quality={quality}")
    return episode, season, quality

def apply_rename_template(template, episode, season, quality):
    """Apply template with placeholders"""
    result = template
    
    if '{episode}' in result:
        result = result.replace('{episode}', episode if episode else 'XX')
    
    if '{season}' in result:
        result = result.replace('{season}', season.zfill(2))
    
    if '{quality}' in result:
        result = result.replace('{quality}', quality)
    
    return result

def is_video_file(file_path):
    """Check if file is a video by extension"""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v', '.wmv', '.mpg', '.mpeg']
    ext = os.path.splitext(file_path)[1].lower()
    return ext in video_extensions

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
                        bar = "▰ " * filled + "▱" * (bar_len - filled)
                        
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

        # Extract metadata
        episode, season, quality = extract_metadata_fast(file_name)
        
        # Apply template
        renamed_template = apply_rename_template(format_template, episode, season, quality)
        
        _, file_extension = os.path.splitext(file_name)
        renamed_file_name = f"{renamed_template}{file_extension}"
        
        logger.info(f"Original: {file_name}")
        logger.info(f"Renamed: {renamed_file_name}")
        
        # Create directories
        os.makedirs("downloads", exist_ok=True)
        
        # File paths
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

        logger.info(f"Downloaded: {download_path} ({file_size} bytes)")

        # ============================================
        # CRITICAL FIX: DETECT VIDEO BY FILE EXTENSION
        # ============================================
        is_video = is_video_file(download_path)
        
        if is_video:
            logger.info(f"Video detected: {download_path}")
            
            # Get duration if not available
            if duration == 0:
                duration = await get_video_duration(download_path)
                logger.info(f"Detected video duration: {duration}s")
            
            await download_msg.edit("**⚙️ Processing: Adding Watermark & Metadata...**")

            # Find font
            font_path = None
            font_paths_to_try = [
                "helper/ZURAMBI.ttf",  # ✅ FIXED: Correct path
                "/usr/share/fonts/truetype/custom/zurambi.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]
            for fp in font_paths_to_try:
                if os.path.exists(fp):
                    font_path = fp
                    logger.info(f"Using font: {font_path}")
                    break
            
            if not font_path:
                logger.warning("No font found, using default")
                font_path = "Arial"  # Fallback
            
            # ============================================
            # WATERMARK: Small, top-left, white, bold
            # ============================================
            watermark_text = "ANIME ATLAS"
            drawtext_filter = (
                f"drawtext=text='{watermark_text}':"
                f"fontfile={font_path}:"
                f"fontsize=10:"
                f"fontcolor=white:"
                f"x=1:"
                f"y=1"
            )

            # ============================================
            # FFmpeg Command: CRF 23 for quality
            # ============================================
            cmd = [
                'ffmpeg', '-i', download_path,
                '-vf', drawtext_filter,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',  # ✅ FIXED: Better quality
                '-c:a', 'copy',
                '-c:s', 'copy',
                '-map', '0',
                '-movflags', '+faststart',
                '-max_muxing_queue_size', '9999',
                '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
                '-metadata', 'artist=Anime Atlas',
                '-metadata', 'author=Anime Atlas',
                '-metadata:s:v', 'title=Join Anime Atlas',
                '-metadata:s:a', 'title=Anime Atlas',
                '-y', '-progress', 'pipe:2', output_path
            ]

            logger.info(f"FFmpeg command: {' '.join(cmd)}")

            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            if duration > 0:
                progress_task = asyncio.create_task(
                    monitor_ffmpeg_progress(process, download_msg, duration, "Processing")
                )
            
            await process.wait()
            
            # ============================================
            # CRITICAL FIX: GUARANTEE PROCESSED FILE EXISTS
            # ============================================
            if process.returncode != 0 or not os.path.exists(output_path):
                stderr = await process.stderr.read()
                error_msg = stderr.decode()
                logger.error(f"FFmpeg failed (code {process.returncode}): {error_msg}")
                
                return await download_msg.edit(
                    f"**❌ Video Processing Failed**\n"
                    f"FFmpeg error. Please contact support."
                )

            logger.info(f"FFmpeg SUCCESS: {output_path}")
            
            # ✅ GUARANTEE: output_path is the processed file
            final_file_size = os.path.getsize(output_path)
            logger.info(f"Original: {humanbytes(file_size)}, Processed: {humanbytes(final_file_size)}")
            
        else:
            # ============================================
            # NON-VIDEO: Just copy file (no watermark)
            # ============================================
            logger.info(f"Non-video file: {download_path}")
            
            await download_msg.edit("**⚙️ Processing: Adding Metadata...**")
            
            cmd = [
                'ffmpeg', '-i', download_path,
                '-c', 'copy',
                '-map', '0',
                '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
                '-metadata', 'artist=Anime Atlas',
                '-metadata', 'author=Anime Atlas',
                '-y', output_path
            ]
            
            logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            
            if process.returncode != 0 or not os.path.exists(output_path):
                logger.warning("FFmpeg failed for non-video, using original")
                output_path = download_path
            
            final_file_size = os.path.getsize(output_path)

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

        # ============================================
        # CRITICAL: UPLOAD PROCESSED FILE (output_path)
        # ============================================
        await download_msg.edit("**📤 Uploading...**")
        
        logger.info(f"UPLOADING FILE: {output_path}")  # ✅ Verification log
        
        try:
            upload_start = time.time()
            
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=output_path,  # ✅ PROCESSED FILE
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
                    video=output_path,  # ✅ PROCESSED FILE
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
                    audio=output_path,  # ✅ PROCESSED FILE
                    caption=caption,
                    thumb=thumb_path,
                    file_name=renamed_file_name,
                    duration=int(duration),
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            
            await download_msg.delete()
            logger.info(f"✅ Upload SUCCESS: {renamed_file_name}")
            
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
