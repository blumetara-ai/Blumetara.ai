import os
import logging
from datetime import datetime
from bson import ObjectId
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, UploadFile, File, status
from fastapi.responses import FileResponse

from app.auth.firebase_auth import get_current_user, get_current_admin
from app.config.config import settings
from app.database.mongodb import get_database
from app.schemas.schemas import (
    UserProfileUpdate, ChatMessageCreate, GoalCreate, 
    GoalProgressCreate, ReminderCreate, FoodLogCreate, WorkoutPlanCreate
)
from app.services.s3_service import s3_service
from app.services.textract_service import textract_service
from app.services.vector_search_service import vector_search_service
from app.services.ai_service import ai_service
from app.utils.scheduler import calculate_next_run

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper to serialize MongoDB ObjectIds
def serialize_doc(doc):
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    return doc

def serialize_list(cursor_list):
    return [serialize_doc(doc) for doc in cursor_list]

# =====================================================================
# AUTH & PROFILE ENDPOINTS
# =====================================================================

@router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "user": current_user
    }

@router.get("/users/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    db = get_database()
    profile = await db.profiles.find_one({"userId": current_user["uid"]})
    if not profile:
        # Create empty profile
        profile = {
            "userId": current_user["uid"],
            "name": current_user.get("name", "User"),
            "ageRange": "Unspecified",
            "gender": "Unspecified",
            "preferences": {"units": "metric", "theme": "dark"},
            "createdAt": datetime.utcnow()
        }
        await db.profiles.insert_one(profile)
    return serialize_doc(profile)

@router.put("/users/profile")
async def update_profile(profile_data: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    update_result = await db.profiles.find_one_and_update(
        {"userId": current_user["uid"]},
        {
            "$set": {
                "name": profile_data.name,
                "ageRange": profile_data.ageRange,
                "gender": profile_data.gender,
                "preferences": profile_data.preferences or {"units": "metric", "theme": "dark"},
                "updatedAt": datetime.utcnow()
            }
        },
        upsert=True,
        return_document=True
    )
    return serialize_doc(update_result)

# =====================================================================
# HEALTH REPORT & AWS TEXTRACT ENDPOINTS
# =====================================================================

@router.post("/reports/upload")
async def upload_report(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    db = get_database()
    
    file_bytes = await file.read()
    file_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
    
    try:
        # Upload raw file bytes to S3
        s3_key = await s3_service.upload_file(file_bytes, file_name, folder=f"reports/{current_user['uid']}")
        
        # Save metadata record in MongoDB
        report = {
            "userId": current_user["uid"],
            "s3Key": s3_key,
            "fileName": file.filename,
            "fileType": file.filename.split(".")[-1].lower(),
            "ocrStatus": "pending",
            "extractedText": "",
            "summary": "",
            "uploadedAt": datetime.utcnow()
        }
        result = await db.health_reports.insert_one(report)
        report["_id"] = str(result.inserted_id)
        
        # Log audit action
        await db.audit_logs.insert_one({
            "actorId": current_user["uid"],
            "action": "report_upload",
            "resourceType": "health_report",
            "resourceId": report["_id"],
            "createdAt": datetime.utcnow()
        })
        
        return {
            "status": "success",
            "message": "Report uploaded successfully. Extraction pending.",
            "report": serialize_doc(report)
        }
    except Exception as e:
        logger.error(f"Failed uploading health report: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/reports/mock-download/{file_name}")
async def download_mock_file(file_name: str):
    # Route for serving mock files stored locally when AWS S3 is bypassed
    local_path = os.path.join("/app/local_s3_mock", file_name)
    if os.path.exists(local_path):
        return FileResponse(local_path)
    raise HTTPException(status_code=404, detail="Mock file not found.")

@router.get("/reports")
async def list_reports(current_user: dict = Depends(get_current_user)):
    db = get_database()
    reports = await db.health_reports.find({"userId": current_user["uid"]}).sort("uploadedAt", -1).to_list(length=100)
    
    # Generate temporary viewing URLs for each report
    serialized_reports = serialize_list(reports)
    for r in serialized_reports:
        r["viewUrl"] = await s3_service.get_presigned_url(r["s3Key"])
    return serialized_reports

@router.get("/reports/{id}")
async def get_report(id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    report = await db.health_reports.find_one({"_id": ObjectId(id), "userId": current_user["uid"]})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    serialized = serialize_doc(report)
    serialized["viewUrl"] = await s3_service.get_presigned_url(report["s3Key"])
    return serialized

@router.post("/reports/{id}/analyze")
async def analyze_report(id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    report = await db.health_reports.find_one({"_id": ObjectId(id), "userId": current_user["uid"]})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    await db.health_reports.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"ocrStatus": "processing"}}
    )
    
    try:
        # 1. AWS Textract Extract
        extracted_text = await textract_service.extract_text(report["s3Key"])
        
        # 2. Ingest into Vector Search (RAG Pipeline)
        await vector_search_service.ingest_report(report_id=id, user_id=current_user["uid"], text=extracted_text)
        
        # 3. Generate Summary using TARA AI context
        summary_query = "Summarize the key metrics of this laboratory report. Focus on values outside normal reference ranges."
        profile = await db.profiles.find_one({"userId": current_user["uid"]})
        ai_summary = await ai_service.generate_response(
            user_id=current_user["uid"], 
            query=summary_query,
            profile=profile
        )
        
        # 4. Save updates in MongoDB
        await db.health_reports.update_one(
            {"_id": ObjectId(id)},
            {
                "$set": {
                    "ocrStatus": "completed",
                    "extractedText": extracted_text,
                    "summary": ai_summary,
                    "analyzedAt": datetime.utcnow()
                }
            }
        )
        
        return {
            "status": "success",
            "message": "Report analyzed successfully.",
            "summary": ai_summary
        }
    except Exception as e:
        logger.error(f"Analysis failed for report {id}: {e}")
        await db.health_reports.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"ocrStatus": "failed"}}
        )
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# =====================================================================
# CHAT & TARA AI ENDPOINTS
# =====================================================================

