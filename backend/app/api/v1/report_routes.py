from fastapi import APIRouter, Depends, status, BackgroundTasks, UploadFile, File, Response
from fastapi.responses import FileResponse
from typing import List
import os
import logging
from app.core.config import settings
from app.core.security import get_current_user_id
from app.modules.health_reports.schemas import ReportUploadInitiate, ReportUploadResponse, ReportResponse
from app.modules.health_reports.service import HealthReportService

router = APIRouter(prefix="/reports", tags=["Health Reports"])
report_service = HealthReportService()
logger = logging.getLogger(__name__)

@router.post("/upload-url", response_model=ReportUploadResponse, status_code=status.HTTP_201_CREATED)
async def initiate_report_upload(
    schema: ReportUploadInitiate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get secure pre-signed S3 upload parameters and initialize report metadata in MongoDB.
    """
    return await report_service.initiate_upload(user_id, schema)

@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    user_id: str = Depends(get_current_user_id)
):
    """
    List all uploaded medical reports for the authenticated user.
    """
    return await report_service.list_reports(user_id)

@router.get("/{id}", response_model=ReportResponse)
async def get_report_details(
    id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get report details, status, extraction text, and a pre-signed S3 download URL.
    """
    return await report_service.get_report(id, user_id)

@router.post("/{id}/process", status_code=status.HTTP_202_ACCEPTED)
async def process_report(
    id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id)
):
    """
    Manually trigger or retry OCR extraction and text embeddings indexing.
    """
    # Enforce ownership check before starting processing
    await report_service.get_report(id, user_id)
    background_tasks.add_task(report_service.process_report, id, user_id)
    return {"message": "Report processing started in the background", "report_id": id}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Permanently delete report files from object storage and erase document text/embeddings index.
    """
    await report_service.delete_report(id, user_id)


# --- LOCAL MOCK HELPER ENDPOINTS ---
# These routes are active only during DEV/MOCK mode to simulate S3 uploads and downloads locally.

@router.post("/mock-upload/{report_id}", status_code=status.HTTP_201_CREATED)
async def mock_s3_upload(
    report_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    DEV helper simulating S3 file storage uploads. Writes file to local storage and triggers the RAG pipeline.
    """
    if not settings.MOCK_SERVICES:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
        
    report = await report_service.repository.get_by_id(report_id)
    if not report:
        return Response(status_code=status.HTTP_404_NOT_FOUND, content="Report not registered")
        
    s3_key = report["s3_key"]
    local_path = os.path.join("./local_storage", s3_key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    # Save file contents locally
    with open(local_path, "wb") as f:
        f.write(await file.read())
        
    logger.info(f"[MOCK UPLOAD] File saved locally to {local_path}. Starting ingestion pipeline.")
    
    # Trigger RAG pipeline background tasks
    background_tasks.add_task(report_service.process_report, report_id, report["user_id"])
    
    return {
        "message": "Mock upload successful. Background extraction initiated.",
        "report_id": report_id,
        "local_path": local_path
    }

@router.get("/mock-download/{s3_key:path}")
async def mock_s3_download(s3_key: str):
    """
    DEV helper serving files stored in local mock storage folder.
    """
    if not settings.MOCK_SERVICES:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
        
    local_path = os.path.join("./local_storage", s3_key)
    if not os.path.exists(local_path):
        return Response(status_code=status.HTTP_404_NOT_FOUND, content="File not found")
        
    return FileResponse(local_path)
