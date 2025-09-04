# engine/schema.py
from enum import Enum


class PortfolioColumns(str, Enum):
    """
    Defines the internal, standardized snake_case column names for the performance engine.
    This serves as the single source of truth for all data contracts within the engine.
    """

    # --- Input Fields ---
    DAY = "day"
    PERF_DATE = "perf_date"
    BEGIN_MV = "begin_mv"
    BOD_CF = "bod_cf"
    EOD_CF = "eod_cf"
    MGMT_FEES = "mgmt_fees"
    END_MV = "end_mv"

    # --- Core Calculated Fields ---
    SIGN = "sign"
    DAILY_ROR = "daily_ror"
    NIP = "nip"
    PERF_RESET = "perf_reset"
    LONG_SHORT = "long_short"

    # --- Control Flags ---
    NCTRL_1 = "nctrl_1"
    NCTRL_2 = "nctrl_2"
    NCTRL_3 = "nctrl_3"
    NCTRL_4 = "nctrl_4"

    # --- Cumulative Return Fields ---
    TEMP_LONG_CUM_ROR = "temp_long_cum_ror"
    TEMP_SHORT_CUM_ROR = "temp_short_cum_ror"
    LONG_CUM_ROR = "long_cum_ror"
    SHORT_CUM_ROR = "short_cum_ror"
    FINAL_CUM_ROR = "final_cum_ror"

    # --- Helper/Temporary Fields ---
    EFFECTIVE_PERIOD_START_DATE = "effective_period_start_date"


# Mapping from legacy API aliases to the internal engine schema.
# This is used by the adapter layer to translate incoming and outgoing data.
API_TO_ENGINE_MAP = {
    "Day": PortfolioColumns.DAY,
    "Perf. Date": PortfolioColumns.PERF_DATE,
    "Begin Market Value": PortfolioColumns.BEGIN_MV,
    "BOD Cashflow": PortfolioColumns.BOD_CF,
    "Eod Cashflow": PortfolioColumns.EOD_CF,
    "Mgmt fees": PortfolioColumns.MGMT_FEES,
    "End Market Value": PortfolioColumns.END_MV,
    "daily ror %": PortfolioColumns.DAILY_ROR,
    "Temp Long Cum Ror %": PortfolioColumns.TEMP_LONG_CUM_ROR,
    "Temp short Cum RoR %": PortfolioColumns.TEMP_SHORT_CUM_ROR,
    "NCTRL 1": PortfolioColumns.NCTRL_1,
    "NCTRL 2": PortfolioColumns.NCTRL_2,
    "NCTRL 3": PortfolioColumns.NCTRL_3,
    "NCTRL 4": PortfolioColumns.NCTRL_4,
    "Perf Reset": PortfolioColumns.PERF_RESET,
    "NIP": PortfolioColumns.NIP,
    "Long Cum Ror %": PortfolioColumns.LONG_CUM_ROR,
    "Short Cum RoR %": PortfolioColumns.SHORT_CUM_ROR,
    "Long /Short": PortfolioColumns.LONG_SHORT,
    "Final Cumulative ROR %": PortfolioColumns.FINAL_CUM_ROR,
    "sign": PortfolioColumns.SIGN,
}

# Invert the map for translating engine output back to the API contract.
ENGINE_TO_API_MAP = {v: k for k, v in API_TO_ENGINE_MAP.items()}