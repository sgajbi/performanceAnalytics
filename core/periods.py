# core/periods.py
from datetime import date, timedelta
from typing import Tuple

import pandas as pd

from .envelope import Periods
from .errors import APIBadRequestError


def resolve_period(period_model: Periods, as_of: date) -> Tuple[date, date]:
    """
    Resolves a Periods model into a concrete (start_date, end_date) tuple.
    """
    period_type = period_model.type
    as_of_ts = pd.Timestamp(as_of)

    if period_type == "EXPLICIT":
        if not period_model.explicit:
            raise APIBadRequestError("Explicit period definition is missing.")
        return period_model.explicit.start, period_model.explicit.end

    if period_type == "ITD":
        # Cannot be resolved without a true inception date, signal this.
        # The caller (engine) will substitute the portfolio's actual start date.
        return date.min, as_of

    end_date = as_of
    if period_type == "YTD":
        start_date = as_of_ts.to_period("Y").start_time.date()
    elif period_type == "QTD":
        start_date = as_of_ts.to_period("Q").start_time.date()
    elif period_type == "MTD":
        start_date = as_of_ts.to_period("M").start_time.date()
    elif period_type == "WTD":
        start_date = (as_of_ts - pd.to_timedelta(as_of_ts.dayofweek, unit="d")).date()
    elif period_type in ["Y1", "Y3", "Y5"]:
        years = int(period_type[1:])
        start_date = (as_of_ts - pd.DateOffset(years=years) + pd.Timedelta(days=1)).date()
    elif period_type == "ROLLING":
        if not period_model.rolling:
            raise APIBadRequestError("Rolling period definition is missing.")
        if period_model.rolling.months:
            start_date = (as_of_ts - pd.DateOffset(months=period_model.rolling.months) + pd.Timedelta(days=1)).date()
        elif period_model.rolling.days:
            start_date = (as_of_ts - pd.Timedelta(days=period_model.rolling.days - 1)).date()
        else:
            raise APIBadRequestError("Invalid rolling period definition.")
    else:
        raise NotImplementedError(f"Period type '{period_type}' is not implemented.")

    return start_date, end_date