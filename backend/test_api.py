import asyncio
import logging
from unittest.mock import patch
from bson import ObjectId
from datetime import datetime

# Setup Mock Collections
class MockCursor:
    def __init__(self, data):
        self.data = data
    async def to_list(self, length=100):
        return self.data
    def sort(self, key, direction=1):
        return self

class MockCollection:
    def __init__(self):
        self.docs = []
    
    async def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        class InsertResult:
            inserted_id = doc["_id"]
        return InsertResult()
        
    async def delete_many(self, query):
        self.docs = [d for d in self.docs if not self._match(d, query)]
        
    async def find_one(self, query):
        for d in self.docs:
            if self._match(d, query):
                return d
        return None
        
    async def find_one_and_update(self, query, update, upsert=False, return_document=None):
        doc = await self.find_one(query)
        if not doc:
            if upsert:
                doc = query.copy()
                if "_id" not in doc:
                    doc["_id"] = ObjectId()
                self.docs.append(doc)
            else:
                return None
        if "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
        return doc
        
    def find(self, query):
        matched = [d for d in self.docs if self._match(d, query)]
        return MockCursor(matched)
        
    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc and "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
                
    def _match(self, doc, query):
        for k, v in query.items():
            if k == "_id":
                val = str(doc.get(k))
                comp = str(v)
                if val != comp:
                    return False
            elif doc.get(k) != v:
                return False
        return True

class MockDatabase:
    def __init__(self):
        self.health_reports = MockCollection()
        self.report_chunks = MockCollection()
        self.profiles = MockCollection()
        self.messages = MockCollection()
        self.conversations = MockCollection()
        self.audit_logs = MockCollection()

# Instantiate Database Mock and patch it globally
mock_db = MockDatabase()
patcher = patch("app.database.mongodb.get_database", return_value=mock_db)
patcher.start()

# Now import services after patching database
from app.config.config import settings
from app.auth.firebase_auth import verify_firebase_token
from app.services.s3_service import s3_service
from app.services.textract_service import textract_service
from app.services.vector_search_service import vector_search_service
from app.services.ai_service import ai_service

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestVerifier")

async def run_tests():
    logger.info("=== Starting Automated Verification Pipeline ===")
    
    # Force mock mode override for offline test runs
    ai_service.api_key_configured = False
    vector_search_service.api_key_configured = False
    
    # 1. Test Mock Auth Validation
    logger.info("Test 1: Decoding mock Firebase token...")
    user_payload = await verify_firebase_token("mock_test-user-123_admin")
    assert user_payload["uid"] == "test-user-123", "User ID mapping failed"
    assert "Admin" in user_payload["roles"], "Role mapping failed"
    logger.info("✅ Test 1: Mock auth mapping succeeded.")

    # 2. Test S3 and Textract Ingestion
    logger.info("Test 2: Uploading file content to mock S3...")
    s3_key = await s3_service.upload_file(b"Mock PDF File Bytes", "test_report.pdf")
    assert s3_key == "reports/test_report.pdf", "S3 path failed"
    
    logger.info("Test 2.1: Running AWS Textract Mock on S3 Object...")
    extracted_text = await textract_service.extract_text(s3_key)
    assert "Vitamin D" in extracted_text, "Textract parser failed"
    logger.info("✅ Test 2: Ingestion and text parsing succeeded.")

    # 3. Test Vector Search Indexing
    logger.info("Test 3: Chunking & Indexing document text...")
    await vector_search_service.ingest_report(
        report_id="66822c954e3cb41122ef3f5a",
        user_id="test-user-123",
        text=extracted_text
    )
    
    logger.info("Test 3.1: Running semantic search query on index...")
    chunks = await vector_search_service.semantic_search(
        user_id="test-user-123",
        query="What is my Vitamin D reference level?"
    )
    assert len(chunks) > 0, "No chunks returned"
    assert "Vitamin D" in chunks[0], "Semantic context match failed"
    logger.info("✅ Test 3: Document vector indexing and search matches succeeded.")

    # Run AI reasoning engine tests in BOTH reasoning modes to verify full logic
    for mode in ["lite", "enterprise"]:
        logger.info(f"--- Running AI Chat Tests in reasoning mode: {mode.upper()} ---")
        settings.AI_REASONING_MODE = mode

        # 4. Test AI RAG chat response & Emergency intercept
        logger.info("Test 4: Requesting RAG AI chat reply from TARA...")
        reply = await ai_service.generate_response(
            user_id="test-user-123",
            query="Tell me about my vitamin D.",
            profile={"name": "Sarah", "gender": "Female", "ageRange": "25-34"}
        )
        assert "18.5" in reply, "AI failed to ground context"
        assert "Sarah" in reply, "AI failed to address user name"
        logger.info("✅ Test 4: RAG prompt generation and context grounding succeeded.")

        # 5. Test Safety emergency override
        logger.info("Test 5: Testing emergency symptom override safety guard...")
        emergency_reply = await ai_service.generate_response(
            user_id="test-user-123",
            query="I have severe chest pain and breathing difficulty",
            profile={"name": "Sarah"}
        )
        assert "⚠️" in emergency_reply, "Safety warning intercept failed"
        assert "URGENT" in emergency_reply, "Emergency warning alert failed"
        logger.info("✅ Test 5: Emergency safety guard system successfully triggered.")

        # 6. Test Off-topic rejection guardrail
        logger.info("Test 6: Testing off-topic query rejection guardrail...")
        offtopic_reply = await ai_service.generate_response(
            user_id="test-user-123",
            query="Can you write a Python function to sort an array?",
            profile={"name": "Sarah"}
        )
        assert "OFF-TOPIC REJECTION" in offtopic_reply, "Off-topic query rejection failed"
        assert "dedicated AI Health Co-Pilot" in offtopic_reply, "Off-topic description failed"
        logger.info("✅ Test 6: Off-topic query rejection successfully triggered.")

    logger.info("=== All Verification Tests Passed Successfully! ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
