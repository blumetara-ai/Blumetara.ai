import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Blumetara AI Backend"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB Settings
    MONGO_URI: str = "mongodb://localhost:27017/blumetara_db"
    DATABASE_NAME: str = "blumetara_db"
    
    # AWS Settings
    AWS_ACCESS_KEY_ID: str = "mock_key"
    AWS_SECRET_ACCESS_KEY: str = "mock_secret"
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "blumetara-reports"
    
    # AI/LLM Settings
    GEMINI_API_KEY: str = ""
    AI_REASONING_MODE: str = "lite"  # options: 'lite' or 'enterprise'
    
    # Firebase Settings
    FIREBASE_PROJECT_ID: str = "blumetara-ai"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
