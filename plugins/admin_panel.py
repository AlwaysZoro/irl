from config import Config, Txt
from helper.database import ZoroBhaiya
from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
import os, sys, time, asyncio, logging, datetime
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
ADMIN_USER_ID = Config.ADMIN

is_restarting = False

@Client.on_message(filters.private & filters.command("restart") & filters.user(ADMIN_USER_ID))
async def restart_bot(b, m):
    global is_restarting
    if not is_restarting:
        is_restarting = True
        restart_msg = await m.reply_text("**🔄 Restarting Bot...**\n\nPlease wait a moment...")
        try:
            await asyncio.sleep(1)
            await restart_msg.edit_text("**✅ Bot Restarted Successfully!**\n\nBot will be back online in a few seconds.")
        except:
            pass
        b.stop()
        time.sleep(2)
        os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.private & filters.command(["tutorial"]))
async def tutorial(bot, message):
    try:
        user_id = message.from_user.id
        format_template = await ZoroBhaiya.get_format_template(user_id)
        await message.reply_text(
            text=Txt.FILE_NAME_TXT.format(
                format_template=format_template or "❌ Not Set - Use: /autorename [format]"
            ),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📚 Full Tutorial", url="https://t.me/AshuSupport")]]
            ),
        )
    except Exception as e:
        logger.error(f"Error in /tutorial: {e}")
        await message.reply_text(
            "**❌ Error**\n\n"
            "Unable to fetch tutorial. Please try again later."
        )

@Client.on_message(filters.private & filters.command(["ping", "p"]))
async def ping(_, message):
    start_t = time.time()
    rm = await message.reply_text("**🏓 Pinging...**")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await rm.edit(f"**🏓 Pong!**\n\n**⚡ Ping:** `{time_taken_s:.3f} ms`")

@Client.on_message(filters.command(["stats", "status"]) & filters.user(Config.ADMIN))
async def get_stats(bot, message):
    total_users = await ZoroBhaiya.total_users_count()
    start_t = time.time()
    st = await message.reply("**📊 Fetching Statistics...**")
    end_t = time.time()
    time_taken_s = (end_t - start_t) * 1000
    await st.edit(
        text=f"**📊 Bot Statistics**\n\n"
        f"**🌐 Current Ping:** `{time_taken_s:.3f} ms`\n"
        f"**👥 Total Users:** `{total_users}`\n"
        f"**⚙️ Status:** `Online & Running`"
    )

@Client.on_message(filters.command("broadcast") & filters.user(Config.ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    all_users = await ZoroBhaiya.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("**📢 Broadcast Started!**\n\nProcessing users...")
    done = 0
    failed = 0
    success = 0
    start_time = time.time()
    total_users = await ZoroBhaiya.total_users_count()
    
    async for user in all_users:
        sts = await send_msg(user["_id"], broadcast_msg)
        if sts == 200:
            success += 1
        else:
            failed += 1
        if sts == 400:
            await ZoroBhaiya.delete_user(user["_id"])
        done += 1
        
        # Update every 20 users
        if not done % 20:
            await sts_msg.edit(
                f"**📢 Broadcast In Progress**\n\n"
                f"**👥 Total Users:** `{total_users}`\n"
                f"**✅ Completed:** `{done} / {total_users}`\n"
                f"**🎯 Success:** `{success}`\n"
                f"**❌ Failed:** `{failed}`"
            )
    
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(
        f"**✅ Broadcast Completed!**\n\n"
        f"**⏱️ Time Taken:** `{completed_in}`\n"
        f"**👥 Total Users:** `{total_users}`\n"
        f"**✅ Completed:** `{done} / {total_users}`\n"
        f"**🎯 Success:** `{success}`\n"
        f"**❌ Failed:** `{failed}`"
    )

async def send_msg(user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(user_id, message)
    except InputUserDeactivated:
        return 400
    except UserIsBlocked:
        return 400
    except PeerIdInvalid:
        return 400
    except Exception:
        return 500
