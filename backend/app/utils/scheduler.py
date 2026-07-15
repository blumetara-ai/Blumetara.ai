import asyncio
import logging
from datetime import datetime
from app.database.mongodb import get_database

logger = logging.getLogger(__name__)

async def start_reminder_scheduler():
    logger.info("Initializing background reminder scheduler daemon...")
    while True:
        try:
            db = get_database()
            if db is not None:
                now = datetime.utcnow()
                # Find active reminders that are due
                due_reminders = await db.reminders.find({
                    "active": True,
                    "nextRunAt": {"$lte": now}
                }).to_list(length=100)
                
                for reminder in due_reminders:
                    user_id = reminder["userId"]
                    rem_type = reminder["type"]
                    rem_id = str(reminder["_id"])
                    
                    logger.info(f"Triggering {rem_type} reminder ({rem_id}) for user {user_id}...")
                    
                    # 1. Store in notifications history
                    await db.notifications.insert_one({
                        "userId": user_id,
                        "reminderId": rem_id,
                        "title": f"Time for your {rem_type} reminder!",
                        "body": "Stay on track with Blumetara.",
                        "status": "sent",
                        "sentAt": datetime.utcnow()
                    })
                    
                    # 2. Update nextRunAt (e.g. advance 1 day for daily)
                    # For demo simplicity, we set nextRunAt to be 24 hours in the future
                    next_run = datetime.utcnow().replace(hour=12, minute=0, second=0) # dummy reset
                    await db.reminders.update_one(
                        {"_id": reminder["_id"]},
                        {"$set": {"nextRunAt": next_run}}
                    )
            
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            
        # Scan every 60 seconds
        await asyncio.sleep(60)
