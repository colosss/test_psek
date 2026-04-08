from asyncio import current_task
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    async_scoped_session,
)
from src.infrastructure.database.db_config import DbSettings

class DataBaseHelper:
    def __init__(self, url: str, echo: bool=False):
        self.engine=create_async_engine(
            url=url,
            echo=echo,
        )
        self.session_factory=async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def get_scope_session(self):
        session = async_scoped_session(
            session_factory = self.session_factory,
            scopefunc = current_task,
        )
        return session
    
    async def session_dependency(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session
            await session.close()

    async def scope_session_dependency(self) -> AsyncSession:
        session = self.get_scope_session()
        yield session
        await session.close()


_db_settings = DbSettings()
db_helper = DataBaseHelper(
    url=_db_settings.url,
    echo=_db_settings.DB_ECHO,
)