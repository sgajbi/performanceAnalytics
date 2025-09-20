# tests/unit/engine/test_contribution.py
from datetime import date
import pandas as pd
import pytest
from app.models.contribution_requests import ContributionRequest, Emit, Smoothing
from common.enums import WeightingScheme
from engine.contribution import (
    _calculate_carino_factors,
    _calculate_daily_instrument_contributions,
    _prepare_hierarchical_data,
)
from engine.schema import PortfolioColumns
from engine.compute import run_calculations
from engine.config import EngineConfig, FeatureFlags
from common.enums import PeriodType


@pytest.fixture
def hierarchical_request_fixture(happy_path_payload):
    """Provides a valid hierarchical request object for testing."""
    payload = happy_path_payload.copy()
    payload["hierarchy"] = ["sector", "region"]
    payload["positions_data"].append({
        "position_id": "Stock_B",
        "meta": {"sector": "Healthcare", "region": "US"},
        "daily_data": [
            {"day": 1, "perf_date": "2025-01-01", "begin_mv": 400, "end_mv": 408},
            {"day": 2, "perf_date": "2025-01-02", "begin_mv": 408, "end_mv": 410},
        ]
    })
    payload["positions_data"][0]["meta"]["region"] = "US"
    payload["period_type"] = "ITD"
    return ContributionRequest.model_validate(payload)


@pytest.fixture
def prepared_data_fixture(hierarchical_request_fixture):
    """Provides the output of the data preparation step for use in other tests."""
    return _prepare_hierarchical_data(hierarchical_request_fixture)


def test_prepare_hierarchical_data(hierarchical_request_fixture):
    """Tests that TWR runs and combines position results with metadata."""
    instruments_df, portfolio_df = _prepare_hierarchical_data(hierarchical_request_fixture)

    assert not instruments_df.empty
    assert not portfolio_df.empty
    assert len(instruments_df) == 4
    assert len(portfolio_df) == 2
    expected_cols = {"daily_ror", "position_id", "sector", "region"}
    assert expected_cols.issubset(instruments_df.columns)
    assert instruments_df[instruments_df["position_id"] == "Stock_A"]["sector"].iloc[0] == "Technology"
    assert instruments_df[instruments_df["position_id"] == "Stock_B"]["sector"].iloc[0] == "Healthcare"


def test_calculate_daily_contributions_bod_weighting(prepared_data_fixture):
    """Tests that daily contributions are calculated correctly using BOD weighting."""
    instruments_df, portfolio_df = prepared_data_fixture
    result_df = _calculate_daily_instrument_contributions(
        instruments_df, portfolio_df, WeightingScheme.BOD, Smoothing(method="NONE")
    )
    stock_a_day_1 = result_df[result_df["position_id"] == "Stock_A"].iloc[0]
    assert stock_a_day_1["daily_weight"] == pytest.approx(0.6)
    assert stock_a_day_1["raw_contribution"] == pytest.approx(0.012)
    stock_b_day_2 = result_df[result_df["position_id"] == "Stock_B"].iloc[1]
    assert stock_b_day_2["daily_weight"] == pytest.approx(408 / 1070)
    assert stock_b_day_2["raw_contribution"] == pytest.approx(0.001869, abs=1e-6)


def test_calculate_daily_contributions_smoothing(prepared_data_fixture):
    """Tests that Carino smoothing correctly adjusts the raw contribution."""
    instruments_df, portfolio_df = prepared_data_fixture
    result_df = _calculate_daily_instrument_contributions(
        instruments_df, portfolio_df, WeightingScheme.BOD, Smoothing(method="CARINO")
    )
    stock_a_day_1 = result_df[result_df["position_id"] == "Stock_A"].iloc[0]
    assert stock_a_day_1["raw_contribution"] == pytest.approx(0.012)
    assert stock_a_day_1["smoothed_contribution"] != pytest.approx(0.012)
    assert stock_a_day_1["smoothed_contribution"] == pytest.approx(0.01194, abs=1e-5)


def test_calculate_carino_factors():
    """Tests the Carino smoothing factor calculation."""
    k_daily = _calculate_carino_factors(pd.Series([0.10]))
    assert k_daily.iloc[0] == pytest.approx(0.95310179)
    k_zero = _calculate_carino_factors(pd.Series([0.0]))
    assert k_zero.iloc[0] == 1.0