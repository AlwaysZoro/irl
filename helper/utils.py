import math, time
from datetime import datetime
from pytz import timezone
from config import Config, Txt 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

async def progress_for_pyrogram(current, total, ud_type, message, start):
    """Enhanced progress callback with minutes:seconds display"""
    now = time.time()
    diff = now - start
    
    # Update every 3 seconds or at completion
    if round(diff % 3.00) == 0 or current == total:        
        try:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            elapsed_time = round(diff) * 1000
            time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
            
            # Convert to minutes:seconds
            elapsed_seconds = int(elapsed_time / 1000)
            eta_seconds = int(time_to_completion / 1000)
            
            elapsed_str = f"{elapsed_seconds//60:02d}:{elapsed_seconds%60:02d}"
            eta_str = f"{eta_seconds//60:02d}:{eta_seconds%60:02d}" if eta_seconds > 0 else "00:00"
            
            progress = "{0}{1}".format(
                ''.join(["■" for _ in range(math.floor(percentage / 5))]),
                ''.join(["□" for _ in range(20 - math.floor(percentage / 5))])
            )            
            
            tmp = progress + Txt.PROGRESS_BAR.format( 
                round(percentage, 2),
                humanbytes(current),
                humanbytes(total),
                humanbytes(speed),            
                eta_str
            )
            
            await message.edit(
                text=f"{ud_type}\n\n{tmp}",               
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✖️ CANCEL ✖️", callback_data="close")]])                                               
            )
        except Exception as e:
            # Don't crash on progress update errors
            logger.debug(f"Progress update error: {e}")
            pass

def humanbytes(size):    
    """Convert bytes to human readable format"""
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power and n < 4:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    """Format milliseconds to human readable time (minutes:seconds)"""
    seconds = int(milliseconds / 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def convert(seconds):
    """Convert seconds to HH:MM:SS format"""
    seconds = int(seconds) % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)
