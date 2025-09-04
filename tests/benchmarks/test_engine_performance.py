# tests/benchmarks/test_engine_performance.py
import json
from pathlib import Path

import pandas as pd
import pytest
from adapters.api_adapter import create_engine_config, create_engine_dataframe
from app.models.requests import PerformanceRequest
from engine.compute import run_calculations
from tests.benchmarks.legacy_calculator import LegacyPortfolioPerformanceCalculator


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def large_input_data():
    """Creates a large, realistic dataset for benchmarking."""
    base_path = Path(__file__).parent.parent.parent
    input_data = load_json_from_file(base_path / "sampleInputlong.json")
    original_daily_data = input_data["daily_data"]
    extended_daily_data = []
    num_replications = 70
    for i in range(num_replications):
        for entry in original_daily_data:
            new_entry = entry.copy()
            day_offset = i * len(original_daily_data)
            date_offset = pd.to_timedelta(day_offset, unit="d")
            new_date = pd.to_datetime(entry["Perf. Date"]) + date_offset
            new_entry["Day"] = entry["Day"] + day_offset
            new_entry["Perf. Date"] = new_date.strftime("%Y-%m-%d")
            extended_daily_data.append(new_entry)
    input_data["daily_data"] = extended_daily_data
    input_data["report_start_date"] = extended_daily_data[0]["Perf. Date"]
    input_data["report_end_date"] = extended_daily_data[-1]["Perf. Date"]
    return input_data


def test_vectorized_engine_performance(benchmark, large_input_data):
    """Benchmarks the new, high-performance vectorized engine (V2)."""
    pydantic_request = PerformanceRequest.model_validate(large_input_data)
    engine_config = create_engine_config(pydantic_request)
    daily_data_list = [item.model_dump(by_alias=True) for item in pydantic_request.daily_data]
    engine_df = create_engine_dataframe(daily_data_list)

    def run():
        run_calculations(engine_df.copy(), engine_config)

    benchmark.group = "Engine Performance Comparison"
    benchmark(run)


def test_legacy_engine_performance(benchmark, large_input_data):
    """Benchmarks the old, slow, iterative engine (V1)."""
    config = {
        "portfolio_number": large_input_data["portfolio_number"],
        "performance_start_date": large_input_data["performance_start_date"],
        "metric_basis": large_input_data["metric_basis"],
        "report_start_date": large_input_data["report_start_date"],
        "report_end_date": large_input_data["report_end_date"],
        "period_type": large_input_data["period_type"],
    }
    daily_data_list = large_input_data["daily_data"]
    calculator = LegacyPortfolioPerformanceCalculator(config=config)

    def run():
        calculator.calculate_performance(daily_data_list, config)

    benchmark.group = "Engine Performance Comparison"
    benchmark(run)