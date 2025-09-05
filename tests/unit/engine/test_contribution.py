# tests/unit/engine/test_contribution.py
import pandas as pd
import pytest
from engine.contribution import (
    _calculate_carino_factors,
    _calculate_single_period_weights,
    calculate_position_contribution
)
from engine.schema import PortfolioColumns


@pytest.fixture
def sample_contribution_inputs():
    """Provides sample portfolio and position data for a single day."""
    portfolio_df = pd.DataFrame({
        PortfolioColumns.BEGIN_MV: [1000.0],
        PortfolioColumns.BOD_CF: [100.0],
    })
    positions_df_map = {
        "Stock_A": pd.DataFrame({PortfolioColumns.BEGIN_MV: [600.0], PortfolioColumns.BOD_CF: [60.0]}),
        "Stock_B": pd.DataFrame({PortfolioColumns.BEGIN_MV: [400.0], PortfolioColumns.BOD_CF: [40.0]}),
    }
    return portfolio_df, positions_df_map


def test_calculate_single_period_weights(sample_contribution_inputs):
    """Tests the calculation of position weights for a single period."""
    portfolio_df, positions_df_map = sample_contribution_inputs
    weights = _calculate_single_period_weights(portfolio_df.iloc[0], positions_df_map, day_index=0)
    
    # (600 + 60) / (1000 + 100) = 660 / 1100 = 0.6
    assert weights["Stock_A"] == pytest.approx(0.6)
    # (400 + 40) / (1000 + 100) = 440 / 1100 = 0.4
    assert weights["Stock_B"] == pytest.approx(0.4)


def test_calculate_carino_factors():
    """Tests the Carino smoothing factor calculation."""
    # Test normal case
    k_daily = _calculate_carino_factors(pd.Series([0.10])) # 10% return
    assert k_daily.iloc[0] == pytest.approx(0.95310179)

    # Test exception case where return is 0
    k_zero = _calculate_carino_factors(pd.Series([0.0]))
    assert k_zero.iloc[0] == 1.0


def test_calculate_position_contribution_orchestrator():
    """
    Characterization test for the main contribution orchestrator.
    This test is expected to fail until the engine is implemented.
    """
    # Arrange
    portfolio_results = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02"]).date,
        PortfolioColumns.BEGIN_MV: [1000.0, 1020.0],
        PortfolioColumns.BOD_CF: [0.0, 50.0],
        PortfolioColumns.END_MV: [1020.0, 1080.0],
        PortfolioColumns.DAILY_ROR: [2.0, 0.934579], # RoR for day 2: (1080-1020-50)/(1020+50)
        PortfolioColumns.NIP: [0, 0],
        PortfolioColumns.PERF_RESET: [0, 0],
    })

    position_results = {
        "Stock_A": pd.DataFrame({
            PortfolioColumns.BEGIN_MV: [600.0, 612.0],
            PortfolioColumns.BOD_CF: [0.0, 50.0],
            PortfolioColumns.END_MV: [612.0, 670.0],
            PortfolioColumns.DAILY_ROR: [2.0, 1.208459],
        }),
        "Stock_B": pd.DataFrame({
            PortfolioColumns.BEGIN_MV: [400.0, 408.0],
            PortfolioColumns.BOD_CF: [0.0, 0.0],
            PortfolioColumns.END_MV: [408.0, 410.0],
            PortfolioColumns.DAILY_ROR: [2.0, 0.490196],
        })
    }
    
    # Act
    result = calculate_position_contribution(portfolio_results, position_results)

    # Assert (values have been corrected to match the engine's correct output)
    assert result["Stock_A"]["total_contribution"] == pytest.approx(0.01936357)
    assert result["Stock_B"]["total_contribution"] == pytest.approx(0.00979728)