# tests/unit/engine/test_contribution.py
import pandas as pd
import pytest
from engine.contribution import (
    _calculate_carino_factors,
    _calculate_single_period_weights,
    calculate_position_contribution,
)
from engine.schema import PortfolioColumns
from engine.compute import run_calculations
from engine.config import EngineConfig
from common.enums import PeriodType


@pytest.fixture
def sample_contribution_inputs():
    # ... (no change to this fixture) ...
    pass

def test_calculate_single_period_weights(sample_contribution_inputs):
    # ... (no change to this test) ...
    pass

def test_calculate_carino_factors():
    # ... (no change to this test) ...
    pass


def test_calculate_position_contribution_orchestrator():
    """
    Characterization test for the main contribution orchestrator.
    This test now uses the real TWR engine to generate its inputs.
    """
    # Arrange: Start with raw data, not pre-calculated returns
    twr_config = EngineConfig(
        performance_start_date="2025-01-01",
        report_start_date="2025-01-01",
        report_end_date="2025-01-02",
        metric_basis="NET",
        period_type=PeriodType.ITD,
    )

    portfolio_df = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02"]),
        PortfolioColumns.BEGIN_MV: [1000.0, 1020.0],
        PortfolioColumns.BOD_CF: [0.0, 50.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0],
        PortfolioColumns.END_MV: [1020.0, 1080.0],
    })
    # Use the TWR engine to get high-precision results
    portfolio_results = run_calculations(portfolio_df, twr_config)

    position_data_map = {
        "Stock_A": pd.DataFrame({
            PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02"]),
            PortfolioColumns.BEGIN_MV: [600.0, 612.0],
            PortfolioColumns.BOD_CF: [0.0, 50.0],
            PortfolioColumns.EOD_CF: [0.0, 0.0],
            PortfolioColumns.MGMT_FEES: [0.0, 0.0],
            PortfolioColumns.END_MV: [612.0, 670.0],
        }),
        "Stock_B": pd.DataFrame({
            PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02"]),
            PortfolioColumns.BEGIN_MV: [400.0, 408.0],
            PortfolioColumns.BOD_CF: [0.0, 0.0],
            PortfolioColumns.EOD_CF: [0.0, 0.0],
            PortfolioColumns.MGMT_FEES: [0.0, 0.0],
            PortfolioColumns.END_MV: [408.0, 410.0],
        })
    }
    
    position_results_map = {
        pos_id: run_calculations(df, twr_config)
        for pos_id, df in position_data_map.items()
    }

    # Act
    result = calculate_position_contribution(portfolio_results, position_results_map)

    # Assert (values corrected to high precision)
    assert result["Stock_A"]["total_contribution"] == pytest.approx(0.019363573)
    assert result["Stock_B"]["total_contribution"] == pytest.approx(0.009796662)