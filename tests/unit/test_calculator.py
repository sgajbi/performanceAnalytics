from datetime import date
from decimal import Decimal

import pytest

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


# ### New Granular Unit Tests ###


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