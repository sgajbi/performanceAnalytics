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
    "Day": PortfolioColumns.DAY.value,
    "Perf. Date": PortfolioColumns.PERF_DATE.value,
    "Begin Market Value": PortfolioColumns.BEGIN_MV.value,
    "BOD Cashflow": PortfolioColumns.BOD_CF.value,
    "Eod Cashflow": PortfolioColumns.EOD_CF.value,
    "Mgmt fees": PortfolioColumns.MGMT_FEES.value,
    "End Market Value": PortfolioColumns.END_MV.value,
    "daily ror %": PortfolioColumns.DAILY_ROR.value,
    "Temp Long Cum Ror %": PortfolioColumns.TEMP_LONG_CUM_ROR.value,
    "Temp short Cum RoR %": PortfolioColumns.TEMP_SHORT_CUM_ROR.value,
    "NCTRL 1": PortfolioColumns.NCTRL_1.value,
    "NCTRL 2": PortfolioColumns.NCTRL_2.value,
    "NCTRL 3": PortfolioColumns.NCTRL_3.value,
    "NCTRL 4": PortfolioColumns.NCTRL_4.value,
    "Perf Reset": PortfolioColumns.PERF_RESET.value,
    "NIP": PortfolioColumns.NIP.value,
    "Long Cum Ror %": PortfolioColumns.LONG_CUM_ROR.value,
    "Short Cum RoR %": PortfolioColumns.SHORT_CUM_ROR.value,
    "Long /Short": PortfolioColumns.LONG_SHORT.value,
    "Final Cumulative ROR %": PortfolioColumns.FINAL_CUM_ROR.value,
    "sign": PortfolioColumns.SIGN.value,
}

# Invert the map for translating engine output back to the API contract.
ENGINE_TO_API_MAP = {v: k for k, v in API_TO_ENGINE_MAP.items()}