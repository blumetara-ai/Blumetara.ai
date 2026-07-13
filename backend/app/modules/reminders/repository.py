from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database.mongo import get_database
from app.modules.reminders.schemas import ReminderCreate, ReminderUpdate, ReminderLogCreate

class ReminderRepository:
    def __init__(self):
        # Collections are initialized lazily because mongo connection is established on app startup
        pass

    @property
    def reminders_collection(self):
        return get_database()["reminders"]

    @property
    def logs_collection(self):
        return get_database()["reminder_logs"]

    def _serialize_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def create(self, user_id: str, schema: ReminderCreate) -> Dict[str, Any]:
        doc = schema.model_dump()
        doc["user_id"] = user_id
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        
        result = await self.reminders_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def get_by_id(self, reminder_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(reminder_id):
            return None
        doc = await self.reminders_collection.find_one({"_id": ObjectId(reminder_id)})
        return self._serialize_doc(doc)

    async def get_user_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.reminders_collection.find({"user_id": user_id})
        results = []
        async for doc in cursor:
            results.append(self._serialize_doc(doc))
        return results

    async def get_all_active(self) -> List[Dict[str, Any]]:
        cursor = self.reminders_collection.find({"is_active": True})
        results = []
        async for doc in cursor:
            results.append(self._serialize_doc(doc))
        return results

    async def update(self, reminder_id: str, user_id: str, schema: ReminderUpdate) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(reminder_id):
            return None
        
        update_data = {k: v for k, v in schema.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_by_id(reminder_id)
            
        update_data["updated_at"] = datetime.utcnow()
        
        result = await self.reminders_collection.find_one_and_update(
            {"_id": ObjectId(reminder_id), "user_id": user_id},
            {"$set": update_data},
            return_document=True
        )
        return self._serialize_doc(result)

    async def delete(self, reminder_id: str, user_id: str) -> bool:
        if not ObjectId.is_valid(reminder_id):
            return False
        
        result = await self.reminders_collection.delete_one(
            {"_id": ObjectId(reminder_id), "user_id": user_id}
        )
        return result.deleted_count > 0

    async def create_log(self, user_id: str, reminder_id: str, type_val: str, med_name: Optional[str], schema: ReminderLogCreate) -> Dict[str, Any]:
        doc = schema.model_dump()
        doc["user_id"] = user_id
        doc["reminder_id"] = reminder_id
        doc["type"] = type_val
        doc["medicine_name"] = med_name
        doc["logged_at"] = datetime.utcnow()
        
        result = await self.logs_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def get_user_logs(self, user_id: str, reminder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = {"user_id": user_id}
        if reminder_id:
            query["reminder_id"] = reminder_id
            
        cursor = self.logs_collection.find(query).sort("logged_at", -1)
        results = []
        async for doc in cursor:
            results.append(self._serialize_doc(doc))
        return results
