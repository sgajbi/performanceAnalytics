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


# ### Unit Tests for NIP and Zero-Value Logic ###


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
        NIP_FIELD: 0,
    }
    # For a NIP day, the function should return the previous day's final values.
    long_ror, short_ror = calculator_instance._calculate_long_short_cum_ror_final(
        current_nip=1,
        current_perf_reset=0,
        current_temp_long_cum_ror=Decimal(0),
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


# ### Unit Test for Standard Compounding ###


def test_long_ror_compounds_correctly(calculator_instance):
    """
    Tests that the geometric linking (compounding) of daily returns for
    long positions is calculated correctly over multiple days.
    """
    # Day 1: 10% gain
    day1_ror = Decimal("10")
    temp_long_ror1 = calculator_instance._calculate_temp_long_cum_ror(
        current_sign=Decimal(1),
        current_daily_ror=day1_ror,
        current_perf_date=date(2025, 1, 1),
        prev_day_calculated=None,
        current_bmv_bcf_sign=Decimal(1),
        effective_period_start_date=date(2025, 1, 1),
    )
    assert temp_long_ror1 == pytest.approx(Decimal("10"))

    # Day 2: Another 10% gain, should compound to 21%
    day2_ror = Decimal("10")
    prev_day2 = {LONG_CUM_ROR_PERCENT_FIELD: temp_long_ror1}
    temp_long_ror2 = calculator_instance._calculate_temp_long_cum_ror(
        current_sign=Decimal(1),
        current_daily_ror=day2_ror,
        current_perf_date=date(2025, 1, 2),
        prev_day_calculated=prev_day2,
        current_bmv_bcf_sign=Decimal(1),
        effective_period_start_date=date(2025, 1, 1),
    )
    # (1 + 0.10) * (1 + 0.10) - 1 = 1.21 - 1 = 0.21 -> 21%
    assert temp_long_ror2 == pytest.approx(Decimal("21"))


# ### Unit Test for Custom Compounding Logic ###


def test_short_ror_compounds_with_custom_formula(calculator_instance):
    """
    Tests that the custom compounding of daily returns for short positions
    is calculated correctly, matching the specific business formula.
    """
    # Day 1: -50% return
    day1_ror = Decimal("-50")
    temp_short_ror1 = calculator_instance._calculate_temp_short_cum_ror(
        current_sign=Decimal(-1),
        current_daily_ror=day1_ror,
        current_perf_date=date(2025, 1, 1),
        prev_day_calculated=None,
        current_bmv_bcf_sign=Decimal(-1),
        effective_period_start_date=date(2025, 1, 1),
    )
    assert temp_short_ror1 == pytest.approx(Decimal("-50"))

    # Day 2: -133.3333...% daily return
    day2_ror = Decimal("-133.33333333333334")
    prev_day2 = {SHORT_CUM_ROR_PERCENT_FIELD: temp_short_ror1}
    temp_short_ror2 = calculator_instance._calculate_temp_short_cum_ror(
        current_sign=Decimal(-1),
        current_daily_ror=day2_ror,
        current_perf_date=date(2025, 1, 2),
        prev_day_calculated=prev_day2,
        current_bmv_bcf_sign=Decimal(-1),
        effective_period_start_date=date(2025, 1, 1),
    )
    # Asserts the result of the custom formula
    assert temp_short_ror2 == pytest.approx(Decimal("-250"))


# ### Unit Tests for NET vs GROSS Logic ###


def test_daily_ror_net_basis_includes_fees(minimal_config):
    """Tests that daily_ror on a NET basis correctly accounts for fees."""
    minimal_config["metric_basis"] = "NET"
    calculator = PortfolioPerformanceCalculator(config=minimal_config)
    data = [
        {
            PERF_DATE_FIELD: date(2025, 1, 5),
            BEGIN_MARKET_VALUE_FIELD: Decimal(400),
            BOD_CASHFLOW_FIELD: Decimal(0),
            EOD_CASHFLOW_FIELD: Decimal(-20),
            MGMT_FEES_FIELD: Decimal(-20),
            END_MARKET_VALUE_FIELD: Decimal(480),
        }
    ]
    df = pd.DataFrame(data)
    effective_start_date = pd.Series([date(2025, 1, 1)])
    ror_series = calculator._calculate_daily_ror_vectorized(df, effective_start_date)
    # (480 - 400 - (-20) + (-20)) / 400 = 80 / 400 = 0.20 -> 20%
    assert ror_series.iloc[0] == pytest.approx(Decimal("20"))


def test_daily_ror_gross_basis_ignores_fees(minimal_config):
    """Tests that daily_ror on a GROSS basis correctly ignores fees."""
    minimal_config["metric_basis"] = "GROSS"
    calculator = PortfolioPerformanceCalculator(config=minimal_config)
    data = [
        {
            PERF_DATE_FIELD: date(2025, 1, 5),
            BEGIN_MARKET_VALUE_FIELD: Decimal(400),
            BOD_CASHFLOW_FIELD: Decimal(0),
            EOD_CASHFLOW_FIELD: Decimal(-20),
            MGMT_FEES_FIELD: Decimal(-20),  # This should be ignored
            END_MARKET_VALUE_FIELD: Decimal(480),
        }
    ]
    df = pd.DataFrame(data)
    effective_start_date = pd.Series([date(2025, 1, 1)])
    ror_series = calculator._calculate_daily_ror_vectorized(df, effective_start_date)
    # (480 - 400 - (-20)) / 400 = 100 / 400 = 0.25 -> 25%
    assert ror_series.iloc[0] == pytest.approx(Decimal("25"))


# ### New Unit Tests for Period Type Logic ###


@pytest.mark.parametrize(
    "period_type, day1_date, day2_date, report_start_date, expected_ror",
    [
        # YTD: Jan 1 -> Jan 2. Should compound.
        ("YTD", date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 1), Decimal("21")),
        # MTD: Jan 31 -> Feb 1. Should reset because it's a new month.
        ("MTD", date(2025, 1, 31), date(2025, 2, 1), date(2025, 1, 31), Decimal("10")),
        # QTD: Mar 31 -> Apr 1. Should reset because it's a new quarter.
        ("QTD", date(2025, 3, 31), date(2025, 4, 1), date(2025, 3, 31), Decimal("10")),
        # Explicit: Report starts on Day 2. Should reset because Day 1 is before the report start.
        ("Explicit", date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 2), Decimal("10")),
    ],
)
def test_ror_resets_based_on_period_type(
    minimal_config, period_type, day1_date, day2_date, report_start_date, expected_ror
):
    """
    Tests that compounding correctly resets based on the period_type
    (YTD, MTD, QTD, Explicit).
    """
    # Arrange: Each day has a 10% gain
    minimal_config["period_type"] = period_type
    minimal_config["report_start_date"] = report_start_date.strftime("%Y-%m-%d")
    minimal_config["report_end_date"] = day2_date.strftime("%Y-%m-%d")
    minimal_config["performance_start_date"] = day1_date.strftime("%Y-%m-%d")

    calculator = PortfolioPerformanceCalculator(config=minimal_config)

    daily_data = [
        {
            "Day": 1,
            PERF_DATE_FIELD: day1_date,
            BEGIN_MARKET_VALUE_FIELD: 1000,
            BOD_CASHFLOW_FIELD: 0,
            EOD_CASHFLOW_FIELD: 0,
            MGMT_FEES_FIELD: 0,
            END_MARKET_VALUE_FIELD: 1100,
        },
        {
            "Day": 2,
            PERF_DATE_FIELD: day2_date,
            BEGIN_MARKET_VALUE_FIELD: 1100,
            BOD_CASHFLOW_FIELD: 0,
            EOD_CASHFLOW_FIELD: 0,
            MGMT_FEES_FIELD: 0,
            END_MARKET_VALUE_FIELD: 1210,
        },
    ]

    # Act
    results = calculator.calculate_performance(daily_data, minimal_config)

    # Assert
    final_day_result = results[-1]
    assert Decimal(str(final_day_result[LONG_CUM_ROR_PERCENT_FIELD])) == pytest.approx(expected_ror)