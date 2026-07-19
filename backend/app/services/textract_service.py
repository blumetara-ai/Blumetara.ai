import os
import logging
import boto3
import asyncio
from app.config.config import settings

logger = logging.getLogger(__name__)

class TextractService:
    def __init__(self):
        # Fall back to mock mode if using default local placeholders
        self.is_mock = (
            settings.AWS_ACCESS_KEY_ID in ["mock_key", "your_real_aws_access_key", "", None] or
            settings.AWS_SECRET_ACCESS_KEY in ["mock_secret", "your_real_aws_secret_key", "", None]
        )
        
        if not self.is_mock:
            try:
                self.textract_client = boto3.client(
                    'textract',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
            except Exception as e:
                logger.error(f"Failed to initialize Boto3 Textract Client: {e}. Defaulting to mock.")
                self.is_mock = True

    async def extract_text(self, s3_key: str) -> str:
        if self.is_mock:
            logger.info(f"Mock Textract: Extracting mock text for key {s3_key}")
            return (
                "Blumetara Diagnostics Lab\n"
                "Patient: John Doe, Age: 34, Gender: Male\n"
                "Date: 2026-06-15\n"
                "-------------------------------------------\n"
                "TEST NAME                RESULT      REFERENCE RANGE\n"
                "Vitamin D, 25-Hydroxy   18.5 ng/mL   [30.0 - 100.0] (DEFICIENT)\n"
                "Hemoglobin               14.2 g/dL    [13.8 - 17.2] (NORMAL)\n"
                "Thyroid Stimulating Hormone (TSH) 4.8 mIU/L [0.4 - 4.0] (HIGH)\n"
                "Cholesterol, Total       210 mg/dL    [< 200] (BORDERLINE HIGH)\n"
                "HbA1c                    5.9 %        [< 5.7 Normal, 5.7-6.4 Prediabetes] (PREDIABETIC)\n"
                "-------------------------------------------\n"
                "Notes: Patient complains of chronic fatigue and joint discomfort. Vitamin D supplementation recommended."
            )

        # Use asynchronous Textract processing for multi-page PDFs
        if s3_key.lower().endswith(".pdf"):
            try:
                logger.info(f"Triggering asynchronous Textract OCR for PDF key: {s3_key}")
                response = await asyncio.to_thread(
                    self.textract_client.start_document_text_detection,
                    DocumentLocation={
                        'S3Object': {
                            'Bucket': settings.S3_BUCKET_NAME,
                            'Name': s3_key
                        }
                    }
                )
                job_id = response['JobId']
                
                # Polling loop to wait for job completion
                while True:
                    status = await asyncio.to_thread(
                        self.textract_client.get_document_text_detection,
                        JobId=job_id
                    )
                    job_status = status['JobStatus']
                    if job_status in ['SUCCEEDED', 'FAILED']:
                        break
                    await asyncio.sleep(2)
                    
                if job_status == 'SUCCEEDED':
                    lines = []
                    next_token = None
                    # Iterate through all paginated blocks
                    while True:
                        params = {"JobId": job_id}
                        if next_token:
                            params["NextToken"] = next_token
                        
                        status_page = await asyncio.to_thread(
                            self.textract_client.get_document_text_detection,
                            **params
                        )
                        
                        for block in status_page.get('Blocks', []):
                            if block.get('BlockType') == 'LINE':
                                lines.append(block.get('Text', ''))
                                
                        next_token = status_page.get('NextToken')
                        if not next_token:
                            break
                            
                    extracted_text = "\n".join(lines)
                    logger.info(f"Successfully processed asynchronous Textract for PDF {s3_key}.")
                    return extracted_text
                else:
                    raise RuntimeError(f"Textract async job failed with status: {job_status}")
            except Exception as e:
                logger.error(f"Asynchronous Textract processing failed: {e}")
                raise e

        # Fallback to synchronous processing for single-page image files
        try:
            response = await asyncio.to_thread(
                self.textract_client.detect_document_text,
                Document={
                    'S3Object': {
                        'Bucket': settings.S3_BUCKET_NAME,
                        'Name': s3_key
                    }
                }
            )
            
            lines = []
            for block in response.get('Blocks', []):
                if block.get('BlockType') == 'LINE':
                    lines.append(block.get('Text', ''))
            
            extracted_text = "\n".join(lines)
            logger.info(f"Successfully processed synchronous Textract for {s3_key}.")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Textract synchronous processing failed: {e}")
            raise e

textract_service = TextractService()
