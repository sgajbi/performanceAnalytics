# tests/unit/models/test_contribution_models.py
import pytest
from pydantic import ValidationError

from app.models.contribution_requests import ContributionRequest
from app.models.contribution_responses import ContributionResponse
from common.enums import PeriodType


@pytest.fixture
def minimal_contribution_payload():
    """Provides a minimal valid payload for a contribution request."""
    return {
        "portfolio_number": "CONTRIB_001",
        "report_start_date": "2025-01-01",
        "report_end_date": "2025-01-31",
        "portfolio_data": {
            "metric_basis": "NET",
            "daily_data": [],
        },
        "positions_data": [
            {"position_id": "Stock_A", "meta": {"sector": "Tech"}, "daily_data": []}
        ],
    }


def test_contribution_request_with_periods_passes(minimal_contribution_payload):
    """Tests that a request using the new top-level 'periods' field is valid."""
    payload = minimal_contribution_payload.copy()
    payload["periods"] = [PeriodType.YTD]
    try:
        req = ContributionRequest.model_validate(payload)
        assert req.portfolio_number == "CONTRIB_001"
        assert req.periods == [PeriodType.YTD]
        assert req.period_type is None
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with 'periods': {e}")


def test_contribution_request_with_legacy_period_type_passes(minimal_contribution_payload):
    """Tests that a request using the legacy 'period_type' field is valid."""
    payload = minimal_contribution_payload.copy()
    payload["period_type"] = PeriodType.ITD
    try:
        req = ContributionRequest.model_validate(payload)
        assert req.period_type == PeriodType.ITD
        assert req.periods is None
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly with legacy 'period_type': {e}")


def test_contribution_request_multi_level_happy_path(minimal_contribution_payload):
    """
    Tests that a multi-level contribution request with a hierarchy
    and other options is parsed correctly.
    """
    payload = minimal_contribution_payload.copy()
    payload["periods"] = [PeriodType.QTD]
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
    payload["periods"] = [PeriodType.YTD]
    payload["weighting_scheme"] = "INVALID_SCHEME"

    with pytest.raises(ValidationError):
        ContributionRequest.model_validate(payload)


def test_contribution_response_multi_level_happy_path():
    """
    Tests that a valid multi-level contribution response payload is parsed
    correctly by the ContributionResponse Pydantic model.
    """
    # This payload matches the structure from RFC-019
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