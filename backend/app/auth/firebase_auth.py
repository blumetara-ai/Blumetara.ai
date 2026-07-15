import logging
import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config.config import settings
from app.database.mongodb import get_database

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Cache for Firebase public certificates
FIREBASE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"
cached_certs = {}
certs_fetched_at = 0

async def fetch_firebase_public_keys():
    global cached_certs
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(FIREBASE_CERTS_URL)
            if response.status_code == 200:
                cached_certs = response.json()
                logger.info("Successfully fetched Firebase public keys.")
            else:
                logger.error(f"Failed to fetch public keys: status {response.status_code}")
    except Exception as e:
        logger.error(f"Exception fetching Firebase certificates: {e}")

async def verify_firebase_token(token: str) -> dict:
    # Check for local testing mock tokens
    if settings.FIREBASE_PROJECT_ID == "mock-firebase-project" or token.startswith("mock_"):
        logger.warning("Using mock token validation for development.")
        # Return mock payload
        parts = token.split("_")
        uid = parts[1] if len(parts) > 1 else "dev-user-123"
        email = f"{uid}@example.com"
        role = "Admin" if "admin" in token else "User"
        return {
            "uid": uid,
            "email": email,
            "roles": [role],
            "name": "Dev User"
        }

    global cached_certs
    if not cached_certs:
        await fetch_firebase_public_keys()
        
    try:
        # Decode without verification first to get the key ID (kid)
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")
        if not kid or kid not in cached_certs:
            # Refresh certs and retry
            await fetch_firebase_public_keys()
            kid = headers.get("kid")
            if not kid or kid not in cached_certs:
                raise JWTError("Invalid key ID (kid)")

        public_key = cached_certs[kid]
        
        # Verify and decode token claims
        audience = settings.FIREBASE_PROJECT_ID
        issuer = f"https://securetoken.google.com/{audience}"
        
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer
        )
        
        # Format the user dict
        user_info = {
            "uid": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get("roles", ["User"]),
            "name": payload.get("name", "")
        }
        return user_info
        
    except JWTError as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    token = credentials.credentials
    user = await verify_firebase_token(token)
    
    # Sync user with database
    db = get_database()
    if db is not None:
        await db.users.update_one(
            {"firebaseUid": user["uid"]},
            {
                "$set": {
                    "email": user["email"],
                    "roles": user["roles"],
                    "updatedAt": "ISODate"
                },
                "$setOnInsert": {
                    "firebaseUid": user["uid"],
                    "status": "active",
                    "createdAt": "ISODate"
                }
            },
            upsert=True
        )
    return user

async def get_current_admin(user: dict = Security(get_current_user)) -> dict:
    if "Admin" not in user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admin permissions required."
        )
    return user
