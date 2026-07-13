import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from app.modules.reminders.schemas import ReminderCreate, ReminderType, ReminderUpdate
from app.modules.reminders.service import ReminderService

class TestWaterReminderService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_water(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderCreate(
            type=ReminderType.WATER,
            times=["08:00", "12:00"],
            timezone="Asia/Kolkata",
            is_active=True
        )

        result = await self.service.create_reminder(self.test_user_id, schema)

        self.assertEqual(result["user_id"], self.test_user_id)
        self.assertEqual(result["type"], ReminderType.WATER)
        self.assertEqual(result["timezone"], "Asia/Kolkata")
        mock_collection.insert_one.assert_called_once()

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

if __name__ == '__main__':
    unittest.main()
