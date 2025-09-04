# tests/unit/engine/characterization_data.py
from datetime import date
from decimal import Decimal
import pandas as pd
from engine.config import EngineConfig, PeriodType
from engine.schema import PortfolioColumns

def long_flip_scenario():
    """Provides the input and expected output for the long flip scenario."""
    engine_config = EngineConfig(
        performance_start_date=date(2024, 12, 31),
        report_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 4),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    input_df = pd.DataFrame({
        PortfolioColumns.DAY: [1, 2, 3, 4],
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]),
        PortfolioColumns.BEGIN_MV: [1000.0, 500.0, -50.0, 1050.0],
        PortfolioColumns.BOD_CF: [0.0, 0.0, 1000.0, 0.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [500.0, -50.0, 1050.0, 1155.0],
    })
    expected_df = pd.DataFrame({
        PortfolioColumns.PERF_DATE: [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3), date(2025, 1, 4)],
        PortfolioColumns.SIGN: [1, 1, 1, 1],
        PortfolioColumns.DAILY_ROR: [-50.0, -110.0, 10.52631579, 10.0],
        PortfolioColumns.NIP: [0, 0, 0, 0],
        PortfolioColumns.PERF_RESET: [0, 1, 0, 0],
        PortfolioColumns.LONG_SHORT: ["L", "L", "L", "L"],
        PortfolioColumns.NCTRL_1: [0, 1, 0, 0],
        PortfolioColumns.NCTRL_2: [0, 0, 0, 0],
        PortfolioColumns.NCTRL_3: [0, 0, 0, 0],
        PortfolioColumns.NCTRL_4: [0, 0, 0, 0],
        PortfolioColumns.TEMP_LONG_CUM_ROR: [-50.0, -105.0, 10.52631579, 21.57894737],
        PortfolioColumns.TEMP_SHORT_CUM_ROR: [0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.LONG_CUM_ROR: [-50.0, 0.0, 10.52631579, 21.57894737],
        PortfolioColumns.SHORT_CUM_ROR: [0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.FINAL_CUM_ROR: [-50.0, 0.0, 10.52631579, 21.57894737],
    })
    return engine_config, input_df, expected_df

def short_flip_scenario():
    """Provides the input and expected output for the short position flip scenario."""
    engine_config = EngineConfig(
        performance_start_date=date(2024, 12, 31),
        report_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 3),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    input_df = pd.DataFrame({
        PortfolioColumns.DAY: [1, 2, 3],
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        PortfolioColumns.BEGIN_MV: [-1000.0, -900.0, 500.0],
        PortfolioColumns.BOD_CF: [0.0, 1500.0, 0.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [-900.0, 500.0, 550.0],
    })
    expected_df = pd.DataFrame({
        PortfolioColumns.PERF_DATE: [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)],
        PortfolioColumns.SIGN: [-1, 1, 1],
        PortfolioColumns.DAILY_ROR: [10.0, -16.66666667, 10.0],
        PortfolioColumns.NIP: [0, 0, 0],
        PortfolioColumns.PERF_RESET: [0, 0, 0],
        PortfolioColumns.LONG_SHORT: ["S", "L", "L"],
        PortfolioColumns.NCTRL_1: [0, 0, 0],
        PortfolioColumns.NCTRL_2: [0, 0, 0],
        PortfolioColumns.NCTRL_3: [0, 0, 0],
        PortfolioColumns.NCTRL_4: [0, 0, 0],
        PortfolioColumns.TEMP_LONG_CUM_ROR: [0.0, -16.66666667, -8.33333333],
        PortfolioColumns.TEMP_SHORT_CUM_ROR: [10.0, 10.0, 10.0],
        PortfolioColumns.LONG_CUM_ROR: [0.0, -16.66666667, -8.33333333],
        PortfolioColumns.SHORT_CUM_ROR: [10.0, 10.0, 10.0],
        PortfolioColumns.FINAL_CUM_ROR: [10.0, -8.33333333, 0.83333333],
    })
    return engine_config, input_df, expected_df

def zero_value_nip_scenario():
    """Provides data for a scenario involving zero-value days and NIP."""
    engine_config = EngineConfig(
        performance_start_date=date(2024, 12, 31),
        report_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 5),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    input_df = pd.DataFrame({
        PortfolioColumns.DAY: [1, 2, 3, 4, 5],
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]),
        PortfolioColumns.BEGIN_MV: [1000.0, 1050.0, 0.0, 0.0, 0.0],
        PortfolioColumns.BOD_CF: [0.0, 0.0, 20.0, 0.0, 100.0],
        PortfolioColumns.EOD_CF: [0.0, -1050.0, -20.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [1050.0, 0.0, 0.0, 0.0, 110.0],
    })
    expected_df = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]).date,
        PortfolioColumns.SIGN: [1, 1, 1, 0, 1],
        PortfolioColumns.DAILY_ROR: [5.0, 0.0, 0.0, 0.0, 10.0],
        PortfolioColumns.NIP: [0, 0, 0, 1, 0],
        PortfolioColumns.PERF_RESET: [0, 0, 0, 0, 0],
        PortfolioColumns.LONG_CUM_ROR: [5.0, 5.0, 5.0, 5.0, 15.5],
        PortfolioColumns.FINAL_CUM_ROR: [5.0, 5.0, 5.0, 5.0, 15.5],
    })
    return engine_config, input_df, expected_df

def standard_growth_scenario():
    """Provides data for a standard growth scenario with cashflows."""
    engine_config = EngineConfig(
        performance_start_date=date(2024, 12, 31),
        report_start_date=date(2025, 1, 1),
        report_end_date=date(2025, 1, 5),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    input_df = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]),
        PortfolioColumns.BEGIN_MV: [100000.0, 101000.0, 102010.0, 100989.9, 127249.29],
        PortfolioColumns.BOD_CF: [0.0, 0.0, 0.0, 25000.0, 0.0],
        PortfolioColumns.EOD_CF: [0.0, 0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.MGMT_FEES: [0.0, 0.0, 0.0, 0.0, 0.0],
        PortfolioColumns.END_MV: [101000.0, 102010.0, 100989.9, 127249.29, 125976.7971],
    })
    expected_df = pd.DataFrame({
        PortfolioColumns.PERF_DATE: pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]).date,
        PortfolioColumns.DAILY_ROR: [1.0, 1.0, -1.0, 0.999596, -1.0],
        PortfolioColumns.FINAL_CUM_ROR: [1.0, 2.01, 0.9899, 1.999391, 0.979397],
    })
    return engine_config, input_df, expected_df