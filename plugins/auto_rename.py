from pyrogram import Client, filters
from helper.database import ZoroBhaiya
import logging

logger = logging.getLogger(__name__)

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id

    # If no arguments, show current format
    if len(message.command) < 2:
        current_format = await ZoroBhaiya.get_format_template(user_id)
        if current_format:
            return await message.reply_text(
                f"**Your Current Auto Rename Format:**\n\n"
                f"`{current_format}`\n\n"
                f"**To change it, use:**\n"
                f"`/autorename [new format]`\n\n"
                f"**Available Placeholders:**\n"
                f"• {{episode}} - Episode number\n"
                f"• {{season}} - Season number\n"
                f"• {{quality}} - Video quality (1080p, 720p, 480p, 4K, etc.)\n\n"
                f"**Example:**\n"
                f"`/autorename S{{season}}E{{episode}} - [{{quality}}]`"
            )
        else:
            return await message.reply_text(
                "**Usage:** `/autorename [format]`\n\n"
                "**Example:**\n"
                "`/autorename S{season}E{episode} - [{quality}]`\n\n"
                "**Available Placeholders:**\n"
                "• {episode} - Episode number\n"
                "• {season} - Season number\n"
                "• {quality} - Video quality (1080p, 720p, 480p, 4K, etc.)\n\n"
                "**More Examples:**\n"
                "`/autorename Naruto S{season}E{episode} [{quality}]`\n"
                "`/autorename Attack on Titan - {episode} ({quality})`\n"
                "`/autorename {season}x{episode} - {quality}`"
            )

    # Extract the format from the command
    format_template = message.text.split(None, 1)[1].strip()

    # Validate format is not empty
    if not format_template:
        return await message.reply_text("**Error:** Format cannot be empty!")

    # Save the format template to the database
    try:
        await ZoroBhaiya.set_format_template(user_id, format_template)
        logger.info(f"User {user_id} set autorename format: {format_template}")
        
        # Verify it was saved by reading it back
        saved_format = await ZoroBhaiya.get_format_template(user_id)
        if saved_format == format_template:
            await message.reply_text(
                f"**✅ Auto Rename Format Saved Successfully!**\n\n"
                f"**Your Format:**\n`{format_template}`\n\n"
                f"Now send any video/document to rename automatically!"
            )
        else:
            logger.error(f"Format verification failed for user {user_id}")
            await message.reply_text(
                "**⚠️ Warning:** Format saved but verification failed. Please try again."
            )
    except Exception as e:
        logger.error(f"Error saving format for user {user_id}: {e}")
        await message.reply_text(
            "**❌ Error saving format!** Please try again or contact support."
        )

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    user_id = message.from_user.id    
    
    if len(message.command) < 2:
        current_media = await ZoroBhaiya.get_media_preference(user_id)
        return await message.reply_text(
            f"**Current Media Type:** {current_media or 'Auto (based on file type)'}\n\n"
            f"**Usage:** `/setmedia [video/document/audio]`\n\n"
            f"**Examples:**\n"
            f"`/setmedia video` - Always upload as video\n"
            f"`/setmedia document` - Always upload as document\n"
            f"`/setmedia audio` - Always upload as audio"
        )

    media_type = message.text.split(None, 1)[1].strip().lower()
    
    # Validate media type
    valid_types = ["video", "document", "audio"]
    if media_type not in valid_types:
        return await message.reply_text(
            f"**❌ Invalid media type!**\n\n"
            f"Valid types: `video`, `document`, `audio`"
        )

    # Save the preferred media type to the database
    try:
        await ZoroBhaiya.set_media_preference(user_id, media_type)
        logger.info(f"User {user_id} set media preference: {media_type}")
        await message.reply_text(f"**✅ Media Preference Set To:** `{media_type}`")
    except Exception as e:
        logger.error(f"Error saving media preference for user {user_id}: {e}")
        await message.reply_text("**❌ Error saving preference!** Please try again.")
