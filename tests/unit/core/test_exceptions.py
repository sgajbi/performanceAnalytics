# tests/unit/core/test_exceptions.py
import pytest

from app.core.exceptions import (
    CalculationLogicError,
    InvalidInputDataError,
    MissingConfigurationError,
    PerformanceCalculatorError,
)


@pytest.mark.parametrize(
    "exception_class, default_message",
    [
        (PerformanceCalculatorError, "Base exception for all performance calculator errors."),
        (InvalidInputDataError, "Invalid input data provided for performance calculation."),
        (CalculationLogicError, "An error occurred during performance calculation logic."),
        (MissingConfigurationError, "Missing required configuration for performance calculator."),
    ],
)
def test_custom_exceptions_instantiation(exception_class, default_message):
    """
    Tests that custom exception classes can be instantiated with both
    default and custom messages.
    """
    # Test with default message
    exc_default = exception_class()
    assert exc_default.message == default_message

    # Test with custom message
    custom_message = "This is a custom message."
    exc_custom = exception_class(custom_message)
    assert exc_custom.message == custom_message