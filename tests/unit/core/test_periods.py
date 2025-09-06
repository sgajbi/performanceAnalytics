# tests/unit/core/test_periods.py
from datetime import date
import pytest
from core.envelope import Periods
from core.periods import resolve_period


@pytest.mark.parametrize(
    "period_def, as_of, expected_start, expected_end",
    [
        ({"type": "EXPLICIT", "explicit": {"start": "2025-02-15", "end": "2025-03-10"}}, "2025-08-31", date(2025, 2, 15), date(2025, 3, 10)),
        ({"type": "YTD"}, "2025-08-31", date(2025, 1, 1), date(2025, 8, 31)),
        ({"type": "QTD"}, "2025-08-31", date(2025, 7, 1), date(2025, 8, 31)),
        ({"type": "MTD"}, "2025-08-31", date(2025, 8, 1), date(2025, 8, 31)),
        ({"type": "WTD"}, "2025-08-31", date(2025, 8, 25), date(2025, 8, 31)), # Sunday is day 6
        ({"type": "Y1"}, "2025-08-31", date(2024, 9, 1), date(2025, 8, 31)),
        ({"type": "Y3"}, "2025-08-31", date(2022, 9, 1), date(2025, 8, 31)),
        ({"type": "Y5"}, "2025-08-31", date(2020, 9, 1), date(2025, 8, 31)),
        ({"type": "ROLLING", "rolling": {"months": 12}}, "2025-08-31", date(2024, 9, 1), date(2025, 8, 31)),
        ({"type": "ROLLING", "rolling": {"days": 63}}, "2025-08-31", date(2025, 6, 30), date(2025, 8, 31)),
        ({"type": "ITD"}, "2025-08-31", date.min, date(2025, 8, 31)),
    ],
    ids=["EXPLICIT", "YTD", "QTD", "MTD", "WTD", "Y1", "Y3", "Y5", "ROLLING_M", "ROLLING_D", "ITD"]
)
def test_resolve_period(period_def, as_of, expected_start, expected_end):
    """Tests that all period types are resolved to the correct start and end dates."""
    period_model = Periods.model_validate(period_def)
    as_of_date = date.fromisoformat(as_of)
    start_date, end_date = resolve_period(period_model, as_of_date)
    assert start_date == expected_start
    assert end_date == expected_end