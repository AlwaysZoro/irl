from pyrogram import Client, filters
from pyrogram.enums import MessageMediaType
from pyrogram.types import InputMediaDocument, Message
from PIL import Image
from datetime import datetime
from helper.utils import progress_for_pyrogram, humanbytes, convert
from helper.database import AshutoshGoswami24
from config import Config
import os
import time
import re
import asyncio
import traceback
import math

# --- QUEUE & PARALLEL CONTROL ---
QUEUE = []
ACTIVE_TASKS = 0
MAX_CONCURRENT_TASKS = 2
QUEUE_LOCK = asyncio.Lock()
# --------------------------------

renaming_operations = {}

# Regex Patterns
pattern1 = re.compile(r"S(\d+)(?:E|EP)(\d+)")
pattern2 = re.compile(r"S(\d+)\s*(?:E|EP|-\s*EP)(\d+)")
pattern3 = re.compile(r"(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)")
pattern3_2 = re.compile(r"(?:\s*-\s*(\d+)\s*)")
pattern4 = re.compile(r"S(\d+)[^\d]*(\d+)", re.IGNORECASE)
patternX = re.compile(r"(\d+)")
pattern5 = re.compile(r"\b(?:.*?(\d{3,4}[^\dp]*p).*?|.*?(\d{3,4}p))\b", re.IGNORECASE)
pattern6 = re.compile(r"[([<{]?\s*4k\s*[)\]>}]?", re.IGNORECASE)
pattern7 = re.compile(r"[([<{]?\s*2k\s*[)\]>}]?", re.IGNORECASE)
pattern8 = re.compile(r"[([<{]?\s*HdRip\s*[)\]>}]?|\bHdRip\b", re.IGNORECASE)
pattern9 = re.compile(r"[([<{]?\s*4kX264\s*[)\]>}]?", re.IGNORECASE)
pattern10 = re.compile(r"[([<{]?\s*4kx265\s*[)\]>}]?", re.IGNORECASE)

def extract_quality(filename):
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
    match = re.search(patternX, filename)
    if match: return match.group(1)
    return None

# --- QUEUE HANDLER ---
async def check_queue_and_process(client):
    global ACTIVE_TASKS
    async with QUEUE_LOCK:
        if ACTIVE_TASKS >= MAX_CONCURRENT_TASKS or not QUEUE:
            return
        
        # Take next job
        message = QUEUE.pop(0)
        ACTIVE_TASKS += 1
    
    try:
        await start_processing(client, message)
    except Exception as e:
        print(f"Error in processing loop: {e}")
    finally:
        async with QUEUE_LOCK:
            ACTIVE_TASKS -= 1
        # Trigger next check
        asyncio.create_task(check_queue_and_process(client))

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    
    # Check settings first to avoid queueing invalid requests
    format_template = await AshutoshGoswami24.get_format_template(user_id)
    if not format_template:
        return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

    # Add to Queue
    async with QUEUE_LOCK:
        QUEUE.append(message)
        q_pos = len(QUEUE)
    
    if ACTIVE_TASKS < MAX_CONCURRENT_TASKS:
        asyncio.create_task(check_queue_and_process(client))
    else:
        await message.reply_text(f"**⏳ Added to Queue.**\n**Position:** {q_pos}\n**Status:** Waiting for available slot...")

