from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from decimal import Decimal, getcontext # Import Decimal and getcontext

class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables.
    """
    APP_NAME: str = "Portfolio Performance Analytics API"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "API for calculating portfolio performance metrics."
    LOG_LEVEL: str = "INFO"

    # New: Setting for decimal precision in financial calculations
    # Defaulting to 10 for now, but can be overridden by env variable
    DECIMAL_PRECISION: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    """
    Caches the settings object for efficient access.
    Initializes Decimal context precision here as it's a global setting for Decimal operations.
    """
    settings = Settings()
    getcontext().prec = settings.DECIMAL_PRECISION # Set the global precision for Decimal
    return settings