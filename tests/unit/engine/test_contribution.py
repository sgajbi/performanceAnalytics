# tests/unit/engine/test_contribution.py
from datetime import date
import pandas as pd
import pytest
from app.models.contribution_requests import ContributionRequest, Emit, Smoothing
from common.enums import WeightingScheme
from engine.contribution import (
    _calculate_carino_factors,
    _calculate_single_period_weights,
    _calculate_daily_instrument_contributions,
    _prepare_hierarchical_data,
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
        PortfolioColumns.BEGIN_MV.value: [1000.0],
        PortfolioColumns.BOD_CF.value: [100.0],
    })
    positions_df_map = {
        "Stock_A": pd.DataFrame({PortfolioColumns.BEGIN_MV.value: [600.0], PortfolioColumns.BOD_CF.value: [60.0]}),
        "Stock_B": pd.DataFrame({PortfolioColumns.BEGIN_MV.value: [400.0], PortfolioColumns.BOD_CF.value: [40.0]}),
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
        PortfolioColumns.PERF_DATE.value: pd.to_datetime(["2025-01-01", "2025-01-02"]),
        PortfolioColumns.BEGIN_MV.value: [1000.0, 1020.0],
        PortfolioColumns.BOD_CF.value: [0.0, 50.0],
        PortfolioColumns.EOD_CF.value: [0.0, 0.0],
        PortfolioColumns.MGMT_FEES.value: [0.0, 0.0],
        PortfolioColumns.END_MV.value: [1020.0, 1080.0],
        PortfolioColumns.NIP.value: [0, 0],
        PortfolioColumns.PERF_RESET.value: [0, 0],
    })
    portfolio_results, _ = run_calculations(portfolio_df, twr_config)
    portfolio_results[PortfolioColumns.PERF_DATE.value] = pd.to_datetime(portfolio_results[PortfolioColumns.PERF_DATE.value])
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
            PortfolioColumns.PERF_DATE.value: pd.to_datetime(["2025-01-01", "2025-01-02"]),
            PortfolioColumns.BEGIN_MV.value: [600.0, 612.0],
            PortfolioColumns.BOD_CF.value: [0.0, 50.0],
            PortfolioColumns.EOD_CF.value: [0.0, 0.0],
            PortfolioColumns.MGMT_FEES.value: [0.0, 0.0],
            PortfolioColumns.END_MV.value: [612.0, 670.0],
        }),
        "Stock_B": pd.DataFrame({
            PortfolioColumns.PERF_DATE.value: pd.to_datetime(["2025-01-01", "2025-01-02"]),
            PortfolioColumns.BEGIN_MV.value: [400.0, 408.0],
            PortfolioColumns.BOD_CF.value: [0.0, 0.0],
            PortfolioColumns.EOD_CF.value: [0.0, 0.0],
            PortfolioColumns.MGMT_FEES.value: [0.0, 0.0],
            PortfolioColumns.END_MV.value: [408.0, 410.0],
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
        PortfolioColumns.PERF_DATE.value: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        PortfolioColumns.BEGIN_MV.value: [1000.0, 1000.0, 0.0],
        PortfolioColumns.BOD_CF.value: [0.0, 1000.0, 0.0],
        PortfolioColumns.EOD_CF.value: [0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES.value: [0.0, 0.0, 0.0],
        PortfolioColumns.END_MV.value: [1000.0, 2000.0, 0.0],
    })
    pos_a_data = pd.DataFrame({
        PortfolioColumns.PERF_DATE.value: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        PortfolioColumns.BEGIN_MV.value: [500.0, 500.0, 0.0],
        PortfolioColumns.BOD_CF.value: [0.0, 750.0, 0.0],
        PortfolioColumns.EOD_CF.value: [0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES.value: [0.0, 0.0, 0.0],
        PortfolioColumns.END_MV.value: [500.0, 1250.0, 0.0],
    })

    portfolio_results, _ = run_calculations(portfolio_data, config)
    pos_a_results, _ = run_calculations(pos_a_data, config)
    position_results_map = {"Stock_A": pos_a_results}

    return portfolio_results, position_results_map


@pytest.fixture
def hierarchical_request_fixture(happy_path_payload):
    """Provides a valid hierarchical request object for testing."""
    payload = happy_path_payload.copy()
    payload["hierarchy"] = ["sector", "region"]
    payload["positions_data"].append({
        "position_id": "Stock_B",
        "meta": {"sector": "Healthcare", "region": "US"},
        "daily_data": [
            {"Perf. Date": "2025-01-01", "Begin Market Value": 400, "End Market Value": 408, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 1},
            {"Perf. Date": "2025-01-02", "Begin Market Value": 408, "End Market Value": 410, "BOD Cashflow": 0, "Eod Cashflow": 0, "Mgmt fees": 0, "Day": 2},
        ]
    })
    payload["positions_data"][0]["meta"]["region"] = "US"
    return ContributionRequest.model_validate(payload)


@pytest.fixture
def prepared_data_fixture(hierarchical_request_fixture):
    """Provides the output of the data preparation step for use in other tests."""
    return _prepare_hierarchical_data(hierarchical_request_fixture)


def test_prepare_hierarchical_data(hierarchical_request_fixture):
    """
    Tests that the data preparation function correctly runs TWR and combines
    position results with metadata into a single DataFrame.
    """
    instruments_df, portfolio_df = _prepare_hierarchical_data(hierarchical_request_fixture)

    assert not instruments_df.empty
    assert not portfolio_df.empty

    # 2 positions * 2 days = 4 rows
    assert len(instruments_df) == 4
    assert len(portfolio_df) == 2

    # Check for essential engine and metadata columns
    expected_cols = {
        PortfolioColumns.DAILY_ROR.value,
        "position_id",
        "sector",
        "region",
    }
    assert expected_cols.issubset(instruments_df.columns)

    # Check that metadata was merged correctly
    assert instruments_df[instruments_df["position_id"] == "Stock_A"]["sector"].iloc[0] == "Technology"
    assert instruments_df[instruments_df["position_id"] == "Stock_B"]["sector"].iloc[0] == "Healthcare"
    assert instruments_df[instruments_df["position_id"] == "Stock_A"]["region"].iloc[0] == "US"


def test_calculate_daily_contributions_bod_weighting(prepared_data_fixture):
    """
    Tests that the daily contributions are calculated correctly using BOD weighting.
    """
    instruments_df, portfolio_df = prepared_data_fixture
    result_df = _calculate_daily_instrument_contributions(
        instruments_df, portfolio_df, WeightingScheme.BOD, Smoothing(method="NONE")
    )

    # Day 1: Stock A Weight = 600 / 1000 = 0.6. RoR = 2.0%. Raw Contrib = 0.6 * 0.02 = 0.012
    stock_a_day_1 = result_df[result_df["position_id"] == "Stock_A"].iloc[0]
    assert stock_a_day_1["daily_weight"] == pytest.approx(0.6)
    assert stock_a_day_1["raw_contribution"] == pytest.approx(0.012)

    # Day 2: Stock B Weight = 408 / (1020 + 50) = 0.381308. RoR = 0.490196%. Raw Contrib = 0.381308 * 0.00490196
    stock_b_day_2 = result_df[result_df["position_id"] == "Stock_B"].iloc[1]
    assert stock_b_day_2["daily_weight"] == pytest.approx(408 / 1070)
    assert stock_b_day_2["raw_contribution"] == pytest.approx(0.001869, abs=1e-6)


def test_calculate_daily_contributions_smoothing(prepared_data_fixture):
    """
    Tests that Carino smoothing correctly adjusts the raw contribution.
    """
    instruments_df, portfolio_df = prepared_data_fixture
    result_df = _calculate_daily_instrument_contributions(
        instruments_df, portfolio_df, WeightingScheme.BOD, Smoothing(method="CARINO")
    )

    # Raw contribution for Stock A on Day 1 was 0.012
    stock_a_day_1 = result_df[result_df["position_id"] == "Stock_A"].iloc[0]
    assert stock_a_day_1["raw_contribution"] == pytest.approx(0.012)
    # Smoothed contribution should be different due to the adjustment factor
    assert stock_a_day_1["smoothed_contribution"] != pytest.approx(0.012)
    assert stock_a_day_1["smoothed_contribution"] == pytest.approx(0.01194, abs=1e-5)


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
        portfolio_results_fixture, position_results_map_fixture, Smoothing(method="CARINO"), Emit()
    )
    port_total_return = ((1 + portfolio_results_fixture[PortfolioColumns.DAILY_ROR.value] / 100).prod() - 1) * 100

    total_contribution_sum = sum(data["total_contribution"] for data in result.values() if isinstance(data, dict))
    assert total_contribution_sum == pytest.approx(port_total_return)

    total_average_weight = sum(data["average_weight"] for data in result.values() if isinstance(data, dict))
    assert total_average_weight == pytest.approx(100.0)

    assert result["Stock_A"]["total_contribution"] == pytest.approx(1.959076, abs=1e-6)
    assert result["Stock_B"]["total_contribution"] == pytest.approx(0.994217, abs=1e-6)


def test_calculate_position_contribution_no_smoothing(portfolio_results_fixture, position_results_map_fixture):
    """Tests that with smoothing disabled, the contribution is a simple arithmetic sum."""
    result = calculate_position_contribution(
        portfolio_results_fixture, position_results_map_fixture, Smoothing(method="NONE"), Emit()
    )
    port_total_return = ((1 + portfolio_results_fixture[PortfolioColumns.DAILY_ROR.value] / 100).prod() - 1) * 100
    total_contribution_sum = sum(data["total_contribution"] for data in result.values() if isinstance(data, dict))

    assert total_contribution_sum != pytest.approx(port_total_return)
    assert result["Stock_A"]["total_contribution"] == pytest.approx(1.947688, abs=1e-6)
    assert result["Stock_B"]["total_contribution"] == pytest.approx(0.986917, abs=1e-6)


def test_calculate_single_period_weights_zero_capital(sample_contribution_inputs):
    """Tests weight calculation when the portfolio has zero average capital."""
    portfolio_df, positions_df_map = sample_contribution_inputs
    portfolio_df_copy = portfolio_df.copy()
    portfolio_df_copy.iloc[0, portfolio_df_copy.columns.get_loc(PortfolioColumns.BEGIN_MV.value)] = 0.0
    portfolio_df_copy.iloc[0, portfolio_df_copy.columns.get_loc(PortfolioColumns.BOD_CF.value)] = 0.0
    weights = _calculate_single_period_weights(portfolio_df_copy.iloc[0], positions_df_map, day_index=0)
    assert weights["Stock_A"] == 0.0
    assert weights["Stock_B"] == 0.0


def test_contribution_adjusts_average_weight_for_nip_day(robust_nip_day_scenario):
    """
    Tests that average weight is correctly adjusted for NIP days per RFC-004.
    """
    portfolio_results, position_results_map = robust_nip_day_scenario
    result = calculate_position_contribution(
        portfolio_results, position_results_map, Smoothing(method="CARINO"), Emit()
    )
    assert result["Stock_A"]["average_weight"] == pytest.approx(56.25)