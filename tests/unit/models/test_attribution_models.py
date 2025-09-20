# tests/unit/models/test_attribution_models.py
import pytest
from pydantic import ValidationError
from app.models.attribution_requests import AttributionRequest
from common.enums import PeriodType


@pytest.fixture
def base_attribution_payload():
    """Provides a base payload for attribution requests, excluding period definitions."""
    return {
        "portfolio_number": "ATTRIB_001",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-31",
        "mode": "by_group",
        "group_by": ["assetClass"],
        "portfolio_groups_data": [],
        "benchmark_groups_data": [
            {
                "key": {"assetClass": "Equity"},
                "observations": [{"date": "2025-01-31", "return_base": 0.05, "weight_bop": 1.0}],
            }
        ],
    }


def test_attribution_request_with_periods_passes(base_attribution_payload):
    """Tests that a request using the new 'periods' array is valid."""
    payload = base_attribution_payload.copy()
    payload["periods"] = [PeriodType.YTD, PeriodType.MTD]
    try:
        AttributionRequest.model_validate(payload)
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with 'periods': {e}")


def test_attribution_request_with_legacy_period_type_passes(base_attribution_payload):
    """Tests that a request using the legacy 'period_type' field is valid."""
    payload = base_attribution_payload.copy()
    payload["period_type"] = PeriodType.ITD
    try:
        AttributionRequest.model_validate(payload)
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with legacy 'period_type': {e}")


def test_attribution_request_with_both_fails(base_attribution_payload):
    """Tests that validation fails if both 'periods' and 'period_type' are provided."""
    payload = base_attribution_payload.copy()
    payload["periods"] = [PeriodType.YTD]
    payload["period_type"] = PeriodType.YTD
    with pytest.raises(ValidationError, match="Exactly one of 'periods' or 'period_type' must be provided"):
        AttributionRequest.model_validate(payload)


def test_attribution_request_with_neither_fails(base_attribution_payload):
    """Tests that validation fails if neither 'periods' nor 'period_type' is provided."""
    with pytest.raises(ValidationError, match="Exactly one of 'periods' or 'period_type' must be provided"):
        AttributionRequest.model_validate(base_attribution_payload)