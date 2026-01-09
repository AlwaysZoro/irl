import re, os, time
id_pattern = re.compile(r'^.\d+$') 

class Config(object):
    # pyro client config
    API_ID    = os.environ.get("API_ID", "")
    API_HASH  = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 

    # database config
    DB_NAME = os.environ.get("DB_NAME","AshutoshGoswami24")     
    DB_URL  = os.environ.get("DB_URL","")
 
    # other configs
    BOT_UPTIME  = time.time()
    START_PIC   = os.environ.get("START_PIC", "https://graph.org/file/29a3acbbab9de5f45a5fe.jpg")
    ADMIN       = [int(admin) if id_pattern.search(admin) else admin for admin in os.environ.get('ADMIN', '8321397181').split()]
    
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003512136864"))
    PORT = int(os.environ.get("PORT", "8080"))
    
    # web response configuration     
    WEBHOOK = bool(os.environ.get("WEBHOOK", "False"))


class Txt(object):
    # part of text configuration
        
    START_TXT = """Hello {} 
    
➻ This Is An Advanced Rename Bot Modified for <b>Anime Atlas</b>.
    
➻ I will automatically rename files, add "ANIME ATLAS" watermark to videos, and set metadata.
    
➻ Use /tutorial Command To Know How To Use Me.

<b>⚡ Processing Capacity:</b> 2 files simultaneously
<b>📊 Queue System:</b> Enabled
<b>📦 Max File Size:</b> 4GB
"""
    
    FILE_NAME_TXT = """<b><u>SETUP AUTO RENAME FORMAT</u></b>

Use These Keywords To Setup Custom File Name

✔ `[episode]` :- To Replace Episode Number
✔ `[quality]` :- To Replace Video Resolution

<b>➻ Example :</b> <code> /autorename Naruto Shippuden S01[episode] [quality][Dual Audio]</code>

<b>➻ Your Current Auto Rename Format :</b> <code>{format_template}</code> """
    
    ABOUT_TXT = f"""<b>🤖 My Name :</b> Auto Rename Bot
<b>📝 Language :</b> <a href='https://python.org'>Python 3</a>
<b>📚 Library :</b> <a href='https://pyrogram.org'>Pyrogram 2.0</a>
<b>🚀 Server :</b> <a href='https://heroku.com'>Heroku</a>
<b>⚙️ Features :</b>
  • Auto Rename with Templates
  • Video Watermarking (ANIME ATLAS)
  • Metadata Management
  • Queue System (2 concurrent)
  • Real-time Progress Tracking
    
<b>♻️ Bot Modified For :</b> Anime Atlas"""

    
    THUMBNAIL_TXT = """<b><u>🖼️  HOW TO SET THUMBNAIL</u></b>
    
⦿ You Can Add Custom Thumbnail Simply By Sending A Photo To Me....
    
⦿ /viewthumb - Use This Command To See Your Thumbnail
⦿ /delthumb - Use This Command To Delete Your Thumbnail"""

    CAPTION_TXT = """<b><u>📝  HOW TO SET CAPTION</u></b>
    
⦿ /set_caption - Use This Command To Set Your Caption
⦿ /see_caption - Use This Command To See Your Caption
⦿ /del_caption - Use This Command To Delete Your Caption

<b>Available Variables:</b>
• {filename} - File name
• {filesize} - File size
• {duration} - Video duration"""

    PROGRESS_BAR = """<b>\n
╭━━━━━━━━━━━━━━━━━━━➣
┣⪼ 🗃️ Size: {1} | {2}
┣⪼ ⏱️ Done : {0}%
┣⪼ 🚀 Speed: {3}/s
┣⪼ ⏰ ETA: {4}
╰━━━━━━━━━━━━━━━━━➣ </b>"""
    
    
    DONATE_TXT = """<b>🥲 Thanks For Showing Interest In Donation! ❤️</b>
    
If You Like My Bots & Projects, You Can 🎁 Donate Me Any Amount From 10 Rs Upto Your Choice.
    
<b>My UPI - PandaWep@ybl</b> """
    
    HELP_TXT = """<b>Hey</b> {}
    
<b>⚙️ Bot Features:</b>
• Auto rename files with custom format
• Add watermark to videos
• Set custom metadata
• Queue system (max 2 concurrent)
• Real-time progress tracking

<b>📋 Commands:</b>
• /autorename - Set rename format
• /setmedia - Set output type (video/document/audio)
• /set_caption - Set custom caption
• /tutorial - View detailed guide

Join Anime Atlas for Support. """
