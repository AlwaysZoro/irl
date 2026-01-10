from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InputMediaDocument, Message
from PIL import Image
from datetime import datetime
from helper.utils import progress_for_pyrogram, humanbytes, convert, format_time
from helper.database import ZoroBhaiya
from config import Config
import os
import time
import re
import asyncio
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Queue system
PROCESSING_SEMAPHORE = asyncio.Semaphore(3)
renaming_operations = {}

# Metadata extraction patterns
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
]

def extract_metadata_fast(filename):
    """Extract episode, season, quality from filename"""
    name_only = os.path.splitext(filename)[0]
    
    episode = None
    season = None
    quality = None
    
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(name_only)
        if match:
            episode = match.group(1)
            break
    
    for pattern in SEASON_PATTERNS:
        match = pattern.search(name_only)
        if match:
            season = match.group(1)
            break
    
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
    
    if not season:
        season = '1'
    if not quality:
        quality = 'Unknown'
    
    return episode, season, quality

def apply_rename_template(template, episode, season, quality):
    """Apply rename template with placeholders"""
    result = template
    
    if '{episode}' in result:
        result = result.replace('{episode}', episode if episode else 'XX')
    
    if '{season}' in result:
        result = result.replace('{season}', season.zfill(2))
    
    if '{quality}' in result:
        result = result.replace('{quality}', quality)
    
    return result

def is_video_file(file_path):
    """Check if file is video by extension"""
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.m4v', '.wmv', '.mpg', '.mpeg']
    ext = os.path.splitext(file_path)[1].lower()
    return ext in video_extensions

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    """Main handler for incoming files - Direct processing without queue"""
    
    user_id = message.from_user.id
    
    try:
        format_template = await ZoroBhaiya.get_format_template(user_id)
    except Exception:
        format_template = None
    
    if not format_template or not format_template.strip():
        return await message.reply_text(
            "**❌ Please Set An Auto Rename Format First!**\n\n"
            "**📝 Use:** `/autorename [format]`\n\n"
            "**📌 Example:**\n"
            "`/autorename [@Anime_Atlas] {episode} - One Piece [{quality}] [Sub]`\n\n"
            "**📤 Available Placeholders:**\n"
            "• `{episode}` - Episode number\n"
            "• `{season}` - Season number\n"
            "• `{quality}` - Video quality\n\n"
            "**💡 Tip:** Use /tutorial for detailed guide!"
        )

    # Check semaphore availability
    if PROCESSING_SEMAPHORE.locked() and PROCESSING_SEMAPHORE._value == 0:
        return await message.reply_text(
            f"**⏳ Processing Queue Full**\n\n"
            f"**🔄 Currently Processing:** 3 files\n"
            f"**⚙️ Status:** All slots occupied\n\n"
            f"Please wait a moment and try again!"
        )
    
    # Process directly with semaphore
    asyncio.create_task(start_processing(client, message))

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
    except Exception:
        return 0

async def monitor_ffmpeg_progress(process, status_msg, duration, operation="Processing"):
    """Monitor FFmpeg progress with MM:SS format"""
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
                        
                        filled = int((percentage / 100) * 20)
                        bar = '▰' * filled + '▱' * (20 - filled)
                        
                        time_done = format_time(seconds_done)
                        time_total = format_time(duration)
                        
                        await status_msg.edit_text(
                            f"**⚙️ {operation}**\n\n"
                            f"{bar}\n\n"
                            f"**📊 Progress:** {percentage}%\n"
                            f"**⏱️ Time:** {time_done} / {time_total}"
                        )
                        last_update = current_time
                except Exception:
                    pass

