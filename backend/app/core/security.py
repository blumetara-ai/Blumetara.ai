from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

# APIKeyHeader extracts the token from HTTP headers
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)
mock_user_header = APIKeyHeader(name="X-Mock-User-ID", auto_error=False)

async def get_current_user_id(
    authorization: str = Security(api_key_header),
    x_mock_user_id: str = Security(mock_user_header)
) -> str:
    # If mock auth is enabled, prioritize mock header or default user
    if settings.MOCK_AUTH:
        if x_mock_user_id:
            return x_mock_user_id
        return "test-user"
        
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header"
        )
        
    # Standard format: Authorization: Bearer <token>
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization token format. Must start with Bearer"
        )
        
    token = authorization.split(" ")[1]
    
    # In production, verify Firebase ID token using firebase_admin sdk
    # For now, we stub this verification so it doesn't fail compilation
    try:
        # firebase_admin.auth.verify_id_token(token)
        # return decoded_token["uid"]
        # Stub implementation for demo/sandbox if credentials aren't set
        if token == "mock-prod-token":
            return "real-firebase-user-123"
        raise ValueError("Invalid token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Firebase Authentication token: {str(e)}"
        )
