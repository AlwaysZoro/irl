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

renaming_operations = {}

# Pattern 1: S01E02 or S01EP02
pattern1 = re.compile(r"S(\d+)(?:E|EP)(\d+)")
# Pattern 2: S01 E02 or S01 EP02 or S01 - E01 or S01 - EP02
pattern2 = re.compile(r"S(\d+)\s*(?:E|EP|-\s*EP)(\d+)")
# Pattern 3: Episode Number After "E" or "EP"
pattern3 = re.compile(r"(?:[([<{]?\s*(?:E|EP)\s*(\d+)\s*[)\]>}]?)")
# Pattern 3_2: episode number after - [hyphen]
pattern3_2 = re.compile(r"(?:\s*-\s*(\d+)\s*)")
# Pattern 4: S2 09 ex.
pattern4 = re.compile(r"S(\d+)[^\d]*(\d+)", re.IGNORECASE)
# Pattern X: Standalone Episode Number
patternX = re.compile(r"(\d+)")
# QUALITY PATTERNS
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

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def auto_rename_files(client, message):
    user_id = message.from_user.id
    
    # Initialize paths for safe cleanup
    download_path = None
    renamed_path = None
    processed_path = None
    thumb_path = None
    
    try:
        format_template = await AshutoshGoswami24.get_format_template(user_id)
        media_preference = await AshutoshGoswami24.get_media_preference(user_id)

        if not format_template:
            return await message.reply_text("Please Set An Auto Rename Format First Using /autorename")

        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name
            media_type = media_preference or "document"
        elif message.video:
            file_id = message.video.file_id
            file_name = f"{message.video.file_name}.mp4"
            media_type = media_preference or "video"
        elif message.audio:
            file_id = message.audio.file_id
            file_name = f"{message.audio.file_name}.mp3"
            media_type = media_preference or "audio"
        else:
            return await message.reply_text("Unsupported File Type")

        if file_id in renaming_operations:
            elapsed_time = (datetime.now() - renaming_operations[file_id]).seconds
            if elapsed_time < 10:
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
        
        # Setup Directories
        renamed_path = f"downloads/{renamed_file_name}"
        processed_path = f"Metadata/{renamed_file_name}" # Used for Final Output (Metadata + Watermark)
        
        os.makedirs(os.path.dirname(renamed_path), exist_ok=True)
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)

        download_msg = await message.reply_text("Downloading the file...")

        # DOWNLOAD
        download_path = await client.download_media(
            message,
            file_name=renamed_path,
            progress=progress_for_pyrogram,
            progress_args=("Download Started...", download_msg, time.time()),
        )
        
        # Rename file locally to match target name (helps with ffmpeg mapping sometimes)
        # Note: download_media already saves it to renamed_path, but strictly ensuring
        if not os.path.exists(renamed_path):
            return await download_msg.edit("Download failed: File not found.")

        await download_msg.edit("Processing: Adding Metadata & Watermark...")

        # FFMPEG PROCESSING (Metadata + Watermark)
        # Hardcoded Metadata
        metadata_cmd = [
            '-metadata', 'title=Join Anime Atlas on Telegram For More Anime',
            '-metadata', 'artist=Anime Atlas',
            '-metadata', 'author=Anime Atlas',
            '-metadata:s:v', 'title=Join Anime Atlas',
            '-metadata:s:a', 'title=Anime Atlas',
            '-metadata:s:s', 'title=Anime Atlas'
        ]

        # Watermark Settings
        watermark_text = "ANIME ATLAS"
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        drawtext_filter = f"drawtext=text='{watermark_text}':x=20:y=20:fontsize=28:fontcolor=white:fontfile={font_path}"

        # Determine if we should watermark (Video files only)
        is_video = media_type == "video" or file_extension.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
        
        cmd = ['ffmpeg', '-i', renamed_path]
        
        if is_video:
            # Re-encode video for watermark, copy audio/subs
            cmd.extend([
                '-vf', drawtext_filter,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '25', # Efficient re-encoding
                '-c:a', 'copy', '-c:s', 'copy',
                '-map', '0'
            ])
        else:
            # Just metadata for Audio/Other, Copy all streams
            cmd.extend([
                '-c', 'copy',
                '-map', '0'
            ])

        # Add Metadata and Output
        cmd.extend(metadata_cmd)
        cmd.extend(['-y', '-loglevel', 'error', processed_path])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_log = stderr.decode()
            await download_msg.edit(f"**FFmpeg Error:**\n`{error_log[:800]}`")
            if Config.LOG_CHANNEL:
                await client.send_message(Config.LOG_CHANNEL, f"**FFmpeg Error for {user_id}:**\n`{error_log}`")
            return

        # Prepare Upload
        await download_msg.edit("Uploading the file...")
        
        final_file_path = processed_path if os.path.exists(processed_path) else renamed_path

        c_caption = await AshutoshGoswami24.get_caption(message.chat.id)
        c_thumb = await AshutoshGoswami24.get_thumbnail(message.chat.id)

        caption = (
            c_caption.format(
                filename=renamed_file_name,
                filesize=humanbytes(message.document.file_size if message.document else message.video.file_size if message.video else message.audio.file_size),
                duration=convert(0),
            )
            if c_caption
            else f"**{renamed_file_name}**"
        )

        if c_thumb:
            thumb_path = await client.download_media(c_thumb)
            if thumb_path:
                img = Image.open(thumb_path).convert("RGB")
                img = img.resize((320, 320))
                img.save(thumb_path, "JPEG")
        elif media_type == "video" and message.video.thumbs:
            thumb_path = await client.download_media(message.video.thumbs[0].file_id)

        # Upload
        if media_type == "document":
            await client.send_document(
                message.chat.id,
                document=final_file_path,
                thumb=thumb_path,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=("Upload Started...", download_msg, time.time()),
            )
        elif media_type == "video":
            await client.send_video(
                message.chat.id,
                video=final_file_path,
                caption=caption,
                thumb=thumb_path,
                duration=0, # Let Telegram calc or extract earlier if needed
                progress=progress_for_pyrogram,
                progress_args=("Upload Started...", download_msg, time.time()),
            )
        elif media_type == "audio":
            await client.send_audio(
                message.chat.id,
                audio=final_file_path,
                caption=caption,
                thumb=thumb_path,
                duration=0,
                progress=progress_for_pyrogram,
                progress_args=("Upload Started...", download_msg, time.time()),
            )
            
        await download_msg.delete()

    except Exception as e:
        trace_error = traceback.format_exc()
        await message.reply_text(f"**An error occurred:** {str(e)}")
        if Config.LOG_CHANNEL:
             await client.send_message(Config.LOG_CHANNEL, f"**Crash Report:**\nUser: {user_id}\nError: `{trace_error}`")
        print(trace_error)

    finally:
        # Cleanup
        if file_id in renaming_operations:
            del renaming_operations[file_id]
        if download_path and os.path.exists(download_path):
            os.remove(download_path)
        if renamed_path and os.path.exists(renamed_path):
            os.remove(renamed_path)
        if processed_path and os.path.exists(processed_path):
            os.remove(processed_path)
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
