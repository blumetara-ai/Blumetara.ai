import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from app.modules.health_reports.schemas import ReportUploadInitiate
from app.modules.health_reports.service import HealthReportService
from app.services.rag_service import rag_service

class TestHealthReportService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HealthReportService()
        self.test_user_id = "user-123"

    @patch("app.modules.health_reports.repository.get_database")
    async def test_initiate_upload_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReportUploadInitiate(
            file_name="blood_report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024 * 1024  # 1MB
        )

        result = await self.service.initiate_upload(self.test_user_id, schema)

        self.assertEqual(result["s3_key"], f"users/{self.test_user_id}/reports/{result['report_id']}/blood_report.pdf")
        self.assertIn("upload_url", result)
        mock_collection.insert_one.assert_called_once()

    def test_initiate_upload_invalid_file_type(self):
        with self.assertRaises(ValueError) as ctx:
            ReportUploadInitiate(
                file_name="invalid_doc.zip",
                file_type="application/zip",
                file_size_bytes=1000
            )
        self.assertIn("Allowed: PDF, JPEG, PNG", str(ctx.exception))

    def test_initiate_upload_file_too_large(self):
        with self.assertRaises(ValueError) as ctx:
            ReportUploadInitiate(
                file_name="huge_file.pdf",
                file_type="application/pdf",
                file_size_bytes=25 * 1024 * 1024  # 25MB
            )
        self.assertIn("exceeds maximum allowed size of 20MB", str(ctx.exception))

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        report_id = ObjectId()
        # Mock get_by_id (returns the report document)
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded"
        }

        # Run process_report
        # We mock external S3/Textract and Gemini calls implicitly by running in DEV/MOCK mode.
        with patch("app.services.ocr_service.settings.MOCK_SERVICES", True), \
             patch("app.services.rag_service.settings.MOCK_SERVICES", True):
            await self.service.process_report(str(report_id), self.test_user_id)

        # Confirm find_one_and_update was called to set status to processed
        # The service updates status sequentially: queued, processing_ocr, processing_chunks, processing_embeddings, processed
        mock_collection.find_one_and_update.assert_called()
        # Ensure chunks were written (insert_many was called on the mock collection)
        mock_collection.insert_many.assert_called_once()

    def test_text_chunking_sliding_window(self):
        text = "abcdefghijklmnopqrstuvwxyz"
        # chunk size = 10, overlap = 4
        # Chunk 1: "abcdefghij" (index 0 to 10)
        # Chunk 2: "g-p" -> start index = 10 - 4 = 6. Chunk: "ghijklmnop"
        # Chunk 3: "m-v" -> start index = 16 - 4 = 12. Chunk: "mnopqrstuv"
        # Chunk 4: "s-z" -> start index = 22 - 4 = 18. Chunk: "stuvwxyz"
        chunks = rag_service.chunk_text(text, chunk_size=10, overlap=4)
        
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0], "abcdefghij")
        self.assertEqual(chunks[1], "ghijklmnop")
        self.assertEqual(chunks[2], "mnopqrstuv")
        self.assertEqual(chunks[3], "stuvwxyz")

    @patch("app.modules.health_reports.repository.get_database")
    async def test_get_report_wrong_user(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": "other-user",
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key"
        }

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_report(str(report_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.health_reports.repository.get_database")
    @patch("app.services.storage_service.storage_service.delete_file", new_callable=AsyncMock)
    async def test_delete_report_success(self, mock_delete_file, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        report_id = ObjectId()
        # Mock get_by_id (called inside get_report)
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key"
        }
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        await self.service.delete_report(str(report_id), self.test_user_id)
        mock_delete_file.assert_called_once_with("some_s3_key")
        mock_collection.delete_one.assert_called_once()

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_failed_ocr(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded"
        }

        # Mock ocr_service to throw exception
        with patch("app.services.ocr_service.ocr_service.extract_text", side_effect=Exception("OCR Service Unavailable")), \
             patch("app.services.ocr_service.settings.MOCK_SERVICES", False):
            await self.service.process_report(str(report_id), self.test_user_id)

        # Verify status is updated to failed (last find_one_and_update call)
        mock_collection.find_one_and_update.assert_called()
        last_call_args = mock_collection.find_one_and_update.call_args[0][1]
        self.assertEqual(last_call_args["$set"]["status"], "failed")

if __name__ == '__main__':
    unittest.main()
