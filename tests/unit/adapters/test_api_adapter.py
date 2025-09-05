# tests/unit/adapters/test_api_adapter.py
from datetime import date
from typing import Any, Dict, List

import pandas as pd
import pytest

from adapters.api_adapter import create_engine_config, create_engine_dataframe
from app.core.constants import PERF_DATE_FIELD, BEGIN_MARKET_VALUE_FIELD
from app.models.requests import PerformanceRequest
from common.enums import Frequency, PeriodType
from engine.config import EngineConfig
from engine.schema import PortfolioColumns


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


def test_create_engine_dataframe_happy_path():
    """
    Tests that a list of daily data dictionaries is correctly converted
    into a DataFrame with internal engine schema column names.
    """
    # Arrange
    api_daily_data: List[Dict[str, Any]] = [
        {PERF_DATE_FIELD: "2025-01-01", BEGIN_MARKET_VALUE_FIELD: 1000},
        {PERF_DATE_FIELD: "2025-01-02", BEGIN_MARKET_VALUE_FIELD: 1010},
    ]

    # Act
    engine_df = create_engine_dataframe(api_daily_data)

    # Assert
    assert isinstance(engine_df, pd.DataFrame)
    assert not engine_df.empty
    assert len(engine_df) == 2
    # Check that API aliases have been renamed to the internal engine schema
    assert PortfolioColumns.PERF_DATE.value in engine_df.columns
    assert PortfolioColumns.BEGIN_MV.value in engine_df.columns
    assert PERF_DATE_FIELD not in engine_df.columns


def test_create_engine_dataframe_empty_input():
    """
    Tests that an empty list of daily data correctly results in an empty DataFrame.
    """
    # Arrange
    empty_api_data: List[Dict[str, Any]] = []

    # Act
    engine_df = create_engine_dataframe(empty_api_data)

    # Assert
    assert isinstance(engine_df, pd.DataFrame)
    assert engine_df.empty