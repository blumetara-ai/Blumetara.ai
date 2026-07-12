import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        pass

    async def send_push_notification(self, user_id: str, title: str, body: str, data: dict = None) -> bool:
        # Mock push notification dispatch
        # In a real app, this would use firebase_admin to send FCM payloads to the user's device token
        log_message = (
            f"\n--- [NOTIFICATION SYSTEM] ---\n"
            f"TO: User '{user_id}'\n"
            f"TITLE: {title}\n"
            f"BODY: {body}\n"
            f"DATA: {data or {}}\n"
            f"-----------------------------\n"
        )
        logger.info(log_message)
        print(log_message)  # Print directly to stdout so it shows up in terminal outputs clearly
        return True

notification_service = NotificationService()
