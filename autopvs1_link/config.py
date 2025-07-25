"""Configuration settings for AutoPVS1 Link."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    AUTOPVS1_BASE_URL: str = "https://autopvs1.bgi.com"
    CACHE_SIZE: int = 256
    CACHE_TTL_HOURS: int = 24
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "*"
    REQUEST_TIMEOUT: int = 30
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
