# tests/unit/engine/test_contribution.py
import pandas as pd
import pytest
from app.models.contribution_requests import Smoothing
from engine.contribution import (
    _calculate_carino_factors,
    _calculate_single_period_weights,
    calculate_position_contribution,
)
from engine.schema import PortfolioColumns
from engine.compute import run_calculations
from engine.config import EngineConfig, FeatureFlags
from common.enums import PeriodType


@pytest.fixture
def sample_contribution_inputs():
    """Provides sample raw portfolio and position data for a single day."""
    portfolio_df = pd.DataFrame({
        PortfolioColumns.BEGIN_MV: [1000.0],
        PortfolioColumns.BOD_CF: [100.0],
    })
    positions_df_map = {
        "Stock_A": pd.DataFrame({PortfolioColumns.BEGIN_MV: [600.0], PortfolioColumns.BOD_CF: [60.0]}),
        "Stock_B": pd.DataFrame({PortfolioColumns.BEGIN_MV: [400.0], PortfolioColumns.BOD_CF: [40.0]}),
    }
    return portfolio_df, positions_df_map

@pytest.fixture
def portfolio_results_fixture() -> pd.DataFrame:
    """Provides a fixture for a processed portfolio DataFrame."""
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
    portfolio_results, _ = run_calculations(portfolio_df, twr_config)
    return portfolio_results


@pytest.fixture
def position_results_map_fixture() -> dict:
    """Provides a fixture for a map of processed position DataFrames."""
    twr_config = EngineConfig(
        performance_start_date="2025-01-01",
        report_start_date="2025-01-01",
        report_end_date="2025-01-02",
        metric_basis="NET",
        period_type=PeriodType.ITD,
    )
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
    return {
        pos_id: run_calculations(df, twr_config)[0]
        for pos_id, df in position_data_map.items()
    }

@pytest.fixture
def robust_nip_day_scenario():
    """
    A robust scenario with a NIP day where the buggy and correct logic
    for average weight produce different results.
    """
    config = EngineConfig(
        performance_start_date="2025-01-01",
        report_start_date="2025-01-01",
        report_end_date="2025-01-03",
        metric_basis="NET",
        period_type=PeriodType.ITD,
        feature_flags=FeatureFlags(use_nip_v2_rule=True)
    )
    portfolio_data = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        PortfolioColumns.BEGIN_MV: [1000.0, 1000.0, 0.0],
        PortfolioColumns.BOD_CF: [0.0, 1000.0, 0.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [1000.0, 2000.0, 0.0],
    })
    pos_a_data = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        PortfolioColumns.BEGIN_MV: [500.0, 500.0, 0.0],
        PortfolioColumns.BOD_CF: [0.0, 750.0, 0.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [500.0, 1250.0, 0.0],
    })

    portfolio_results, _ = run_calculations(portfolio_data, config)
    pos_a_results, _ = run_calculations(pos_a_data, config)
    position_results_map = {"Stock_A": pos_a_results}

    return portfolio_results, position_results_map


def test_calculate_single_period_weights(sample_contribution_inputs):
    """Tests the calculation of position weights for a single period."""
    portfolio_df, positions_df_map = sample_contribution_inputs
    weights = _calculate_single_period_weights(portfolio_df.iloc[0], positions_df_map, day_index=0)
    assert weights["Stock_A"] == pytest.approx(0.6)
    assert weights["Stock_B"] == pytest.approx(0.4)


def test_single_period_weights_sum_to_one(sample_contribution_inputs):
    """Tests that the sum of all position weights for a period equals 1."""
    portfolio_df, positions_df_map = sample_contribution_inputs
    weights = _calculate_single_period_weights(
        portfolio_df.iloc[0], positions_df_map, day_index=0
    )
    assert sum(weights.values()) == pytest.approx(1.0)


def test_calculate_carino_factors():
    """Tests the Carino smoothing factor calculation."""
    k_daily = _calculate_carino_factors(pd.Series([0.10]))
    assert k_daily.iloc[0] == pytest.approx(0.95310179)
    k_zero = _calculate_carino_factors(pd.Series([0.0]))
    assert k_zero.iloc[0] == 1.0


def test_calculate_position_contribution_orchestrator(portfolio_results_fixture, position_results_map_fixture):
    """Characterization test for the main contribution orchestrator with Carino smoothing."""
    result = calculate_position_contribution(
        portfolio_results_fixture, position_results_map_fixture, Smoothing(method="CARINO")
    )
    port_total_return = ((1 + portfolio_results_fixture[PortfolioColumns.DAILY_ROR] / 100).prod() - 1) * 100

    total_contribution_sum = sum(data["total_contribution"] for data in result.values())
    assert total_contribution_sum == pytest.approx(port_total_return)

    total_average_weight = sum(data["average_weight"] for data in result.values())
    assert total_average_weight == pytest.approx(100.0)

    assert result["Stock_A"]["total_contribution"] == pytest.approx(1.959076, abs=1e-6)
    assert result["Stock_B"]["total_contribution"] == pytest.approx(0.994217, abs=1e-6)


def test_calculate_position_contribution_no_smoothing(portfolio_results_fixture, position_results_map_fixture):
    """Tests that with smoothing disabled, the contribution is a simple arithmetic sum."""
    result = calculate_position_contribution(
        portfolio_results_fixture, position_results_map_fixture, Smoothing(method="NONE")
    )
    port_total_return = ((1 + portfolio_results_fixture[PortfolioColumns.DAILY_ROR] / 100).prod() - 1) * 100
    total_contribution_sum = sum(data["total_contribution"] for data in result.values())

    assert total_contribution_sum != pytest.approx(port_total_return)
    assert result["Stock_A"]["total_contribution"] == pytest.approx(1.94766, abs=1e-5)
    assert result["Stock_B"]["total_contribution"] == pytest.approx(0.99411, abs=1e-5)


def test_calculate_single_period_weights_zero_capital(sample_contribution_inputs):
    """Tests weight calculation when the portfolio has zero average capital."""
    portfolio_df, positions_df_map = sample_contribution_inputs
    portfolio_df_copy = portfolio_df.copy()
    portfolio_df_copy.iloc[0, portfolio_df_copy.columns.get_loc(PortfolioColumns.BEGIN_MV)] = 0.0
    portfolio_df_copy.iloc[0, portfolio_df_copy.columns.get_loc(PortfolioColumns.BOD_CF)] = 0.0
    weights = _calculate_single_period_weights(portfolio_df_copy.iloc[0], positions_df_map, day_index=0)
    assert weights["Stock_A"] == 0.0
    assert weights["Stock_B"] == 0.0


def test_contribution_adjusts_average_weight_for_nip_day(robust_nip_day_scenario):
    """
    Tests that average weight is correctly adjusted for NIP days per RFC-004.
    """
    portfolio_results, position_results_map = robust_nip_day_scenario
    result = calculate_position_contribution(portfolio_results, position_results_map, Smoothing(method="CARINO"))
    assert result["Stock_A"]["average_weight"] == pytest.approx(56.25)