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


def test_attribution_request_with_analyses_passes(base_attribution_payload):
    """Tests that a request using the new 'analyses' array is valid."""
    # --- START FIX: Align test with new model ---
    payload = base_attribution_payload.copy()
    payload["analyses"] = [{"period": PeriodType.YTD, "frequencies": ["monthly"]}]
    try:
        AttributionRequest.model_validate(payload)
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with 'analyses': {e}")
    # --- END FIX ---


def test_attribution_request_with_empty_analyses_fails(base_attribution_payload):
    """Tests that validation fails if 'analyses' is an empty list."""
    # --- START FIX: Align test with new model ---
    payload = base_attribution_payload.copy()
    payload["analyses"] = []
    with pytest.raises(ValidationError, match="analyses list cannot be empty"):
        AttributionRequest.model_validate(payload)
    # --- END FIX ---


def test_attribution_request_with_no_analyses_fails(base_attribution_payload):
    """Tests that validation fails if the 'analyses' field is missing entirely."""
    # --- START FIX: Align test with new model ---
    with pytest.raises(ValidationError, match="Field required"):
        AttributionRequest.model_validate(base_attribution_payload)
    # --- END FIX ---