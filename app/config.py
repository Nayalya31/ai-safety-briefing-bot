from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(alias="OPENAI_MODEL")
    database_url: str = Field(alias="DATABASE_URL")
    materials_dir: Path = Field(default=Path("materials"), alias="MATERIALS_DIR")
    demo_access_enabled: bool = Field(default=True, alias="DEMO_ACCESS_ENABLED")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    health_port: int = Field(default=8080, alias="HEALTH_PORT", ge=1, le=65535)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def require_async_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL должен использовать postgresql+asyncpg://")
        return value

    @field_validator("openai_model")
    @classmethod
    def require_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("OPENAI_MODEL не задан")
        return value.strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
