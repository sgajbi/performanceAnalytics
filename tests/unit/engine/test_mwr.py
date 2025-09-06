# tests/unit/engine/test_mwr.py
from datetime import date
from typing import List, Dict
import pytest
from engine.mwr import calculate_money_weighted_return


@pytest.mark.parametrize(
    "beginning_mv, ending_mv, cash_flows, expected_mwr",
    [
        (100.0, 110.0, [], 10.0),
        (100000.0, 115000.0, [
            {"amount": 10000.0, "date": "2025-03-15"},
            {"amount": -5000.0, "date": "2025-09-20"},
        ], 9.523809),
        (100.0, 110.0, [{"amount": -100.0, "date": "2025-01-01"}], 0.0),
    ]
)
def test_calculate_money_weighted_return(
    beginning_mv: float,
    ending_mv: float,
    cash_flows: List[Dict],
    expected_mwr: float
):
    """
    Tests the money-weighted return calculation with various scenarios.
    """
    result = calculate_money_weighted_return(beginning_mv, ending_mv, cash_flows)
    assert result == pytest.approx(expected_mwr)