async def start_processing(client, message):
    """Main processing function"""
    async with PROCESSING_SEMAPHORE:
        user_id = message.from_user.id
        download_path = None
        output_path = None
        thumb_path = None
        status_msg = None
        
        try:
            # Get user settings
            try:
                format_template = await ZoroBhaiya.get_format_template(user_id)
            except Exception:
                format_template = None
            
            if not format_template or not format_template.strip():
                return await message.reply_text(
                    "**❌ Error:** Format template not found.\n"
                    "Please set it again with `/autorename`"
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

            # Extract metadata and apply template
            episode, season, quality = extract_metadata_fast(file_name)
            renamed_template = apply_rename_template(format_template, episode, season, quality)
            _, file_extension = os.path.splitext(file_name)
            renamed_file_name = f"{renamed_template}{file_extension}"
            
            os.makedirs("downloads", exist_ok=True)
            
            timestamp = int(time.time())
            download_path = f"downloads/{timestamp}_{file_name}"
            output_path = f"downloads/output_{timestamp}{file_extension}"
            
            # STEP 1: DOWNLOAD
            status_msg = await message.reply_text("**📥 Downloading your file...**\n\nPlease wait...")

            download_start = time.time()
            await client.download_media(
                message,
                file_name=download_path,
                progress=progress_for_pyrogram,
                progress_args=("**📥 Downloading...**", status_msg, download_start),
            )
            
            if not os.path.exists(download_path):
                return await status_msg.edit_text("**❌ Download Failed**\n\nFile not found after download.")

            # STEP 2: PROCESSING
            is_video = is_video_file(download_path)
            
            if is_video:
                if duration == 0:
                    duration = await get_video_duration(download_path)
                
                await status_msg.edit_text("**⚙️ Processing metadata and watermark...**\n\nThis may take a moment...")

                font_path = "helper/ZURAMBI.ttf"
                if not os.path.exists(font_path):
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                
                if not os.path.exists(font_path):
                    font_path = "Arial"
                
                watermark_text = "ANIME ATLAS"
                drawtext_filter = (
                    f"drawtext=text='{watermark_text}':"
                    f"fontfile={font_path}:"
                    f"fontsize=14:"
                    f"fontcolor=white:"
                    f"x=3:"
                    f"y=3"
                )

                cmd = [
                    'ffmpeg', '-i', download_path,
                    '-vf', drawtext_filter,
                    '-c:v', 'libx264',
                    '-preset', 'veryfast',
                    '-crf', '23',
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

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                if duration > 0:
                    asyncio.create_task(
                        monitor_ffmpeg_progress(process, status_msg, duration, "Processing")
                    )
                
                await process.wait()
                
                if process.returncode != 0 or not os.path.exists(output_path):
                    return await status_msg.edit_text(
                        "**❌ Video Processing Failed**\n\n"
                        "FFmpeg error occurred. Please contact support."
                    )

                final_file_size = os.path.getsize(output_path)
                
            else:
                await status_msg.edit_text("**⚙️ Processing metadata...**\n\nAlmost done...")
                
                cmd = [
                    'ffmpeg', '-i', download_path,
                    '-c', 'copy',
                    '-map', '0',
                    '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
                    '-metadata', 'artist=Anime Atlas',
                    '-metadata', 'author=Anime Atlas',
                    '-y', output_path
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.wait()
                
                if process.returncode != 0 or not os.path.exists(output_path):
                    output_path = download_path
                
                final_file_size = os.path.getsize(output_path)

            if final_file_size > 2000 * 1024 * 1024:
                return await status_msg.edit_text(
                    "**❌ File Too Large**\n\n"
                    "The processed file exceeds Telegram's 2GB limit.\n"
                    "Please try with a smaller file."
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
                else f"**📁 {renamed_file_name}**\n\n📦 Size: {humanbytes(final_file_size)}"
            )

            # Prepare thumbnail
            if c_thumb:
                try:
                    thumb_path = await client.download_media(c_thumb)
                    if thumb_path:
                        img = Image.open(thumb_path).convert("RGB")
                        img = img.resize((320, 320))
                        img.save(thumb_path, "JPEG")
                except Exception:
                    thumb_path = None
            elif is_video and message.video and message.video.thumbs:
                try:
                    thumb_path = await client.download_media(message.video.thumbs[0].file_id)
                except Exception:
                    thumb_path = None

            # STEP 3: UPLOAD
            await status_msg.edit_text("**📤 Uploading to Telegram...**\n\nFinalizing...")
            
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
                        progress_args=("**📤 Uploading...**", status_msg, upload_start),
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
                        progress_args=("**📤 Uploading...**", status_msg, upload_start),
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
                        progress_args=("**📤 Uploading...**", status_msg, upload_start),
                    )
                
                try:
                    await status_msg.delete()
                except:
                    pass
                
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 150:
                    error_msg = error_msg[:150] + "..."
                await status_msg.edit_text(
                    f"**❌ Upload Failed**\n\n"
                    f"Error: {error_msg}\n\n"
                    f"Please try again or contact support."
                )

        except Exception as e:
            if status_msg:
                try:
                    error_msg = str(e)
                    if len(error_msg) > 150:
                        error_msg = error_msg[:150] + "..."
                    await status_msg.edit_text(
                        f"**❌ An Error Occurred**\n\n"
                        f"Error: {error_msg}\n\n"
                        f"Please try again or contact @Sanji_Fr"
                    )
                except:
                    pass

        finally:
            if file_id in renaming_operations:
                del renaming_operations[file_id]
            
            for path in [download_path, output_path, thumb_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
