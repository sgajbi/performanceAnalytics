# tests/unit/models/test_contribution_models.py
import pytest
from pydantic import ValidationError

from app.models.contribution_requests import ContributionRequest
from app.models.contribution_responses import ContributionResponse


@pytest.fixture
def minimal_contribution_payload():
    """Provides a minimal valid payload for a single-level contribution request."""
    return {
        "portfolio_number": "CONTRIB_001",
        "portfolio_data": {
            "report_start_date": "2025-01-01",
            "report_end_date": "2025-01-31",
            "metric_basis": "NET",
            "period_type": "ITD",
            "daily_data": [],
        },
        "positions_data": [],
    }


def test_contribution_request_single_level_happy_path(minimal_contribution_payload):
    """
    Tests that a standard, single-level contribution request payload is parsed
    correctly by the ContributionRequest model, validating default values.
    """
    try:
        req = ContributionRequest.model_validate(minimal_contribution_payload)
        assert req.portfolio_number == "CONTRIB_001"
        assert req.hierarchy is None
        assert req.weighting_scheme == "BOD"
        assert req.smoothing.method == "CARINO"
        assert req.emit.by_level is False
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly for single-level request: {e}")


def test_contribution_request_multi_level_happy_path(minimal_contribution_payload):
    """
    Tests that a multi-level contribution request with a hierarchy
    and other options is parsed correctly.
    """
    payload = minimal_contribution_payload.copy()
    payload["hierarchy"] = ["assetClass", "sector"]
    payload["weighting_scheme"] = "AVG_CAPITAL"
    payload["emit"] = {"by_level": True}

    try:
        req = ContributionRequest.model_validate(payload)
        assert req.hierarchy == ["assetClass", "sector"]
        assert req.weighting_scheme == "AVG_CAPITAL"
        assert req.emit.by_level is True
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly for multi-level request: {e}")


def test_contribution_request_invalid_weighting_scheme(minimal_contribution_payload):
    """
    Tests that the model raises a validation error for an invalid weighting_scheme.
    """
    payload = minimal_contribution_payload.copy()
    payload["weighting_scheme"] = "INVALID_SCHEME"

    with pytest.raises(ValidationError):
        ContributionRequest.model_validate(payload)


def test_contribution_response_multi_level_happy_path():
    """
    Tests that a valid multi-level contribution response payload is parsed
    correctly by the ContributionResponse Pydantic model.
    """
    payload = {
        "calculation_id": "a4b7e289-7e28-4b7e-8e28-7e284b7e8e28",
        "portfolio_number": "HIERARCHY_01",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-31",
        "summary": {
            "portfolio_contribution": 1.82,
            "coverage_mv_pct": 99.7,
            "weighting_scheme": "BOD",
        },
        "levels": [
            {
                "level": 1,
                "name": "assetClass",
                "rows": [
                    {"key": {"assetClass": "Equity"}, "contribution": 1.14, "weight_avg": 62.0},
                    {"key": {"assetClass": "Bond"}, "contribution": 0.61, "weight_avg": 35.0},
                ],
            },
            {
                "level": 2,
                "name": "sector",
                "parent": "assetClass",
                "rows": [{"key": {"assetClass": "Equity", "sector": "Tech"}, "contribution": 0.71, "children_count": 12}],
            },
        ],
        "meta": {
            "calculation_id": "a4b7e289-7e28-4b7e-8e28-7e284b7e8e28",
            "engine_version": "0.4.0",
            "precision_mode": "FLOAT64",
            "annualization": {"enabled": False, "basis": "BUS/252"},
            "calendar": {"type": "BUSINESS"},
            "periods": {"type": "YTD", "start": "2025-01-01", "end": "2025-01-31"},
        },
        "diagnostics": {"nip_days": 0, "reset_days": 0, "effective_period_start": "2025-01-01", "notes": []},
        "audit": {"counts": {"input_positions": 50}},
    }

    try:
        resp = ContributionResponse.model_validate(payload)
        assert resp.summary.portfolio_contribution == 1.82
        assert len(resp.levels) == 2
        assert resp.levels[0].name == "assetClass"
        assert resp.levels[1].rows[0].key["sector"] == "Tech"
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly for multi-level response: {e}")