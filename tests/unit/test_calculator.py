from datetime import date
from decimal import Decimal

import pandas as pd
import pytest
from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    BOD_CASHFLOW_FIELD,
    END_MARKET_VALUE_FIELD,
    EOD_CASHFLOW_FIELD,
    LONG_CUM_ROR_PERCENT_FIELD,
    MGMT_FEES_FIELD,
    NIP_FIELD,
    PERF_DATE_FIELD,
    SHORT_CUM_ROR_PERCENT_FIELD,
)
from app.services.calculator import PortfolioPerformanceCalculator


@pytest.fixture
def minimal_config():
    """Provides a minimal valid config dictionary for the calculator."""
    return {
        "performance_start_date": "2023-01-01",
        "report_end_date": "2023-01-31",
        "metric_basis": "NET",
    }


@pytest.fixture
def calculator_instance(minimal_config):
    """Provides a PortfolioPerformanceCalculator instance for tests."""
    return PortfolioPerformanceCalculator(config=minimal_config)


def test_parse_date_valid_format(calculator_instance):
    """Test that _parse_date correctly parses a valid date string."""
    date_str = "2023-01-15"
    expected_date = date(2023, 1, 15)
    parsed_date = calculator_instance._parse_date(date_str)
    assert parsed_date == expected_date


def test_parse_date_invalid_format_returns_none(calculator_instance):
    """Test that _parse_date returns None for an invalid date format."""
    date_str = "15-01-2023"  # Invalid format
    parsed_date = calculator_instance._parse_date(date_str)
    assert parsed_date is None


def test_parse_date_none_input_returns_none(calculator_instance):
    """Test that _parse_date handles None input gracefully."""
    parsed_date = calculator_instance._parse_date(None)
    assert parsed_date is None


def test_parse_date_empty_string_returns_none(calculator_instance):
    """Test that _parse_date handles an empty string."""
    parsed_date = calculator_instance._parse_date("")
    assert parsed_date is None


# ### Existing Granular Unit Tests ###


def test_get_sign(calculator_instance):
    """Tests the _get_sign helper function."""
    assert calculator_instance._get_sign(100) == 1
    assert calculator_instance._get_sign(-50) == -1
    assert calculator_instance._get_sign(0) == 0


def test_calculate_perf_reset(calculator_instance):
    """Tests the _calculate_perf_reset helper function."""
    assert calculator_instance._calculate_perf_reset(0, 0, 0, 0) == 0
    assert calculator_instance._calculate_perf_reset(1, 0, 0, 0) == 1
    assert calculator_instance._calculate_perf_reset(0, 1, 0, 0) == 1
    assert calculator_instance._calculate_perf_reset(0, 0, 1, 0) == 1
    assert calculator_instance._calculate_perf_reset(0, 0, 0, 1) == 1
    assert calculator_instance._calculate_perf_reset(1, 1, 0, 0) == 1


def test_sign_persists_without_cashflow(calculator_instance):
    """
    Tests that the sign from the previous day is carried forward if the sign
    flips but there are no cashflows to justify it.
    """
    prev_day = {"sign": -1, "Eod Cashflow": 0, "Perf Reset": 0}
    # val_for_sign is positive, but prev_sign was negative with no current cashflow
    new_sign = calculator_instance._calculate_sign(
        current_day=2, val_for_sign=100, prev_day_calculated=prev_day, current_bod_cf=Decimal(0)
    )
    assert new_sign == -1


def test_sign_flips_with_cashflow(calculator_instance):
    """
    Tests that the sign flips if the value changes and there is a current
    day cashflow.
    """
    prev_day = {"sign": -1, "Eod Cashflow": 0, "Perf Reset": 0}
    # val_for_sign is positive, and there is a BOD cashflow to justify the change
    new_sign = calculator_instance._calculate_sign(
        current_day=2, val_for_sign=100, prev_day_calculated=prev_day, current_bod_cf=Decimal(1100)
    )
    assert new_sign == 1


# ### New Unit Tests for NIP and Zero-Value Logic ###


def test_nip_triggered_for_all_zero_day(calculator_instance):
    """Tests that the NIP flag is correctly triggered for a day with all zero values."""
    data = [
        {
            BEGIN_MARKET_VALUE_FIELD: Decimal(0),
            BOD_CASHFLOW_FIELD: Decimal(0),
            END_MARKET_VALUE_FIELD: Decimal(0),
            EOD_CASHFLOW_FIELD: Decimal(0),
        }
    ]
    df = pd.DataFrame(data)
    nip_series = calculator_instance._calculate_nip_vectorized(df)
    assert nip_series.iloc[0] == 1


def test_nip_not_triggered_for_offsetting_cashflow(calculator_instance):
    """
    Tests that NIP is not triggered for a day with offsetting cashflows that
    don't meet the specific (and unusual) NIP formula.
    """
    data = [
        {
            BEGIN_MARKET_VALUE_FIELD: Decimal(0),
            BOD_CASHFLOW_FIELD: Decimal(20),
            END_MARKET_VALUE_FIELD: Decimal(0),
            EOD_CASHFLOW_FIELD: Decimal(-20),
        }
    ]
    df = pd.DataFrame(data)
    nip_series = calculator_instance._calculate_nip_vectorized(df)
    assert nip_series.iloc[0] == 0


def test_ror_carries_forward_on_nip_day(calculator_instance):
    """
    Tests that final cumulative RoR is carried forward from the previous day
    when the current day is a NIP day.
    """
    prev_day = {
        LONG_CUM_ROR_PERCENT_FIELD: Decimal("5.0"),
        SHORT_CUM_ROR_PERCENT_FIELD: Decimal("0"),
        NIP_FIELD: 0,  # Add the missing key
    }
    # For a NIP day, the function should return the previous day's final values.
    long_ror, short_ror = calculator_instance._calculate_long_short_cum_ror_final(
        current_nip=1,
        current_perf_reset=0,
        current_temp_long_cum_ror=Decimal(0),  # Temp values are irrelevant on a NIP day
        current_temp_short_cum_ror=Decimal(0),
        current_bod_cf=Decimal(0),
        prev_day_calculated=prev_day,
        next_day_data=None,
        effective_period_start_date=date(2025, 1, 1),
        current_perf_date=date(2025, 1, 2),
    )
    assert long_ror == Decimal("5.0")
    assert short_ror == Decimal("0")


def test_daily_ror_is_zero_for_zero_denominator(calculator_instance):
    """
    Tests that daily_ror is safely calculated as 0 when the denominator
    (BMV + BOD_CF) is zero.
    """
    data = [
        {
            "Day": 1,
            PERF_DATE_FIELD: date(2025, 1, 1),
            BEGIN_MARKET_VALUE_FIELD: Decimal(0),
            BOD_CASHFLOW_FIELD: Decimal(0),
            EOD_CASHFLOW_FIELD: Decimal(0),
            MGMT_FEES_FIELD: Decimal(0),
            END_MARKET_VALUE_FIELD: Decimal(0),
        }
    ]
    df = pd.DataFrame(data)
    effective_start_date = pd.Series([date(2025, 1, 1)])
    ror_series = calculator_instance._calculate_daily_ror_vectorized(df, effective_start_date)
    assert ror_series.iloc[0] == Decimal(0)