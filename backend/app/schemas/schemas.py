from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Auth & Profile
class UserProfileUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    ageRange: str = Field(..., description="e.g. '25-34'")
    gender: str = Field(..., description="e.g. 'Male', 'Female', 'Other'")
    preferences: Optional[dict] = None

# Chat
class ChatMessageCreate(BaseModel):
    conversationId: Optional[str] = None
    query: str = Field(..., min_length=1)

# Health Goals
class GoalCreate(BaseModel):
    goalType: str = Field(..., description="weight | water | steps | sleep | workout | custom")
    targetValue: float
    currentValue: float
    unit: str
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None

class GoalProgressCreate(BaseModel):
    value: float
    notes: Optional[str] = None

# Reminders
class ReminderCreate(BaseModel):
    type: str = Field(..., description="medicine | water | goal")
    medicineName: Optional[str] = None
    dosage: Optional[str] = None
    time: str = Field(..., description="HH:MM format")
    frequency: str = Field("daily", description="daily | weekly | custom")
    daysOfWeek: Optional[List[int]] = None
    timezone: str = Field("UTC")

# Food Logs
class FoodLogCreate(BaseModel):
    items: str = Field(..., description="e.g., 'Oatmeal with honey and almonds'")
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None

# Workout Plans
class WorkoutPlanCreate(BaseModel):
    fitnessGoal: str = Field(..., description="fat_loss | muscle_gain | general_fitness")
    difficulty: str = Field("beginner", description="beginner | intermediate | advanced")
    schedule: Optional[List[str]] = None