@router.post("/ai/chat")
async def chat_with_tara(chat_data: ChatMessageCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    
    conversation_id = chat_data.conversationId
    if not conversation_id:
        # Create new conversation thread
        conv_result = await db.conversations.insert_one({
            "userId": current_user["uid"],
            "title": f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "createdAt": datetime.utcnow(),
            "lastMessageAt": datetime.utcnow()
        })
        conversation_id = str(conv_result.inserted_id)

    # 1. Fetch profile to inject user context and check daily chat quota
    profile = await db.profiles.find_one({"userId": current_user["uid"]})
    if not profile:
        profile = {
            "userId": current_user["uid"],
            "name": "User",
            "ageRange": "Unspecified",
            "gender": "Unspecified",
            "dailyChatCount": 0,
            "lastChatDate": ""
        }
        await db.profiles.insert_one(profile)

    # Enforce Daily Chat Quota limit (20 queries per day)
    today_str = datetime.now().strftime("%Y-%m-%d")
    last_chat_date = profile.get("lastChatDate", "")
    daily_chat_count = profile.get("dailyChatCount", 0)

    if last_chat_date == today_str:
        if daily_chat_count >= 20:
            raise HTTPException(
                status_code=429,
                detail="Daily chat quota exceeded. You have reached your limit of 20 messages per day."
            )
        new_count = daily_chat_count + 1
    else:
        new_count = 1

    # Update database profile with new count and date
    await db.profiles.update_one(
        {"userId": current_user["uid"]},
        {"$set": {"dailyChatCount": new_count, "lastChatDate": today_str}}
    )

    # 2. Get AI Response with RAG & safety filters
    response_text = await ai_service.generate_response(
        user_id=current_user["uid"],
        query=chat_data.query,
        profile=profile
    )
    
    # 3. Save User message
    await db.messages.insert_one({
        "conversationId": conversation_id,
        "role": "user",
        "content": chat_data.query,
        "createdAt": datetime.utcnow()
    })
    
    # 4. Save AI message
    await db.messages.insert_one({
        "conversationId": conversation_id,
        "role": "assistant",
        "content": response_text,
        "createdAt": datetime.utcnow()
    })
    
    # 5. Update Conversation timestamp
    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"lastMessageAt": datetime.utcnow()}}
    )
    
    return {
        "conversationId": conversation_id,
        "reply": response_text
    }

