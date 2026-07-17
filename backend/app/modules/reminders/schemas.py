from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from enum import Enum
from datetime import datetime
import re

class ReminderType(str, Enum):
    MEDICINE = "MEDICINE"
    WATER = "WATER"

class ReminderAction(str, Enum):
    TAKEN = "TAKEN"
    MISSED = "MISSED"
    SNOOZED = "SNOOZED"

class ReminderCreate(BaseModel):
    type: ReminderType
    medicine_name: Optional[str] = None
    dose: Optional[str] = None
    times: List[str] = Field(..., description="List of times in 24-hour HH:MM format")
    timezone: str = Field(default="Asia/Kolkata", description="Timezone of the user")
    is_active: bool = True

    @field_validator("times")
    @classmethod
    def validate_times(cls, v: List[str]) -> List[str]:
        time_regex = re.compile(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
        for time_str in v:
            if not time_regex.match(time_str):
                raise ValueError(f"Time '{time_str}' must be in 24-hour HH:MM format")
        return v

    @model_validator(mode="after")
    def validate_medicine(self) -> 'ReminderCreate':
        if self.type == ReminderType.MEDICINE and not self.medicine_name:
            raise ValueError("medicine_name is required when reminder type is MEDICINE")
        return self

class ReminderUpdate(BaseModel):
    medicine_name: Optional[str] = None
    dose: Optional[str] = None
    times: Optional[List[str]] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("times")
    @classmethod
    def validate_times(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        time_regex = re.compile(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
        for time_str in v:
            if not time_regex.match(time_str):
                raise ValueError(f"Time '{time_str}' must be in 24-hour HH:MM format")
        return v

class ReminderResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    type: ReminderType
    medicine_name: Optional[str] = None
    dose: Optional[str] = None
    times: List[str]
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ReminderLogCreate(BaseModel):
    action: ReminderAction
    scheduled_time: datetime = Field(..., description="Target time the reminder was scheduled for")

class ReminderLogResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    reminder_id: str
    type: ReminderType
    medicine_name: Optional[str] = None
    action: ReminderAction
    scheduled_time: datetime
    logged_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
