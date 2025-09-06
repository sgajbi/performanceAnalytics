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
)
from app.models.attribution_requests import AttributionRequest
from app.models.requests import DailyInputData


@pytest.fixture
def single_period_data():
    """Provides aligned data for a single period for attribution testing."""
    data = {'group': ['Equity', 'Bonds', 'Cash'], 'w_p': [0.60, 0.30, 0.10], 'r_p': [0.10, 0.04, 0.01], 'w_b': [0.50, 0.40, 0.10], 'r_b': [0.08, 0.03, 0.01]}
    df = pd.DataFrame(data).set_index('group')
    df['r_b_total'] = (df['w_b'] * df['r_b']).sum()
    return df


@pytest.fixture
def by_group_request_data():
    """Provides a sample AttributionRequest for by_group mode where weights sum to 1."""
    return {
        "portfolio_number": "ATTRIB_UNIT_TEST_01", "mode": "by_group", "groupBy": ["sector"], "model": "BF", "linking": "carino", "frequency": "monthly",
        "portfolio_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-15", "return": 0.02, "weight_bop": 0.5}, {"date": "2025-02-10", "return": 0.01, "weight_bop": 0.6}]},
            {"key": {"sector": "Other"}, "observations": [{"date": "2025-01-15", "return": 0.01, "weight_bop": 0.5}, {"date": "2025-02-10", "return": 0.005, "weight_bop": 0.4}]}
        ],
        "benchmark_groups_data": [
            {"key": {"sector": "Tech"}, "observations": [{"date": "2025-01-10", "return": 0.01, "weight_bop": 0.4}, {"date": "2025-02-12", "return": -0.01, "weight_bop": 0.45}]},
            {"key": {"sector": "Other"}, "observations": [{"date": "2025-01-10", "return": 0.005, "weight_bop": 0.6}, {"date": "2025-02-12", "return": 0.002, "weight_bop": 0.55}]}
        ],
    }


def test_align_and_prepare_data_by_group(by_group_request_data):
    """Tests the data preparation and alignment logic for a by_group request."""
    request = AttributionRequest.model_validate(by_group_request_data)
    aligned_df = _align_and_prepare_data(request, request.portfolio_groups_data)
    assert not aligned_df.empty
    assert aligned_df.index.names == ['date', 'group_0']


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
    response = run_attribution_calculations(request)
    assert abs(response.reconciliation.residual) < 1e-9


def test_run_attribution_calculations_geometric_linking(by_group_request_data):
    """
    Tests the main orchestrator with Menchero linking, verifying the components
    and the final, expected residual.
    """
    request = AttributionRequest.model_validate(by_group_request_data)
    response = run_attribution_calculations(request)
    assert response.reconciliation.total_active_return == pytest.approx(0.0195438)
    assert response.reconciliation.sum_of_effects == pytest.approx(0.0193728)
    expected_residual = 0.0195438 - 0.0193728
    assert response.reconciliation.residual == pytest.approx(expected_residual)


def test_prepare_data_from_instruments():
    """
    Tests the aggregation of instrument data into portfolio groups.
    """
    daily_data_p = [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 1000, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 1025}]
    daily_data_aapl = [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 600, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 624}] # 4% return
    daily_data_msft = [{"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 400, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "End Market Value": 401}] # 0.25% return
    
    request_data = {
        "portfolio_number": "TEST", "mode": "by_instrument", "groupBy": ["sector"], "linking": "none",
        "portfolio_data": {"report_start_date": "2025-01-01", "report_end_date": "2025-01-01", "metric_basis": "NET", "period_type": "YTD", "daily_data": daily_data_p},
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
    assert tech_group.key == {"sector": "Tech"}
    
    obs = tech_group.observations[0]
    # Total weight should be sum of instrument weights: (600/1000) + (400/1000) = 1.0
    assert obs['weight_bop'] == pytest.approx(1.0)
    # Group return is weighted average: (0.6 * 4% + 0.4 * 0.25%) = 2.4% + 0.1% = 2.5%
    assert obs['return'] == pytest.approx(0.025)