# tests/unit/models/test_responses_models.py
from uuid import uuid4
import pytest
from pydantic import ValidationError

from app.models.responses import PerformanceResponse
from core.envelope import Meta, Diagnostics, Audit


@pytest.fixture
def base_response_footer():
    """Provides a valid shared response footer (meta, diagnostics, audit)."""
    calc_id = uuid4()
    return {
        "meta": {
            "calculation_id": str(calc_id),
            "engine_version": "1.0.0",
            "precision_mode": "FLOAT64",
            "annualization": {"enabled": False},
            "calendar": {"type": "BUSINESS"},
            "periods": {},
        },
        "diagnostics": {
            "nip_days": 0,
            "reset_days": 0,
            "effective_period_start": "2025-01-01",
        },
        "audit": {"counts": {"input_rows": 10}},
    }


@pytest.fixture
def single_period_result_payload():
    """Provides a valid payload for a single period's result."""
    return {
        "breakdowns": {
            "daily": [
                {
                    "period": "2025-01-01",
                    "summary": {
                        "begin_mv": 100,
                        "end_mv": 101,
                        "net_cash_flow": 0,
                        "period_return_pct": 1.0,
                    },
                }
            ]
        }
    }


def test_performance_response_new_structure_passes(
    base_response_footer, single_period_result_payload
):
    """Tests that a response with the new 'results_by_period' structure is valid."""
    payload = {
        "calculation_id": base_response_footer["meta"]["calculation_id"],
        "portfolio_number": "TEST_01",
        "results_by_period": {
            "YTD": single_period_result_payload,
            "MTD": single_period_result_payload,
        },
        **base_response_footer,
    }
    try:
        response = PerformanceResponse.model_validate(payload)
        assert "YTD" in response.results_by_period
        assert "MTD" in response.results_by_period
        assert response.breakdowns is None  # Old field should be absent
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly for new structure: {e}")


def test_performance_response_legacy_structure_passes(
    base_response_footer, single_period_result_payload
):
    """Tests that a response with the legacy 'breakdowns' field is still valid."""
    payload = {
        "calculation_id": base_response_footer["meta"]["calculation_id"],
        "portfolio_number": "TEST_01",
        **single_period_result_payload,
        **base_response_footer,
    }
    try:
        response = PerformanceResponse.model_validate(payload)
        assert response.breakdowns is not None
        assert response.results_by_period is None  # New field should be absent
    except ValidationError as e:
        pytest.fail(f"Validation failed unexpectedly for legacy structure: {e}")


def test_performance_response_with_both_structures_fails(
    base_response_footer, single_period_result_payload
):
    """Tests that validation fails if both legacy and new structures are present."""
    payload = {
        "calculation_id": base_response_footer["meta"]["calculation_id"],
        "portfolio_number": "TEST_01",
        "results_by_period": {"YTD": single_period_result_payload},
        **single_period_result_payload,
        **base_response_footer,
    }
    with pytest.raises(ValidationError, match="Provide either 'results_by_period' or the legacy"):
        PerformanceResponse.model_validate(payload)


def test_performance_response_with_neither_structure_fails(base_response_footer):
    """Tests that validation fails if no result structure is provided."""
    payload = {
        "calculation_id": base_response_footer["meta"]["calculation_id"],
        "portfolio_number": "TEST_01",
        **base_response_footer,
    }
    with pytest.raises(ValidationError, match="Provide either 'results_by_period' or the legacy"):
        PerformanceResponse.model_validate(payload)