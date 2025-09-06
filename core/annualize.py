# core/annualize.py
from typing import Literal

import numpy as np

from .errors import APIBadRequestError

BasisType = Literal["BUS/252", "ACT/365", "ACT/ACT"]


def annualize_return(
    period_return: float, num_periods: int, periods_per_year: float, basis: BasisType
) -> float:
    """
    Annualizes a period return using geometric compounding.

    Args:
        period_return: The return for the entire period (e.g., 0.05 for 5%).
        num_periods: The number of periods in the given timeframe (e.g., number of days).
        periods_per_year: The number of periods in a year (e.g., 252 for business days).
        basis: The annualization basis, used for validation.

    Returns:
        The annualized return.
    """
    if num_periods <= 0:
        raise APIBadRequestError("Number of periods for annualization must be positive.")

    if periods_per_year <= 0:
        raise APIBadRequestError("Periods per year for annualization must be positive.")

    # For ACT/ACT, the scale factor is simply 365.25 / actual days
    if basis == "ACT/ACT":
        scale = 365.25 / num_periods
    else:
        scale = periods_per_year / num_periods

    return (1 + period_return) ** scale - 1