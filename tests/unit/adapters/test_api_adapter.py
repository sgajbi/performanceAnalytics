# tests/unit/adapters/test_api_adapter.py
from datetime import date
from typing import Any, Dict, List

import pandas as pd
import pytest

from adapters.api_adapter import create_engine_config, create_engine_dataframe, format_breakdowns_for_response
from app.core.constants import BEGIN_MARKET_VALUE_FIELD, END_MARKET_VALUE_FIELD, PERF_DATE_FIELD
from app.models.requests import PerformanceRequest
from app.models.responses import PerformanceResultItem, PerformanceSummary
from common.enums import Frequency, PeriodType
from engine.config import EngineConfig
from engine.schema import PortfolioColumns


@pytest.fixture
def sample_engine_outputs():
    """Provides sample, raw engine outputs for testing the response formatter."""
    breakdowns_data = {
        Frequency.DAILY: [
            {
                "period": "2025-01-01",
                "summary": {
                    PortfolioColumns.BEGIN_MV: 1000.0,
                    PortfolioColumns.END_MV: 1010.0,
                    "net_cash_flow": 0.0,
                    "period_return_pct": 1.0,
                },
            }
        ],
        Frequency.MONTHLY: [
            {
                "period": "2025-01",
                "summary": {
                    PortfolioColumns.BEGIN_MV: 1000.0,
                    PortfolioColumns.END_MV: 1010.0,
                    "net_cash_flow": 0.0,
                    "period_return_pct": 1.0,
                },
            }
        ],
    }
    daily_results_df = pd.DataFrame(
        [
            {
                PortfolioColumns.PERF_DATE: date(2025, 1, 1),
                PortfolioColumns.BEGIN_MV: 1000.0,
                PortfolioColumns.END_MV: 1010.0,
            }
        ]
    )
    return breakdowns_data, daily_results_df


def test_create_engine_config():
    """
    Tests that the adapter correctly converts a PerformanceRequest
    into an EngineConfig object.
    """
    request_data = {
        "portfolio_number": "TEST_01",
        "performance_start_date": "2024-12-31",
        "report_end_date": "2025-01-31",
        "metric_basis": "NET",
        "period_type": "YTD",
        "frequencies": ["daily"],
        "daily_data": [],
    }
    pydantic_request = PerformanceRequest.model_validate(request_data)

    engine_config = create_engine_config(pydantic_request)

    assert isinstance(engine_config, EngineConfig)
    assert engine_config.performance_start_date == date(2024, 12, 31)
    assert engine_config.metric_basis == "NET"
    assert engine_config.rounding_precision == 6


def test_create_engine_dataframe_happy_path():
    """
    Tests that a list of daily data dictionaries is correctly converted
    into a DataFrame with internal engine schema column names.
    """
    api_daily_data: List[Dict[str, Any]] = [
        {PERF_DATE_FIELD: "2025-01-01", BEGIN_MARKET_VALUE_FIELD: 1000},
        {PERF_DATE_FIELD: "2025-01-02", BEGIN_MARKET_VALUE_FIELD: 1010},
    ]

    engine_df = create_engine_dataframe(api_daily_data)

    assert isinstance(engine_df, pd.DataFrame)
    assert not engine_df.empty
    assert PortfolioColumns.PERF_DATE.value in engine_df.columns
    assert PortfolioColumns.BEGIN_MV.value in engine_df.columns


def test_create_engine_dataframe_empty_input():
    """
    Tests that an empty list of daily data correctly results in an empty DataFrame.
    """
    empty_api_data: List[Dict[str, Any]] = []
    engine_df = create_engine_dataframe(empty_api_data)
    assert isinstance(engine_df, pd.DataFrame)
    assert engine_df.empty


def test_create_engine_dataframe_raises_error():
    """
    Tests that the adapter function correctly raises a ValueError for malformed input,
    ensuring the exception path is covered.
    """
    malformed_api_data = [
        {PERF_DATE_FIELD: "2025-01-01", BEGIN_MARKET_VALUE_FIELD: 1000},
        "not_a_dictionary"
    ]
    with pytest.raises(ValueError, match="Failed to process daily data"):
        create_engine_dataframe(malformed_api_data)


def test_format_breakdowns_for_response_daily(sample_engine_outputs):
    """
    Tests that the daily breakdown is formatted correctly, including
    the nested daily_data field with API-aliased keys.
    """
    breakdowns_data, daily_results_df = sample_engine_outputs
    formatted_response = format_breakdowns_for_response(breakdowns_data, daily_results_df, compat_legacy_names=False)

    assert Frequency.DAILY in formatted_response
    daily_breakdown = formatted_response[Frequency.DAILY]
    result_item = daily_breakdown[0]
    assert isinstance(result_item, PerformanceResultItem)
    assert isinstance(result_item.summary, PerformanceSummary)
    assert result_item.summary.begin_market_value == 1000.0
    assert result_item.daily_data is not None
    nested_daily = result_item.daily_data[0]
    assert BEGIN_MARKET_VALUE_FIELD in nested_daily


def test_format_breakdowns_for_response_monthly(sample_engine_outputs):
    """
    Tests that aggregated breakdowns (e.g., monthly) are formatted
    correctly, with the daily_data field being None.
    """
    breakdowns_data, daily_results_df = sample_engine_outputs
    formatted_response = format_breakdowns_for_response(breakdowns_data, daily_results_df, compat_legacy_names=False)

    assert Frequency.MONTHLY in formatted_response
    monthly_breakdown = formatted_response[Frequency.MONTHLY]
    result_item = monthly_breakdown[0]
    assert isinstance(result_item, PerformanceResultItem)
    assert result_item.period == "2025-01"
    assert result_item.daily_data is None


def test_format_breakdowns_for_response_empty_input():
    """
    Tests that the formatter handles empty engine output gracefully.
    """
    empty_breakdowns = {}
    empty_df = pd.DataFrame()
    formatted_response = format_breakdowns_for_response(empty_breakdowns, empty_df, compat_legacy_names=False)
    assert formatted_response == {}