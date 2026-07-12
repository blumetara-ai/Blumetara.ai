"""
Extended, more robust test suite for ReminderService.

These tests build on the existing test_reminder_service.py by adding:
  - Schema/validation edge cases (bad time formats, empty lists, blank names)
  - Additional CRUD failure paths (invalid IDs, DB errors, wrong-user across all ops)
  - update_reminder success paths (partial update, times update, is_active toggle)
  - log_action edge cases (reminder not found, multiple actions, missing scheduled_time)
  - get_user_reminders with real data (not just the empty case)
  - Idempotency / defensive checks (duplicate times, unsorted times)

NOTE: A few of these assert behavior (e.g. exact status codes, whether times get
sorted/deduped) that I inferred from the patterns in your original test file. If your
actual service.py/schemas.py differs, adjust the assertions marked with "# ASSUMPTION".
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.modules.reminders.schemas import (
    ReminderCreate,
    ReminderType,
    ReminderUpdate,
    ReminderLogCreate,
    ReminderAction,
)
from app.modules.reminders.service import ReminderService


def make_mock_db():
    """Helper to build a mock db + collection pair, wired the same way as the
    original test file so behavior stays consistent."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection
    return mock_db, mock_collection


class TestReminderSchemaValidation(unittest.IsolatedAsyncioTestCase):
    """Pure schema-level validation — no DB involved."""

    def test_medicine_missing_name_raises(self):
        with self.assertRaises(ValueError) as ctx:
            ReminderCreate(
                type=ReminderType.MEDICINE,
                times=["09:00"],
                timezone="UTC",
            )
        self.assertIn("medicine_name is required when reminder type is MEDICINE", str(ctx.exception))

    def test_medicine_blank_name_raises(self):
        # A whitespace-only name should be treated the same as missing. # ASSUMPTION
        with self.assertRaises(ValueError):
            ReminderCreate(
                type=ReminderType.MEDICINE,
                times=["09:00"],
                timezone="UTC",
                medicine_name="   ",
            )

    def test_empty_times_list_raises(self):
        with self.assertRaises(ValueError):
            ReminderCreate(
                type=ReminderType.WATER,
                times=[],
                timezone="UTC",
            )

    def test_invalid_time_format_raises(self):
        with self.assertRaises(ValueError):
            ReminderCreate(
                type=ReminderType.WATER,
                times=["25:00"],  # invalid hour
                timezone="UTC",
            )

    def test_invalid_time_format_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            ReminderCreate(
                type=ReminderType.WATER,
                times=["not-a-time"],
                timezone="UTC",
            )

    def test_midnight_boundary_is_valid(self):
        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["00:00", "23:59"],
            timezone="UTC",
        )
        self.assertIn("00:00", schema.times)
        self.assertIn("23:59", schema.times)

    def test_water_reminder_does_not_require_medicine_name(self):
        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["08:00"],
            timezone="UTC",
        )
        self.assertIsNone(getattr(schema, "medicine_name", None))

    def test_invalid_timezone_at_creation_raises(self):
        # If timezone validity is checked at schema level rather than only on update. # ASSUMPTION
        with self.assertRaises(ValueError):
            ReminderCreate(
                type=ReminderType.WATER,
                times=["08:00"],
                timezone="Not/A_RealZone",
            )


class TestCreateReminder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_medicine_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderCreate(
            type=ReminderType.MEDICINE,
            times=["09:00", "21:00"],
            timezone="Asia/Kolkata",
            medicine_name="Paracetamol",
            is_active=True,
        )

        result = await self.service.create_reminder(self.test_user_id, schema)

        self.assertEqual(result["medicine_name"], "Paracetamol")
        self.assertEqual(result["type"], ReminderType.MEDICINE)
        mock_collection.insert_one.assert_called_once()

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_defaults_is_active_true(self, mock_get_db):
        # If is_active is not passed, default should be True. # ASSUMPTION
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["08:00"],
            timezone="UTC",
        )
        result = await self.service.create_reminder(self.test_user_id, schema)
        self.assertTrue(result["is_active"])

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_duplicate_times_deduped_or_rejected(self, mock_get_db):
        # Duplicate times in the same reminder should either be deduped by the
        # service, or rejected by schema validation. Adjust to match actual
        # behavior. # ASSUMPTION
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["08:00", "08:00", "12:00"],
            timezone="UTC",
        )
        result = await self.service.create_reminder(self.test_user_id, schema)
        self.assertEqual(len(result["times"]), len(set(result["times"])))

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_db_failure_propagates(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.insert_one.side_effect = Exception("connection reset")

        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["08:00"],
            timezone="UTC",
        )
        with self.assertRaises(Exception):
            await self.service.create_reminder(self.test_user_id, schema)


