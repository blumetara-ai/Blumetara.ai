from bson import ObjectId
from fastapi import HTTPException, status
import logging
from typing import List, Dict, Any, Optional
from app.modules.health_reports.repository import HealthReportRepository
from app.modules.health_reports.schemas import ReportUploadInitiate, ReportUploadResponse
from app.services.storage_service import storage_service
from app.services.ocr_service import ocr_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

class HealthReportService:
    def __init__(self):
        self.repository = HealthReportRepository()

    async def initiate_upload(self, user_id: str, schema: ReportUploadInitiate) -> Dict[str, Any]:
        """
        Request upload authorization, create pending DB metadata, and generate pre-signed upload credentials.
        """
        report_id = str(ObjectId())
        
        # Generate upload details
        upload_details = await storage_service.generate_upload_url(
            user_id=user_id,
            report_id=report_id,
            file_name=schema.file_name,
            file_type=schema.file_type
        )
        
        # Create record in database
        await self.repository.create(
            user_id=user_id,
            file_name=schema.file_name,
            s3_key=upload_details["s3_key"]
        )
        
        return {
            "report_id": report_id,
            "upload_url": upload_details["upload_url"],
            "s3_key": upload_details["s3_key"],
            "fields": upload_details.get("fields", {})
        }

    async def process_report(self, report_id: str, user_id: str) -> None:
        """
        Runs the full document intelligence pipeline:
        OCR extraction -> Chunking -> Embeddings -> Vector DB save.
        Designed to run asynchronously in a background thread.
        """
        logger.info(f"Starting background processing for report {report_id} (User: {user_id})")
        
        # Load report metadata
        report = await self.repository.get_by_id(report_id)
        if not report or report["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
            
        if report.get("status") == "processed":
            logger.info(f"Report {report_id} is already processed. Short-circuiting.")
            return

        try:
            # 1. Update status to queued
            await self.repository.update_status(report_id, "queued")
            s3_key = report["s3_key"]
            
            # 2. Extract text (OCR)
            await self.repository.update_status(report_id, "processing_ocr")
            ocr_result = await ocr_service.extract_text(s3_key)
            extracted_text = ocr_result["text"]
            confidence = ocr_result["confidence"]
            
            # 3. Chunk text
            await self.repository.update_status(report_id, "processing_chunks")
            chunks = rag_service.chunk_text(extracted_text)
            
            # 4. Generate embeddings and save
            if chunks:
                await self.repository.update_status(report_id, "processing_embeddings")
                embeddings = await rag_service.generate_embeddings(chunks)
                
                # Store text chunks with high-dimensional vector embeddings
                await self.repository.store_chunks(
                    report_id=report_id,
                    user_id=user_id,
                    chunks=chunks,
                    embeddings=embeddings
                )
                
            # 5. Finalize status
            await self.repository.update_status(
                report_id=report_id,
                status="processed",
                ocr_confidence=confidence,
                extracted_text=extracted_text
            )
            logger.info(f"Successfully processed report {report_id}")
            
        except Exception as e:
            logger.error(f"Failed to process report {report_id}: {str(e)}")
            await self.repository.update_status(report_id, "failed")

    async def get_report(self, report_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get report metadata and a temporary pre-signed download URL.
        """
        report = await self.repository.get_by_id(report_id)
        if report is None or report["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
            
        # Enforce temporary S3 download link security (expiry: 15 mins)
        download_url = await storage_service.generate_download_url(report["s3_key"])
        report["download_url"] = download_url
        return report

    async def list_reports(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.repository.get_user_reports(user_id)

    async def delete_report(self, report_id: str, user_id: str) -> None:
        # Verify ownership
        report = await self.get_report(report_id, user_id)
        
        # Delete S3 binary object
        await storage_service.delete_file(report["s3_key"])
        
        # Delete Mongo metadata and indices
        success = await self.repository.delete(report_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report could not be deleted"
            )

# Commit 1: feat(health-reports): define validation schemas for medical document uploads

# Commit 2: feat(health-reports): implement storage service pre-signed URL generation

# Commit 3: feat(health-reports): build AWS Textract/Gemini OCR text extraction engine

# Commit 4: feat(health-reports): build text chunking and vector embedding generation pipelines
