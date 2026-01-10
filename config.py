import re, os, time
id_pattern = re.compile(r'^.\d+$') 

class Config(object):
    # pyro client config
    API_ID    = os.environ.get("API_ID", "")
    API_HASH  = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "") 

    # database config
    DB_NAME = os.environ.get("DB_NAME","AutoRename")     
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
        
    START_TXT = """<b>👋 Hello {} 
    
✨ This Is An Advanced Auto Rename Bot Modified for <b>Anime Atlas</b>.

🎯 <u>What I Can Do:</u>
• Automatically rename files with custom templates
• Add "ANIME ATLAS" watermark to videos
• Embed custom metadata
• Support files up to 4GB

📊 <b>Processing Capacity:</b> 3 files simultaneously
📦 <b>Max File Size:</b> 4GB

Click Help button below to get started! 👇</b>
"""
    
    FILE_NAME_TXT = """<b><u>🎬 SETUP AUTO RENAME FORMAT</u></b>

Use these keywords to create your custom file name:

✅ <code>{episode}</code> - Episode Number
✅ <code>{quality}</code> - Video Resolution
✅ <code>{season}</code> - Season Number

<b>📝 Example:</b> 
<code>/autorename Naruto Shippuden S{season}E{episode} [{quality}] [Dual]</code>

<b>🔧 Your Current Format:</b> 
<code>{format_template}</code>"""
    
    ABOUT_TXT = """<b>🤖 Bot Information</b>

<b>📛 Name:</b> Auto Rename Bot
<b>🔢 Version:</b> 2.0 Advanced
<b>📝 Language:</b> <a href='https://python.org'>Python 3</a>
<b>📚 Library:</b> <a href='https://pyrogram.org'>Pyrogram 2.0</a>

<b>⚙️ Features:</b>
  ✅ Auto Rename with Templates
  ✅ Video Watermarking (ANIME ATLAS)
  ✅ Custom Metadata Management
  ✅ Queue System (3 concurrent)
  ✅ Real-time Progress Tracking
  ✅ Support up to 4GB Files
    
<b>♻️ Modified For:</b> Anime Atlas
<b>👨‍💻 Developer:</b> @AshuSupport"""

    
    THUMBNAIL_TXT = """<b><u>🖼️ HOW TO SET THUMBNAIL</u></b>
    
📌 <b>Setting Custom Thumbnail:</b>
Simply send me a photo and I'll save it as your thumbnail!

<b>📋 Available Commands:</b>
• <code>/viewthumb</code> - View your current thumbnail
• <code>/delthumb</code> - Delete your thumbnail

💡 <b>Tip:</b> Use high-quality images for best results!"""

    CAPTION_TXT = """<b><u>📝 HOW TO SET CAPTION</u></b>
    
<b>📋 Available Commands:</b>
• <code>/set_caption</code> - Set your custom caption
• <code>/see_caption</code> - View your current caption
• <code>/del_caption</code> - Delete your caption

<b>🔤 Available Variables:</b>
• <code>{filename}</code> - File name
• <code>{filesize}</code> - File size
• <code>{duration}</code> - Video duration

<b>📝 Example:</b>
<code>/set_caption 📕 Name: {filename}
🔗 Size: {filesize}
⏰ Duration: {duration}</code>"""

    PROGRESS_BAR = """<b>\n
╭━━━━━━━━━━━━━━━━━━━➣
┣⪼ 🗃️ Size: {1} / {2}
┣⪼ ⏳ Progress: {0}%
┣⪼ 🚀 Speed: {3}/s
┣⪼ ⏱️ Time: {4}
╰━━━━━━━━━━━━━━━━━━━➣ </b>"""
    
    
    DONATE_TXT = """<b>🥲 Thanks For Showing Interest In Donation! ❤️</b>
    
If You Like My Bots & Projects, You Can 🎁 Donate Me Any Amount From 10 Rs Upto Your Choice.
    
<b>💳 UPI ID:</b> <code>KHELKHATAMBETA</code>

Your support helps keep this bot running! 🙏"""
    
    HELP_TXT = """<b>👋 Hey {}</b>
    
<b>📚 How To Use This Bot:</b>

<b>Step 1️⃣:</b> Set your auto rename format
Use: <code>/autorename [format]</code>

<b>Step 2️⃣:</b> Send me any file (video/document/audio)

<b>Step 3️⃣:</b> Wait for processing & enjoy! ✨

<b>⚙️ Bot Features:</b>
✅ Auto rename with custom templates
✅ Add watermark to videos
✅ Set custom metadata
✅ Queue system (max 3 concurrent)
✅ Real-time progress tracking
✅ Support files up to 4GB

<b>📋 All Commands:</b>
• <code>/autorename</code> - Set rename format
• <code>/setmedia</code> - Set output type
• <code>/set_caption</code> - Set custom caption
• <code>/viewthumb</code> - View thumbnail
• <code>/tutorial</code> - Detailed guide

<b>💬 Need Help?</b> Join @AshuSupport"""
