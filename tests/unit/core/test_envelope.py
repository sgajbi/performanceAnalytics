# tests/unit/core/test_envelope.py
from datetime import date
import pytest
from pydantic import ValidationError
from core.envelope import BaseRequest, Periods, RollingPeriod, FXRequestBlock


def test_base_request_validation_happy_path():
    """Tests that a minimal valid BaseRequest payload is parsed correctly."""
    payload = {"as_of": "2025-08-31", "periods": {"type": "YTD"}}
    try:
        req = BaseRequest.model_validate(payload)
        assert req.as_of == date(2025, 8, 31)
        assert req.periods.type == "YTD"
        assert req.precision_mode == "FLOAT64"  # Check default
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly: {e}")


def test_periods_model_validation():
    """Tests validation rules within the Periods model."""
    # Fails because type is EXPLICIT but no explicit block is provided
    with pytest.raises(ValidationError, match='"explicit" period definition is required'):
        Periods(type="EXPLICIT")

    # Fails because type is ROLLING but no rolling block is provided
    with pytest.raises(ValidationError, match='"rolling" period definition is required'):
        Periods(type="ROLLING")

    # Succeeds
    Periods(type="EXPLICIT", explicit={"start": "2025-01-01", "end": "2025-01-31"})
    Periods(type="ROLLING", rolling={"months": 12})


def test_rolling_period_validation():
    """Tests that either months or days must be specified, but not both."""
    # Fails because both are provided
    with pytest.raises(ValidationError, match='Exactly one of "months" or "days" must be specified'):
        RollingPeriod(months=12, days=252)

    # Fails because neither is provided
    with pytest.raises(ValidationError, match='Exactly one of "months" or "days" must be specified'):
        RollingPeriod()

    # Succeeds
    RollingPeriod(months=12)
    RollingPeriod(days=63)


def test_fx_request_block_validation():
    """Tests that the new FXRequestBlock model validates correctly."""
    payload = {
        "source": "CLIENT_SUPPLIED",
        "fixing": "EOD",
        "rates": [{"date": "2025-09-08", "ccy": "EUR", "rate": 1.10}]
    }
    try:
        fx_block = FXRequestBlock.model_validate(payload)
        assert fx_block.rates[0].ccy == "EUR"
    except ValidationError as e:
        pytest.fail(f"FXRequestBlock validation failed unexpectedly: {e}")