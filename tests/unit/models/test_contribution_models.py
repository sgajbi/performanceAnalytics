# tests/unit/models/test_contribution_models.py
import pytest
from pydantic import ValidationError

from app.models.contribution_requests import ContributionRequest


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