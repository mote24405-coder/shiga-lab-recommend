from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/lab_recommend"
    sync_database_url: str = "postgresql://postgres:password@localhost:5432/lab_recommend"
    secret_key: str = "dev-secret-key-change-in-production"
    app_env: str = "development"
    admin_password: str = "admin"
    debug: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
