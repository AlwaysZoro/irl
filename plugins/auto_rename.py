from pyrogram import Client, filters
from helper.database import ZoroBhaiya

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id

    # If no arguments, show current format
    if len(message.command) < 2:
        current_format = await ZoroBhaiya.get_format_template(user_id)
        if current_format:
            return await message.reply_text(
                f"**🎬 Your Current Auto Rename Format:**\n\n"
                f"`{current_format}`\n\n"
                f"**📝 To Change It:**\n"
                f"`/autorename [new format]`\n\n"
                f"**🔤 Available Placeholders:**\n"
                f"• `{{episode}}` - Episode number\n"
                f"• `{{season}}` - Season number\n"
                f"• `{{quality}}` - Video quality (1080p, 720p, 480p, 4K, etc.)\n\n"
                f"**💡 Example:**\n"
                f"`/autorename S{{season}}E{{episode}} - [{{quality}}]`"
            )
        else:
            return await message.reply_text(
                "**🎬 Setup Auto Rename Format**\n\n"
                "**📝 Usage:** `/autorename [format]`\n\n"
                "**🔤 Available Placeholders:**\n"
                "• `{episode}` - Episode number\n"
                "• `{season}` - Season number\n"
                "• `{quality}` - Video quality (1080p, 720p, 480p, 4K, etc.)\n\n"
                "**💡 Examples:**\n"
                "`/autorename Naruto S{season}E{episode} [{quality}]`\n"
                "`/autorename Attack on Titan - {episode} ({quality})`\n"
                "`/autorename {season}x{episode} - {quality}`\n\n"
                "**📚 For detailed guide, use:** `/tutorial`"
            )

    # Extract the format from the command
    format_template = message.text.split(None, 1)[1].strip()

    # Validate format is not empty
    if not format_template:
        return await message.reply_text(
            "**❌ Error: Format Cannot Be Empty!**\n\n"
            "Please provide a valid format.\n\n"
            "**Example:** `/autorename S{season}E{episode} [{quality}]`"
        )

    # Save the format template to the database
    try:
        await ZoroBhaiya.set_format_template(user_id, format_template)
        
        # Verify it was saved by reading it back
        saved_format = await ZoroBhaiya.get_format_template(user_id)
        if saved_format == format_template:
            await message.reply_text(
                f"**✅ Auto Rename Format Saved Successfully!**\n\n"
                f"**📝 Your Format:**\n`{format_template}`\n\n"
                f"**🎯 Next Step:**\nSend any video/document to rename automatically!\n\n"
                f"**💡 Tip:** The bot will automatically extract episode, season, and quality from your files!"
            )
        else:
            logger.error(f"Format verification failed for user {user_id}")
            await message.reply_text(
                "**⚠️ Warning: Format Saved But Verification Failed**\n\n"
                "Please try setting the format again.\n"
                "If the issue persists, contact @AshuSupport"
            )
        else:
            await message.reply_text(
            "**❌ Error Saving Format!**\n\n"
            "Something went wrong. Please try again.\n"
            "If the issue persists, contact @AshuSupport"
        )

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    user_id = message.from_user.id    
    
    if len(message.command) < 2:
        current_media = await ZoroBhaiya.get_media_preference(user_id)
        return await message.reply_text(
            f"**🎥 Current Media Type:** `{current_media or 'Auto (based on file type)'}`\n\n"
            f"**📝 Usage:** `/setmedia [video/document/audio]`\n\n"
            f"**💡 Examples:**\n"
            f"`/setmedia video` - Always upload as video\n"
            f"`/setmedia document` - Always upload as document\n"
            f"`/setmedia audio` - Always upload as audio\n\n"
            f"**ℹ️ Note:** If not set, the bot will automatically detect the media type."
        )

    media_type = message.text.split(None, 1)[1].strip().lower()
    
    # Validate media type
    valid_types = ["video", "document", "audio"]
    if media_type not in valid_types:
        return await message.reply_text(
            f"**❌ Invalid Media Type!**\n\n"
            f"**Valid Types:**\n"
            f"• `video`\n"
            f"• `document`\n"
            f"• `audio`\n\n"
            f"**Example:** `/setmedia video`"
        )

    # Save the preferred media type to the database
    try:
        await ZoroBhaiya.set_media_preference(user_id, media_type)
        await message.reply_text(
            f"**✅ Media Preference Set Successfully!**\n\n"
            f"**🎥 Upload Type:** `{media_type}`\n\n"
            f"All your files will now be uploaded as {media_type}."
        )
    except:
        await message.reply_text(
            "**❌ Error Saving Preference!**\n\n"
            "Something went wrong. Please try again.\n"
            "If the issue persists, contact @AshuSupport"
        )
