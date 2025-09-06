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