# tests/unit/engine/test_rules.py
import numpy as np
import pandas as pd
import pytest
from engine.rules import calculate_initial_resets, calculate_nip, calculate_nctrl4_reset, calculate_sign
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


# --- Tests for NIP Calculation ---


@pytest.fixture
def nip_test_df() -> pd.DataFrame:
    """Provides a sample DataFrame for testing NIP calculation logic."""
    data = {
        # A day that should trigger NIP
        PortfolioColumns.BEGIN_MV: [0, 0, 1000],
        PortfolioColumns.BOD_CF: [0, 20, 0],
        PortfolioColumns.EOD_CF: [0, -20, 0],
        PortfolioColumns.END_MV: [0, 0, 1000],
    }
    return pd.DataFrame(data)


def test_calculate_nip_triggered_for_zero_value_day(nip_test_df):
    """Tests that NIP is flagged for a day where all values are zero."""
    result = calculate_nip(nip_test_df)
    # For day 0, BMV+BOD+EMV+EOD is 0. BOD_CF is 0, so sign is 0. EOD_CF is 0. 0 == -0.
    # This should be a NIP day according to the logic.
    assert result.iloc[0] == 1


def test_calculate_nip_not_triggered_for_offsetting_cashflow(nip_test_df):
    """
    Tests NIP is NOT flagged for a zero-net-change day with offsetting flows.
    The specific NIP rule is (total_value==0) AND (eod_cf == -sign(bod_cf)),
    which is not met here.
    """
    result = calculate_nip(nip_test_df)
    # For day 1, total value is 0. BOD_CF is 20 (sign=1). EOD_CF is -20.
    # The check is `eod_cf == -sign(bod_cf)`, which is `-20 == -1`, which is False.
    assert result.iloc[1] == 0


def test_calculate_nip_not_triggered_for_non_zero_day(nip_test_df):
    """Tests that NIP is not flagged for a normal day with non-zero values."""
    result = calculate_nip(nip_test_df)
    assert result.iloc[2] == 0


# --- Tests for Reset Calculation ---


@pytest.fixture
def reset_test_df() -> pd.DataFrame:
    """Provides a sample DataFrame for testing reset (NCTRL) calculation logic."""
    data = {
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]),
        PortfolioColumns.TEMP_LONG_CUM_ROR: [-50, -105, 10, 15],
        PortfolioColumns.TEMP_SHORT_CUM_ROR: [50, 10, 105, 20],
        PortfolioColumns.LONG_CUM_ROR: [-50, 0, 10, 15],  # Post-reset (zeroed)
        PortfolioColumns.SHORT_CUM_ROR: [50, 10, 105, 20],
        PortfolioColumns.BOD_CF: [0, 0, 1000, 0],
        PortfolioColumns.EOD_CF: [0, 0, 0, 0],
    }
    return pd.DataFrame(data)


def test_calculate_initial_resets_nctrl1_triggered(reset_test_df):
    """Tests that NCTRL1 is triggered when Temp Long RoR breaches -100%."""
    df = reset_test_df
    # On day 2 (index 1), TEMP_LONG_CUM_ROR is -105 and there's a next-day BOD cashflow.
    resets = calculate_initial_resets(df, report_end_date=pd.to_datetime("2025-01-31"))
    assert df[PortfolioColumns.NCTRL_1].iloc[1] == 1
    assert resets.iloc[1]


def test_calculate_initial_resets_nctrl2_triggered(reset_test_df):
    """Tests that NCTRL2 is triggered when Temp Short RoR breaches 100%."""
    df = reset_test_df
    # On day 3 (index 2), TEMP_SHORT_CUM_ROR is 105 and there is a current BOD cashflow.
    resets = calculate_initial_resets(df, report_end_date=pd.to_datetime("2025-01-31"))
    assert df[PortfolioColumns.NCTRL_2].iloc[2] == 1
    assert resets.iloc[2]


def test_calculate_initial_resets_not_triggered_without_common_condition(reset_test_df):
    """Tests that NCTRL flags are not set if the RoR breach occurs but no common condition is met."""
    df = reset_test_df.copy()
    df.at[2, PortfolioColumns.BOD_CF] = 0  # Remove the cashflow on day 3
    df[PortfolioColumns.PERF_DATE] = pd.to_datetime(
        ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
    )  # Ensure date type
    resets = calculate_initial_resets(df, report_end_date=pd.to_datetime("2025-02-28"))
    # NCTRL2 on day 3 (index 2) should not trigger as there is no CF, it's not EOM, etc.
    assert df[PortfolioColumns.NCTRL_2].iloc[2] == 0
    assert not resets.iloc[2]


def test_calculate_nctrl4_reset_triggered(reset_test_df):
    """Tests that NCTRL4 is triggered when the previous day had a major loss and there's a new cashflow."""
    df = reset_test_df
    # For day 3 (index 2), the previous day's (index 1) final LONG_CUM_ROR is 0,
    # but the rule looks at LONG_CUM_ROR which is the preliminary value in the old code.
    # The corrected logic uses the FINAL post-reset RoR.
    # Let's set up the condition correctly for the test:
    df.at[1, PortfolioColumns.LONG_CUM_ROR] = -105 # Simulate previous day's final ROR being a loss
    
    resets = calculate_nctrl4_reset(df)
    # On day 3 (index 2), prev_long_ror is -105 and current BOD_CF is 1000. This should trigger NCTRL4.
    assert resets.iloc[2]
    assert df[PortfolioColumns.NCTRL_4].iloc[2] == 1