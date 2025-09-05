# tests/unit/adapters/test_api_adapter.py
from datetime import date

import pandas as pd
import pytest

from adapters.api_adapter import create_engine_config
from app.models.requests import PerformanceRequest
from common.enums import Frequency, PeriodType
from engine.config import EngineConfig


def test_create_engine_config():
    """
    Tests that the adapter correctly converts a PerformanceRequest
    into an EngineConfig object.
    """
    # Arrange
    request_data = {
        "portfolio_number": "TEST_01",
        "performance_start_date": "2024-12-31",
        "report_end_date": "2025-01-31",
        "metric_basis": "NET",
        "period_type": "YTD",
        "frequencies": ["daily"],
        "daily_data": []
    }
    pydantic_request = PerformanceRequest.model_validate(request_data)

    # Act
    engine_config = create_engine_config(pydantic_request)

    # Assert
    assert isinstance(engine_config, EngineConfig)
    assert engine_config.performance_start_date == date(2024, 12, 31)
    assert engine_config.report_end_date == date(2025, 1, 31)
    assert engine_config.metric_basis == "NET"
    assert engine_config.period_type == PeriodType.YTD
    assert engine_config.rounding_precision == 4  # Default value