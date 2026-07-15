import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure backend app is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Setup in-memory mock database for offline safety
from unittest.mock import patch
from bson import ObjectId

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
        return type('Result', (object,), {"inserted_id": doc["_id"]})()
    async def delete_many(self, query):
        pass
    async def find_one(self, query):
        return None
    def find(self, query):
        matched = [d for d in self.docs if d.get("userId") == query.get("userId")]
        return MockCursor(matched)

class MockDatabase:
    def __init__(self):
        self.health_reports = MockCollection()
        self.report_chunks = MockCollection()
        self.profiles = MockCollection()
        self.messages = MockCollection()
        self.conversations = MockCollection()
        self.audit_logs = MockCollection()

mock_db = MockDatabase()
patcher = patch("app.database.mongodb.get_database", return_value=mock_db)
patcher.start()

# Import configuration and services
from app.config.config import settings
from app.services.ai_service import ai_service
from app.services.vector_search_service import vector_search_service

async def run_live_check():
    print("==================================================================")
    print("              TARA AI AGENT - LIVE TEST RUNNER")
    print("==================================================================")
    
    # 1. Print status
    if not settings.GEMINI_API_KEY:
        print("❌ Error: GEMINI_API_KEY is not set in backend/.env!")
        print("Please open backend/.env in VS Code, add your key, and save it first.")
        return
        
    print(f"✅ Loaded API Key from .env: {settings.GEMINI_API_KEY[:8]}...")
    print(f"Reasoning Mode Configured: {settings.AI_REASONING_MODE.upper()}")
    
    # 2. Add sample RAG context to local memory
    mock_text = (
        "Patient Vitamin D, 25-Hydroxy level is 18.5 ng/mL.\n"
        "Reference Range: 30.0 - 100.0 ng/mL. Status: DEFICIENT."
    )
    await vector_search_service.ingest_report(
        report_id="test-report-id",
        user_id="test-user-run",
        text=mock_text
    )
    print("✅ Ingested mock lab results into local memory store.")
    
    # 3. Trigger Live Query
    query = "What should I do about my vitamin D?"
    print(f"\nSending Query to Google Gemini: \"{query}\"...")
    
    try:
        reply = await ai_service.generate_response(
            user_id="test-user-run",
            query=query,
            profile={"name": "Sarah", "gender": "Female", "ageRange": "25-34"}
        )
        print("\n------------------------- TARA RESPONSE -------------------------")
        print(reply)
        print("------------------------------------------------------------------")
        print("\n🎉 Live API Connection Check Completed Successfully!")
    except Exception as e:
        print(f"\n❌ API Call Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_live_check())
