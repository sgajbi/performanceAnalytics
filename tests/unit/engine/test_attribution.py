# tests/unit/engine/test_attribution.py
import pandas as pd
import pytest

from common.enums import AttributionModel
from engine.attribution import (
    _calculate_single_period_effects,
    _align_and_prepare_data,
    run_attribution_calculations,
)
from app.models.attribution_requests import AttributionRequest


@pytest.fixture
def single_period_data():
    """Provides aligned data for a single period for attribution testing."""
    data = {
        'group': ['Equity', 'Bonds', 'Cash'],
        'w_p': [0.60, 0.30, 0.10],
        'r_p': [0.10, 0.04, 0.01],
        'w_b': [0.50, 0.40, 0.10],
        'r_b': [0.08, 0.03, 0.01],
    }
    df = pd.DataFrame(data).set_index('group')
    df['r_b_total'] = (df['w_b'] * df['r_b']).sum()
    return df


@pytest.fixture
def by_group_request_data():
    """Provides a sample AttributionRequest for by_group mode."""
    return {
        "portfolio_number": "ATTRIB_UNIT_TEST_01",
        "mode": "by_group",
        "groupBy": ["sector"],
        "model": "BF",
        "linking": "none",
        "frequency": "monthly",
        "portfolio_groups_data": [
            {
                "key": {"sector": "Tech"},
                "observations": [
                    {"date": "2025-01-15", "return": 0.02, "weight_bop": 0.5},
                    {"date": "2025-01-31", "return": 0.03, "weight_bop": 0.5},
                    {"date": "2025-02-10", "return": 0.01, "weight_bop": 0.6},
                ],
            }
        ],
        "benchmark_groups_data": [
            {
                "key": {"sector": "Tech"},
                "observations": [
                    {"date": "2025-01-10", "return": 0.01, "weight_bop": 0.4},
                    {"date": "2025-02-12", "return": -0.01, "weight_bop": 0.45},
                ],
            }
        ],
    }


def test_align_and_prepare_data_by_group(by_group_request_data):
    """
    Tests the data preparation and alignment logic for a by_group request.
    """
    request = AttributionRequest.model_validate(by_group_request_data)
    aligned_df = _align_and_prepare_data(request)

    assert not aligned_df.empty
    assert aligned_df.index.names == ['date', 'group_0']

    jan_data = aligned_df.loc[pd.Timestamp('2025-01-31')]
    assert jan_data.loc[('Tech',), 'w_p'] == pytest.approx(0.5)
    assert jan_data.loc[('Tech',), 'w_b'] == pytest.approx(0.4)
    assert jan_data.loc[('Tech',), 'r_p'] == pytest.approx(0.0506)
    assert jan_data.loc[('Tech',), 'r_b'] == pytest.approx(0.01)

    feb_data = aligned_df.loc[pd.Timestamp('2025-02-28')]
    assert feb_data.loc[('Tech',), 'w_p'] == pytest.approx(0.6)
    assert feb_data.loc[('Tech',), 'r_p'] == pytest.approx(0.01)
    assert feb_data.loc[('Tech',), 'r_b'] == pytest.approx(-0.01)

    assert jan_data['r_b_total'].iloc[0] == pytest.approx(0.004)
    assert feb_data['r_b_total'].iloc[0] == pytest.approx(-0.0045)


def test_calculate_single_period_brinson_fachler(single_period_data):
    """
    Tests the Brinson-Fachler model calculation for a single period.
    """
    result_df = _calculate_single_period_effects(single_period_data, AttributionModel.BRINSON_FACHLER)
    total_effects = result_df[['allocation', 'selection', 'interaction']].sum().sum()
    assert total_effects == pytest.approx(0.020)


def test_calculate_single_period_brinson_hood_beebower(single_period_data):
    """
    Tests the Brinson-Hood-Beebower model calculation for a single period.
    """
    result_df = _calculate_single_period_effects(single_period_data, AttributionModel.BRINSON_HOOD_BEEBOWER)
    total_effects = result_df[['allocation', 'selection', 'interaction']].sum().sum()
    assert total_effects == pytest.approx(0.021)


def test_run_attribution_calculations_by_group_single_level(by_group_request_data):
    """
    Tests the main orchestrator for a single-level by_group request.
    """
    request = AttributionRequest.model_validate(by_group_request_data)
    response = run_attribution_calculations(request)

    assert response.portfolio_number == "ATTRIB_UNIT_TEST_01"
    assert len(response.levels) == 1
    
    level1 = response.levels[0]
    assert level1.dimension == "sector"
    assert len(level1.groups) == 1
    tech_group = level1.groups[0]

    # Expected values from manual calculation for BF model
    total_alloc = 0.0006 - 0.000825
    total_sel = 0.01624 + 0.009
    total_inter = 0.00406 + 0.003
    
    assert tech_group.allocation == pytest.approx(total_alloc)
    assert tech_group.selection == pytest.approx(total_sel)
    assert tech_group.interaction == pytest.approx(total_inter)
    assert level1.totals.total_effect == pytest.approx(total_alloc + total_sel + total_inter)

    # Expected Active Return = 0.0318
    assert response.reconciliation.total_active_return == pytest.approx(0.0318)
    assert abs(response.reconciliation.residual) < 1e-9