from typing import Optional
from fastapi import HTTPException, Security, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy Firebase Admin initialization
_firebase_initialized = False

def _ensure_firebase():
    """Initialize Firebase Admin SDK on first use, not at module import."""
    global _firebase_initialized
    if _firebase_initialized:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={
                'projectId': settings.FIREBASE_PROJECT_ID
            })
            logger.info(f"Firebase Admin SDK initialized for project {settings.FIREBASE_PROJECT_ID}")
        _firebase_initialized = True
        return True
    except Exception as e:
        logger.warning(f"Firebase Admin SDK initialization skipped (local dev mode): {e}")
        return False

security_scheme = HTTPBearer(auto_error=False)

class AuthenticatedUser:
    def __init__(self, uid: str, email: Optional[str] = None, name: Optional[str] = None):
        self.uid = uid
        self.email = email
        self.name = name or "Demo User"

async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    x_dev_user_id: Optional[str] = Header(None, alias="X-Dev-User-Id")
) -> AuthenticatedUser:
    """
    Validates Firebase ID token from Authorization Bearer header.
    In development mode, allows optional X-Dev-User-Id header for seamless local testing.
    """
    # 1. Check for Bearer token
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
        if _ensure_firebase():
            try:
                from firebase_admin import auth
                decoded_token = auth.verify_id_token(token, check_revoked=True)
                uid = decoded_token.get("uid")
                email = decoded_token.get("email")
                name = decoded_token.get("name")
                return AuthenticatedUser(uid=uid, email=email, name=name)
            except Exception as e:
                logger.error(f"Firebase Token Verification Error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authentication token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            logger.warning("Firebase not available, falling back to dev mode auth")

    # 2. Local development fallback
    if settings.ENVIRONMENT == "development":
        user_id = x_dev_user_id or "demo-user-001"
        return AuthenticatedUser(uid=user_id, email=f"{user_id}@nextbite.local", name="Alex Demo")

    # 3. Production rejection
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