# --- MAIN LOGIC ---
async def start_processing(client, message):
    user_id = message.from_user.id
    download_path = None
    renamed_path = None
    processed_path = None
    thumb_path = None
    download_msg = None
    
    try:
        format_template = await AshutoshGoswami24.get_format_template(user_id)
        media_preference = await AshutoshGoswami24.get_media_preference(user_id)

        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name
            file_size = message.document.file_size
            media_type = media_preference or "document"
        elif message.video:
            file_id = message.video.file_id
            file_name = f"{message.video.file_name}.mp4"
            file_size = message.video.file_size
            media_type = media_preference or "video"
        elif message.audio:
            file_id = message.audio.file_id
            file_name = f"{message.audio.file_name}.mp3"
            file_size = message.audio.file_size
            media_type = media_preference or "audio"
        else:
            return

        if file_id in renaming_operations:
            return
        renaming_operations[file_id] = datetime.now()

        # Rename Logic
        episode_number = extract_episode_number(file_name)
        if episode_number:
            format_template = format_template.replace("[episode]", "EP" + str(episode_number), 1)
            quality = extract_quality(file_name)
            format_template = format_template.replace("[quality]", quality)

        _, file_extension = os.path.splitext(file_name)
        renamed_file_name = f"{format_template}{file_extension}"
        
        renamed_path = f"downloads/{renamed_file_name}"
        processed_path = f"Metadata/{renamed_file_name}"
        
        os.makedirs(os.path.dirname(renamed_path), exist_ok=True)
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)

        download_msg = await message.reply_text("🚀 **Starting Download...**")

        # 1. DOWNLOAD
        download_path = await client.download_media(
            message,
            file_name=renamed_path,
            progress=progress_for_pyrogram,
            progress_args=("**📥 Downloading...**", download_msg, time.time()),
        )
        
        if not os.path.exists(renamed_path):
            return await download_msg.edit("❌ Download Failed.")

        # 2. PROCESSING (Fixing the Freeze)
        await download_msg.edit("**⚙️ Processing: Adding Metadata & Watermark...**")

        # Get Duration
        duration = 0
        try:
            if message.video: duration = message.video.duration
            elif message.audio: duration = message.audio.duration
            if duration == 0:
                # Probe duration if missing
                proc = await asyncio.create_subprocess_exec(
                    "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", download_path,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                duration = float(stdout.decode().strip())
        except:
            duration = 0

        # Build FFmpeg Command
        metadata_cmd = [
            '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
            '-metadata', 'artist=Anime Atlas',
            '-metadata', 'author=Anime Atlas'
        ]
        
        watermark_text = "ANIME ATLAS"
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        drawtext = f"drawtext=text='{watermark_text}':x=20:y=20:fontsize=24:fontcolor=white:fontfile={font_path}"
        
        is_video = media_type == "video" or file_extension.lower() in ['.mp4', '.mkv', '.avi']
        
        cmd = ['ffmpeg', '-i', renamed_path]
        if is_video:
            cmd.extend([
                '-vf', drawtext,
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', # Fast encoding
                '-c:a', 'copy', '-c:s', 'copy', '-map', '0'
            ])
        else:
            cmd.extend(['-c', 'copy', '-map', '0'])
        
        cmd.extend(metadata_cmd)
        cmd.extend(['-y', processed_path])

        # Execute Non-Blocking
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Monitor Progress
        start_time = time.time()
        last_update = 0
        
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            
            line_str = line.decode('utf-8', errors='ignore').strip()
            
            # Progress update logic
            if "time=" in line_str and duration > 0:
                now = time.time()
                if now - last_update > 5: # Update every 5s
                    try:
                        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})', line_str)
                        if time_match:
                            h, m, s = map(int, time_match.groups())
                            secs = h*3600 + m*60 + s
                            pct = int((secs / duration) * 100)
                            
                            # Simple Bar
                            done = int((pct/100)*15)
                            bar = "⬢"*done + "⬡"*(15-done)
                            
                            await download_msg.edit(
                                f"**⚙️ Processing...**\n\n{bar}\n**Done:** {pct}%"
                            )
                            last_update = now
                    except:
                        pass
        
        await process.wait()

        # Fallback if processing failed
        final_file_path = processed_path if os.path.exists(processed_path) else renamed_path

        # 3. UPLOAD
        await download_msg.edit("**📤 Uploading...**")
        
        c_caption = await AshutoshGoswami24.get_caption(message.chat.id)
        c_thumb = await AshutoshGoswami24.get_thumbnail(message.chat.id)

        caption = c_caption.format(filename=renamed_file_name, filesize=humanbytes(file_size), duration=convert(duration)) if c_caption else f"**{renamed_file_name}**"

        if c_thumb:
            thumb_path = await client.download_media(c_thumb)
            if thumb_path:
                Image.open(thumb_path).convert("RGB").resize((320, 320)).save(thumb_path, "JPEG")
        elif media_type == "video" and message.video.thumbs:
            thumb_path = await client.download_media(message.video.thumbs[0].file_id)

        try:
            if media_type == "document":
                await client.send_document(message.chat.id, document=final_file_path, thumb=thumb_path, caption=caption, progress=progress_for_pyrogram, progress_args=("**📤 Uploading...**", download_msg, time.time()))
            elif media_type == "video":
                await client.send_video(message.chat.id, video=final_file_path, caption=caption, thumb=thumb_path, duration=int(duration), progress=progress_for_pyrogram, progress_args=("**📤 Uploading...**", download_msg, time.time()))
            elif media_type == "audio":
                await client.send_audio(message.chat.id, audio=final_file_path, caption=caption, thumb=thumb_path, duration=int(duration), progress=progress_for_pyrogram, progress_args=("**📤 Uploading...**", download_msg, time.time()))
            
            await download_msg.delete()
        except Exception as e:
            await download_msg.edit(f"**❌ Upload Failed:** {e}")

    except Exception as e:
        print(f"Error: {e}")
        if download_msg:
            await download_msg.edit(f"**❌ Error:** {e}")
    finally:
        # Cleanup
        if file_id in renaming_operations: del renaming_operations[file_id]
        for p in [download_path, renamed_path, processed_path, thumb_path]:
            if p and os.path.exists(p): os.remove(p)
