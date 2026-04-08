from src.infrastructure.auth.jwt import create_token, DUMMY_ADMIN_UUID, DUMMY_USER_UUID
from src.core.repositories import AbstractUserRepository
from passlib.context import CryptContext
from uuid import UUID
from src.infrastructure.cache.redis_client import get_redis, invalidate_slots_cache
from src.infrastructure.auth.jwt import decode_token

pwd_context=CryptContext(schemes=["bcrypt"], deprecated="auto")
TOKEN_TTL=600
class DummyLoginUseCase:
    def __init__(self, user_repo: AbstractUserRepository):
        self._users=user_repo

    async def execute(self, role: str)->str:
        if role not in ("admin", "user"):
            raise ValueError("INVALID_REQUEST: invalid role")
        uid=UUID(DUMMY_ADMIN_UUID) if role=="admin" else UUID(DUMMY_USER_UUID)
        await self._users.get_or_create_dummy(uid, role=role)
        token=create_token(user_id=str(uid), role=role)
        redis=get_redis()
        await redis.set(
            f"whitelist:users:{str(uid)}",
            token,
            ex=TOKEN_TTL
        )
        return token
    
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
    
    async def execute(self, email: str, password: str)->str:
        user=await self._users.get_by_email(email)
        if not user or not user.hashed_password:
            raise ValueError("UNAUTHORIZED: invalid credentials")
        if not pwd_context.verify(password, user.hashed_password):
            raise ValueError("UNAUTHORIZED: invalid credentials")
        token=create_token(user_id=str(user.id), role=user.role)
        redis=get_redis()
        await redis.set(
            f"whitelist:users:{str(user.id)}",
            token,
            ex=TOKEN_TTL
        )
        return token
    
class LogoutUseCase:
    async def execute(self, token: str, user_id: str)->None:
        redis=get_redis()
        payload=decode_token(token)
        remaining_ttl=payload["exp"]-int(self.__import__("time").time())
        if remaining_ttl>0:
            await redis.set(
                f"blacklist:token:{token}",
                "1",
                ex=remaining_ttl
            )
        await redis.delete(f"whitelist:users:{user_id}")

class TokenValidationService:
    async def if_valid(self, token: str, user_id: str)->bool:
        redis=get_redis()
        
        in_blacklist=await redis.exists(f"blacklist:token:{token}")
        if in_blacklist:
            return False
        
        stored_token=await redis.get(f"whitelist:users:{user_id}")
        if not stored_token:
            return False
        
        if stored_token!=token:
            return False
        
        return True
