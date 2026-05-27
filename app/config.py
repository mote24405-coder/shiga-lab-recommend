from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/lab_recommend"
    secret_key: str = "dev-secret-key-change-in-production"
    app_env: str = "development"
    admin_username: str = "admin"
    admin_password: str = "admin"
    debug: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}

    def model_post_init(self, __context) -> None:
        # Railway provides DATABASE_URL as postgres:// or postgresql://
        # Convert to postgresql+asyncpg:// for asyncpg
        url = self.database_url
        if url.startswith("postgres://"):
            object.__setattr__(self, "database_url", "postgresql+asyncpg://" + url[len("postgres://"):])
        elif url.startswith("postgresql://"):
            object.__setattr__(self, "database_url", "postgresql+asyncpg://" + url[len("postgresql://"):])


@lru_cache
def get_settings() -> Settings:
    return Settings()
