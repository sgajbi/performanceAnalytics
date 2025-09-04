# engine/rules.py
from decimal import Decimal

import numpy as np
import pandas as pd
from engine.config import EngineConfig
from engine.schema import PortfolioColumns


def _get_decimal_sign(d: Decimal) -> Decimal:
    """Helper to get the sign of a Decimal object."""
    if d > 0:
        return Decimal(1)
    elif d < 0:
        return Decimal(-1)
    return Decimal(0)


def calculate_sign(df: pd.DataFrame) -> pd.Series:
    """Vectorized calculation of the 'sign' column, supporting both float and Decimal."""
    is_decimal_mode = df[PortfolioColumns.BEGIN_MV].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0

    if is_decimal_mode:
        initial_sign = (df[PortfolioColumns.BEGIN_MV] + df[PortfolioColumns.BOD_CF]).apply(_get_decimal_sign)
    else:
        initial_sign = np.sign(df[PortfolioColumns.BEGIN_MV] + df[PortfolioColumns.BOD_CF])

    prev_eod_cf = df[PortfolioColumns.EOD_CF].shift(1, fill_value=zero)
    prev_perf_reset = df[PortfolioColumns.PERF_RESET].shift(1, fill_value=zero)
    is_flip_event = ((df[PortfolioColumns.BOD_CF] != zero) | (prev_eod_cf != zero) | (prev_perf_reset == 1))
    is_flip_event.iloc[0] = True
    flip_group = is_flip_event.cumsum()
    event_signs = initial_sign.where(is_flip_event)
    final_sign = event_signs.groupby(flip_group).ffill().fillna(zero)
    return final_sign.astype(int)


def calculate_nip(df: pd.DataFrame, config: EngineConfig) -> pd.Series:
    """Vectorized calculation of the 'No Investment Period' (NIP) flag."""
    is_decimal_mode = df[PortfolioColumns.BEGIN_MV].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0

    if config.feature_flags.use_nip_v2_rule:
        # Simplified V2 Rule from RFC
        cond = (df[PortfolioColumns.BEGIN_MV] + df[PortfolioColumns.BOD_CF] == zero) & \
               (df[PortfolioColumns.END_MV] + df[PortfolioColumns.EOD_CF] == zero)
        return cond.astype(int)

    # Legacy V1 Rule
    is_zero_value = (
        df[PortfolioColumns.BEGIN_MV]
        + df[PortfolioColumns.BOD_CF]
        + df[PortfolioColumns.END_MV]
        + df[PortfolioColumns.EOD_CF]
    ) == zero

    bod_cf_series = df[PortfolioColumns.BOD_CF]
    eod_cf_series = df[PortfolioColumns.EOD_CF]

    if is_decimal_mode:
        sign_of_bod_cf = bod_cf_series.apply(_get_decimal_sign)
    else:
        sign_of_bod_cf = np.sign(bod_cf_series)

    is_offsetting_cf = eod_cf_series == -sign_of_bod_cf
    return (is_zero_value & is_offsetting_cf).astype(int)


def calculate_initial_resets(df: pd.DataFrame, report_end_date: pd.Timestamp) -> pd.Series:
    """Calculates resets based on NCTRL 1, 2, and 3, which use preliminary RoR."""
    is_decimal_mode = df[PortfolioColumns.BOD_CF].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0

    eom_mask = df[PortfolioColumns.PERF_DATE].dt.is_month_end
    next_day_bod_cf = df[PortfolioColumns.BOD_CF].shift(-1).fillna(zero)
    next_date_beyond_period = df[PortfolioColumns.PERF_DATE].shift(-1) > report_end_date

    cond_common = (
        (df[PortfolioColumns.BOD_CF] != zero)
        | (next_day_bod_cf != zero)
        | (df[PortfolioColumns.EOD_CF] != zero)
        | eom_mask
        | next_date_beyond_period
    )

    cond_nctrl1 = df[PortfolioColumns.TEMP_LONG_CUM_ROR] < -100
    cond_nctrl2 = df[PortfolioColumns.TEMP_SHORT_CUM_ROR] > 100
    cond_nctrl3 = (df[PortfolioColumns.TEMP_SHORT_CUM_ROR] < -100) & (df[PortfolioColumns.TEMP_LONG_CUM_ROR] != 0)

    nctrl1 = (cond_nctrl1 & ~cond_nctrl1.shift(1, fill_value=False)) & cond_common
    nctrl2 = (cond_nctrl2 & ~cond_nctrl2.shift(1, fill_value=False)) & cond_common
    nctrl3 = (cond_nctrl3 & ~cond_nctrl3.shift(1, fill_value=False)) & cond_common

    df[PortfolioColumns.NCTRL_1] = nctrl1.astype(int)
    df[PortfolioColumns.NCTRL_2] = nctrl2.astype(int)
    df[PortfolioColumns.NCTRL_3] = nctrl3.astype(int)
    df[PortfolioColumns.NCTRL_4] = 0

    return nctrl1 | nctrl2 | nctrl3


def calculate_nctrl4_reset(df: pd.DataFrame) -> pd.Series:
    """Calculates resets based on NCTRL 4, which uses final, zeroed RoR."""
    is_decimal_mode = df[PortfolioColumns.BOD_CF].dtype == "object"
    zero = Decimal(0) if is_decimal_mode else 0.0
    hundred = Decimal(-100) if is_decimal_mode else -100.0

    prev_long_ror = df[PortfolioColumns.LONG_CUM_ROR].shift(1, fill_value=zero)
    prev_short_ror = df[PortfolioColumns.SHORT_CUM_ROR].shift(1, fill_value=zero)
    prev_eod_cf = df[PortfolioColumns.EOD_CF].shift(1, fill_value=zero)

    nctrl4 = ((prev_long_ror <= hundred) | (prev_short_ror >= -hundred)) & (
        (df[PortfolioColumns.BOD_CF] != zero) | (prev_eod_cf != zero)
    )

    df[PortfolioColumns.NCTRL_4] = nctrl4.astype(int)
    return nctrl4