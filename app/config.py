from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Sistema de Gestión de Inventario"
    app_environment: str = "development"
    debug: bool = False
    database_url: str = Field(
        default="postgresql+psycopg://inventory_user:inventory_password@localhost:5432/inventory_db"
    )
    recent_movements_limit: int = Field(default=8, ge=1, le=50)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="INVENTORY_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
