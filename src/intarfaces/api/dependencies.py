from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.infrastructure.auth.jwt import decode_token
from src.infrastructure.cache.redis_client import get_redis

bearer=HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials=Depends(bearer)
)->dict:
    try:
        payload=decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "invalid token"}}
        )
    
    token=credentials.credentials
    user_id=payload["user_id"]
    redis=get_redis()
    if await redis.exists(f"blacklist:token:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "token revoked"}}
        )
    
    stored_token=await redis.get(f"whitelist:users:{user_id}")
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "session expired"}}
        )
    
    if stored_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "token superseded"}}
        )
    
    return{"user_id": payload["user_id"], "role": payload["role"]}

    
async def require_admin(current_user: dict=Depends(get_current_user))->dict:
    if current_user["role"]!="admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "admin role required"}},
        )
    return current_user

async def require_user(current_user: dict=Depends(get_current_user))->dict:
    if current_user["role"]!="user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "user role required"}},
        )
    return current_user
