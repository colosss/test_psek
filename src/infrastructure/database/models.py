from sqlalchemy.orm import Mapped, mapped_column
from src.infrastructure.database.base import Base
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
# from sqlalchemy.sql.expression import

class User(Base):
    __tablename__="user"
    id: Mapped[str]=mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True)
    role: Mapped[str]=mapped_column(String(10))
    hashed_password: Mapped[str|None]=mapped_column(String(255), nullable=True)