@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    db = get_database()
    conversations = await db.conversations.find({"userId": current_user["uid"]}).sort("lastMessageAt", -1).to_list(length=50)
    return serialize_list(conversations)

@router.get("/conversations/{id}/messages")
async def list_messages(id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    # Confirm ownership
    conv = await db.conversations.find_one({"_id": ObjectId(id), "userId": current_user["uid"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    messages = await db.messages.find({"conversationId": id}).sort("createdAt", 1).to_list(length=200)
    return serialize_list(messages)

# =====================================================================
# GOALS TRACKING ENDPOINTS
# =====================================================================

@router.post("/goals")
async def create_goal(goal_data: GoalCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    goal = {
        "userId": current_user["uid"],
        "goalType": goal_data.goalType,
        "targetValue": goal_data.targetValue,
        "currentValue": goal_data.currentValue,
        "unit": goal_data.unit,
        "startDate": goal_data.startDate or datetime.utcnow(),
        "endDate": goal_data.endDate,
        "active": True
    }
    result = await db.goals.insert_one(goal)
    goal["_id"] = str(result.inserted_id)
    return serialize_doc(goal)

@router.get("/goals")
async def get_goals(current_user: dict = Depends(get_current_user)):
    db = get_database()
    goals = await db.goals.find({"userId": current_user["uid"]}).to_list(length=100)
    return serialize_list(goals)

@router.post("/goals/{id}/progress")
async def log_goal_progress(id: str, progress_data: GoalProgressCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    # Find goal and verify ownership
    goal = await db.goals.find_one({"_id": ObjectId(id), "userId": current_user["uid"]})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    # Log checkpoint
    progress = {
        "goalId": id,
        "userId": current_user["uid"],
        "value": progress_data.value,
        "recordedAt": datetime.utcnow(),
        "notes": progress_data.notes
    }
    await db.goal_progress.insert_one(progress)
    
    # Update current value in primary goal document
    await db.goals.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"currentValue": progress_data.value}}
    )
    
    return {"status": "success", "currentValue": progress_data.value}

# =====================================================================
# MEDICATION & WATER REMINDER ENDPOINTS
# =====================================================================

@router.post("/reminders")
async def create_reminder(reminder_data: ReminderCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    
    # Save medicine profile if present
    med_id = None
    if reminder_data.type == "medicine" and reminder_data.medicineName:
        med_res = await db.medicines.insert_one({
            "userId": current_user["uid"],
            "name": reminder_data.medicineName,
            "dosage": reminder_data.dosage or "1 pill",
            "stockCount": 30, # Default initial count
            "active": True
        })
        med_id = str(med_res.inserted_id)
        
    reminder = {
        "userId": current_user["uid"],
        "type": reminder_data.type,
        "targetId": med_id,
        "time": reminder_data.time,
        "frequency": reminder_data.frequency,
        "daysOfWeek": reminder_data.daysOfWeek or [],
        "timezone": reminder_data.timezone,
        "active": True,
        "nextRunAt": calculate_next_run(reminder_data.time, reminder_data.timezone)
    }
    result = await db.reminders.insert_one(reminder)
    reminder["_id"] = str(result.inserted_id)
    return serialize_doc(reminder)

@router.get("/reminders")
async def list_reminders(current_user: dict = Depends(get_current_user)):
    db = get_database()
    reminders = await db.reminders.find({"userId": current_user["uid"]}).to_list(length=100)
    
    # If the reminder is a medicine, join details
    serialized = serialize_list(reminders)
    for r in serialized:
        if r.get("targetId"):
            med = await db.medicines.find_one({"_id": ObjectId(r["targetId"])})
            if med:
                r["medicineDetails"] = serialize_doc(med)
    return serialized

@router.post("/reminders/{id}/log")
async def log_reminder_adherence(id: str, status: str = "taken", current_user: dict = Depends(get_current_user)):
    db = get_database()
    # Log user compliance
    await db.notifications.insert_one({
        "userId": current_user["uid"],
        "reminderId": id,
        "status": status,
        "timestamp": datetime.utcnow()
    })
    return {"status": "success", "logged": status}

# =====================================================================
# FOOD LOGS (MOCK/COMING SOON PRESETS)
# =====================================================================

@router.post("/food-logs")
async def log_food(food_data: FoodLogCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    # Simple log entry
    log = {
        "userId": current_user["uid"],
        "items": food_data.items,
        "calories": food_data.calories or 250.0,
        "protein": food_data.protein or 10.0,
        "carbs": food_data.carbs or 30.0,
        "fat": food_data.fat or 8.0,
        "loggedAt": datetime.utcnow()
    }
    await db.food_logs.insert_one(log)
    return serialize_doc(log)

@router.get("/food-logs")
async def list_food(current_user: dict = Depends(get_current_user)):
    db = get_database()
    logs = await db.food_logs.find({"userId": current_user["uid"]}).sort("loggedAt", -1).to_list(length=50)
    return serialize_list(logs)

# =====================================================================
# WORKOUT MODULE ENDPOINTS
# =====================================================================

@router.post("/workout-plans")
async def generate_workout_plan(plan_data: WorkoutPlanCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    
    # AI generates personalized workout routine based on parameters
    difficulty = plan_data.difficulty
    goal = plan_data.fitnessGoal
    
    # Set default structures
    exercises = []
    if goal == "fat_loss":
        exercises = [
            {"name": "Jumping Jacks", "sets": 3, "reps": "30 secs"},
            {"name": "Bodyweight Squats", "sets": 4, "reps": "15 reps"},
            {"name": "Mountain Climbers", "sets": 3, "reps": "20 secs"},
            {"name": "Plank Hold", "sets": 3, "reps": "45 secs"}
        ]
    elif goal == "muscle_gain":
        exercises = [
            {"name": "Push-Ups", "sets": 4, "reps": "12 reps"},
            {"name": "Lunges", "sets": 3, "reps": "10 reps per leg"},
            {"name": "Dumbbell Rows (or water bottle equivalent)", "sets": 4, "reps": "12 reps"},
            {"name": "Glute Bridges", "sets": 3, "reps": "15 reps"}
        ]
    else: # General fitness
        exercises = [
            {"name": "Brisk Walk", "sets": 1, "reps": "20 mins"},
            {"name": "Bird-Dog Pose", "sets": 3, "reps": "10 reps"},
            {"name": "Squats", "sets": 3, "reps": "12 reps"},
            {"name": "Crunches", "sets": 3, "reps": "15 reps"}
        ]

    plan = {
        "userId": current_user["uid"],
        "fitnessGoal": goal,
        "difficulty": difficulty,
        "exercises": exercises,
        "schedule": plan_data.schedule or ["Monday", "Wednesday", "Friday"],
        "createdAt": datetime.utcnow()
    }
    
    # Save the workout plan
    await db.workout_plans.insert_one(plan)
    return serialize_doc(plan)

@router.get("/workout-plans")
async def get_workout_plan(current_user: dict = Depends(get_current_user)):
    db = get_database()
    plan = await db.workout_plans.find_one({"userId": current_user["uid"]}, sort=[("createdAt", -1)])
    if not plan:
        raise HTTPException(status_code=404, detail="No active workout plan found.")
    return serialize_doc(plan)

# =====================================================================
# ADMIN PANEL OPERATIONS (SECURE)
# =====================================================================

@router.get("/admin/users")
async def admin_list_users(admin: dict = Depends(get_current_admin)):
    db = get_database()
    users = await db.users.find().to_list(length=100)
    return serialize_list(users)

@router.get("/admin/audit-logs")
async def admin_list_audits(admin: dict = Depends(get_current_admin)):
    db = get_database()
    audits = await db.audit_logs.find().sort("createdAt", -1).to_list(length=200)
    return serialize_list(audits)
