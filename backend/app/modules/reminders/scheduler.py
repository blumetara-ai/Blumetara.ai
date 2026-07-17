from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from app.modules.reminders.repository import ReminderRepository
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Single instance of AsyncIOScheduler
scheduler = AsyncIOScheduler()

async def check_due_reminders():
    """
    Background job that runs every minute to scan all active reminders,
    checks if their scheduled times match the current local time in their respective timezones,
    and fires notification dispatches.
    """
    logger.debug("Running background scan for due reminders...")
    try:
        repo = ReminderRepository()
        active_reminders = await repo.get_all_active()
        
        for reminder in active_reminders:
            tz_str = reminder.get("timezone", "Asia/Kolkata")
            times = reminder.get("times", [])
            user_id = reminder.get("user_id")
            reminder_id = reminder.get("_id")
            
            try:
                user_tz = ZoneInfo(tz_str)
            except Exception:
                logger.error(f"Invalid timezone configuration '{tz_str}' for reminder {reminder_id}")
                continue
                
            # Current time in user's timezone
            now_user = datetime.now(user_tz)
            current_time_str = now_user.strftime("%H:%M")
            
            # Check if this minute matches the configured reminders schedule
            if current_time_str in times:
                # Determine title & body based on reminder type
                rem_type = reminder.get("type")
                if rem_type == "MEDICINE":
                    med_name = reminder.get("medicine_name", "your medicine")
                    dose = reminder.get("dose", "")
                    title = "Medication Reminder"
                    body = f"Time to take your {med_name}" + (f" ({dose})" if dose else "")
                else:  # WATER
                    title = "Hydration Reminder"
                    body = "Time to drink a glass of water!"
                    
                # Dispatch notification
                logger.info(f"Triggering due reminder {reminder_id} for user {user_id} at local time {current_time_str}")
                await notification_service.send_push_notification(
                    user_id=user_id,
                    title=title,
                    body=body,
                    data={
                        "reminder_id": reminder_id,
                        "type": rem_type,
                        "scheduled_time": now_user.replace(second=0, microsecond=0).isoformat()
                    }
                )
                
    except Exception as e:
        logger.error(f"Error in background reminders scan: {str(e)}")

def init_scheduler():
    # Run the check every 60 seconds
    scheduler.add_job(
        check_due_reminders,
        "interval",
        seconds=60,
        id="reminder_scan_job",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Background Reminders Scheduler initialized and started.")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background Reminders Scheduler shutdown.")