class TestGetReminder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_get_reminder_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_reminder(str(ObjectId()), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_get_reminder_wrong_user_returns_404_not_403(self, mock_get_db):
        # Deliberately checking we don't leak existence via a 403 instead of 404.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": "other-user",
            "type": "WATER",
            "times": ["08:00"],
        }
        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_reminder(str(reminder_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_get_reminder_invalid_object_id_format(self):
        # Passing a non-ObjectId string should raise a controlled error, not a
        # raw bson InvalidId leaking out. # ASSUMPTION: service wraps this as
        # HTTPException(400) or ValueError — adjust as needed.
        with self.assertRaises((HTTPException, ValueError, InvalidId)):
            await self.service.get_reminder("not-a-valid-object-id", self.test_user_id)


class TestListReminders(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_list_reminders_empty(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        mock_cursor = MagicMock()
        mock_cursor.__aiter__.return_value = []
        mock_collection.find.return_value = mock_cursor

        result = await self.service.get_user_reminders(self.test_user_id)
        self.assertEqual(len(result), 0)

    @patch("app.modules.reminders.repository.get_database")
    async def test_list_reminders_returns_multiple_mapped_correctly(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        docs = [
            {"_id": ObjectId(), "user_id": self.test_user_id, "type": "WATER", "times": ["08:00"], "is_active": True},
            {"_id": ObjectId(), "user_id": self.test_user_id, "type": "MEDICINE", "times": ["09:00"],
             "medicine_name": "Vitamin D", "is_active": False},
        ]

        mock_cursor = MagicMock()
        mock_cursor.__aiter__.return_value = iter(docs)
        mock_collection.find.return_value = mock_cursor

        result = await self.service.get_user_reminders(self.test_user_id)
        self.assertEqual(len(result), 2)
        types = {r["type"] for r in result}
        self.assertEqual(types, {"WATER", "MEDICINE"})

    @patch("app.modules.reminders.repository.get_database")
    async def test_list_reminders_only_scoped_to_user(self, mock_get_db):
        # Confirms the query filter includes the requesting user_id so we don't
        # leak other users' reminders.
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        mock_cursor = MagicMock()
        mock_cursor.__aiter__.return_value = []
        mock_collection.find.return_value = mock_cursor

        await self.service.get_user_reminders(self.test_user_id)
        args, kwargs = mock_collection.find.call_args
        # The filter dict is typically the first positional arg.
        filter_arg = args[0] if args else kwargs.get("filter", {})
        self.assertEqual(filter_arg.get("user_id"), self.test_user_id)


class TestUpdateReminder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_timezone_invalid(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00"],
        }
        schema = ReminderUpdate(timezone="Invalid/Timezone")
        with self.assertRaises(HTTPException) as ctx:
            await self.service.update_reminder(str(reminder_id), self.test_user_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid timezone", ctx.exception.detail)

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_reminder_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        schema = ReminderUpdate(is_active=False)
        with self.assertRaises(HTTPException) as ctx:
            await self.service.update_reminder(str(ObjectId()), self.test_user_id, schema)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_reminder_wrong_user(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": "someone-else",
            "type": "WATER",
            "times": ["08:00"],
        }
        schema = ReminderUpdate(is_active=False)
        with self.assertRaises(HTTPException) as ctx:
            await self.service.update_reminder(str(reminder_id), self.test_user_id, schema)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_reminder_partial_update_preserves_other_fields(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        existing = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00", "12:00"],
            "timezone": "UTC",
            "is_active": True,
        }
        mock_collection.find_one.return_value = existing
        mock_collection.find_one_and_update.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00", "12:00"],
            "timezone": "UTC",
            "is_active": False,
        }

        schema = ReminderUpdate(is_active=False)
        result = await self.service.update_reminder(str(reminder_id), self.test_user_id, schema)

        self.assertFalse(result["is_active"])
        # Fields not part of the update should be untouched.
        self.assertEqual(result["times"], ["08:00", "12:00"])
        self.assertEqual(result["timezone"], "UTC")

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_reminder_times_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00"],
            "timezone": "UTC",
            "is_active": True,
        }
        mock_collection.find_one_and_update.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["07:30", "13:30", "19:30"],
            "timezone": "UTC",
            "is_active": True,
        }

        schema = ReminderUpdate(times=["07:30", "13:30", "19:30"])
        result = await self.service.update_reminder(str(reminder_id), self.test_user_id, schema)
        self.assertEqual(result["times"], ["07:30", "13:30", "19:30"])

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_reminder_invalid_time_in_update_rejected(self, mock_get_db):
        with self.assertRaises(ValueError):
            ReminderUpdate(times=["99:99"])


class TestDeleteReminder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_delete_reminder_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00"],
        }
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        await self.service.delete_reminder(str(reminder_id), self.test_user_id)
        mock_collection.delete_one.assert_called_once()

    @patch("app.modules.reminders.repository.get_database")
    async def test_delete_reminder_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            await self.service.delete_reminder(str(ObjectId()), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_delete_reminder_wrong_user(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": "not-the-owner",
            "type": "WATER",
            "times": ["08:00"],
        }
        with self.assertRaises(HTTPException) as ctx:
            await self.service.delete_reminder(str(reminder_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)
        mock_collection.delete_one.assert_not_called()

    @patch("app.modules.reminders.repository.get_database")
    async def test_delete_reminder_idempotent_double_delete(self, mock_get_db):
        # First call succeeds; simulate a second call after the doc is gone.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = None  # already deleted

        with self.assertRaises(HTTPException) as ctx:
            await self.service.delete_reminder(str(reminder_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)


class TestLogAction(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_taken_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": ReminderType.MEDICINE,
            "medicine_name": "Paracetamol",
            "times": ["08:00"],
        }
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderLogCreate(action=ReminderAction.TAKEN, scheduled_time=datetime.utcnow())
        result = await self.service.log_action(str(reminder_id), self.test_user_id, schema)

        self.assertEqual(result["action"], ReminderAction.TAKEN)
        self.assertEqual(result["medicine_name"], "Paracetamol")

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_skipped_success(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": ReminderType.WATER,
            "times": ["08:00"],
        }
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderLogCreate(action=ReminderAction.SKIPPED, scheduled_time=datetime.utcnow())
        result = await self.service.log_action(str(reminder_id), self.test_user_id, schema)
        self.assertEqual(result["action"], ReminderAction.SKIPPED)

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_reminder_not_found(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        schema = ReminderLogCreate(action=ReminderAction.TAKEN, scheduled_time=datetime.utcnow())
        with self.assertRaises(HTTPException) as ctx:
            await self.service.log_action(str(ObjectId()), self.test_user_id, schema)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_wrong_user(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": "other-user",
            "type": ReminderType.WATER,
            "times": ["08:00"],
        }
        schema = ReminderLogCreate(action=ReminderAction.TAKEN, scheduled_time=datetime.utcnow())
        with self.assertRaises(HTTPException) as ctx:
            await self.service.log_action(str(reminder_id), self.test_user_id, schema)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_future_scheduled_time_allowed_or_rejected(self, mock_get_db):
        # Logging an action for a future scheduled_time — decide whether this
        # should be rejected (can't log something that hasn't happened yet) or
        # allowed (e.g. pre-logging a planned skip). # ASSUMPTION: currently
        # allowed; flip to assertRaises if your service rejects it.
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": ReminderType.WATER,
            "times": ["08:00"],
        }
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        future_time = datetime.utcnow() + timedelta(days=1)
        schema = ReminderLogCreate(action=ReminderAction.TAKEN, scheduled_time=future_time)
        result = await self.service.log_action(str(reminder_id), self.test_user_id, schema)
        self.assertIsNotNone(result)

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_db_failure_propagates(self, mock_get_db):
        mock_db, mock_collection = make_mock_db()
        mock_get_db.return_value = mock_db
        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": ReminderType.WATER,
            "times": ["08:00"],
        }
        mock_collection.insert_one.side_effect = Exception("write timeout")

        schema = ReminderLogCreate(action=ReminderAction.TAKEN, scheduled_time=datetime.utcnow())
        with self.assertRaises(Exception):
            await self.service.log_action(str(reminder_id), self.test_user_id, schema)


if __name__ == "__main__":
    unittest.main()