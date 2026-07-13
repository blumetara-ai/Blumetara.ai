import boto3
import logging
import asyncio
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        if settings.MOCK_SERVICES:
            logger.info("OCRService initialized in DEV mode. Simulating Textract.")
        else:
            self.textract_client = boto3.client(
                "textract",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            logger.info("OCRService initialized in PROD mode using AWS Textract.")

    async def extract_text(self, s3_key: str) -> Dict[str, Any]:
        """
        Extract text from report stored in S3.
        Supports PDF/JPEG/PNG.
        """
        if settings.MOCK_SERVICES:
            # Simulate latency
            await asyncio.sleep(1.5)
            # Standard mock clinical lab report text
            mock_text = (
                "METROPOLIS HEALTH LABORATORIES\n"
                "PATIENT DEMOGRAPHICS:\n"
                "Name: John Doe | Age: 42 | Gender: Male\n"
                "Date Collected: 2026-07-10\n"
                "\n"
                "TEST RESULTS:\n"
                "1. Fasting Blood Glucose: 112 mg/dL (Reference Range: 70 - 100 mg/dL) [HIGH]\n"
                "2. Total Cholesterol: 245 mg/dL (Reference Range: < 200 mg/dL) [HIGH]\n"
                "3. Triglycerides: 165 mg/dL (Reference Range: < 150 mg/dL) [HIGH]\n"
                "4. Hemoglobin (Hb): 15.2 g/dL (Reference Range: 13.8 - 17.2 g/dL) [NORMAL]\n"
                "5. Thyroid Stimulating Hormone (TSH): 2.4 mIU/L (Reference Range: 0.4 - 4.0 mIU/L) [NORMAL]\n"
                "\n"
                "CLINICAL NOTE:\n"
                "Fasting glucose levels indicate impaired fasting glucose (prediabetes). Elevated cholesterol "
                "suggests borderline hypercholesterolemia. Dietary modifications and exercise are recommended."
            )
            return {
                "text": mock_text,
                "confidence": 0.99,
                "pages": 1
            }
            
        try:
            # Call AWS Textract (synchronous detect_document_text for images/PDFs under 1 page)
            # In a fully async production queue, we would use start_document_text_detection for PDFs
            # For the MVP, detect_document_text works for standard single-page reports/images.
            loop = asyncio.get_event_loop()
            
            # Execute block inside loop executor to make the synchronous boto3 call non-blocking
            response = await loop.run_in_executor(
                None,
                lambda: self.textract_client.detect_document_text(
                    Document={
                        "S3Object": {
                            "Bucket": settings.S3_BUCKET_NAME,
                            "Name": s3_key
                        }
                    }
                )
            )
            
            text_lines = []
            confidences = []
            
            for block in response.get("Blocks", []):
                if block.get("BlockType") == "LINE":
                    text_lines.append(block.get("Text", ""))
                    confidences.append(block.get("Confidence", 100.0))
                    
            extracted_text = "\n".join(text_lines)
            average_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 1.0
            
            logger.info(f"Successfully processed OCR for S3 key: {s3_key}. Confidence: {average_confidence:.2f}")
            return {
                "text": extracted_text,
                "confidence": average_confidence,
                "pages": 1
            }
        except Exception as e:
            logger.error(f"Failed to perform Textract OCR: {str(e)}")
            raise

ocr_service = OCRService()
