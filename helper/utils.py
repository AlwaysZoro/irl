import math, time
from datetime import datetime
from pytz import timezone
from config import Config, Txt 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

async def progress_for_pyrogram(current, total, ud_type, message, start):
    """Enhanced progress callback with better error handling"""
    now = time.time()
    diff = now - start
    
    # Update every 5 seconds or at completion
    if round(diff % 5.00) == 0 or current == total:        
        try:
            percentage = current * 100 / total
            speed = current / diff if diff > 0 else 0
            elapsed_time = round(diff) * 1000
            time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
            estimated_total_time = elapsed_time + time_to_completion

            elapsed_time_str = TimeFormatter(milliseconds=elapsed_time)
            estimated_total_time_str = TimeFormatter(milliseconds=estimated_total_time)

            progress = "{0}{1}".format(
                ''.join(["■" for i in range(math.floor(percentage / 5))]),
                ''.join(["□" for i in range(20 - math.floor(percentage / 5))])
            )            
            
            tmp = progress + Txt.PROGRESS_BAR.format( 
                round(percentage, 2),
                humanbytes(current),
                humanbytes(total),
                humanbytes(speed),            
                estimated_total_time_str if estimated_total_time_str != '' else "0 s"
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
    """Format milliseconds to human readable time"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    
    return tmp[:-2] if tmp else "0s"

def convert(seconds):
    """Convert seconds to HH:MM:SS format"""
    seconds = int(seconds) % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)
