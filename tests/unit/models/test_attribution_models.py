# tests/unit/models/test_attribution_models.py
import pytest
from pydantic import ValidationError
from app.models.attribution_requests import AttributionRequest


def test_attribution_request_by_instrument_validation():
    """Tests that a valid 'by_instrument' payload is correctly parsed by the AttributionRequest model."""
    payload = {
        "portfolio_number": "ATTRIB_001",
        "mode": "by_instrument",
        "group_by": ["assetClass"],
        "portfolio_data": {
            "report_start_date": "2025-01-01",
            "report_end_date": "2025-01-31",
            "metric_basis": "NET",
            "period_type": "ITD",
            "daily_data": [],
        },
        "instruments_data": [
            {"instrument_id": "AAPL", "meta": {"assetClass": "Equity"}, "daily_data": []}
        ],
        "benchmark_groups_data": [
            {
                "key": {"assetClass": "Equity"},
                "observations": [
                    {"date": "2025-01-31", "return": 0.05, "weight_bop": 1.0}
                ],
            }
        ],
    }

    try:
        AttributionRequest.model_validate(payload)
    except ValidationError as e:
        pytest.fail(f"Pydantic model validation failed unexpectedly: {e}")