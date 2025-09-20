# tests/unit/engine/test_attribution.py
import pandas as pd
import pytest
import numpy as np

from common.enums import AttributionModel, LinkingMethod
from engine.attribution import (
    _calculate_single_period_effects,
    _align_and_prepare_data,
    run_attribution_calculations,
    _prepare_data_from_instruments,
    _link_effects_top_down,
)
from app.models.attribution_requests import AttributionRequest


@pytest.fixture
def single_period_data():
    """Provides aligned data for a single period for attribution testing."""
    data = {'group': ['Equity', 'Bonds', 'Cash'], 'w_p': [0.60, 0.30, 0.10], 'r_base_p': [0.10, 0.04, 0.01], 'w_b': [0.50, 0.40, 0.10], 'r_base_b': [0.08, 0.03, 0.01]}
    df = pd.DataFrame(data).set_index('group')
    df['r_b_total'] = (df['w_b'] * df['r_base_b']).sum()
    return df


@pytest.fixture
def by_group_request_data():
    """Provides a sample AttributionRequest for by_group mode where weights sum to 1."""
    return {
        "portfolio_number": "ATTRIB_UNIT_TEST_01", "mode": "by_group", "group_by": ["sector"], "model": "BF", "linking": "carino", "frequency": "monthly",
        "report_start_date": "2025-01-01", "report_end_date": "2025-02-28", "period_type": "ITD",
        "portfolio_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-15", "return": 0.02, "weight_bop": 0.5}, {"date": "2025-02-10", "return": 0.01, "weight_bop": 0.6}]},
            {"key": {"sector": "Other"}, "observations": [{"date": "2025-01-15", "return": 0.01, "weight_bop": 0.5}, {"date": "2025-02-10", "return": 0.005, "weight_bop": 0.4}]}
        ],
        "benchmark_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-10", "return_base": 0.01, "weight_bop": 0.4}, {"date": "2025-02-12", "return_base": -0.01, "weight_bop": 0.45}]},
            {"key": {"sector": "Other"}, "observations": [{"date": "2025-01-10", "return_base": 0.005, "weight_bop": 0.6}, {"date": "2025-02-12", "return_base": 0.002, "weight_bop": 0.55}]}
        ],
    }


def test_align_and_prepare_data_by_group(by_group_request_data):
    """Tests the data preparation and alignment logic for a by_group request."""
    request = AttributionRequest.model_validate(by_group_request_data)
    aligned_df = _align_and_prepare_data(request, request.portfolio_groups_data)
    assert not aligned_df.empty
    assert aligned_df.index.names == ['date', 'sector']


def test_calculate_single_period_brinson_fachler(single_period_data):
    """Tests the Brinson-Fachler model calculation for a single period."""
    result_df = _calculate_single_period_effects(single_period_data, AttributionModel.BRINSON_FACHLER)
    total_effects = result_df[['allocation', 'selection', 'interaction']].sum().sum()
    assert total_effects == pytest.approx(0.020)


def test_calculate_single_period_brinson_hood_beebower(single_period_data):
    """Tests the Brinson-Hood-Beebower model calculation for a single period."""
    result_df = _calculate_single_period_effects(single_period_data, AttributionModel.BRINSON_HOOD_BEEBOWER)
    total_effects = result_df[['allocation', 'selection', 'interaction']].sum().sum()
    assert total_effects == pytest.approx(0.021)


def test_run_attribution_calculations_arithmetic_linking(by_group_request_data):
    """Tests the main orchestrator with simple arithmetic linking."""
    by_group_request_data['linking'] = 'none'
    request = AttributionRequest.model_validate(by_group_request_data)
    response, _ = run_attribution_calculations(request)
    assert abs(response.reconciliation.residual) < 1e-9


def test_run_attribution_calculations_geometric_linking(by_group_request_data):
    """Tests the main orchestrator with top-down geometric linking enabled."""
    request = AttributionRequest.model_validate(by_group_request_data)
    response, _ = run_attribution_calculations(request)
    assert abs(response.reconciliation.residual) < 1e-9
    assert response.reconciliation.sum_of_effects == pytest.approx(response.reconciliation.total_active_return)


def test_prepare_data_from_instruments():
    """Tests the aggregation of instrument data into portfolio groups."""
    daily_data_p = [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 1000, "end_mv": 1025}]
    daily_data_aapl = [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 600, "end_mv": 624}]
    daily_data_msft = [{"day": 1, "perf_date": "2025-01-01", "begin_mv": 400, "end_mv": 401}]

    request_data = {
        "portfolio_number": "TEST", "mode": "by_instrument", "group_by": ["sector"], "linking": "none", "frequency": "daily",
        "report_start_date": "2025-01-01", "report_end_date": "2025-01-01", "period_type": "ITD",
        "portfolio_data": {"metric_basis": "NET", "daily_data": daily_data_p},
        "instruments_data": [
            {"instrument_id": "AAPL", "meta": {"sector": "Tech"}, "daily_data": daily_data_aapl},
            {"instrument_id": "MSFT", "meta": {"sector": "Tech"}, "daily_data": daily_data_msft}
        ],
        "benchmark_groups_data": []
    }
    request = AttributionRequest.model_validate(request_data)

    result_groups = _prepare_data_from_instruments(request)

    assert len(result_groups) == 1
    tech_group = result_groups[0]
    obs = tech_group.observations[0]

    assert obs['weight_bop'] == pytest.approx(1.0)
    assert obs['return_base'] == pytest.approx(0.025)


def test_prepare_data_from_instruments_missing_portfolio_data():
    """Tests that a ValueError is raised if portfolio_data is missing in by_instrument mode."""
    request_data = {
        "portfolio_number": "TEST", "mode": "by_instrument", "group_by": ["sector"], "instruments_data": [], "benchmark_groups_data": [], "linking": "none",
        "report_start_date": "2025-01-01", "report_end_date": "2025-01-01", "period_type": "ITD",
    }
    request = AttributionRequest.model_validate(request_data)
    with pytest.raises(ValueError, match="'portfolio_data' and 'instruments_data' are required"):
        _prepare_data_from_instruments(request)