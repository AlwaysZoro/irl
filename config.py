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
        
    START_TXT = """**👋 Hello {}**
    
**✨ This Is An Advanced Auto Rename Bot Modified for Anime Atlas.**

**🎯 What I Can Do:**
• Automatically rename files with custom templates
• Add "ANIME ATLAS" watermark to videos
• Embed custom metadata
• Support files up to 4GB

**📊 Processing Capacity:** 3 files simultaneously
**📦 Max File Size:** 4GB

**Click Help button below to get started! 👇**
"""
    
    FILE_NAME_TXT = """**🎬 SETUP AUTO RENAME FORMAT**

**Use these keywords to create your custom file name:**

✅ `{{episode}}` - Episode Number
✅ `{{quality}}` - Video Resolution
✅ `{{season}}` - Season Number

**📝 Example:**
`/autorename Naruto Shippuden S{{season}}E{{episode}} [{{quality}}] [Dual]`

**🔧 Your Current Format:**
`{format_template}`
"""
    
    ABOUT_TXT = """**🤖 Bot Information**

**📛 Name:** Auto Rename Bot
**📢 Version:** 2.0 Advanced
**🔍 Language:** <a href='https://python.org'>Python 3</a>
**📚 Library:** <a href='https://pyrogram.org'>Pyrogram 2.0</a>

**⚙️ Features:**
  ✅ Auto Rename with Templates
  ✅ Video Watermarking (ANIME ATLAS)
  ✅ Custom Metadata Management
  ✅ Queue System (3 concurrent)
  ✅ Real-time Progress Tracking
  ✅ Support up to 4GB Files
    
**♻️ Modified For:** Anime Atlas
**👨‍💻 Developer:** @AshuSupport
"""

    
    THUMBNAIL_TXT = """**🖼️ HOW TO SET THUMBNAIL**
    
**📌 Setting Custom Thumbnail:**
Simply send me a photo and I'll save it as your thumbnail!

**📋 Available Commands:**
• `/viewthumb` - View your current thumbnail
• `/delthumb` - Delete your thumbnail

**💡 Tip:** Use high-quality images for best results!
"""

    CAPTION_TXT = """**📝 HOW TO SET CAPTION**
    
**📋 Available Commands:**
• `/set_caption` - Set your custom caption
• `/see_caption` - View your current caption
• `/del_caption` - Delete your caption

**📤 Available Variables:**
• `{filename}` - File name
• `{filesize}` - File size
• `{duration}` - Video duration

**📝 Example:**
`/set_caption 📕 Name: {filename}
📗 Size: {filesize}
⏰ Duration: {duration}`
"""

    PROGRESS_BAR = """**\n
╭──────────────────⟢
┣⪼ 🗃️ Size: {1} / {2}
┣⪼ ⏳ Progress: {0}%
┣⪼ 🚀 Speed: {3}/s
┣⪼ ⏱️ Time: {4}
╰──────────────────⟢ **
"""
    
    
    DONATE_TXT = """**🥲 Thanks For Showing Interest In Donation! ❤️**
    
If You Like My Bots & Projects, You Can 🎁 Donate Me Any Amount From 10 Rs Upto Your Choice.
    
**💳 UPI ID:** `KHELKHATAMBETA`

Your support helps keep this bot running! 🙏
"""
    
    HELP_TXT = """**👋 Hey {}**
    
**📚 How To Use This Bot:**

**Step 1️⃣:** Set your auto rename format
Use: `/autorename [format]`

**Step 2️⃣:** Send me any file (video/document/audio)

**Step 3️⃣:** Wait for processing & enjoy! ✨

**⚙️ Bot Features:**
✅ Auto rename with custom templates
✅ Add watermark to videos
✅ Set custom metadata
✅ Queue system (max 3 concurrent)
✅ Real-time progress tracking
✅ Support files up to 4GB

**📋 All Commands:**
• `/autorename` - Set rename format
• `/setmedia` - Set output type
• `/set_caption` - Set custom caption
• `/viewthumb` - View thumbnail
• `/tutorial` - Detailed guide

**💬 Need Help?** Join @AshuSupport
"""
