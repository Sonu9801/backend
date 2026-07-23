import os
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

# The directory where photos are saved
UPLOAD_DIR = "uploads/attendance_photos"
# Delete files older than 60 days
RETENTION_DAYS = 60

async def cleanup_old_attendance_photos():
    """
    Background task to automatically delete attendance photos
    that are older than a specific number of days.
    """
    while True:
        try:
            if os.path.exists(UPLOAD_DIR):
                current_time = time.time()
                deleted_count = 0
                
                for filename in os.listdir(UPLOAD_DIR):
                    filepath = os.path.join(UPLOAD_DIR, filename)
                    
                    if os.path.isfile(filepath):
                        # Get file modification time
                        file_mtime = os.path.getmtime(filepath)
                        
                        # Calculate age in days
                        age_days = (current_time - file_mtime) / (24 * 3600)
                        
                        if age_days > RETENTION_DAYS:
                            os.remove(filepath)
                            deleted_count += 1
                            
                if deleted_count > 0:
                    logger.info(f"Auto-deleted {deleted_count} old attendance photos (older than {RETENTION_DAYS} days).")
            
        except Exception as e:
            logger.error(f"Error in cleanup_old_attendance_photos task: {e}")
            
        # Wait for 24 hours before running again
        await asyncio.sleep(24 * 3600)
