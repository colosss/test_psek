from src.infrastructure.auth.jwt import (
    create_access_token,
    create_refresh_token,
    DUMMY_ADMIN_UUID, 
    DUMMY_USER_UUID
)
from src.core.repositories import AbstractUserRepository
from passlib.context import CryptContext
from uuid import UUID
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.auth.jwt import decode_token
import time
from src.application.mappers.tokens import(
    whitelist_key,
    blacklist_key,
    refresh_key,
)
from src.config.settings import settings

REFRESH_TTL_SEC = settings.REFRESH_TTL
ACCESS_TTL_SEC = settings.ACCESS_TTL

async def _revoke_old_access(redis, user_id: str, device_id: str) -> None:
    old = await redis.get(whitelist_key(user_id, device_id))
    if old:
        try:
            payload = decode_token(old)
            remaining = payload["exp"] - int(time.time())
            if remaining > 0:
                await redis.set(blacklist_key(old), "1", ex=remaining)
        except ValueError:
            pass


async def _issue_token_pair(redis, user_id: str, role: str, device_id: str) -> dict:

    await _revoke_old_access(redis, user_id, device_id)

    access = create_access_token(user_id=user_id, role=role)
    refresh = create_refresh_token(user_id=user_id)

    await redis.set(whitelist_key(user_id, device_id), access, ex=ACCESS_TTL_SEC)
    await redis.set(refresh_key(user_id, device_id), refresh, ex=REFRESH_TTL_SEC)

    return {"access_token": access, "refresh_token": refresh}



pwd_context=CryptContext(schemes=["bcrypt"], deprecated="auto")
TOKEN_TTL=600
class DummyLoginUseCase:
    def __init__(self, user_repo: AbstractUserRepository):
        self._users=user_repo

    async def execute(self, role: str, device_id: str)->str:
        if role not in ("admin", "user"):
            raise ValueError("INVALID_REQUEST: invalid role")
        uid=UUID(DUMMY_ADMIN_UUID) if role=="admin" else UUID(DUMMY_USER_UUID)
        await self._users.get_or_create_dummy(uid, role=role)
        redis=await get_redis()
        return await _issue_token_pair(redis, str(uid), role, device_id)
    
class RegisterUseCase:
    def __init__(self, user_repo:AbstractUserRepository):
        self._users=user_repo

    async def execute(self, email: str, password: str, role: str="user"):
        existing=await self._users.get_by_email(email)
        if existing:
            raise ValueError("INVALID_REQUEST: email already exists")
        hashed=pwd_context.hash(password)
        return await self._users.create(email=email, role=role, hashed_password=hashed)
    
class LoginUseCase:
    def __init__(self, user_repo: AbstractUserRepository):
        self._users=user_repo
    
    async def execute(self, email: str, password: str, device_id: str)->dict:
        user=await self._users.get_by_email(email)
        if not user or not user.hashed_password:
            raise ValueError("UNAUTHORIZED: invalid credentials")
        if not pwd_context.verify(password, user.hashed_password):
            raise ValueError("UNAUTHORIZED: invalid credentials")
        
        redis=await get_redis()
        return await _issue_token_pair(redis, str(user.id), user.role, device_id)
    
class LogoutUseCase:
    async def execute(self, access_token: str, user_id: str, device_id: str)->None:
        redis=await get_redis()
        try:
            payload=decode_token(access_token)
            remaining_ttl=payload["exp"]-int(time.time())
            if remaining_ttl>0:
                await redis.set(
                    blacklist_key(access_token),
                    "1",
                    ex=remaining_ttl
                )
        except ValueError: ...
        await redis.delete(whitelist_key(user_id, device_id))
        await redis.delete(refresh_key(user_id, device_id))


class RefreshTokenUseCase:
    def __init__(self, user_repo: AbstractUserRepository):
        self._users=user_repo
    
    async def execute(self, refresh_token: str, device_id)->dict:
        try:
            payload=decode_token(refresh_token)
        except ValueError:
            raise ValueError("UNAUTHORIZED: invalid refresh token")
        
        if payload.get("type")!="refresh":
            raise ValueError("UNAUTHORIZED: wrong token type")
        
        user_id=payload["user_id"]
        redis=await get_redis()
        
        stored=await redis.get(refresh_key(user_id, device_id))
        if not stored:
            raise ValueError("UNAUTHORIZED: refresh token not found or already used")

        if stored!=refresh_token:
            await redis.delete(whitelist_key(user_id, device_id))
            await redis.delete(refresh_key(user_id, device_id))
            raise ValueError("UNAUTHORIZED: refresh token reuse detected — session revoked")
        
        user=await self._users.get_by_id(UUID(user_id))
        if not user:
            raise ValueError("UNAUTHORIZED: user not found")
        
        return await _issue_token_pair(redis, str(user.id), user.role, device_id)