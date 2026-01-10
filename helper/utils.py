import math
import time
import asyncio

async def progress_for_pyrogram(current, total, ud_type, message, start):
    """
    Enhanced progress tracking with MM:SS format
    """
    now = time.time()
    diff = now - start
    
    if round(diff % 5.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff)
        
        if speed > 0:
            time_to_completion = round((total - current) / speed)
            estimated_total_time = elapsed_time + time_to_completion
        else:
            time_to_completion = 0
            estimated_total_time = 0

        elapsed_formatted = format_time(elapsed_time)
        eta_formatted = format_time(time_to_completion)
        
        # Progress bar
        filled_length = int(20 * current // total)
        bar = '▰' * filled_length + '▱' * (20 - filled_length)
        
        tmp = f"""
<b>{ud_type}</b>

{bar}

<b>📊 Progress:</b> {percentage:.1f}%
<b>📦 Size:</b> {humanbytes(current)} / {humanbytes(total)}
<b>🚀 Speed:</b> {humanbytes(speed)}/s
<b>⏱️ Elapsed:</b> {elapsed_formatted}
<b>⏳ ETA:</b> {eta_formatted}
"""
        
        try:
            await message.edit_text(text=tmp)
        except Exception as e:
            pass

def humanbytes(size):
    """Convert bytes to human readable format"""
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {Dic_powerN[n]}B"

def format_time(seconds):
    """Format seconds to MM:SS"""
    if seconds == 0:
        return "00:00"
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    
    return f"{minutes:02d}:{secs:02d}"

def convert(seconds):
    """Convert seconds to readable format (for duration)"""
    return format_time(int(seconds))
