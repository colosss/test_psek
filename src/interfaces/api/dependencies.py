from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.infrastructure.auth.jwt import decode_token
from src.infrastructure.cache.redis_client import get_redis
from src.application.mappers.tokens import whitelist_key

bearer=HTTPBearer()

async def get_current_user(
        credentials: HTTPAuthorizationCredentials=Depends(bearer),
        device_id: str | None=None,
)->dict:
    try:
        payload=decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "invalid token"}}
        )
    
    if payload.get("type")!="access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "wrong token type"}},
        )
    
    token=credentials.credentials
    user_id=payload["user_id"]
    redis=await get_redis()

    if await redis.exists(f"blacklist:token:{token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "token revoked"}}
        )
    
    if device_id:
        stored_token=await redis.get(whitelist_key(user_id, device_id))
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


def require_role(*roles: str)->dict:
    async def checker(current_user: dict=Depends(get_current_user))->dict:
        if current_user["role"] not in roles:
            role=current_user["role"]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": f"{role} role required"}},
            )
        return current_user
    return checker