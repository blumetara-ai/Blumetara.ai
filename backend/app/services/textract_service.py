import os
import logging
import boto3
from app.config.config import settings

logger = logging.getLogger(__name__)

class TextractService:
    def __init__(self):
        self.is_mock = (settings.AWS_ACCESS_KEY_ID == "mock_key" or settings.AWS_SECRET_ACCESS_KEY == "mock_secret")
        
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
            # Generate a realistic mock medical report text
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

        try:
            # We call Textract using the S3 object reference
            response = self.textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': settings.S3_BUCKET_NAME,
                        'Name': s3_key
                    }
                }
            )
            
            # Reconstruct lines
            lines = []
            for block in response.get('Blocks', []):
                if block.get('BlockType') == 'LINE':
                    lines.append(block.get('Text', ''))
            
            extracted_text = "\n".join(lines)
            logger.info(f"Successfully processed Textract for {s3_key}.")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Textract processing failed: {e}")
            raise e

textract_service = TextractService()
