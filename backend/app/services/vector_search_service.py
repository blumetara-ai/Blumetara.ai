import logging
import numpy as np
from app.config.config import settings
from app.database.mongodb import get_database
import google.generativeai as genai

logger = logging.getLogger(__name__)

class VectorSearchService:
    def __init__(self):
        self.api_key_configured = bool(settings.GEMINI_API_KEY)
        if self.api_key_configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        else:
            logger.warning("GEMINI_API_KEY not set. Vector search will generate mock embeddings.")

    def chunk_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
        if not text:
            return []
        words = text.split()
        chunks = []
        # Basic chunking by word count to keep layout clean
        step = chunk_size - chunk_overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
        return chunks

    async def generate_embedding(self, text: str) -> list[float]:
        if not self.api_key_configured:
            # Generate a reproducible mock embedding based on character hash (768 dimensions)
            np.random.seed(abs(hash(text)) % (2**32))
            mock_emb = np.random.uniform(-0.1, 0.1, 768).tolist()
            return mock_emb
            
        try:
            # Use Gemini embedding model
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Failed to generate Gemini embedding: {e}")
            # Fallback to random mock
            np.random.seed(abs(hash(text)) % (2**32))
            return np.random.uniform(-0.1, 0.1, 768).tolist()

    async def ingest_report(self, report_id: str, user_id: str, text: str):
        db = get_database()
        if db is None:
            logger.error("Database connection unavailable for RAG ingestion.")
            return

        chunks = self.chunk_text(text)
        logger.info(f"Ingesting report {report_id} into {len(chunks)} chunks...")
        
        # Clear existing chunks
        await db.report_chunks.delete_many({"reportId": report_id})
        
        for idx, chunk_text in enumerate(chunks):
            embedding = await self.generate_embedding(chunk_text)
            await db.report_chunks.insert_one({
                "reportId": report_id,
                "userId": user_id,
                "chunkIndex": idx,
                "chunkText": chunk_text,
                "embedding": embedding
            })
        logger.info(f"Successfully ingested report {report_id}.")

    async def semantic_search(self, user_id: str, query: str, limit: int = 3) -> list[str]:
        db = get_database()
        if db is None:
            return []

        query_emb = await self.generate_embedding(query)

        # 1. Try MongoDB Atlas Vector Search (production route)
        try:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_emb,
                        "numCandidates": limit * 5,
                        "limit": limit,
                        "filter": {"userId": user_id}
                    }
                }
            ]
            cursor = db.report_chunks.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            if results:
                logger.info("Retrieved chunks using Atlas Vector Search.")
                return [r["chunkText"] for r in results]
        except Exception as e:
            # Vector search index might not exist yet or local database is running
            logger.warning(f"Atlas Vector Search failed or unsupported locally ({e}). Falling back to local cosine calculation...")

        # 2. Local fallback: Fetch all chunks for this user and compute similarity in Python
        try:
            chunks = await db.report_chunks.find({"userId": user_id}).to_list(length=500)
            if not chunks:
                return []

            similarities = []
            q_vec = np.array(query_emb)
            
            for chunk in chunks:
                c_vec = np.array(chunk["embedding"])
                # Compute cosine similarity
                dot_prod = np.dot(q_vec, c_vec)
                norm_q = np.linalg.norm(q_vec)
                norm_c = np.linalg.norm(c_vec)
                
                similarity = dot_prod / (norm_q * norm_c) if norm_q > 0 and norm_c > 0 else 0
                similarities.append((similarity, chunk["chunkText"]))

            # Sort by similarity descending
            similarities.sort(key=lambda x: x[0], reverse=True)
            top_chunks = [text for score, text in similarities[:limit]]
            logger.info(f"Retrieved {len(top_chunks)} chunks using Python cosine similarity.")
            return top_chunks
            
        except Exception as ex:
            logger.error(f"Local similarity calculation failed: {ex}")
            return []

vector_search_service = VectorSearchService()
