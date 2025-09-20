# tests/unit/models/test_requests_models.py
import pytest
from pydantic import ValidationError

from app.models.requests import PerformanceRequest
from common.enums import PeriodType


@pytest.fixture
def base_twr_payload():
    """Provides a base payload for TWR requests, excluding period definitions."""
    return {
        "portfolio_number": "VALIDATION_TEST",
        "performance_start_date": "2024-12-31",
        "metric_basis": "NET",
        "report_end_date": "2025-01-31",
        "frequencies": ["daily"],
        "daily_data": [],
    }


def test_performance_request_with_periods_passes(base_twr_payload):
    """Tests that validation succeeds when the new 'periods' array is used."""
    payload = base_twr_payload.copy()
    payload["periods"] = [PeriodType.YTD, PeriodType.MTD]
    try:
        PerformanceRequest.model_validate(payload)
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with 'periods': {e}")


def test_performance_request_with_period_type_passes(base_twr_payload):
    """Tests that validation succeeds with the legacy 'period_type' for backward compatibility."""
    payload = base_twr_payload.copy()
    payload["period_type"] = PeriodType.YTD
    try:
        PerformanceRequest.model_validate(payload)
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with 'period_type': {e}")


def test_performance_request_with_both_fails(base_twr_payload):
    """Tests that validation fails if both 'periods' and 'period_type' are provided."""
    payload = base_twr_payload.copy()
    payload["periods"] = [PeriodType.YTD]
    payload["period_type"] = PeriodType.YTD
    with pytest.raises(ValidationError, match="Exactly one of 'periods' or 'period_type' must be provided"):
        PerformanceRequest.model_validate(payload)


def test_performance_request_with_neither_fails(base_twr_payload):
    """Tests that validation fails if neither 'periods' nor 'period_type' is provided."""
    with pytest.raises(ValidationError, match="Exactly one of 'periods' or 'period_type' must be provided"):
        PerformanceRequest.model_validate(base_twr_payload)


def test_performance_request_with_empty_periods_list_fails(base_twr_payload):
    """Tests that validation fails if 'periods' is an empty list."""
    payload = base_twr_payload.copy()
    payload["periods"] = []
    with pytest.raises(ValidationError, match="The 'periods' list cannot be empty"):
        PerformanceRequest.model_validate(payload)