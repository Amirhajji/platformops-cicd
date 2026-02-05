from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "PlatformOPS Backend"
    DEBUG: bool = True

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "platformops"
    DB_USER: str = "platformops"
    DB_PASSWORD: str = "platformops"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
