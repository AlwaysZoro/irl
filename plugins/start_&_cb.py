import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from helper.database import ZoroBhaiya
from config import Config, Txt

@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user = message.from_user
    await ZoroBhaiya.add_user(client, message)
    button = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📢 Updates", url="https://t.me/ZoroBhaiya"),
                InlineKeyboardButton("💬 Support", url="https://t.me/AshuSupport"),
            ],
            [
                InlineKeyboardButton("⚙️ Help", callback_data="help"),
                InlineKeyboardButton("💙 About", callback_data="about"),
            ]
        ]
    )
    if Config.START_PIC:
        await message.reply_photo(
            Config.START_PIC,
            caption=Txt.START_TXT.format(user.mention),
            reply_markup=button,
        )
    else:
        await message.reply_text(
            text=Txt.START_TXT.format(user.mention),
            reply_markup=button,
            disable_web_page_preview=True,
        )

@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "home":
        await query.message.edit_text(
            text=Txt.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("📢 Updates", url="https://t.me/ZoroBhaiya"),
                        InlineKeyboardButton("💬 Support", url="https://t.me/AshuSupport"),
                    ],
                    [
                        InlineKeyboardButton("⚙️ Help", callback_data="help"),
                        InlineKeyboardButton("💙 About", callback_data="about"),
                    ]
                ]
            ),
        )
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT.format(client.mention),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("⚙️ Setup AutoRename Format ⚙️", callback_data="file_names")],
                    [InlineKeyboardButton("🖼️ Thumbnail", callback_data="thumbnail"), InlineKeyboardButton("✏️ Caption", callback_data="caption")],
                    [InlineKeyboardButton("🏠 Home", callback_data="home"), InlineKeyboardButton("💰 Donate", callback_data="donate")],
                ]
            ),
        )
    elif data == "about":
        await query.message.edit_text(
            text=Txt.ABOUT_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✖️ Close", callback_data="close"), InlineKeyboardButton("🔙 Back", callback_data="home")]]
            ),
        )
    elif data == "close":
        await query.message.delete()
    elif data == "file_names":
        format_template = await ZoroBhaiya.get_format_template(user_id)
        await query.message.edit_text(
            text=Txt.FILE_NAME_TXT.format(
                format_template=format_template or "Not Set - Use: /autorename [format]"
            ),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help")]]
            ),
        )
    elif data == "thumbnail":
        await query.message.edit_text(
            text=Txt.THUMBNAIL_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help")]]
            ),
        )
    elif data == "caption":
        await query.message.edit_text(
            text=Txt.CAPTION_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help")]]
            ),
        )
    elif data == "donate":
        await query.message.edit_text(
            text=Txt.DONATE_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="help")]]
            ),
        )
