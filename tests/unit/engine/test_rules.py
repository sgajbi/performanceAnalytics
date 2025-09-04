# tests/unit/engine/test_rules.py
import numpy as np
import pandas as pd
import pytest
from engine.rules import calculate_sign
from engine.schema import PortfolioColumns


@pytest.fixture
def sign_test_df() -> pd.DataFrame:
    """Provides a sample DataFrame for testing sign calculation logic."""
    data = {
        PortfolioColumns.BEGIN_MV: [1000, 500, -200, -150, 800],
        PortfolioColumns.BOD_CF: [0, 0, 1000, 0, 0],
        PortfolioColumns.EOD_CF: [0, -800, 0, 0, 0],
        PortfolioColumns.PERF_RESET: [0, 0, 0, 1, 0],
    }
    df = pd.DataFrame(data)
    # The `calculate_sign` function expects PERF_RESET to already be calculated.
    # We initialize it here to simulate the state when the function is called.
    return df


def test_calculate_sign_initial_day(sign_test_df):
    """Tests that the sign is correctly determined by BMV + BOD_CF on the first day."""
    result = calculate_sign(sign_test_df)
    assert result.iloc[0] == 1  # 1000 + 0 is positive


def test_calculate_sign_persists_on_flip_without_cashflow(sign_test_df):
    """
    Tests that the sign carries over from the previous day if it flips without
    a cashflow or reset event to justify it.
    """
    # Day 2: BMV (500) + BOD_CF (0) is positive, but prev sign was positive.
    # Day 3: BMV (-200) + BOD_CF (1000) is positive.
    # Let's create a specific scenario for this test.
    df = sign_test_df.copy()
    df.at[1, PortfolioColumns.BEGIN_MV] = -600  # BMV+BOD is now -600
    df.at[1, PortfolioColumns.BOD_CF] = 0
    df.at[1, PortfolioColumns.EOD_CF] = 0  # from prev day is 0

    result = calculate_sign(df)
    # The sign at index 1 should remain 1 from the previous day, not flip to -1.
    assert result.iloc[1] == 1


def test_calculate_sign_flips_with_bod_cashflow(sign_test_df):
    """Tests that the sign correctly flips when there is a BOD cashflow."""
    result = calculate_sign(sign_test_df)
    # Day 3: BMV (-200) + BOD_CF (1000) is positive, justifying the flip from the previous day's sign.
    # The previous day's (Day 2) sign would be 1 (500+0).
    # But on Day 3, there's a huge BOD cashflow, so it should be allowed to change.
    # The initial sign on Day 3 is sign(-200+1000) = 1.
    assert result.iloc[2] == 1


def test_calculate_sign_flips_with_prev_eod_cashflow(sign_test_df):
    """Tests that the sign correctly flips when there was an EOD cashflow on the prior day."""
    result = calculate_sign(sign_test_df)
    # Day 2 has a prev_eod_cf of -800 from Day 1. This justifies a potential sign flip on Day 2.
    # Let's manufacture a flip.
    df = sign_test_df.copy()
    df.at[2, PortfolioColumns.BEGIN_MV] = -900
    df.at[2, PortfolioColumns.BOD_CF] = 0
    df.at[1, PortfolioColumns.EOD_CF] = -1500  # prev_eod_cf for day 2 is -1500

    result = calculate_sign(df)
    # Sign for Day 1 is 1. Sign for Day 2 is 1.
    # Initial sign for Day 3 is -1. Because prev_eod_cf on day 2 is not 0, it is allowed to flip.
    assert result.iloc[2] == -1


def test_calculate_sign_flips_after_perf_reset(sign_test_df):
    """Tests that the sign is allowed to flip on the day after a performance reset."""
    result = calculate_sign(sign_test_df)
    # Day 4 has a perf_reset on the prior day (Day 3).
    # This should allow the sign to change freely on Day 4.
    # Let's force a flip.
    df = sign_test_df.copy()
    df.at[4, PortfolioColumns.BEGIN_MV] = -100  # Initial sign for day 4 is -1
    df.at[3, PortfolioColumns.PERF_RESET] = 1   # prev_perf_reset for day 4 is 1

    result = calculate_sign(df)
    assert result.iloc[4] == -1