import httpx
import logging
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        if settings.MOCK_SERVICES or not settings.GEMINI_API_KEY:
            logger.info("RAGService initialized in DEV mode. Simulating embeddings.")
        else:
            logger.info("RAGService initialized in PROD mode. Using Gemini API (text-embedding-004).")

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """
        Split raw text into structured chunks of `chunk_size` characters with `overlap` overlap.
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            if end == text_len:
                break
            start += chunk_size - overlap
            
        return chunks

    async def generate_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """
        Call Gemini API to generate vector embeddings for a list of text chunks.
        Falls back to dummy vectors if running in mock/dev mode.
        """
        if settings.MOCK_SERVICES or not settings.GEMINI_API_KEY:
            # Return dummy 768-dimension vectors (all 0.0 except the index)
            logger.info(f"Generating {len(chunks)} mock embeddings (768-dim)")
            dummy_vectors = []
            for i in range(len(chunks)):
                dummy_vec = [0.0] * 768
                dummy_vec[i % 768] = 1.0  # simple orthogonal-like mock vectors
                dummy_vectors.append(dummy_vec)
            return dummy_vectors

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={settings.GEMINI_API_KEY}"
            embeddings = []
            
            async with httpx.AsyncClient() as client:
                for chunk in chunks:
                    payload = {
                        "model": "models/text-embedding-004",
                        "content": {
                            "parts": [{"text": chunk}]
                        }
                    }
                    response = await client.post(url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    vector = data["embedding"]["values"]
                    embeddings.append(vector)
                    
            logger.info(f"Generated {len(embeddings)} embeddings using Gemini text-embedding-004")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate Gemini embeddings: {str(e)}")
            raise

rag_service = RAGService()
