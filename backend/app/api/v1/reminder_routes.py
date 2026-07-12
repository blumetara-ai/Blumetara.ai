from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from app.core.security import get_current_user_id
from app.modules.reminders.schemas import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderLogCreate,
    ReminderLogResponse
)
from app.modules.reminders.service import ReminderService

router = APIRouter(prefix="/reminders", tags=["Reminders"])
reminder_service = ReminderService()

@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    schema: ReminderCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new time-based reminder (either MEDICINE or WATER).
    """
    return await reminder_service.create_reminder(user_id, schema)

@router.get("/", response_model=List[ReminderResponse])
async def list_reminders(
    user_id: str = Depends(get_current_user_id)
):
    """
    List all active and inactive reminder configurations for the authenticated user.
    """
    return await reminder_service.get_user_reminders(user_id)

@router.get("/{id}", response_model=ReminderResponse)
async def get_reminder(
    id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieve details of a specific reminder schedule.
    """
    return await reminder_service.get_reminder(id, user_id)

@router.put("/{id}", response_model=ReminderResponse)
async def update_reminder(
    id: str,
    schema: ReminderUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Update an existing reminder schedule (times, timezone, or description).
    """
    return await reminder_service.update_reminder(id, user_id, schema)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Permanently delete a reminder configuration.
    """
    await reminder_service.delete_reminder(id, user_id)

@router.post("/{id}/action", response_model=ReminderLogResponse, status_code=status.HTTP_201_CREATED)
async def log_reminder_action(
    id: str,
    schema: ReminderLogCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Log a response action to a scheduled reminder (e.g., TAKEN, MISSED, SNOOZED).
    """
    return await reminder_service.log_action(id, user_id, schema)

@router.get("/history/logs", response_model=List[ReminderLogResponse])
async def get_reminder_history(
    reminder_id: Optional[str] = Query(None, description="Filter logs by a specific reminder schedule"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Fetch history logs of reminder dispatches and user responses.
    """
    return await reminder_service.get_logs(user_id, reminder_id)
