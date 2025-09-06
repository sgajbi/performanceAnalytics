# adapters/api_adapter.py
import logging
from typing import Any, Dict, List

import pandas as pd
from app.core.constants import (
    BEGIN_MARKET_VALUE_FIELD,
    END_MARKET_VALUE_FIELD,
    FINAL_CUMULATIVE_ROR_PERCENT_FIELD,
)
from app.models.requests import PerformanceRequest
from app.models.responses import PerformanceBreakdown, PerformanceResultItem, PerformanceSummary
from common.enums import Frequency
from engine.config import EngineConfig
from engine.schema import API_TO_ENGINE_MAP, ENGINE_TO_API_MAP, PortfolioColumns

logger = logging.getLogger(__name__)


def create_engine_config(request: PerformanceRequest) -> EngineConfig:
    """Creates an EngineConfig object from an API PerformanceRequest."""
    # This function will be updated in a subsequent step to use the new `periods` model.
    # For now, it maintains backward compatibility with the existing date fields.
    return EngineConfig(
        performance_start_date=request.performance_start_date,
        report_start_date=request.report_start_date,
        report_end_date=request.report_end_date,
        metric_basis=request.metric_basis,
        period_type=request.period_type,
        rounding_precision=request.rounding_precision,
    )


def create_engine_dataframe(daily_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Creates a Pandas DataFrame for the engine from the raw daily data list,
    mapping API aliases to the internal engine schema.
    """
    if not daily_data:
        return pd.DataFrame()
    try:
        df = pd.DataFrame(daily_data)
        df.rename(columns=API_TO_ENGINE_MAP, inplace=True)
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
    aliased_daily_df = daily_results_df.rename(columns=ENGINE_TO_API_MAP)
    aliased_daily_records = aliased_daily_df.to_dict(orient="records")

    for freq, results in breakdowns_data.items():
        formatted_results = []
        for i, result_item in enumerate(results):
            summary_data = result_item["summary"]

            pydantic_summary_data = {
                BEGIN_MARKET_VALUE_FIELD: summary_data.get(PortfolioColumns.BEGIN_MV),
                END_MARKET_VALUE_FIELD: summary_data.get(PortfolioColumns.END_MV),
                "net_cash_flow": summary_data.get("net_cash_flow"),
                FINAL_CUMULATIVE_ROR_PERCENT_FIELD: summary_data.get(PortfolioColumns.FINAL_CUM_ROR),
            }
            summary_model = PerformanceSummary.model_validate(pydantic_summary_data)

            daily_data_for_period = None
            if freq == Frequency.DAILY and i < len(aliased_daily_records):
                daily_data_for_period = [aliased_daily_records[i]]

            formatted_results.append(
                PerformanceResultItem(
                    period=result_item["period"],
                    summary=summary_model,
                    daily_data=daily_data_for_period,
                )
            )
        response_breakdowns[freq] = formatted_results
    return response_breakdowns