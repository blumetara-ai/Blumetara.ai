from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Blumetara AI"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    APP_ENV: str = "dev"  # dev, staging, prod
    MOCK_AUTH: bool = True  # If True, bypass Firebase JWT verification via X-Mock-User-ID header
    
    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "blumetara"
    
    # AWS configuration
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = None
    
    # Toggle for using mock S3/Textract/Gemini operations locally
    MOCK_SERVICES: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
