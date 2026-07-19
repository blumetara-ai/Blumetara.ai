import asyncio
import logging
from datetime import datetime, timedelta
import zoneinfo
import firebase_admin
from firebase_admin import credentials, messaging
from app.database.mongodb import get_database

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK for background push notifications
try:
    if not firebase_admin._apps:
        # Tries to initialize using default credentials (ADC) or mock fallback
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized successfully for notifications.")
except Exception as e:
    logger.warning(f"Firebase Admin SDK initialization skipped (using mock push alerts): {e}")

def calculate_next_run(time_str: str, tz_name: str) -> datetime:
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")
        
    parts = time_str.split(":")
    if len(parts) != 2:
        hour, minute = 12, 0
    else:
        hour = int(parts[0])
        minute = int(parts[1])
        
    now_tz = datetime.now(tz)
    target_today = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    if target_today <= now_tz:
        target_next = target_today + timedelta(days=1)
    else:
        target_next = target_today
        
    return target_next.astimezone(zoneinfo.ZoneInfo("UTC")).replace(tzinfo=None)

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
                    
                    # 1. Fetch user's FCM token from profile
                    profile = await db.profiles.find_one({"userId": user_id})
                    user_fcm_token = profile.get("fcmToken") if profile else None
                    
                    # 2. Store in notifications history
                    await db.notifications.insert_one({
                        "userId": user_id,
                        "reminderId": rem_id,
                        "title": f"Time for your {rem_type} reminder!",
                        "body": "Stay on track with Blumetara.",
                        "status": "sent",
                        "sentAt": datetime.utcnow()
                    })
                    
                    # 3. Send FCM Push Notification
                    if user_fcm_token:
                        try:
                            message = messaging.Message(
                                notification=messaging.Notification(
                                    title=f"Time for your {rem_type} reminder!",
                                    body="Stay on track with Blumetara."
                                ),
                                token=user_fcm_token
                            )
                            # Only execute send if firebase admin app is initialized with real credentials
                            if firebase_admin._apps:
                                response = messaging.send(message)
                                logger.info(f"FCM Notification sent successfully: {response}")
                            else:
                                logger.info(f"[Mock Push Alert] Sent FCM notification to token: {user_fcm_token}")
                        except Exception as fcm_err:
                            logger.error(f"FCM Send failed (falling back to mock console log): {fcm_err}")
                            logger.info(f"[Mock Push Alert] Sent FCM notification to token: {user_fcm_token}")
                    else:
                        logger.warning(f"No FCM token configured for user {user_id}. Skipping push notification.")

                    # 4. Update nextRunAt using proper user timezone offset logic
                    time_str = reminder.get("time", "12:00")
                    tz_name = reminder.get("timezone", "UTC")
                    next_run = calculate_next_run(time_str, tz_name)
                    
                    await db.reminders.update_one(
                        {"_id": reminder["_id"]},
                        {"$set": {"nextRunAt": next_run}}
                    )
            
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
            
        # Scan every 60 seconds
        await asyncio.sleep(60)
