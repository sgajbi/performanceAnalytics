from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables.
    """
    APP_NAME: str = "Portfolio Performance Analytics API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "API for calculating portfolio performance metrics."
    LOG_LEVEL: str = "INFO"

    # Example of a sensitive setting, loaded from .env or environment variable
    # This would typically be for a database URL, API key, etc.
    # We don't have one yet, but this shows how to structure it.
    # SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    """
    Caches the settings object for efficient access.
    """
    return Settings()