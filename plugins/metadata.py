from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.private & filters.command("metadata"))
async def handle_metadata(bot: Client, message: Message):
    await message.reply_text(
        "**⚠️ Metadata Settings**\n\n"
        "Metadata is currently **hardcoded** by the Administrator.\n"
        "You cannot change it manually.\n\n"
        "**Default Metadata:**\n"
        "Title: `Join Anime Atlas on Telegram For More Anime`\n"
        "Author: `Anime Atlas`"
    )
