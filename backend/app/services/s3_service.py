import os
import logging
import boto3
from botocore.exceptions import ClientError
from app.config.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.is_mock = (settings.AWS_ACCESS_KEY_ID == "mock_key" or settings.AWS_SECRET_ACCESS_KEY == "mock_secret")
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.local_dir = os.path.join(backend_dir, "local_s3_mock")
        
        if self.is_mock:
            logger.warning("AWS Credentials not configured. S3 Service running in LOCAL MOCK mode.")
            os.makedirs(self.local_dir, exist_ok=True)
        else:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
            except Exception as e:
                logger.error(f"Failed to initialize Boto3 S3 Client: {e}. Defaulting to mock mode.")
                self.is_mock = True
                os.makedirs(self.local_dir, exist_ok=True)

    async def upload_file(self, file_content: bytes, file_name: str, folder: str = "reports") -> str:
        s3_key = f"{folder}/{file_name}"
        
        if self.is_mock:
            file_path = os.path.join(self.local_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info(f"Mock S3: Saved file locally to {file_path}")
            return s3_key
            
        try:
            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_content
            )
            logger.info(f"Successfully uploaded {s3_key} to AWS S3.")
            return s3_key
        except ClientError as e:
            logger.error(f"S3 Upload failed: {e}")
            raise e

    async def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        if self.is_mock:
            # Return a local server URL serving the mock file
            file_name = s3_key.split("/")[-1]
            return f"http://localhost:8000/api/v1/reports/mock-download/{file_name}"
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.S3_BUCKET_NAME, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned S3 URL: {e}")
            return ""

s3_service = S3Service()
