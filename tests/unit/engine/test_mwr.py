# tests/unit/engine/test_mwr.py
from datetime import date

import numpy as np
import pytest

from app.models.mwr_requests import CashFlow
from core.envelope import Annualization
from engine.mwr import _xirr, calculate_money_weighted_return


@pytest.mark.parametrize(
    "begin_mv, end_mv, cash_flows, as_of, expected_mwr",
    [
        (100.0, 110.0, [], date(2025, 12, 31), 10.0),
        (
            100000.0,
            115000.0,
            [
                CashFlow(amount=10000.0, date=date(2025, 3, 15)),
                CashFlow(amount=-5000.0, date=date(2025, 9, 20)),
            ],
            date(2025, 12, 31),
            9.756097,
        ),
        (100.0, 110.0, [CashFlow(amount=-100.0, date=date(2025, 1, 1))], date(2025, 12, 31), 220.0),
    ],
)
def test_calculate_mwr_dietz(begin_mv, end_mv, cash_flows, as_of, expected_mwr):
    """Tests the Simple Dietz calculation."""
    result = calculate_money_weighted_return(begin_mv, end_mv, cash_flows, "DIETZ", Annualization(enabled=False), as_of)
    assert result.mwr == pytest.approx(expected_mwr)
    assert result.method == "DIETZ"


def test_calculate_mwr_xirr():
    """Tests the XIRR calculation against a known example."""
    result = calculate_money_weighted_return(
        begin_mv=1000.0,
        end_mv=1300.0,
        cash_flows=[
            CashFlow(amount=100.0, date=date(2025, 2, 1)),
            CashFlow(amount=50.0, date=date(2025, 4, 1)),
            CashFlow(amount=-200.0, date=date(2025, 8, 1)),
        ],
        calculation_method="XIRR",
        annualization=Annualization(enabled=False),
        as_of=date(2025, 12, 31),
    )
    assert result.method == "XIRR"
    assert result.mwr == pytest.approx(36.89, abs=1e-2)


def test_calculate_mwr_xirr_fallback_to_dietz():
    """Tests that XIRR correctly falls back to Dietz when no sign change is present."""
    result = calculate_money_weighted_return(
        begin_mv=1000.0,
        end_mv=-200.0,
        cash_flows=[CashFlow(amount=100.0, date=date(2025, 3, 15))],
        calculation_method="XIRR",
        annualization=Annualization(enabled=False),
        as_of=date(2025, 12, 31),
    )
    assert result.method == "DIETZ"
    assert "No sign change in cash flows." in result.notes
    assert "XIRR failed, falling back to Simple Dietz." in result.notes
    assert result.mwr == pytest.approx(-123.8095, abs=1e-4)


def test_calculate_mwr_dietz_annualization():
    """Tests that the Dietz MWR is correctly annualized."""
    start_date = date(2025, 1, 1)
    end_date = date(2025, 6, 30)

    result = calculate_money_weighted_return(
        begin_mv=1000.0,
        end_mv=1060.0,
        cash_flows=[CashFlow(amount=50.0, date=start_date)],
        calculation_method="DIETZ",
        annualization=Annualization(enabled=True, basis="ACT/365"),
        as_of=end_date,
    )

    assert result.method == "DIETZ"
    assert result.mwr == pytest.approx(0.9756, abs=1e-4)
    assert result.mwr_annualized == pytest.approx(1.9882, abs=1e-4)


def test_calculate_mwr_zero_denominator():
    """Tests that MWR correctly handles a zero denominator."""
    result = calculate_money_weighted_return(
        begin_mv=-50.0,
        end_mv=50.0,
        cash_flows=[CashFlow(amount=100.0, date=date(2025, 1, 1))],
        calculation_method="DIETZ",
        annualization=Annualization(enabled=False),
        as_of=date(2025, 12, 31),
    )
    assert result.method == "DIETZ"
    assert result.mwr == 0.0
    assert "Calculation resulted in a zero denominator." in result.notes


def test_xirr_handles_solver_exception(mocker):
    mocker.patch("engine.mwr.brentq", side_effect=RuntimeError("solver failed"))
    values = [-100.0, 120.0]
    dates = [date(2025, 1, 1), date(2025, 12, 31)]
    result = _xirr(values=np.array(values), dates=np.array(dates))
    assert result["converged"] is False
    assert result["rate"] is None
    assert "failed to converge" in result["notes"]
