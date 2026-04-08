from abc import ABC, abstractmethod
from typing import Optional, Sequence
from uuid import UUID
from datetime import date as date_type
from src.core.domain.models import (
    User
)

class AbstractUserRepository(ABC):
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID)->Optional[User]: ...

    @abstractmethod
    async def get_by_email(self, email: str)->Optional[User]: ...

    @abstractmethod
    async def create(self, email: str, role: str, hashed_password: Optional[str])->User: ...

    @abstractmethod
    async def get_or_create_dummy(self, user_id: UUID, role: str)->User: ...