import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from bson import ObjectId
from app.modules.reminders.schemas import ReminderCreate, ReminderType, ReminderUpdate, ReminderLogCreate, ReminderAction
from app.modules.reminders.service import ReminderService

class TestReminderService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_water(self, mock_get_db):
        # Setup mocks
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        # Create schema for Water
        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["08:00", "12:00", "16:00"],
            timezone="Asia/Kolkata",
            is_active=True
        )

        result = await self.service.create_reminder(self.test_user_id, schema)

        # Assertions
        self.assertEqual(result["user_id"], self.test_user_id)
        self.assertEqual(result["type"], ReminderType.WATER)
        self.assertEqual(result["times"], ["08:00", "12:00", "16:00"])
        self.assertEqual(result["timezone"], "Asia/Kolkata")
        self.assertTrue(result["is_active"])
        self.assertIn("created_at", result)
        mock_collection.insert_one.assert_called_once()

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_medicine_missing_name(self, mock_get_db):
        # Validate that raising validation error occurs for MEDICINE type with missing name
        with self.assertRaises(ValueError) as ctx:
            ReminderCreate(
                type=ReminderType.MEDICINE,
                times=["09:00"],
                timezone="UTC"
            )
        self.assertIn("medicine_name is required when reminder type is MEDICINE", str(ctx.exception))

    @patch("app.modules.reminders.repository.get_database")
    async def test_get_reminder_not_found(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        mock_collection.find_one.return_value = None

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_reminder(str(ObjectId()), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_get_reminder_wrong_user(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": "other-user",
            "type": "WATER",
            "times": ["08:00"]
        }

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_reminder(str(reminder_id), self.test_user_id)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.modules.reminders.repository.get_database")
    async def test_log_action_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        reminder_id = ObjectId()
        # Mock get_by_id (called within service.log_action via service.get_reminder)
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": ReminderType.MEDICINE,
            "medicine_name": "Paracetamol",
            "times": ["08:00"]
        }

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderLogCreate(
            action=ReminderAction.TAKEN,
            scheduled_time=datetime.utcnow()
        )

        result = await self.service.log_action(str(reminder_id), self.test_user_id, schema)

        self.assertEqual(result["user_id"], self.test_user_id)
        self.assertEqual(result["reminder_id"], str(reminder_id))
        self.assertEqual(result["action"], ReminderAction.TAKEN)
        self.assertEqual(result["type"], ReminderType.MEDICINE)
        self.assertEqual(result["medicine_name"], "Paracetamol")
        self.assertIn("logged_at", result)

    @patch("app.modules.reminders.repository.get_database")
    async def test_list_reminders_empty(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        # Mock async cursor
        mock_cursor = MagicMock()
        mock_cursor.__aiter__.return_value = []
        mock_collection.find.return_value = mock_cursor

        result = await self.service.get_user_reminders(self.test_user_id)
        self.assertEqual(len(result), 0)

    @patch("app.modules.reminders.repository.get_database")
    async def test_delete_reminder_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00"]
        }
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)

        await self.service.delete_reminder(str(reminder_id), self.test_user_id)
        mock_collection.delete_one.assert_called_once()

    @patch("app.modules.reminders.repository.get_database")
    async def test_update_timezone_invalid(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        reminder_id = ObjectId()
        mock_collection.find_one.return_value = {
            "_id": reminder_id,
            "user_id": self.test_user_id,
            "type": "WATER",
            "times": ["08:00"]
        }

        from fastapi import HTTPException
        schema = ReminderUpdate(timezone="Invalid/Timezone")
        with self.assertRaises(HTTPException) as ctx:
            await self.service.update_reminder(str(reminder_id), self.test_user_id, schema)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid timezone", ctx.exception.detail)

if __name__ == '__main__':
    unittest.main()
