# tests/unit/engine/characterization_data.py
from datetime import date
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
        PortfolioColumns.DAY: [1, 2, 3, 4],
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