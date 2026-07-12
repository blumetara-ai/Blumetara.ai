import os
import boto3
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.mock_dir = "./local_storage"
        if settings.MOCK_SERVICES:
            os.makedirs(self.mock_dir, exist_ok=True)
            logger.info(f"StorageService initialized in DEV mode. Mock uploads saved to: {self.mock_dir}")
        else:
            # Production AWS configuration
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            logger.info(f"StorageService initialized in PROD mode. Targeting S3 bucket: {settings.S3_BUCKET_NAME}")

    def _get_s3_key(self, user_id: str, report_id: str, file_name: str) -> str:
        # Sanitize filename
        safe_name = os.path.basename(file_name).replace(" ", "_")
        return f"users/{user_id}/reports/{report_id}/{safe_name}"

    async def generate_upload_url(self, user_id: str, report_id: str, file_name: str, file_type: str) -> Dict[str, Any]:
        s3_key = self._get_s3_key(user_id, report_id, file_name)
        
        if settings.MOCK_SERVICES:
            # In mock mode, we mock the pre-signed URL upload flow.
            # We return a local url endpoint that the developer can POST files to.
            mock_url = f"http://localhost:8000/api/v1/reports/mock-upload/{report_id}"
            return {
                "upload_url": mock_url,
                "s3_key": s3_key,
                "fields": {}
            }
            
        try:
            # Generate POST presigned url (highly convenient for direct frontend uploads)
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Fields={"Content-Type": file_type},
                Conditions=[
                    {"Content-Type": file_type},
                    ["content-length-range", 0, 20971520]  # Max 20MB
                ],
                ExpiresIn=900  # 15 mins
            )
            return {
                "upload_url": presigned_post["url"],
                "s3_key": s3_key,
                "fields": presigned_post["fields"]
            }
        except Exception as e:
            logger.error(f"Failed to generate presigned S3 upload URL: {str(e)}")
            raise

    async def generate_download_url(self, s3_key: str) -> str:
        if settings.MOCK_SERVICES:
            # Return path to locally stored mock file
            return f"http://localhost:8000/api/v1/reports/mock-download/{s3_key}"
            
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.S3_BUCKET_NAME,
                    "Key": s3_key
                },
                ExpiresIn=900  # 15 mins
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned S3 download URL: {str(e)}")
            raise

    async def delete_file(self, s3_key: str) -> bool:
        if settings.MOCK_SERVICES:
            # Delete local file if it exists
            local_path = os.path.join(self.mock_dir, s3_key)
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Deleted local mock report file: {local_path}")
            return True
            
        try:
            self.s3_client.delete_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key
            )
            logger.info(f"Deleted S3 report object: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 file: {str(e)}")
            return False

storage_service = StorageService()
