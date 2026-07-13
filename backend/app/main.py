import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config import settings
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.endpoints import router as api_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered healthcare assistant backend for Blumetara AI.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS Middleware
# Allowing cross-origin requests from Flutter app (web / mobile emulator ports) and React Admin Panel.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins (e.g. your Next.js domain)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import asyncio
from app.utils.scheduler import start_reminder_scheduler

# Register Database Lifecycles
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    asyncio.create_task(start_reminder_scheduler())

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "docs": "/docs"
    }
