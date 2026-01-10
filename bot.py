import logging
import logging.config
import warnings
import pyrogram
from pyrogram import Client, idle, __version__
from pyrogram.raw.all import layer
from config import Config
from aiohttp import web
from pytz import timezone
from datetime import datetime
import asyncio
from route import web_server
import pyromod

# Explicitly set the channel ID fix
pyrogram.utils.MIN_CHANNEL_ID = -1003512136864

# Minimal Logging Setup - Only Important Messages
logging.basicConfig(
    level=logging.ERROR,
    format="%(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Silence all library noise
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pyrogram.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection").setLevel(logging.ERROR)
logging.getLogger("aiohttp").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="ZoroBhaiya",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=15,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start web server
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, Config.PORT).start()
        
        logger.info(f"✅ Bot Started: @{me.username}")

        if Config.LOG_CHANNEL:
            try:
                curr = datetime.now(timezone("Asia/Kolkata"))
                date = curr.strftime("%d %B, %Y")
                time = curr.strftime("%I:%M:%S %p")
                await self.send_message(
                    Config.LOG_CHANNEL,
                    f"**✅ {me.mention} Is Online!**\n\n"
                    f"**📅 Date:** `{date}`\n"
                    f"**⏰ Time:** `{time}`\n"
                    f"**📦 Version:** `{__version__}`\n"
                    f"**⚙️ Status:** `Running`"
                )
            except:
                pass

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot Stopped")

bot_instance = Bot()

async def main():
    """Main async entry point"""
    try:
        await bot_instance.start()
        await idle()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await bot_instance.stop()

if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="There is no current event loop")
    
    # Run the bot
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
