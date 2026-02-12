from datetime import timedelta
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "PlatformOPS Backend"
    DEBUG: bool = True
    APP_PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    # For VM deployment:
    DB_HOST: str = "192.168.21.1"

    # For local Windows execution:
    # DB_HOST: str = "localhost"

    DB_PORT: int = 5432
    DB_NAME: str = "platformops"
    DB_USER: str = "platformops"
    DB_PASSWORD: str = "platformops"

    SECRET_KEY: str = "CHANGE_ME_SUPER_SECRET"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "platformops@local.test"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
