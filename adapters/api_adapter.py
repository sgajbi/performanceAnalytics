# adapters/api_adapter.py
import logging
from typing import Any, Dict, List

import pandas as pd
from app.models.requests import PerformanceRequest
from app.models.responses import PerformanceBreakdown, PerformanceResultItem, PerformanceSummary
from common.enums import Frequency
from engine.config import EngineConfig, PrecisionMode
from engine.schema import PortfolioColumns

logger = logging.getLogger(__name__)


def create_engine_config(request: PerformanceRequest) -> EngineConfig:
    """Creates an EngineConfig object from an API PerformanceRequest."""
    return EngineConfig(
        performance_start_date=request.performance_start_date,
        report_start_date=request.report_start_date,
        report_end_date=request.report_end_date,
        metric_basis=request.metric_basis,
        period_type=request.period_type,
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
        # --- START FIX: Handle duplicate dates in input data ---
        if "perf_date" in df.columns:
            # Keep the last entry for any given date to allow for corrections
            df.drop_duplicates(subset=['perf_date'], keep='last', inplace=True)
        # --- END FIX ---
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