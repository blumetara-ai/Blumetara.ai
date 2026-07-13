from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.database.mongo import get_database

class HealthReportRepository:
    def __init__(self):
        pass

    @property
    def reports_collection(self):
        return get_database()["health_reports"]

    @property
    def chunks_collection(self):
        return get_database()["report_chunks"]

    def _serialize_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def create(self, user_id: str, file_name: str, s3_key: str) -> Dict[str, Any]:
        doc = {
            "user_id": user_id,
            "file_name": file_name,
            "s3_key": s3_key,
            "status": "uploaded",
            "ocr_confidence": None,
            "extracted_text": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await self.reports_collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return doc

    async def get_by_id(self, report_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(report_id):
            return None
        doc = await self.reports_collection.find_one({"_id": ObjectId(report_id)})
        return self._serialize_doc(doc)

    async def get_user_reports(self, user_id: str) -> List[Dict[str, Any]]:
        cursor = self.reports_collection.find({"user_id": user_id}).sort("created_at", -1)
        results = []
        async for doc in cursor:
            results.append(self._serialize_doc(doc))
        return results

    async def update_status(
        self, 
        report_id: str, 
        status: str, 
        ocr_confidence: Optional[float] = None, 
        extracted_text: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(report_id):
            return None
            
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        if ocr_confidence is not None:
            update_data["ocr_confidence"] = ocr_confidence
        if extracted_text is not None:
            update_data["extracted_text"] = extracted_text
            
        result = await self.reports_collection.find_one_and_update(
            {"_id": ObjectId(report_id)},
            {"$set": update_data},
            return_document=True
        )
        return self._serialize_doc(result)

    async def delete(self, report_id: str, user_id: str) -> bool:
        if not ObjectId.is_valid(report_id):
            return False
            
        # Delete report metadata
        result = await self.reports_collection.delete_one(
            {"_id": ObjectId(report_id), "user_id": user_id}
        )
        # Delete associated chunks
        await self.chunks_collection.delete_many({"report_id": report_id})
        return result.deleted_count > 0

    async def store_chunks(self, report_id: str, user_id: str, chunks: List[str], embeddings: List[List[float]]) -> None:
        """
        Inserts document chunks and associated vector embeddings into report_chunks collection.
        """
        if not chunks:
            return
            
        chunk_docs = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_docs.append({
                "report_id": report_id,
                "user_id": user_id,
                "chunk_index": idx,
                "chunk_text": chunk_text,
                "embedding": embedding,
                "created_at": datetime.utcnow()
            })
            
        await self.chunks_collection.insert_many(chunk_docs)
