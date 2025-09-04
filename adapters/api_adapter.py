# adapters/api_adapter.py
import logging
from datetime import date
from typing import Any, Dict, List

import pandas as pd
from app.core.exceptions import InvalidInputDataError
from app.models.requests import PerformanceRequest
from app.models.responses import SummaryPerformance
from engine.config import EngineConfig
from engine.schema import API_TO_ENGINE_MAP, ENGINE_TO_API_MAP, PortfolioColumns

logger = logging.getLogger(__name__)


def create_engine_config(request: PerformanceRequest) -> EngineConfig:
    """Creates an EngineConfig object from an API PerformanceRequest."""
    return EngineConfig(
        performance_start_date=request.performance_start_date,
        report_start_date=request.report_start_date,
        report_end_date=request.report_end_date,
        metric_basis=request.metric_basis,
        period_type=request.period_type,
    )


def create_engine_dataframe(daily_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Creates a Pandas DataFrame for the engine from the raw daily data list,
    mapping API aliases to the internal engine schema.
    """
    if not daily_data:
        raise InvalidInputDataError("Daily data list cannot be empty.")

    try:
        df = pd.DataFrame(daily_data)
        df.rename(columns=API_TO_ENGINE_MAP, inplace=True)
        return df
    except Exception as e:
        logger.exception("Failed to create DataFrame from daily data.")
        raise InvalidInputDataError(f"Failed to process daily data: {e}")


def format_engine_output(
    engine_df: pd.DataFrame, engine_config: EngineConfig
) -> (List[Dict[str, Any]], Dict[str, Any]):
    """
    Formats the engine's output DataFrame back into the API response structure,
    including creating the summary block and mapping internal names to API aliases.
    """
    if engine_df.empty:
        summary = _create_empty_summary()
        return [], summary

    summary = _create_summary_from_engine_df(engine_df)
    aliased_df = engine_df.rename(columns=ENGINE_TO_API_MAP)

    # Ensure all expected API columns are present
    for api_alias in API_TO_ENGINE_MAP.keys():
        if api_alias not in aliased_df.columns and api_alias != 'sign':
             aliased_df[api_alias] = None

    # Convert date objects back to strings for JSON
    date_col_alias = ENGINE_TO_API_MAP.get(PortfolioColumns.PERF_DATE)
    if date_col_alias in aliased_df.columns:
        aliased_df[date_col_alias] = aliased_df[date_col_alias].apply(
            lambda x: x.strftime("%Y-%m-%d") if isinstance(x, date) else x
        )

    daily_results = aliased_df.to_dict(orient="records")
    return daily_results, summary


def _create_summary_from_engine_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Helper to calculate the summary block from the final engine DataFrame."""
    try:
        first_day = df.iloc[0]
        last_day = df.iloc[-1]

        summary = {
            ENGINE_TO_API_MAP[PortfolioColumns.BEGIN_MV]: first_day[PortfolioColumns.BEGIN_MV],
            ENGINE_TO_API_MAP[PortfolioColumns.END_MV]: last_day[PortfolioColumns.END_MV],
            ENGINE_TO_API_MAP[PortfolioColumns.FINAL_CUM_ROR]: last_day[PortfolioColumns.FINAL_CUM_ROR],
            ENGINE_TO_API_MAP[PortfolioColumns.BOD_CF]: df[PortfolioColumns.BOD_CF].sum(),
            ENGINE_TO_API_MAP[PortfolioColumns.EOD_CF]: df[PortfolioColumns.EOD_CF].sum(),
            ENGINE_TO_API_MAP[PortfolioColumns.MGMT_FEES]: df[PortfolioColumns.MGMT_FEES].sum(),
            ENGINE_TO_API_MAP[PortfolioColumns.NIP]: 1 if df[PortfolioColumns.NIP].sum() > 0 else 0,
            ENGINE_TO_API_MAP[PortfolioColumns.PERF_RESET]: 1 if df[PortfolioColumns.PERF_RESET].sum() > 0 else 0,
            ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_1]: 1 if df[PortfolioColumns.NCTRL_1].sum() > 0 else 0,
            ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_2]: 1 if df[PortfolioColumns.NCTRL_2].sum() > 0 else 0,
            ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_3]: 1 if df[PortfolioColumns.NCTRL_3].sum() > 0 else 0,
            ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_4]: 1 if df[PortfolioColumns.NCTRL_4].sum() > 0 else 0,
        }
    except (IndexError, KeyError) as e:
        logger.warning(f"Could not generate summary from non-empty DataFrame, returning empty. Error: {e}")
        return _create_empty_summary()

    return summary


def _create_empty_summary() -> Dict[str, Any]:
    """Helper to generate a zeroed-out summary block."""
    return {
        ENGINE_TO_API_MAP[PortfolioColumns.BEGIN_MV]: 0.0,
        ENGINE_TO_API_MAP[PortfolioColumns.END_MV]: 0.0,
        ENGINE_TO_API_MAP[PortfolioColumns.FINAL_CUM_ROR]: 0.0,
        ENGINE_TO_API_MAP[PortfolioColumns.BOD_CF]: 0.0,
        ENGINE_TO_API_MAP[PortfolioColumns.EOD_CF]: 0.0,
        ENGINE_TO_API_MAP[PortfolioColumns.MGMT_FEES]: 0.0,
        ENGINE_TO_API_MAP[PortfolioColumns.NIP]: 0,
        ENGINE_TO_API_MAP[PortfolioColumns.PERF_RESET]: 0,
        ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_1]: 0,
        ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_2]: 0,
        ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_3]: 0,
        ENGINE_TO_API_MAP[PortfolioColumns.NCTRL_4]: 0,
    }


def format_summary_for_response(summary_data: Dict[str, Any], config: EngineConfig) -> SummaryPerformance:
    """Formats the summary dictionary into the Pydantic response model."""
    summary_data["report_start_date"] = config.report_start_date
    summary_data["report_end_date"] = config.report_end_date
    return SummaryPerformance.model_validate(summary_data)