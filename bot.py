import logging
import warnings
import pyrogram
from pyrogram import Client, idle, __version__
from config import Config
from aiohttp import web
from pytz import timezone
from datetime import datetime
import asyncio
from route import web_server
import pyromod
import signal
import sys

# Channel ID fix
pyrogram.utils.MIN_CHANNEL_ID = -1003512136864

# Clean logging - only critical messages
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Silence library noise
for logger_name in ["pyrogram", "pyrogram.session", "pyrogram.connection", "aiohttp", "motor"]:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

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
        self.is_running = False

    async def start(self):
        await super().start()
        self.is_running = True
        me = await self.get_me()
        self.mention = me.mention
        self.username = me.username
        
        # Start web server
        try:
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", Config.PORT).start()
        except Exception as e:
            logger.error(f"Web server error: {e}")
        
        logger.info(f"✅ Bot Started Successfully: @{me.username}")

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
        if self.is_running:
            self.is_running = False
            try:
                await super().stop()
                logger.info("Bot stopped cleanly")
            except Exception:
                pass

bot_instance = Bot()
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    shutdown_event.set()

async def main():
    """Main async entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot_instance.start()
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await bot_instance.stop()

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            loop.close()
        except:
            pass
