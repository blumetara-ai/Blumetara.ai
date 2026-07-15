from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime

class ReportUploadInitiate(BaseModel):
    file_name: str
    file_type: str
    file_size_bytes: int = Field(..., description="File size in bytes")

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("File name cannot be empty")
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid file name. Path traversal characters are not allowed.")
        return v.strip()

    @field_validator("file_size_bytes")
    @classmethod
    def validate_file_size(cls, v: int) -> int:
        max_size = 20 * 1024 * 1024  # Max 20MB
        if v <= 0:
            raise ValueError("File size must be greater than zero")
        if v > max_size:
            raise ValueError("File size exceeds maximum allowed size of 20MB")
        return v

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str) -> str:
        allowed_types = ["application/pdf", "image/jpeg", "image/jpg", "image/png"]
        if v.lower() not in allowed_types:
            raise ValueError(f"File type '{v}' is not supported. Allowed: PDF, JPEG, PNG")
        return v.lower()

class ReportUploadResponse(BaseModel):
    report_id: str
    upload_url: str
    s3_key: str
    fields: Dict[str, str] = Field(default_factory=dict, description="Pre-signed URL extra fields")

class ReportResponse(BaseModel):
    id: str = Field(..., alias="_id")
    user_id: str
    file_name: str
    s3_key: str
    status: str
    ocr_confidence: Optional[float] = None
    extracted_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
