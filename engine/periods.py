# engine/periods.py
import pandas as pd

from engine.config import EngineConfig, PeriodType


def get_effective_period_start_dates(
    perf_dates_dt: pd.Series, config: EngineConfig
) -> pd.Series:
    """
    Vectorized calculation of the effective period start date for each row.
    Returns a Series with dtype=datetime64[ns].
    """
    if config.period_type == PeriodType.YTD:
        effective_starts = perf_dates_dt.dt.to_period("Y").dt.start_time
    elif config.period_type == PeriodType.MTD:
        effective_starts = perf_dates_dt.dt.to_period("M").dt.start_time
    elif config.period_type == PeriodType.QTD:
        effective_starts = perf_dates_dt.dt.to_period("Q").dt.start_time
    elif config.period_type == PeriodType.EXPLICIT:
        explicit_start = max(
            config.performance_start_date,
            config.report_start_date or config.performance_start_date,
        )
        # Consistently return a named series
        return pd.Series(pd.to_datetime(explicit_start), index=perf_dates_dt.index, name=perf_dates_dt.name)
    else:
        # Fallback case, though validation should prevent this.
        return pd.Series(pd.to_datetime(config.performance_start_date), index=perf_dates_dt.index, name=perf_dates_dt.name)

    perf_start_dt = pd.to_datetime(config.performance_start_date)

    return effective_starts.where(
        effective_starts >= perf_start_dt, perf_start_dt
    )