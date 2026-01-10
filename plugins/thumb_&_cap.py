from pyrogram import Client, filters
from helper.database import ZoroBhaiya

@Client.on_message(filters.private & filters.command("set_caption"))
async def add_caption(client, message):
    if len(message.command) == 1:
        return await message.reply_text(
            "**📝 Set Custom Caption**\n\n"
            "**Usage:** `/set_caption [your caption]`\n\n"
            "**Available Variables:**\n"
            "• `{filename}` - File name\n"
            "• `{filesize}` - File size\n"
            "• `{duration}` - Video duration\n\n"
            "**Example:**\n"
            "`/set_caption 📕 Name: {filename}\n🔗 Size: {filesize}\n⏰ Duration: {duration}`"
        )
    caption = message.text.split(" ", 1)[1]
    await ZoroBhaiya.set_caption(message.from_user.id, caption=caption)
    await message.reply_text(
        "**✅ Caption Saved Successfully!**\n\n"
        f"**Your Caption:**\n`{caption}`\n\n"
        "This will be applied to all your uploads."
    )

@Client.on_message(filters.private & filters.command("del_caption"))
async def delete_caption(client, message):
    caption = await ZoroBhaiya.get_caption(message.from_user.id)
    if not caption:
        return await message.reply_text(
            "**❌ No Caption Found**\n\n"
            "You don't have any custom caption set.\n"
            "Use `/set_caption` to create one!"
        )
    await ZoroBhaiya.set_caption(message.from_user.id, caption=None)
    await message.reply_text(
        "**🗑️ Caption Deleted Successfully!**\n\n"
        "Your custom caption has been removed."
    )

@Client.on_message(filters.private & filters.command(["see_caption", "view_caption"]))
async def see_caption(client, message):
    caption = await ZoroBhaiya.get_caption(message.from_user.id)
    if caption:
        await message.reply_text(
            f"**📝 Your Current Caption:**\n\n"
            f"`{caption}`\n\n"
            f"**Available Variables:**\n"
            f"• `{{filename}}` - File name\n"
            f"• `{{filesize}}` - File size\n"
            f"• `{{duration}}` - Video duration"
        )
    else:
        await message.reply_text(
            "**❌ No Caption Found**\n\n"
            "You don't have any custom caption set.\n"
            "Use `/set_caption` to create one!"
        )

@Client.on_message(filters.private & filters.command(["view_thumb", "viewthumb"]))
async def viewthumb(client, message):
    thumb = await ZoroBhaiya.get_thumbnail(message.from_user.id)
    if thumb:
        await client.send_photo(
            chat_id=message.chat.id, 
            photo=thumb,
            caption="**🖼️ Your Current Thumbnail**\n\nThis will be used for all your uploads."
        )
    else:
        await message.reply_text(
            "**❌ No Thumbnail Found**\n\n"
            "You don't have any custom thumbnail set.\n"
            "Send me a photo to set it as thumbnail!"
        )

@Client.on_message(filters.private & filters.command(["del_thumb", "delthumb"]))
async def removethumb(client, message):
    thumb = await ZoroBhaiya.get_thumbnail(message.from_user.id)
    if not thumb:
        return await message.reply_text(
            "**❌ No Thumbnail Found**\n\n"
            "You don't have any custom thumbnail to delete."
        )
    await ZoroBhaiya.set_thumbnail(message.from_user.id, file_id=None)
    await message.reply_text(
        "**🗑️ Thumbnail Deleted Successfully!**\n\n"
        "Your custom thumbnail has been removed."
    )

@Client.on_message(filters.private & filters.photo)
async def addthumbs(client, message):
    mkn = await message.reply_text("**⏳ Saving Thumbnail...**")
    await ZoroBhaiya.set_thumbnail(
        message.from_user.id, file_id=message.photo.file_id
    )
    await mkn.edit(
        "**✅ Thumbnail Saved Successfully!**\n\n"
        "This thumbnail will be used for all your uploads.\n\n"
        "**Commands:**\n"
        "• `/viewthumb` - View current thumbnail\n"
        "• `/delthumb` - Delete thumbnail"
    )
