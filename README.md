# 🎬 Auto Rename Bot - Complete Documentation

<p align="center">
  <img src="https://graph.org/file/386500b2d4b21d5d1f772.jpg" alt="Auto Rename Bot" width="600">
</p>

<p align="center">
  <b>Advanced Telegram Auto Rename Bot with Watermarking & Metadata Support</b>
</p>

---

## 📋 Table of Contents

- [Features](#-features)
- [User Commands](#-user-commands)
- [Admin Commands](#-admin-commands)
- [How to Use](#-how-to-use)
- [Template Variables](#-template-variables)
- [Bot Functions](#-bot-functions)
- [Technical Specifications](#-technical-specifications)
- [Deployment](#-deployment)
- [Environment Variables](#-environment-variables)
- [Support](#-support)

---

## ✨ Features

### 🎯 Core Features
- ✅ **Auto Rename Files** - Automatically rename files using custom templates
- ✅ **Video Watermarking** - Add "ANIME ATLAS" watermark to all videos
- ✅ **Custom Metadata** - Embed custom metadata in all files
- ✅ **Smart Queue System** - Process up to 3 files simultaneously
- ✅ **Large File Support** - Handle files up to 4GB
- ✅ **Real-time Progress** - Live progress tracking with MM:SS time format
- ✅ **Custom Thumbnails** - Set custom thumbnails for uploads
- ✅ **Custom Captions** - Create personalized captions with variables
- ✅ **Media Type Selection** - Choose output format (video/document/audio)
- ✅ **Metadata Extraction** - Auto-detect episode, season, and quality from filenames

### 🔧 Technical Features
- ✅ High-quality video encoding (CRF 23)
- ✅ Efficient stream copying for audio/subtitles
- ✅ Automatic metadata embedding
- ✅ Smart file cleanup
- ✅ Error handling and recovery
- ✅ Database-backed user settings
- ✅ Broadcast messaging system
- ✅ User statistics tracking

---

## 📝 User Commands

### 🚀 Essential Commands

#### `/start`
**Description:** Start the bot and see the welcome message  
**Usage:** `/start`  
**Response:** Welcome message with inline buttons for Help, About, Updates, and Support

---

#### `/autorename [format]`
**Description:** Set your custom auto rename format  
**Usage:** `/autorename [your format template]`

**Examples:**
```
/autorename S{season}E{episode} - [{quality}]
/autorename Naruto Shippuden S{season}E{episode} [{quality}] [Dual Audio]
/autorename [@Anime_Atlas] {episode} - One Piece [{quality}] [Sub]
/autorename Attack on Titan - Episode {episode} ({quality})
```

**Without Arguments:**
```
/autorename
```
Shows your current format and examples

**Available Placeholders:**
- `{episode}` - Episode number (e.g., 01, 142)
- `{season}` - Season number (e.g., 01, 02)
- `{quality}` - Video quality (e.g., 1080p, 720p, 4K)

---

#### `/setmedia [type]`
**Description:** Set your preferred media upload type  
**Usage:** `/setmedia [video/document/audio]`

**Examples:**
```
/setmedia video       # Always upload as video
/setmedia document    # Always upload as document
/setmedia audio       # Always upload as audio
```

**Without Arguments:**
```
/setmedia
```
Shows current media preference

---

### 🖼️ Thumbnail Commands

#### `/viewthumb` or `/view_thumb`
**Description:** View your current custom thumbnail  
**Usage:** `/viewthumb`  
**Response:** Shows your saved thumbnail or error if none exists

---

#### `/delthumb` or `/del_thumb`
**Description:** Delete your custom thumbnail  
**Usage:** `/delthumb`  
**Response:** Confirmation that thumbnail was deleted

---

#### **Send Photo (To Set Thumbnail)**
**Description:** Simply send any photo to the bot to set it as your thumbnail  
**Usage:** Send a photo directly to the bot  
**Response:** Confirmation that thumbnail was saved

---

### ✏️ Caption Commands

#### `/set_caption [caption]`
**Description:** Set your custom caption for all uploads  
**Usage:** `/set_caption [your caption with variables]`

**Examples:**
```
/set_caption 📕 Name: {filename}
🔗 Size: {filesize}
⏰ Duration: {duration}

/set_caption {filename} - {filesize}

/set_caption 🎬 {filename}
📦 {filesize} | ⏱️ {duration}
Join @AnimeAtlas for more!
```

**Available Variables:**
- `{filename}` - The renamed file name
- `{filesize}` - File size (e.g., 450.5 MB)
- `{duration}` - Video duration (e.g., 23:45)

---

#### `/see_caption` or `/view_caption`
**Description:** View your current custom caption  
**Usage:** `/see_caption`  
**Response:** Shows your saved caption or error if none exists

---

#### `/del_caption`
**Description:** Delete your custom caption  
**Usage:** `/del_caption`  
**Response:** Confirmation that caption was deleted

---

### 📚 Information Commands

#### `/tutorial`
**Description:** Get detailed tutorial on how to use the bot  
**Usage:** `/tutorial`  
**Response:** Shows your current format and link to full tutorial

---

#### `/metadata`
**Description:** View information about metadata settings  
**Usage:** `/metadata`  
**Response:** Shows default metadata that's applied to all files

---

#### `/ping` or `/p`
**Description:** Check bot response time  
**Usage:** `/ping`  
**Response:** Bot latency in milliseconds

---

## 👑 Admin Commands

### 🔐 Restricted to Bot Administrators Only

#### `/restart`
**Description:** Restart the bot  
**Usage:** `/restart`  
**Access:** Admin only  
**Response:** Restarts the bot process

---

#### `/stats` or `/status`
**Description:** Get bot statistics  
**Usage:** `/stats`  
**Access:** Admin only  
**Response:** Shows:
- Current ping
- Total users
- Bot status

---

#### `/broadcast`
**Description:** Send a message to all bot users  
**Usage:** Reply to any message with `/broadcast`  
**Access:** Admin only

**How to use:**
1. Send or forward the message you want to broadcast
2. Reply to that message with `/broadcast`
3. Bot will send it to all users

**Response:** Shows broadcast progress:
- Total users
- Success count
- Failed count
- Completion time

---

## 🎯 How to Use

### Step-by-Step Guide

#### 1️⃣ **Initial Setup**

1. Start the bot: `/start`
2. Set your rename format: `/autorename S{season}E{episode} [{quality}]`
3. (Optional) Set thumbnail: Send a photo
4. (Optional) Set caption: `/set_caption {filename} - {filesize}`
5. (Optional) Set media type: `/setmedia video`

---

#### 2️⃣ **Renaming Files**

1. Send any file (video/document/audio) to the bot
2. Bot will automatically:
   - Download the file
   - Extract episode, season, and quality
   - Apply your rename format
   - Add watermark (for videos)
   - Embed metadata
   - Upload with new name

---

#### 3️⃣ **Progress Tracking**

During processing, you'll see:
```
📥 Downloading...
Progress: 45%
Size: 450 MB / 1 GB
Speed: 2.5 MB/s
Time: 03:21 / 12:45

⚙️ Processing metadata and watermark...
Progress: 78%
Time: 02:15 / 05:30

📤 Uploading...
Progress: 92%
Size: 920 MB / 1 GB
Speed: 3.2 MB/s
Time: 04:50 / 06:20
```

---

## 🔤 Template Variables

### How Variables Work

The bot automatically extracts information from your file names and applies it to your template.

### Variable Details

| Variable | Description | Example Output |
|----------|-------------|----------------|
| `{episode}` | Episode number extracted from filename | `01`, `142`, `0325` |
| `{season}` | Season number extracted from filename | `01`, `02`, `10` |
| `{quality}` | Video quality extracted from filename | `1080p`, `720p`, `4K` |

### Extraction Examples

**Original Filename:**
```
Naruto Shippuden - 142 [1080p].mkv
```

**Extracted Values:**
- Episode: `142`
- Season: `1` (default if not found)
- Quality: `1080p`

**Your Template:**
```
/autorename Naruto S{season}E{episode} [{quality}]
```

**Final Output:**
```
Naruto S01E142 [1080p].mkv
```

---

### More Examples

| Original Filename | Template | Output |
|-------------------|----------|--------|
| `One Piece 1055 [720p].mp4` | `One Piece - {episode} [{quality}]` | `One Piece - 1055 [720p].mp4` |
| `AOT S04E28 [1080p].mkv` | `Attack on Titan S{season}E{episode} ({quality})` | `Attack on Titan S04E28 (1080p).mkv` |
| `Demon Slayer 26 4K.mp4` | `[Anime Atlas] {episode} - DS [{quality}]` | `[Anime Atlas] 26 - DS [4K].mp4` |

---

## 🛠️ Bot Functions

### 1. **Auto Rename**
- Extracts metadata from filename
- Applies your custom template
- Preserves file extension
- Supports all file types

### 2. **Video Watermarking**
- Adds "ANIME ATLAS" watermark
- Positioned: Top-left corner
- Color: White
- Font: Custom ZURAMBI font
- Size: Small and non-intrusive
- Quality: High (CRF 23)

### 3. **Metadata Embedding**
**Default Metadata:**
- Title: `Join Anime Atlas on Telegram For More Anime`
- Artist: `Anime Atlas`
- Author: `Anime Atlas`
- Video Stream: `Join Anime Atlas`
- Audio Stream: `Anime Atlas`

### 4. **Queue Management**
- Process 3 files simultaneously
- FIFO (First In, First Out) system
- Shows queue position if busy
- No file limit in queue

### 5. **Smart Detection**
**Episode Detection:**
- Pattern: `S01E05`, `EP142`, `Episode 23`
- Standalone numbers: `142`, `0325`
- Handles 1-4 digit episode numbers

**Season Detection:**
- Pattern: `S01`, `Season 2`, `S04E28`
- Defaults to `01` if not found

**Quality Detection:**
- Patterns: `1080p`, `720p`, `480p`, `4K`, `2K`
- Formats: `[1080p]`, `(720p)`, `4K`
- Defaults to `Unknown` if not found

### 6. **File Processing**

**For Videos:**
1. Download file
2. Extract metadata
3. Apply watermark using FFmpeg
4. Add metadata
5. Re-encode with high quality (CRF 23)
6. Upload

**For Non-Videos:**
1. Download file
2. Extract metadata
3. Add metadata only (no watermark)
4. Upload

### 7. **Progress Tracking**
- Real-time percentage
- Upload/Download speed
- Time elapsed (MM:SS format)
- Estimated time remaining (MM:SS format)
- File size progress (current/total)
- Visual progress bar

### 8. **Custom Captions**
**Variables Available:**
- `{filename}` - Final renamed filename
- `{filesize}` - Human-readable size (e.g., 1.2 GB)
- `{duration}` - Video length in MM:SS format

**Example:**
```
Caption: 📕 {filename} | 📦 {filesize} | ⏰ {duration}
Output: 📕 One Piece E1055.mp4 | 📦 450.5 MB | ⏰ 23:45
```

### 9. **Thumbnail Management**
- Upload any photo as thumbnail
- Automatically resized to 320x320
- Applied to all uploads
- Can be changed anytime
- Can be deleted

### 10. **Database Functions**
- Store user settings persistently
- Format templates per user
- Caption templates per user
- Thumbnail per user
- Media preferences per user
- User statistics

---

## ⚙️ Technical Specifications

### File Support
- **Max File Size:** 4 GB (Telegram limit: 2 GB after processing)
- **Supported Formats:** All video, audio, and document formats
- **Video Codecs:** H.264, H.265, VP9, AV1, etc.
- **Audio Codecs:** AAC, MP3, OPUS, FLAC, etc.

### Processing Details
- **Video Encoding:** libx264 with CRF 23 (high quality)
- **Audio Processing:** Stream copy (no re-encoding)
- **Subtitle Processing:** Stream copy (preserved)
- **Watermark:** FFmpeg drawtext filter
- **Metadata:** FFmpeg metadata tags

### Performance
- **Concurrent Processing:** 3 files maximum
- **Queue:** Unlimited
- **Progress Updates:** Every 5 seconds
- **Download Speed:** Depends on Telegram servers
- **Upload Speed:** Depends on Telegram servers

### System Requirements
- Python 3.10+
- FFmpeg with libx264
- MongoDB database
- 2GB+ RAM recommended
- SSD storage recommended

---

## 🚀 Deployment

### Deployment Platforms

#### 1. **Heroku**
[![Deploy to Heroku](https://img.shields.io/badge/Deploy%20On%20Heroku-black?style=for-the-badge&logo=heroku)](https://dashboard.heroku.com/new?template=https://github.com/Codeflix-Bots/Auto-Rename-Bot)

#### 2. **Koyeb**
[![Deploy to Koyeb](https://img.shields.io/badge/Deploy%20On%20Koyeb-black?style=for-the-badge&logo=Koyeb)](https://app.koyeb.com/deploy?type=git&repository=https://github.com/Codeflix-Bots/AutoRenameBot&branch=master&name=AutoReanemBot)

#### 3. **Render**
Use `render.yaml` configuration file provided

#### 4. **VPS/Local Server**
```bash
# Clone repository
git clone https://github.com/YourRepo/Auto-Rename-Bot.git
cd Auto-Rename-Bot

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg
sudo apt update
sudo apt install ffmpeg fonts-dejavu-core -y

# Set environment variables
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export BOT_TOKEN="your_bot_token"
export DB_URL="your_mongodb_url"
export ADMIN="your_user_id"

# Run bot
python3 bot.py
```

---

## 🔐 Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Get from my.telegram.org | `12345678` |
| `API_HASH` | Get from my.telegram.org | `abc123def456...` |
| `BOT_TOKEN` | Get from @BotFather | `123456:ABC-DEF...` |
| `DB_URL` | MongoDB connection URL | `mongodb+srv://...` |
| `ADMIN` | Admin user ID(s) | `123456789` or `123456789 987654321` |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DB_NAME` | MongoDB database name | `AutoRename` | `MyBotDB` |
| `LOG_CHANNEL` | Private channel for logs | None | `-1001234567890` |
| `START_PIC` | Start message image URL | Default image | `https://graph.org/file/...` |
| `WEBHOOK` | Enable webhook mode | `False` | `True` or `False` |
| `PORT` | Web server port | `8080` | `8080` |

---

## 📊 How to Get Variables

### 1. **API_ID and API_HASH**
1. Go to https://my.telegram.org
2. Login with your phone number
3. Click on "API Development Tools"
4. Create a new application
5. Copy `API_ID` and `API_HASH`

### 2. **BOT_TOKEN**
1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow instructions
5. Copy the bot token

### 3. **DB_URL (MongoDB)**
1. Go to https://cloud.mongodb.com
2. Create a free account
3. Create a new cluster
4. Click "Connect"
5. Choose "Connect your application"
6. Copy the connection string
7. Replace `<password>` with your database password

### 4. **ADMIN (Your User ID)**
1. Open Telegram
2. Search for `@userinfobot`
3. Start the bot
4. It will send your user ID

### 5. **LOG_CHANNEL**
1. Create a private channel
2. Add your bot as admin
3. Send a message in the channel
4. Forward it to `@userinfobot`
5. Copy the channel ID (starts with -100)

---

## 📞 Support

### Get Help
- **Support Group:** [@AshuSupport](https://t.me/AshuSupport)
- **Updates Channel:** [@ZoroBhaiya](https://t.me/ZoroBhaiya)

### Report Issues
If you encounter any issues:
1. Try the `/restart` command (admin only)
2. Check your format template with `/autorename`
3. Contact support group with:
   - Error message
   - File type and size
   - Your format template

---

## 🎯 Quick Reference Card

### Basic Workflow
```
1. /start
2. /autorename S{season}E{episode} [{quality}]
3. Send file
4. Wait for processing
5. Receive renamed file
```

### Essential Commands
```
/start          - Start bot
/autorename     - Set format
/setmedia       - Set media type
/set_caption    - Set caption
/viewthumb      - View thumbnail
/tutorial       - Get help
```

### Template Example
```
Template: Naruto S{season}E{episode} [{quality}]
File:     Naruto - 142 [1080p].mkv
Result:   Naruto S01E142 [1080p].mkv
```

---

## 📝 Notes

- Bot processes maximum 3 files simultaneously
- Files larger than 2GB after processing will fail (Telegram limit)
- Watermark is only added to video files
- Metadata is added to all file types
- Queue position shows when bot is busy
- All user settings are stored in database
- Bot supports all video/audio/document formats

---

## ⚡ Features Summary

✅ Auto Rename with Templates  
✅ Video Watermarking (ANIME ATLAS)  
✅ Custom Metadata Embedding  
✅ Queue System (3 concurrent)  
✅ Real-time Progress (MM:SS format)  
✅ Custom Thumbnails  
✅ Custom Captions with Variables  
✅ Media Type Selection  
✅ Smart Metadata Extraction  
✅ Support Files up to 4GB  
✅ Broadcast System  
✅ User Statistics  
✅ High-Quality Encoding (CRF 23)  
✅ Efficient Processing  
✅ Error Recovery  

---

## 🎬 Modified For
**Anime Atlas**

---

<p align="center">
  <b>Made with ❤️ for Anime Atlas Community</b>
</p>

<p align="center">
  <a href="https://telegram.me/Sanji_Fr">
    <img src="https://img.shields.io/badge/-Support%20Group-blue.svg?style=for-the-badge&logo=Telegram">
  </a>
  <a href="https://telegram.me/Sanji_Fr">
    <img src="https://img.shields.io/badge/-Updates%20Channel-blue.svg?style=for-the-badge&logo=Telegram">
  </a>
</p>
