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
PROCESSING_SEMAPHORE = asyncio.Semaphore(2)  # Max 2 concurrent
QUEUE = asyncio.Queue()
QUEUE_TASK_RUNNING = False
# ----------------------------

renaming_operations = {}

# Pattern 1: S01E02 or S01EP02
pattern1 = re.compile(r"S(\d+)(?:E|EP)(\d+)", re.IGNORECASE)
# Pattern 2: S01 E02 or S01 EP02 or S01 - E01 or S01 - EP02
pattern2 = re.compile(r"S(\d+)\s*(?:E|EP|-\s*EP)(\d+)", re.IGNORECASE)
# Pattern 3: Episode Number After "E" or "EP"
pattern3 = re.compile(r"(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)", re.IGNORECASE)
# Pattern 3_2: episode number after - [hyphen]
pattern3_2 = re.compile(r"(?:\s*-\s*(\d+)\s*)")
# Pattern 4: S2 09 ex.
pattern4 = re.compile(r"S(\d+)[^\d]*(\d+)", re.IGNORECASE)
# QUALITY PATTERNS
pattern5 = re.compile(r"\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b", re.IGNORECASE)
pattern6 = re.compile(r"[([<{]?\s*4k\s*[)\]>}]?", re.IGNORECASE)
pattern7 = re.compile(r"[([<{]?\s*2k\s*[)\]>}]?", re.IGNORECASE)
pattern8 = re.compile(r"[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b", re.IGNORECASE)
pattern9 = re.compile(r"[([<{]?\s*4kX264\s*[)\]>}]?", re.IGNORECASE)
pattern10 = re.compile(r"[([<{]?\s*4kx265\s*[)\]>}]?", re.IGNORECASE)

def extract_quality(filename):
    """Extract quality from filename"""
    match5 = re.search(pattern5, filename)
    if match5: return match5.group(1) or match5.group(2)
    match6 = re.search(pattern6, filename)
    if match6: return "4k"
    match7 = re.search(pattern7, filename)
    if match7: return "2k"
    match8 = re.search(pattern8, filename)
    if match8: return "HdRip"
    match9 = re.search(pattern9, filename)
    if match9: return "4kX264"
    match10 = re.search(pattern10, filename)
    if match10: return "4kx265"
    return "Unknown"

def extract_episode_number(filename):
    """Extract episode number from filename"""
    match = re.search(pattern1, filename)
    if match: return match.group(2)
    match = re.search(pattern2, filename)
    if match: return match.group(2)
    match = re.search(pattern3, filename)
    if match: return match.group(1)
    match = re.search(pattern3_2, filename)
    if match: return match.group(1)
    match = re.search(pattern4, filename)
    if match: return match.group(2)
    return None

