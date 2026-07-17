from fastapi import APIRouter
from app.api.v1.reminder_routes import router as reminder_router
from app.api.v1.report_routes import router as report_router

api_router = APIRouter()
api_router.include_router(reminder_router)
api_router.include_router(report_router)
