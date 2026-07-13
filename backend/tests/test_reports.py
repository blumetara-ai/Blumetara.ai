"""
Extended, more robust test suite for HealthReportService + rag_service.chunk_text.

Builds on the existing test_health_reports.py by adding:
  - Schema validation edge cases (boundary file size, all allowed types, bad names)
  - initiate_upload robustness (DB failure, s3_key shape per file type)
  - process_report state-machine coverage (not found, wrong user, already processed,
    empty-OCR-text, embedding failure, MOCK_SERVICES on/off)
  - chunk_text edge cases (short text, exact-length text, zero/large overlap, empty input)
  - get_report / delete_report failure paths (not found, invalid id, storage failure)

NOTE: I only have your original test file, not service.py/schemas.py/rag_service.py.
Assertions inferred rather than confirmed against source are marked "# ASSUMPTION" —
please adjust those if your actual implementation differs.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.modules.health_reports.schemas import ReportUploadInitiate
from app.modules.health_reports.service import HealthReportService
from app.services.rag_service import rag_service


def make_mock_db():
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    return mock_db, mock_collection


class TestReportUploadSchemaValidation(unittest.TestCase):
    """Pure schema validation — no DB, no async needed."""

    def test_valid_pdf(self):
        schema = ReportUploadInitiate(
            file_name="report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
        )
        self.assertEqual(schema.file_type, "application/pdf")

    def test_valid_jpeg(self):
        schema = ReportUploadInitiate(
            file_name="scan.jpg",
            file_type="image/jpeg",
            file_size_bytes=1024,
        )
        self.assertEqual(schema.file_type, "image/jpeg")

    def test_valid_png(self):
        schema = ReportUploadInitiate(
            file_name="scan.png",
            file_type="image/png",
            file_size_bytes=1024,
        )
        self.assertEqual(schema.file_type, "image/png")

    def test_invalid_file_type_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            ReportUploadInitiate(
                file_name="invalid_doc.zip",
                file_type="application/zip",
                file_size_bytes=1000,
            )
        self.assertIn("Allowed: PDF, JPEG, PNG", str(ctx.exception))

    def test_file_too_large_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            ReportUploadInitiate(
                file_name="huge_file.pdf",
                file_type="application/pdf",
                file_size_bytes=25 * 1024 * 1024,
            )
        self.assertIn("exceeds maximum allowed size of 20MB", str(ctx.exception))

    def test_file_size_exactly_at_20mb_boundary(self):
        # Confirm whether the limit is inclusive (<=20MB allowed) or exclusive.
        # ASSUMPTION: inclusive — adjust to assertRaises if your service is
        # strictly "< 20MB".
        schema = ReportUploadInitiate(
            file_name="exactly_20mb.pdf",
            file_type="application/pdf",
            file_size_bytes=20 * 1024 * 1024,
        )
        self.assertEqual(schema.file_size_bytes, 20 * 1024 * 1024)

    def test_file_size_one_byte_over_boundary_rejected(self):
        with self.assertRaises(ValueError):
            ReportUploadInitiate(
                file_name="just_over.pdf",
                file_type="application/pdf",
                file_size_bytes=20 * 1024 * 1024 + 1,
            )

    def test_zero_byte_file_rejected(self):
        # An empty file is presumably not a valid upload. # ASSUMPTION
        with self.assertRaises(ValueError):
            ReportUploadInitiate(
                file_name="empty.pdf",
                file_type="application/pdf",
                file_size_bytes=0,
            )

    def test_negative_file_size_rejected(self):
        with self.assertRaises(ValueError):
            ReportUploadInitiate(
                file_name="bad.pdf",
                file_type="application/pdf",
                file_size_bytes=-100,
            )

    def test_empty_file_name_rejected(self):
        with self.assertRaises(ValueError):
            ReportUploadInitiate(
                file_name="",
                file_type="application/pdf",
                file_size_bytes=1024,
            )

    def test_file_name_with_path_traversal_rejected_or_sanitized(self):
        # Guard against a file_name like "../../etc/passwd" being used verbatim
        # to build an s3_key. # ASSUMPTION: schema rejects it outright; if your
        # service instead sanitizes it, change this to check the sanitized value.
        with self.assertRaises(ValueError):
            ReportUploadInitiate(
                file_name="../../etc/passwd.pdf",
                file_type="application/pdf",
                file_size_bytes=1024,
            )


class TestInitiateUpload(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HealthReportService()
        self.test_user_id = "user-123"

    @patch("app.modules.health_reports.repository.get_database")
    async def test_initiate_upload_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReportUploadInitiate(
            file_name="blood_report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024 * 1024,
        )
        result = await self.service.initiate_upload(self.test_user_id, schema)

        self.assertEqual(
            result["s3_key"],
            f"users/{self.test_user_id}/reports/{result['report_id']}/blood_report.pdf",
        )
        self.assertIn("upload_url", result)

    @patch("app.modules.health_reports.repository.get_database")
    async def test_initiate_upload_png_s3_key_shape(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReportUploadInitiate(
            file_name="scan.png",
            file_type="image/png",
            file_size_bytes=2048,
        )
        result = await self.service.initiate_upload(self.test_user_id, schema)
        self.assertTrue(result["s3_key"].endswith("scan.png"))
        self.assertIn(self.test_user_id, result["s3_key"])

    @patch("app.modules.health_reports.repository.get_database")
    async def test_initiate_upload_sets_initial_status_uploaded_or_pending(self, mock_get_db):
        # The new report doc should start in a not-yet-processed state.
        # ASSUMPTION on the exact literal value — adjust if different.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReportUploadInitiate(
            file_name="report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
        )
        await self.service.initiate_upload(self.test_user_id, schema)
        inserted_doc = mock_collection.insert_one.call_args[0][0]
        self.assertIn(inserted_doc.get("status"), ("uploaded", "pending", "queued"))

    @patch("app.modules.health_reports.repository.get_database")
    async def test_initiate_upload_db_failure_propagates(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.insert_one.side_effect = Exception("connection reset")

        schema = ReportUploadInitiate(
            file_name="report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
        )
        with self.assertRaises(Exception):
            await self.service.initiate_upload(self.test_user_id, schema)


class TestProcessReport(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HealthReportService()
        self.test_user_id = "user-123"

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_success_status_sequence(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded",
        }

        with patch("app.services.ocr_service.settings.MOCK_SERVICES", True), \
             patch("app.services.rag_service.settings.MOCK_SERVICES", True):
            await self.service.process_report(str(report_id), self.test_user_id)

        statuses_set = [
            call.args[1]["$set"]["status"]
            for call in mock_collection.find_one_and_update.call_args_list
            if "status" in call.args[1].get("$set", {})
        ]
        self.assertIn("processed", statuses_set)
        self.assertNotIn("failed", statuses_set)
        mock_collection.insert_many.assert_called_once()

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            await self.service.process_report(str(ObjectId()), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_wrong_user(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": "other-user",
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded",
        }
        with self.assertRaises(HTTPException) as ctx:
            await self.service.process_report(str(report_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_already_processed_is_idempotent(self, mock_get_db):
        # Re-processing an already-processed report shouldn't re-run OCR/chunk/
        # embedding pipeline. # ASSUMPTION: service short-circuits; if it
        # instead re-processes every time, this test should be removed/inverted.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "processed",
        }

        with patch("app.services.ocr_service.settings.MOCK_SERVICES", True), \
             patch("app.services.rag_service.settings.MOCK_SERVICES", True):
            await self.service.process_report(str(report_id), self.test_user_id)

        mock_collection.insert_many.assert_not_called()

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_failed_ocr_sets_status_failed(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded",
        }

        with patch("app.services.ocr_service.ocr_service.extract_text",
                    side_effect=Exception("OCR Service Unavailable")), \
             patch("app.services.ocr_service.settings.MOCK_SERVICES", False):
            await self.service.process_report(str(report_id), self.test_user_id)

        last_call_args = mock_collection.find_one_and_update.call_args[0][1]
        self.assertEqual(last_call_args["$set"]["status"], "failed")

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_empty_ocr_text_skips_chunking(self, mock_get_db):
        # If OCR returns empty/whitespace text, there's nothing to chunk or
        # embed — service should mark failed (or "processed" with 0 chunks)
        # rather than crash. # ASSUMPTION: marks as failed.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded",
        }

        with patch("app.services.ocr_service.ocr_service.extract_text",
                    new=AsyncMock(return_value="   ")), \
             patch("app.services.ocr_service.settings.MOCK_SERVICES", False):
            await self.service.process_report(str(report_id), self.test_user_id)

        last_call_args = mock_collection.find_one_and_update.call_args[0][1]
        self.assertIn(last_call_args["$set"]["status"], ("failed", "processed"))

    @patch("app.modules.health_reports.repository.get_database")
    async def test_process_report_embedding_failure_sets_status_failed(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "uploaded",
        }

        with patch("app.services.ocr_service.settings.MOCK_SERVICES", True), \
             patch("app.services.rag_service.settings.MOCK_SERVICES", False), \
             patch("app.services.rag_service.rag_service.generate_embeddings",
                    side_effect=Exception("Embedding API unavailable")):
            await self.service.process_report(str(report_id), self.test_user_id)

        last_call_args = mock_collection.find_one_and_update.call_args[0][1]
        self.assertEqual(last_call_args["$set"]["status"], "failed")


class TestChunkText(unittest.TestCase):
    """rag_service.chunk_text — pure function, no mocks needed."""

    def test_sliding_window_basic(self):
        text = "abcdefghijklmnopqrstuvwxyz"
        chunks = rag_service.chunk_text(text, chunk_size=10, overlap=4)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0], "abcdefghij")
        self.assertEqual(chunks[1], "ghijklmnop")
        self.assertEqual(chunks[2], "mnopqrstuv")
        self.assertEqual(chunks[3], "stuvwxyz")

    def test_text_shorter_than_chunk_size_returns_single_chunk(self):
        text = "short text"
        chunks = rag_service.chunk_text(text, chunk_size=100, overlap=10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_text_exactly_chunk_size_returns_single_chunk(self):
        text = "a" * 10
        chunks = rag_service.chunk_text(text, chunk_size=10, overlap=4)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], text)

    def test_zero_overlap_no_repeated_characters(self):
        text = "abcdefghij"  # 10 chars
        chunks = rag_service.chunk_text(text, chunk_size=5, overlap=0)
        self.assertEqual(chunks, ["abcde", "fghij"])

    def test_empty_text_returns_no_chunks(self):
        chunks = rag_service.chunk_text("", chunk_size=10, overlap=4)
        self.assertEqual(chunks, [])

    def test_overlap_greater_or_equal_to_chunk_size_raises(self):
        # An overlap >= chunk_size would create an infinite/non-advancing
        # sliding window — should be rejected defensively. # ASSUMPTION
        with self.assertRaises(ValueError):
            rag_service.chunk_text("abcdefghij", chunk_size=5, overlap=5)

    def test_chunk_size_zero_or_negative_raises(self):
        with self.assertRaises(ValueError):
            rag_service.chunk_text("abcdefghij", chunk_size=0, overlap=0)

    def test_whitespace_only_text_returns_no_chunks(self):
        # ASSUMPTION: whitespace-only input is treated like empty input.
        chunks = rag_service.chunk_text("     ", chunk_size=10, overlap=2)
        self.assertEqual(chunks, [])


class TestGetReport(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HealthReportService()
        self.test_user_id = "user-123"

    @patch("app.modules.health_reports.repository.get_database")
    async def test_get_report_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
            "status": "processed",
        }
        result = await self.service.get_report(str(report_id), self.test_user_id)
        self.assertEqual(result["file_name"], "blood_report.pdf")

    @patch("app.modules.health_reports.repository.get_database")
    async def test_get_report_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_report(str(ObjectId()), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.health_reports.repository.get_database")
    async def test_get_report_wrong_user(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": "other-user",
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
        }
        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_report(str(report_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_get_report_invalid_object_id_format(self):
        with self.assertRaises((HTTPException, ValueError, InvalidId)):
            await self.service.get_report("not-a-valid-object-id", self.test_user_id)


class TestDeleteReport(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HealthReportService()
        self.test_user_id = "user-123"

    @patch("app.modules.health_reports.repository.get_database")
    @patch("app.services.storage_service.storage_service.delete_file", new_callable=AsyncMock)
    async def test_delete_report_success(self, mock_delete_file, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
        }
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        await self.service.delete_report(str(report_id), self.test_user_id)
        mock_delete_file.assert_called_once_with("some_s3_key")
        mock_collection.delete_one.assert_called_once()

    @patch("app.modules.health_reports.repository.get_database")
    async def test_delete_report_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            await self.service.delete_report(str(ObjectId()), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.health_reports.repository.get_database")
    async def test_delete_report_wrong_user(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": "not-the-owner",
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
        }
        with self.assertRaises(HTTPException) as ctx:
            await self.service.delete_report(str(report_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)
        mock_collection.delete_one.assert_not_called()

    @patch("app.modules.health_reports.repository.get_database")
    @patch("app.services.storage_service.storage_service.delete_file", new_callable=AsyncMock)
    async def test_delete_report_storage_failure_does_not_delete_db_doc(self, mock_delete_file, mock_get_db):
        # If S3 deletion fails, the DB record should arguably NOT be removed
        # (to avoid an orphaned/undeletable S3 object with no tracking doc).
        # ASSUMPTION: service propagates the storage error and skips delete_one.
        # If your service deletes the DB doc regardless, invert this assertion.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
        }
        mock_delete_file.side_effect = Exception("S3 unavailable")

        with self.assertRaises(Exception):
            await self.service.delete_report(str(report_id), self.test_user_id)
        mock_collection.delete_one.assert_not_called()

    @patch("app.modules.health_reports.repository.get_database")
    @patch("app.services.storage_service.storage_service.delete_file", new_callable=AsyncMock)
    async def test_delete_report_deletes_associated_chunks(self, mock_delete_file, mock_get_db):
        # Deleting a report should also clean up its RAG chunks, not just the
        # report document, to avoid orphaned embeddings. # ASSUMPTION
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        report_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": report_id,
            "user_id": self.test_user_id,
            "file_name": "blood_report.pdf",
            "s3_key": "some_s3_key",
        }
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)
        mock_collection.delete_many.return_value = MagicMock(deleted_count=3)

        await self.service.delete_report(str(report_id), self.test_user_id)
        mock_collection.delete_many.assert_called()


if __name__ == "__main__":
    unittest.main()