import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    COOKIES_DIR: str = "./cookies"
    DB_PATH: str = "./accounts.db"
    PLATFORM_DB_PATH: str = "./platform_accounts.db"
    REFRESH_EVERY: int = 500
    PROXY: str | None = os.environ.get(
        "https_proxy"
    ) or os.environ.get("HTTPS_PROXY")

    model_config = {"env_file": ".env"}


settings = Settings()
