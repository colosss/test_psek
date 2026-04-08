from pydantic_settings import BaseSettings, SettingsConfigDict
from src.infrastructure.database.db_config import DbSettings

class Settings(BaseSettings):
    model_config=SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    """
    Так как в репозитории нет .env файла,
    поэтому прописываю значения по умолчанию,
    чтобы сервис можно было запустить без ошибки.
    В рельных условиях значения берутся строго из .env файла
    """
    JWT_SECRET_KEY: str="qylI_uuIlf0xvBaB39ElGWv-ulGpQmxL8_c0c8aAiEY" #Для проверки работоспособности
    JWT_ALGORITHM: str="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MODE: str="normal" 

    @property
    def db(self)->DbSettings:
        return DbSettings()
    
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db.DB_USER}:{self.db.DB_PASSWORD}@{self.db.DB_HOST}:{self.db.DB_PORT}/{self.db.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        return f"postgresql://{self.db.DB_USER}:{self.db.DB_PASSWORD}@{self.db.DB_HOST}:{self.db.DB_PORT}/{self.db.DB_NAME}"

settings=Settings()