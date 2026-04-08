from src.infrastructure.auth.jwt import create_token, DUMMY_ADMIN_UUID, DUMMY_USER_UUID
from src.core.repositories import AbstractUserRepository
from passlib.context import CryptContext
from uuid import UUID
from src.infrastructure.cache.redis_client import get_redis, invalidate_slots_cache

pwd_context=CryptContext(schemes=["bcrypt"], deprecated="auto")

class DummyLoginUseCase:
    def __init__(self, user_repo: AbstractUserRepository):
        self._users=user_repo

    async def execute(self, role: str)->str:
        if role not in ("admin", "user"):
            raise ValueError("INVALID_REQUEST: invalid role")
        uid=UUID(DUMMY_ADMIN_UUID) if role=="admin" else UUID(DUMMY_USER_UUID)
        await self._users.get_or_create_dummy(uid, role=role)
        return create_token(user_id=str(uid), role=role)
    
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
        return create_token(user_id=str(user.id), role=user.role)