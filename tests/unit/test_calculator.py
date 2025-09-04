from datetime import date

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