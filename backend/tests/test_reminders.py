import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from bson import ObjectId
from app.modules.reminders.schemas import ReminderCreate, ReminderType, ReminderUpdate
from app.modules.reminders.service import ReminderService

class TestMedicineReminderService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = ReminderService()
        self.test_user_id = "user-123"

    @patch("app.modules.reminders.repository.get_database")
    async def test_create_reminder_medicine(self, mock_get_db):
        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db

        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_insert_result

        schema = ReminderCreate(
            type=ReminderType.MEDICINE,
            medicine_name="Advil",
            dose="200mg",
            times=["08:00"],
            timezone="Asia/Kolkata",
            is_active=True
        )

        result = await self.service.create_reminder(self.test_user_id, schema)

        self.assertEqual(result["user_id"], self.test_user_id)
        self.assertEqual(result["type"], ReminderType.MEDICINE)
        self.assertEqual(result["medicine_name"], "Advil")
        self.assertEqual(result["dose"], "200mg")
        mock_collection.insert_one.assert_called_once()

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

if __name__ == '__main__':
    unittest.main()
