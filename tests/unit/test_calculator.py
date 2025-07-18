from datetime import date

import pytest

from app.core.config import get_settings  # IMPORTANT CHANGE: Import get_settings
from app.core.exceptions import InvalidInputDataError
from app.services.calculator import PortfolioPerformanceCalculator


@pytest.fixture
def calculator_instance():
    """Provides a PortfolioPerformanceCalculator instance for tests."""
    # Call get_settings() to retrieve the settings object
    config_settings = get_settings()
    return PortfolioPerformanceCalculator(config=config_settings)  # Pass the retrieved settings


def test_parse_date_valid_format(calculator_instance):
    """
    Test that _parse_date correctly parses a valid date string.
    """
    date_str = "2023-01-15"
    expected_date = date(2023, 1, 15)
    parsed_date = calculator_instance._parse_date(date_str)
    assert parsed_date == expected_date


def test_parse_date_invalid_format(calculator_instance):
    """
    Test that _parse_date raises InvalidInputDataError for an invalid date format.
    """
    date_str = "15-01-2023"  # Invalid format
    with pytest.raises(InvalidInputDataError) as excinfo:
        calculator_instance._parse_date(date_str)
    assert "Invalid date format" in str(excinfo.value)


def test_parse_date_none_input(calculator_instance):
    """
    Test that _parse_date handles None input gracefully (though method expects string).
    """
    with pytest.raises(InvalidInputDataError) as excinfo:
        calculator_instance._parse_date(None)
    assert "Date input must be a string" in str(excinfo.value)


def test_parse_date_empty_string(calculator_instance):
    """
    Test that _parse_date handles empty string input.
    """
    with pytest.raises(InvalidInputDataError) as excinfo:
        calculator_instance._parse_date("")
    assert "Date input cannot be empty" in str(excinfo.value)
