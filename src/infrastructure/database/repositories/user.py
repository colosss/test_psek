from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.infrastructure.database.models import User as UserModel
from src.core.repositories import AbstractUserRepository
from src.core.domain.models import User
from typing import Optional
from uuid import UUID
import uuid
from src.application.mappers.user import user_db_to_domain

class UserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession):
        self.session=session

    async def get_by_id(self, user_id: UUID)->Optional[User]:
        u=await self.session.get(UserModel, user_id)
        return user_db_to_domain(u) if u else None
    
    async def get_by_email(self, email: str)->Optional[User]:
        result=await self.session.execute(select(UserModel).where(UserModel.email==email))
        u=result.scalar_one_or_none()
        return user_db_to_domain(u) if u else None
    
    async def create(self, email: str, role: str, hashed_password: Optional[str])->User:
        u=UserModel(id=uuid.v(), email=email, role=role,hashed_password=hashed_password)
        self.session.add(u)
        await self.session.commit()
        await self.session.refresh(u)
        return user_db_to_domain(u)
    
    async def get_or_create_dummy(self, user_id: UUID, role: str)->User:
        u=await self.session.get(UserModel, user_id)
        if u:
            return user_db_to_domain(u)
        u=UserModel(id=user_id, email=f"dummy_{role}@system.local", role=role, hashed_password=None)
        self.session.add(u)
        await self.session.commit()
        await self.session.refresh(u)
        return user_db_to_domain(u)
    
    async def ban_user_by_id(self, user_id: UUID)->None:
        u=await self.session.get(UserModel, user_id)
        if u is None:
            return None
        u.role="banned"
        await self.session.commit()
        await self.session.refresh(u)
        return user_db_to_domain(u)
    
