# adapters/api_adapter.py
import logging
from typing import Any, Dict, List
from datetime import date

import pandas as pd
from app.models.requests import PerformanceRequest
from app.models.responses import PerformanceBreakdown, PerformanceResultItem, PerformanceSummary, SinglePeriodPerformanceResult
from common.enums import Frequency, PeriodType
from engine.config import EngineConfig, PrecisionMode
from engine.schema import PortfolioColumns

logger = logging.getLogger(__name__)


def create_engine_config(
    request: PerformanceRequest, effective_start_date: date, effective_end_date: date
) -> EngineConfig:
    """Creates an EngineConfig object from an API PerformanceRequest and an effective date range."""
    return EngineConfig(
        performance_start_date=request.performance_start_date,
        report_start_date=effective_start_date,
        report_end_date=effective_end_date,
        metric_basis=request.metric_basis,
        period_type=PeriodType.EXPLICIT,  # The engine now always runs on an explicit range
        rounding_precision=request.rounding_precision,
        precision_mode=PrecisionMode(request.precision_mode),
        data_policy=request.data_policy,
        currency_mode=request.currency_mode,
        report_ccy=request.report_ccy,
        fx=request.fx,
        hedging=request.hedging,
    )


def create_engine_dataframe(daily_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Creates a Pandas DataFrame for the engine from the raw daily data list.
    No renaming is needed as the API contract now matches the engine's snake_case schema.
    """
    if not daily_data:
        return pd.DataFrame()
    try:
        df = pd.DataFrame(daily_data)
        if "perf_date" in df.columns:
            df.drop_duplicates(subset=["perf_date"], keep="last", inplace=True)
        return df
    except Exception as e:
        logger.exception("Failed to create DataFrame from daily data.")
        raise ValueError(f"Failed to process daily data: {e}")


def format_breakdowns_for_response(
    breakdowns_data: Dict[Frequency, List[Dict]], daily_results_df: pd.DataFrame
) -> PerformanceBreakdown:
    """
    Takes the pure breakdown dict from the engine and formats it into
    the Pydantic response models.
    """
    response_breakdowns = {}
    daily_records = daily_results_df.to_dict(orient="records")

    for freq, results in breakdowns_data.items():
        formatted_results = []
        for i, result_item in enumerate(results):
            summary_data = result_item["summary"]

            pydantic_summary_data = {
                "begin_mv": summary_data.get(PortfolioColumns.BEGIN_MV),
                "end_mv": summary_data.get(PortfolioColumns.END_MV),
                "net_cash_flow": summary_data.get("net_cash_flow"),
                **summary_data,
            }

            # --- FIX START: Correctly populate cumulative return for daily summaries ---
            if freq == Frequency.DAILY and "cumulative_return_pct_to_date" not in pydantic_summary_data:
                 if "final_cum_ror" in summary_data:
                      pydantic_summary_data["cumulative_return_pct_to_date"] = summary_data["final_cum_ror"]
            # --- FIX END ---

            summary_model = PerformanceSummary.model_validate(pydantic_summary_data)

            daily_data_for_period = None
            if freq == Frequency.DAILY and i < len(daily_records):
                daily_data_for_period = [daily_records[i]]

            formatted_results.append(
                PerformanceResultItem(
                    period=result_item["period"],
                    summary=summary_model,
                    daily_data=daily_data_for_period,
                )
            )
        response_breakdowns[freq] = formatted_results
    return response_breakdowns