def extract_season_number(filename):
    """Extract season number from filename"""
    match = re.search(pattern1, filename)
    if match: return match.group(1)
    match = re.search(pattern2, filename)
    if match: return match.group(1)
    match = re.search(pattern4, filename)
    if match: return match.group(1)
    return None

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
    format_template = await ZoroBhaiya.get_format_template(user_id)
    if not format_template:
        return await message.reply_text(
            "**Please Set An Auto Rename Format First Using /autorename**\n\n"
            "Example: `/autorename S{season}E{episode} - [{quality}]`"
        )

    # Start queue processor if not running
    if not QUEUE_TASK_RUNNING:
        asyncio.create_task(queue_processor(client))
    
    # Add to queue
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
            if current_time - last_update > 3:  # Update every 3 seconds
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
    renamed_path = None
    processed_path = None
    thumb_path = None
    download_msg = None
    
    try:
        format_template = await ZoroBhaiya.get_format_template(user_id)
        media_preference = await ZoroBhaiya.get_media_preference(user_id)

        # File Type & ID Logic
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

        # Check if already processing
        if file_id in renaming_operations:
            return

        renaming_operations[file_id] = datetime.now()

        # Extract metadata from filename
        episode_number = extract_episode_number(file_name)
        season_number = extract_season_number(file_name)
        quality = extract_quality(file_name)

        # Replace placeholders in template
        renamed_template = format_template
        if episode_number:
            renamed_template = renamed_template.replace("{episode}", str(episode_number))
        if season_number:
            renamed_template = renamed_template.replace("{season}", str(season_number))
        renamed_template = renamed_template.replace("{quality}", quality)

        _, file_extension = os.path.splitext(file_name)
        renamed_file_name = f"{renamed_template}{file_extension}"
        
        # Create unique paths
        timestamp = int(time.time())
        renamed_path = f"downloads/{timestamp}_{renamed_file_name}"
        processed_path = f"Metadata/{timestamp}_{renamed_file_name}"
        
        os.makedirs("downloads", exist_ok=True)
        os.makedirs("Metadata", exist_ok=True)

        download_msg = await message.reply_text("🚀 **Starting Download...**")

        # DOWNLOAD with progress
        download_path = await client.download_media(
            message,
            file_name=renamed_path,
            progress=progress_for_pyrogram,
            progress_args=("**📥 Downloading...**", download_msg, time.time()),
        )
        
        if not os.path.exists(renamed_path):
            logger.error(f"Download failed: File not found at {renamed_path}")
            return await download_msg.edit("❌ **Download Failed:** File not found.")

        logger.info(f"Downloaded: {renamed_path} ({file_size} bytes)")

        # --- FFMPEG PROCESSING ---
        is_video = media_type == "video" or file_extension.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v']
        
        # Get actual duration from file if needed
        if duration == 0 and is_video:
            duration = await get_video_duration(renamed_path)
            logger.info(f"Detected video duration: {duration}s")
        
        await download_msg.edit("**⚙️ Processing: Adding Metadata & Watermark...**")

        # Metadata commands
        metadata_cmd = [
            '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
            '-metadata', 'artist=Anime Atlas',
            '-metadata', 'author=Anime Atlas',
            '-metadata:s:v', 'title=Join Anime Atlas',
            '-metadata:s:a', 'title=Anime Atlas',
            '-metadata:s:s', 'title=Anime Atlas'
        ]

        # Watermark setup
        watermark_text = "ANIME ATLAS"
        
        # Try to use ZURAMBI font, fallback to DejaVu
        font_path = "/tmp/zurambi.ttf"
        if not os.path.exists(font_path):
            font_paths_to_try = [
                "/usr/share/fonts/truetype/custom/zurambi.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ]
            for fp in font_paths_to_try:
                if os.path.exists(fp):
                    font_path = fp
                    break
        
        # Watermark filter with white color and bold style
        drawtext_filter = (
            f"drawtext=text='{watermark_text}':"
            f"x=20:y=20:"
            f"fontsize=24:"
            f"fontcolor=white:"
            f"fontfile={font_path}:"
            f"borderw=2:"
            f"bordercolor=black"
        )

        # Build FFmpeg command
        cmd = ['ffmpeg', '-i', renamed_path]
        
        if is_video:
            # Video with watermark
            cmd.extend([
                '-vf', drawtext_filter,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '23',
                '-c:a', 'copy',
                '-c:s', 'copy',
                '-map', '0',
                '-max_muxing_queue_size', '9999'
            ])
        else:
            # Non-video, just copy streams
            cmd.extend(['-c', 'copy', '-map', '0'])

        cmd.extend(metadata_cmd)
        cmd.extend(['-y', '-progress', 'pipe:2', processed_path])

        logger.info(f"FFmpeg command: {' '.join(cmd)}")

        # Run FFmpeg asynchronously with progress monitoring
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Monitor progress in background
        if is_video and duration > 0:
            progress_task = asyncio.create_task(
                monitor_ffmpeg_progress(process, download_msg, duration, "Processing")
            )
        
        await process.wait()
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode()
            logger.error(f"FFmpeg error (code {process.returncode}): {error_msg}")
            
            if not os.path.exists(processed_path):
                # Try to use original file if processing failed
                if os.path.exists(renamed_path):
                    logger.warning("FFmpeg failed, using original file")
                    processed_path = renamed_path
                else:
                    return await download_msg.edit(
                        f"**❌ Processing Failed**\n"
                        f"FFmpeg error code: {process.returncode}\n"
                        f"Check logs for details."
                    )

        logger.info(f"FFmpeg completed: {processed_path}")

        # UPLOAD with progress
        await download_msg.edit("**📤 Uploading...**")
        
        final_file_path = processed_path if os.path.exists(processed_path) else renamed_path
        final_file_size = os.path.getsize(final_file_path)

        # Check file size limit (2GB safe limit for Telegram)
        if final_file_size > 2000 * 1024 * 1024:
            return await download_msg.edit(
                "**❌ File too large (>2GB)**\n"
                "Telegram has a file size limit of 2GB.\n"
                "Please compress the file and try again."
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

        # Upload based on media type
        try:
            upload_start = time.time()
            
            if media_type == "document":
                await client.send_document(
                    message.chat.id,
                    document=final_file_path,
                    thumb=thumb_path,
                    caption=caption,
                    force_document=True,
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            elif media_type == "video":
                await client.send_video(
                    message.chat.id,
                    video=final_file_path,
                    caption=caption,
                    thumb=thumb_path,
                    duration=int(duration),
                    supports_streaming=True,
                    progress=progress_for_pyrogram,
                    progress_args=("**📤 Uploading...**", download_msg, upload_start),
                )
            elif media_type == "audio":
                await client.send_audio(
                    message.chat.id,
                    audio=final_file_path,
                    caption=caption,
                    thumb=thumb_path,
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
        # Cleanup
        if file_id in renaming_operations:
            del renaming_operations[file_id]
        
        # Clean up all temporary files
        for path in [download_path, renamed_path, processed_path, thumb_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Cleaned up: {path}")
                except Exception as e:
                    logger.error(f"Cleanup error for {path}: {e}")
