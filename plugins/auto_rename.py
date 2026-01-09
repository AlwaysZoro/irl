from pyrogram import Client, filters
from helper.database import ZoroBhaiya

@Client.on_message(filters.private & filters.command("autorename"))
async def auto_rename_command(client, message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:** /autorename [format]\n\n"
            "**Example:** /autorename S{season}E{episode} - [{quality}]\n\n"
            "**Available Placeholders:**\n"
            "• {episode} - Episode number\n"
            "• {season} - Season number\n"
            "• {quality} - Video quality"
        )

    # Extract the format from the command
    format_template = message.text.split("/autorename", 1)[1].strip()

    # Save the format template to the database
    await ZoroBhaiya.set_format_template(user_id, format_template)

    await message.reply_text("**Auto Rename Format Updated Successfully! ✅**")

@Client.on_message(filters.private & filters.command("setmedia"))
async def set_media_command(client, message):
    user_id = message.from_user.id    
    
    if len(message.command) < 2:
         return await message.reply_text("**Usage:** /setmedia [video/document/audio]")

    media_type = message.text.split("/setmedia", 1)[1].strip().lower()

    # Save the preferred media type to the database
    await ZoroBhaiya.set_media_preference(user_id, media_type)

    await message.reply_text(f"**Media Preference Set To :** {media_type} ✅")
