# tests/unit/engine/test_exceptions.py
import pytest
from engine.exceptions import (
    EngineError,
    InvalidEngineInputError,
    EngineCalculationError,
)

@pytest.mark.parametrize(
    "exception_class, default_message",
    [
        (EngineError, "An error occurred in the performance engine."),
        (InvalidEngineInputError, "Invalid input data provided to the engine."),
        (EngineCalculationError, "An error occurred during an engine calculation."),
    ]
)
def test_engine_exceptions(exception_class, default_message):
    """Tests that custom exceptions can be instantiated."""
    # Test with default message
    exc_default = exception_class()
    assert exc_default.message == default_message

    # Test with custom message
    custom_message = "This is a custom message."
    exc_custom = exception_class(custom_message)
    assert exc_custom.message == custom_message