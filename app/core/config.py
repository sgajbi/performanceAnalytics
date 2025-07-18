# app/core/config.py

import os
from decimal import getcontext
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Portfolio Performance Analytics API"  # Corrected to uppercase APP_NAME
    APP_VERSION: str = "0.1.0"  # Corrected to uppercase APP_VERSION
    APP_DESCRIPTION: str = (
        "API for calculating portfolio performance metrics."  # Corrected to uppercase APP_DESCRIPTION
    )
    LOG_LEVEL: str = "INFO"
    decimal_precision: int = 28

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings():
    """
    Caches the settings object for efficient access.
    Initializes Decimal context precision here as it's a global setting for Decimal operations.
    """
    settings = Settings()
    getcontext().prec = settings.decimal_precision
    return settings
