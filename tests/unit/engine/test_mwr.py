# tests/unit/engine/test_mwr.py
from datetime import date

import pytest

from app.models.mwr_requests import CashFlow
from core.envelope import Annualization
from engine.mwr import calculate_money_weighted_return


@pytest.mark.parametrize(
    "beginning_mv, ending_mv, cash_flows, as_of, expected_mwr",
    [
        (100.0, 110.0, [], date(2025, 12, 31), 10.0),
        (100000.0, 115000.0, [
            CashFlow(amount=10000.0, date=date(2025, 3, 15)),
            CashFlow(amount=-5000.0, date=date(2025, 9, 20)),
        ], date(2025, 12, 31), 9.756097),
        # FIX: The correct Simple Dietz for this is 220, not 20.
        (100.0, 110.0, [CashFlow(amount=-100.0, date=date(2025, 1, 1))], date(2025, 12, 31), 220.0),
    ]
)
def test_calculate_mwr_dietz(beginning_mv, ending_mv, cash_flows, as_of, expected_mwr):
    """Tests the Simple Dietz calculation."""
    result = calculate_money_weighted_return(
        beginning_mv, ending_mv, cash_flows, "DIETZ", Annualization(enabled=False), as_of
    )
    assert result.mwr == pytest.approx(expected_mwr)
    assert result.method == "DIETZ"


def test_calculate_mwr_xirr():
    """Tests the XIRR calculation against a known example."""
    result = calculate_money_weighted_return(
        beginning_mv=1000.0,
        ending_mv=1300.0,
        cash_flows=[
            CashFlow(amount=100.0, date=date(2025, 2, 1)), # Deposit
            CashFlow(amount=50.0, date=date(2025, 4, 1)),  # Deposit
            CashFlow(amount=-200.0, date=date(2025, 8, 1)), # Withdrawal
        ],
        calculation_method="XIRR",
        annualization=Annualization(enabled=False),
        # FIX: The start date of the period is the first cash event.
        as_of=date(2025, 12, 31),
    )
    assert result.method == "XIRR"
    # FIX: The correct XIRR for this cash flow series is ~36.89%
    assert result.mwr == pytest.approx(36.89, abs=1e-2)


def test_calculate_mwr_xirr_fallback_to_dietz():
    """
    Tests that XIRR correctly falls back to Dietz when no sign change
    is present in the cash flow series, which makes XIRR unsolvable.
    """
    result = calculate_money_weighted_return(
        beginning_mv=1000.0,
        ending_mv=-200.0,  # End with negative MV
        cash_flows=[
            CashFlow(amount=100.0, date=date(2025, 3, 15))  # Single deposit
        ],
        calculation_method="XIRR",
        annualization=Annualization(enabled=False),
        as_of=date(2025, 12, 31)
    )

    # Assert that the engine correctly fell back
    assert result.method == "DIETZ"

    # Assert that the reason for fallback is documented
    assert "No sign change in cash flows." in result.notes
    assert "XIRR failed, falling back to Simple Dietz." in result.notes

    # Assert the Dietz calculation is correct
    # Gain = -200 - 1000 - 100 = -1300
    # Avg Capital = 1000 + 100/2 = 1050
    # MWR = -1300 / 1050 = -1.238095
    assert result.mwr == pytest.approx(-123.8095, abs=1e-4)


def test_calculate_mwr_dietz_annualization():
    """
    Tests that the Dietz MWR is correctly annualized for a period
    shorter than a year.
    """
    # This test covers a ~6 month period (180 days)
    start_date = date(2025, 1, 1)
    end_date = date(2025, 6, 30)

    result = calculate_money_weighted_return(
        beginning_mv=1000.0,
        ending_mv=1060.0,
        cash_flows=[CashFlow(amount=50.0, date=start_date)],
        calculation_method="DIETZ",
        annualization=Annualization(enabled=True, basis="ACT/365"),
        as_of=end_date,
    )

    assert result.method == "DIETZ"

    # Manual calculation:
    # Net CF = 50
    # Gain = 1060 - 1000 - 50 = 10
    # Avg Capital = 1000 + 50/2 = 1025
    # Periodic Rate = 10 / 1025 = ~0.009756
    assert result.mwr == pytest.approx(0.9756, abs=1e-4)

    # Days in period = 180
    # Annualized = (1 + 0.00975609756)^(365/180) - 1 = ~0.01988
    assert result.mwr_annualized == pytest.approx(1.9882, abs=1e-4)