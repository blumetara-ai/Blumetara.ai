import os
import sys
import asyncio
import logging
from unittest.mock import patch
from bson import ObjectId

# Ensure app is on path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to show engine traces neatly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TARA-Shell")

# Setup Mock Collections for local memory database
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

# Now import services
from app.config.config import settings
from app.services.ai_service import ai_service
from app.services.vector_search_service import vector_search_service

async def interactive_chat():
    print("==================================================================")
    print("      TARA AI AGENT - INTERACTIVE DEVELOPMENT TERMINAL")
    print("==================================================================")
    
    # 1. Ask for API Key configuration
    api_key = input("\nEnter your Gemini API Key (or press [Enter] to run in Mock Mode): ").strip()
    if api_key:
        settings.GEMINI_API_KEY = api_key
        ai_service.api_key_configured = True
        vector_search_service.api_key_configured = True
        # Re-configure library
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        print("✅ Gemini Live Mode activated.")
    else:
        print("ℹ️ Running in Mock Fallback Mode.")

    # 2. Setup Mode
    print("\nSelect Reasoning Mode:")
    print("  [1] LITE mode (Single-Agent, cheap & fast)")
    print("  [2] ENTERPRISE mode (Parallel-Isolated Multi-Agent Consensus)")
    mode_choice = input("Select [1/2] (Default: 1): ").strip()
    if mode_choice == "2":
        settings.AI_REASONING_MODE = "enterprise"
        print("⚡ ENTERPRISE parallel-isolated consensus enabled.")
    else:
        settings.AI_REASONING_MODE = "lite"
        print("⚡ LITE single-agent reasoning enabled.")

    # 3. Setup User Profile
    print("\n--- Setup User Profile ---")
    user_name = input("User Name (Default: Sarah): ").strip() or "Sarah"
    gender = input("Gender (Default: Female): ").strip() or "Female"
    age = input("Age (Default: 29): ").strip() or "29"
    profile = {"name": user_name, "gender": gender, "ageRange": age}
    
    # 4. Ask to upload a mock lab report for RAG testing
    print("\nDo you want to simulate uploading a deficient Vitamin D blood test report?")
    rag_choice = input("Simulate upload? [y/n] (Default: y): ").strip().lower()
    if rag_choice != "n":
        mock_text = (
            f"LABORATORY TEST REPORT\n"
            f"Patient Name: {user_name}\n"
            f"--- RESULTS ---\n"
            f"Vitamin D, 25-Hydroxy: 18.5 ng/mL (Reference Range: 30.0 - 100.0 ng/mL - STATUS: DEFICIENT)\n"
            f"Iron, Serum: 85 ug/dL (Reference Range: 50 - 170 ug/dL - STATUS: NORMAL)"
        )
        # Ingest text chunks and local vector search database mock
        await vector_search_service.ingest_report(
            report_id="66822c954e3cb41122ef3f5a",
            user_id="test-user-shell",
            text=mock_text
        )
        print("✅ Mock report uploaded and indexed in vector store.")
    else:
        print("ℹ️ Starting with empty health context.")

    print("\nChat session active. Type 'exit' or 'quit' to close.")
    print("------------------------------------------------------------------")
    
    while True:
        try:
            query = input(f"\n[{user_name}] > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye from TARA!")
                break
                
            print("\nTARA is thinking...")
            reply = await ai_service.generate_response(
                user_id="test-user-shell",
                query=query,
                profile=profile
            )
            print(f"\n[TARA] 🤖\n{reply}")
            print("\n" + "="*50)
            
        except KeyboardInterrupt:
            print("\nGoodbye from TARA!")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(interactive_chat())
