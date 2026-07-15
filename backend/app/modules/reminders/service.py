from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import HTTPException, status
from typing import List, Dict, Any, Optional
from app.modules.reminders.repository import ReminderRepository
from app.modules.reminders.schemas import ReminderCreate, ReminderUpdate, ReminderLogCreate

class ReminderService:
    def __init__(self):
        self.repository = ReminderRepository()

    def _validate_timezone(self, tz_str: str) -> None:
        try:
            ZoneInfo(tz_str)
        except ZoneInfoNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid timezone: '{tz_str}'. Must be a valid IANA timezone name."
            )

    async def create_reminder(self, user_id: str, schema: ReminderCreate) -> Dict[str, Any]:
        self._validate_timezone(schema.timezone)
        return await self.repository.create(user_id, schema)

    async def get_reminder(self, reminder_id: str, user_id: str) -> Dict[str, Any]:
        reminder = await self.repository.get_by_id(reminder_id)
        if reminder is None or reminder["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found"
            )
        return reminder

    async def get_user_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.repository.get_user_reminders(user_id)

    async def update_reminder(self, reminder_id: str, user_id: str, schema: ReminderUpdate) -> Dict[str, Any]:
        # Validate timezone if updated
        if schema.timezone is not None:
            self._validate_timezone(schema.timezone)
            
        # Verify ownership first
        await self.get_reminder(reminder_id, user_id)
        
        updated = await self.repository.update(reminder_id, user_id, schema)
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found"
            )
        return updated

    async def delete_reminder(self, reminder_id: str, user_id: str) -> None:
        # Verify ownership first
        await self.get_reminder(reminder_id, user_id)
        
        success = await self.repository.delete(reminder_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found or could not be deleted"
            )

    async def log_action(self, reminder_id: str, user_id: str, schema: ReminderLogCreate) -> Dict[str, Any]:
        # Verify ownership & load reminder metadata for the log
        reminder = await self.get_reminder(reminder_id, user_id)
        
        return await self.repository.create_log(
            user_id=user_id,
            reminder_id=reminder_id,
            type_val=reminder["type"],
            med_name=reminder.get("medicine_name"),
            schema=schema
        )

    async def get_logs(self, user_id: str, reminder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if reminder_id:
            # Verify ownership
            await self.get_reminder(reminder_id, user_id)
        return await self.repository.get_user_logs(user_id, reminder_id)

# Commit 1: feat(water-reminder): define validation schemas for water intake schedules

# Commit 2: feat(water-reminder): enforce HH:MM format checks for user times

# Commit 3: feat(water-reminder): implement database initialization and repository setup

# Commit 4: feat(water-reminder): support fetching active records inside repository

# Commit 5: feat(water-reminder): add deletion execution to database model

# Commit 6: feat(water-reminder): design service creation and validation wrapper

# Commit 7: feat(water-reminder): configure console logging and debug services formats

# Commit 8: feat(water-reminder): build background interval checks routines

# Commit 9: feat(water-reminder): build rest routes definitions for reminders configuration

# Commit 10: feat(water-reminder): mount router to general api workspace path

# Commit 11: test(water-reminder): write schemas validations unit tests

# Commit 12: test(water-reminder): test database mock connection configurations

# Commit 13: test(water-reminder): verify deletion counts outcomes

# Commit 14: docs(water-reminder): updates readme document file local guidelines
