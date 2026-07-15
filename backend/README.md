# Blumetara AI - Reminders Backend Service

This directory contains the Python/FastAPI backend implementing the **Proactive Reminders (Medicine & Water Tracker)** feature.

The code is structured as a **modular monolith** in accordance with the system design specs, making it easy to integrate with the health reports and chatbot modules later.

---

## Folder Structure

```
backend/
  requirements.txt
  app/
    main.py
    core/
      config.py       # Configuration management (Pydantic settings)
      security.py     # Auth helper (Firebase JWT verify + developer mock mode)
    database/
      mongo.py        # MongoDB connection lifecycle using Motor
    services/
      notification_service.py # Simulated push notifications log
    api/
      v1/
        router.py     # Central v1 router mount
        reminder_routes.py # CRUD and log endpoints for reminders
    modules/
      reminders/
        schemas.py    # Request/response validation schemas
        repository.py # Database interactions
        service.py    # Core business logic (timezone check, etc.)
        scheduler.py  # Background reminder scanner (APScheduler)
  tests/
    test_reminders.py # Unit tests with isolated DB mocks
```

---

## Getting Started

### 1. Installation
Ensure you have Python 3.10+ installed. Install the backend dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file at the root of the `backend/` directory to configure environment variables.
```env
# Database configuration
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=blumetara

# API Mode configurations
APP_ENV=dev
MOCK_AUTH=True
```
*Note: If `MOCK_AUTH=True`, the backend bypasses Firebase Authentication and permits direct request testing by supplying the header `X-Mock-User-ID: your-user-id` (or defaulting to `test-user`).*

### 3. Run the Server
Start the Uvicorn development server:
```bash
uvicorn app.main:app --reload
```
The server will boot on `http://127.0.0.1:8000`.

### 4. Interactive Docs (Swagger UI)
Visit the interactive documentation page to try out the endpoints:
👉 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## REST Endpoints Overview

### Reminder Configurations
- **Create Reminder**: `POST /api/v1/reminders`
  - Body:
    ```json
    {
      "type": "MEDICINE",
      "medicine_name": "Metformin",
      "dose": "500mg",
      "times": ["08:00", "20:00"],
      "timezone": "Asia/Kolkata",
      "is_active": true
    }
    ```
- **List User Reminders**: `GET /api/v1/reminders`
- **Retrieve Reminder**: `GET /api/v1/reminders/{id}`
- **Update Reminder**: `PUT /api/v1/reminders/{id}`
- **Delete Reminder**: `DELETE /api/v1/reminders/{id}`

### Reminder History & Logs
- **Log User Action**: `POST /api/v1/reminders/{id}/action`
  - Body:
    ```json
    {
      "action": "TAKEN",
      "scheduled_time": "2026-07-12T08:00:00Z"
    }
    ```
- **Fetch History Log**: `GET /api/v1/reminders/history/logs`

### Health Reports Configurations & Ingestion
- **Request Upload URL**: `POST /api/v1/reports/upload-url`
  - Body:
    ```json
    {
      "file_name": "blood_report.pdf",
      "file_type": "application/pdf",
      "file_size_bytes": 1048576
    }
    ```
- **List Reports**: `GET /api/v1/reports`
- **Get Report Details (Download URL + Extracted Text)**: `GET /api/v1/reports/{id}`
- **Manually Process/Retry**: `POST /api/v1/reports/{id}/process`
- **Delete Report**: `DELETE /api/v1/reports/{id}`

---

## Local Development Mock Testing for Uploads

When `MOCK_SERVICES=True`, uploading to S3 is simulated locally:
1. Call `POST /api/v1/reports/upload-url` to register the report. It returns an upload URL: `http://localhost:8000/api/v1/reports/mock-upload/{report_id}`.
2. Make a `multipart/form-data` POST request to that upload URL with your file attached as `file`.
3. The server saves the file inside the local directory `./local_storage/` and automatically runs the text extraction and chunking pipeline.
4. You can call `GET /api/v1/reports/{id}` to verify the processing status (`uploaded` -> `queued` -> `processing_ocr` -> `processed`) and read the mock extracted text.

---

## Verification & Testing

### Running Unit Tests
All unit tests are mock-based and can be run without starting MongoDB or Docker:
```bash
PYTHONPATH=. python3 -m unittest discover -s tests
```


# Dev Integration Complete
