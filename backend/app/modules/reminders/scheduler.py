from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from app.modules.reminders.repository import ReminderRepository
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def check_due_reminders():
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
                continue
                
            now_user = datetime.now(user_tz)
            current_time_str = now_user.strftime("%H:%M")
            
            if current_time_str in times:
                await notification_service.send_push_notification(
                    user_id=user_id,
                    title="Hydration Reminder",
                    body="Time to drink a glass of water!",
                    data={
                        "reminder_id": reminder_id,
                        "type": "WATER",
                        "scheduled_time": now_user.replace(second=0, microsecond=0).isoformat()
                    }
                )
    except Exception as e:
        logger.error(f"Error in background water reminders scan: {str(e)}")

def init_scheduler():
    scheduler.add_job(
        check_due_reminders,
        "interval",
        seconds=60,
        id="reminder_scan_job",
        replace_existing=True
    )
    scheduler.start()

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
