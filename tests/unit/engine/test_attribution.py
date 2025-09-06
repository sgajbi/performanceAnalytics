# tests/unit/engine/test_attribution.py
import pandas as pd
import pytest
from engine.attribution import _calculate_single_period_effects
from common.enums import AttributionModel


@pytest.fixture
def single_period_data():
    """Provides aligned data for a single period for attribution testing."""
    data = {
        'group': ['Equity', 'Bonds', 'Cash'],
        'w_p': [0.60, 0.30, 0.10], # Portfolio weights
        'r_p': [0.10, 0.04, 0.01], # Portfolio returns
        'w_b': [0.50, 0.40, 0.10], # Benchmark weights
        'r_b': [0.08, 0.03, 0.01], # Benchmark returns
    }
    df = pd.DataFrame(data).set_index('group')
    # Calculate total benchmark return: (0.5*0.08 + 0.4*0.03 + 0.1*0.01) = 0.053
    df['r_b_total'] = 0.053
    return df


def test_calculate_single_period_brinson_fachler(single_period_data):
    """
    Tests the Brinson-Fachler model calculation for a single period.
    """
    # Act
    result_df = _calculate_single_period_effects(single_period_data, AttributionModel.BRINSON_FACHLER)

    # Assert
    # Equity Allocation: (0.6 - 0.5) * (0.08 - 0.053) = 0.0027
    assert result_df.loc['Equity', 'allocation'] == pytest.approx(0.0027)
    # Equity Selection: 0.5 * (0.10 - 0.08) = 0.0100
    assert result_df.loc['Equity', 'selection'] == pytest.approx(0.0100)
    # Equity Interaction: (0.6 - 0.5) * (0.10 - 0.08) = 0.0020
    assert result_df.loc['Equity', 'interaction'] == pytest.approx(0.0020)

    # Total Active Return (0.073 - 0.053 = 0.020) should equal sum of all effects
    total_effects = result_df['allocation'].sum() + result_df['selection'].sum() + result_df['interaction'].sum()
    assert total_effects == pytest.approx(0.020)


def test_calculate_single_period_brinson_hood_beebower(single_period_data):
    """
    Tests the Brinson-Hood-Beebower model calculation for a single period.
    """
    # Act
    result_df = _calculate_single_period_effects(single_period_data, AttributionModel.BRINSON_HOOD_BEEBOWER)

    # Assert
    # Equity Allocation: (0.6 - 0.5) * 0.08 = 0.0080
    assert result_df.loc['Equity', 'allocation'] == pytest.approx(0.0080)
    # Equity Selection: 0.6 * (0.10 - 0.08) = 0.0120
    assert result_df.loc['Equity', 'selection'] == pytest.approx(0.0120)

    # Total Active Return (0.020) should equal sum of all effects
    total_effects = result_df['allocation'].sum() + result_df['selection'].sum() + result_df['interaction'].sum()
    assert total_effects == pytest.approx(0.020)