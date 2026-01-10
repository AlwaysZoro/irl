from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.private & filters.command("metadata"))
async def handle_metadata(bot: Client, message: Message):
    await message.reply_text(
        "**⚙️ Metadata Settings**\n\n"
        "**ℹ️ Info:**\n"
        "Metadata is currently **hardcoded** by the Administrator for consistency.\n\n"
        "**📋 Default Metadata:**\n"
        "• **Title:** `Join Anime Atlas on Telegram For More Anime`\n"
        "• **Artist:** `Anime Atlas`\n"
        "• **Author:** `Anime Atlas`\n\n"
        "**✅ This metadata is automatically added to all your files during processing.**\n\n"
        "If you need custom metadata, please contact @AshuSupport"
    )
