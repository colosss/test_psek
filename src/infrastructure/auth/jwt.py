from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from src.config.settings import settings

DUMMY_ADMIN_UUID = "00000000-0000-0000-0000-000000000001"
DUMMY_USER_UUID = "00000000-0000-0000-0000-000000000002"
DUMMY_BANNED_USER_UUID = "00000000-0000-0000-0000-000000000003"

def create_token(user_id: str, role: str)->str:
    expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload={
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc)+expires_delta
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str)->dict:
    try:
        payload=jwt.decode(token, settings.JWT_SECRET_KEY,algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid token")