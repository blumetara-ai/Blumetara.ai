from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.database.mongo import connect_to_mongo, close_mongo_connection
from app.modules.reminders.scheduler import init_scheduler, shutdown_scheduler
from app.api.v1.router import api_router

# Setup logger configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing database connection...")
    await connect_to_mongo()
    
    logger.info("Initializing background scheduler...")
    init_scheduler()
    
    yield
    
    # Shutdown tasks
    logger.info("Shutting down background scheduler...")
    shutdown_scheduler()
    
    logger.info("Closing database connection...")
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API monolith powering TARA AI health co-pilot, report OCR ingestion, and proactive reminders.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configurations for mobile/web accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registrations
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "status": "healthy",
        "api_v1_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
