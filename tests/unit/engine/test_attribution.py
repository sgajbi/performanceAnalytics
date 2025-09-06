# tests/unit/engine/test_attribution.py
import pandas as pd
import pytest
import numpy as np

from common.enums import AttributionModel, LinkingMethod
from engine.attribution import (
    _calculate_single_period_effects,
    _align_and_prepare_data,
    run_attribution_calculations,
    _link_effects_carino,
)
from app.models.attribution_requests import AttributionRequest


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
        "portfolio_number": "ATTRIB_UNIT_TEST_01", "mode": "by_group", "groupBy": ["sector"], "model": "BF", "linking": "none", "frequency": "monthly",
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
    aligned_df = _align_and_prepare_data(request)
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


def test_run_attribution_calculations_by_group_no_linking(by_group_request_data):
    """Tests the main orchestrator with simple arithmetic linking."""
    request = AttributionRequest.model_validate(by_group_request_data)
    response = run_attribution_calculations(request)
    assert abs(response.reconciliation.residual) < 1e-9


def test_link_effects_carino():
    """Tests the Carino smoothing logic for linking multi-period effects."""
    dates = pd.to_datetime(['2025-01-31', '2025-02-28'])
    effects_df = pd.DataFrame({
        'allocation': [0.005, -0.002], 'selection': [0.010, 0.005], 'interaction': [0.001, -0.001]
    }, index=pd.MultiIndex.from_product([dates, ['Equity']], names=['date', 'group']))
    
    per_period_returns = pd.DataFrame({
        'p_return': [0.026, 0.002], 'b_return': [0.010, 0.000]
    }, index=dates)

    linked_effects = _link_effects_carino(effects_df, per_period_returns)
    
    # Total Active Return = (1.026*1.002)-1 - (1.01*1.0)-1 = 1.028052 - 1.01 = 0.018052
    total_linked_effect = linked_effects.sum().sum()
    assert total_linked_effect == pytest.approx(0.018052)


def test_run_attribution_calculations_with_carino_linking(by_group_request_data):
    """Tests the main orchestrator with Carino linking enabled."""
    by_group_request_data['linking'] = 'carino'
    request = AttributionRequest.model_validate(by_group_request_data)
    response = run_attribution_calculations(request)

    assert response.linking == LinkingMethod.CARINO
    assert abs(response.reconciliation.residual) < 1e-9
    assert response.reconciliation.sum_of_effects == pytest.approx(response.reconciliation.total_active_return)