# tests/benchmarks/test_engine_performance.py
import json
from pathlib import Path

import pandas as pd
import pytest
from app.models.requests import PerformanceRequest
from adapters.api_adapter import (
    create_engine_config,
    create_engine_dataframe,
)
from engine.compute import run_calculations


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def large_input_data():
    """
    Creates a large, realistic dataset for benchmarking by extending a sample file.
    Scope is 'module' to avoid regenerating the data for each benchmark function.
    """
    base_path = Path(__file__).parent.parent.parent
    input_data = load_json_from_file(base_path / "sampleInputlong.json")
    
    original_daily_data = input_data["daily_data"]
    extended_daily_data = []
    
    num_replications = 70
    
    for i in range(num_replications):
        for entry in original_daily_data:
            new_entry = entry.copy()
            day_offset = i * len(original_daily_data)
            date_offset = pd.to_timedelta(day_offset, unit='d')
            new_date = pd.to_datetime(entry["Perf. Date"]) + date_offset
            
            new_entry["Day"] = entry["Day"] + day_offset
            new_entry["Perf. Date"] = new_date.strftime('%Y-%m-%d')
            extended_daily_data.append(new_entry)
            
    input_data["daily_data"] = extended_daily_data
    input_data["report_start_date"] = extended_daily_data[0]["Perf. Date"]
    input_data["report_end_date"] = extended_daily_data[-1]["Perf. Date"]
    
    return input_data


def test_baseline_engine_performance(benchmark, large_input_data):
    """
    Benchmarks the V1 engine (refactored architecture but still iterative).
    This provides the baseline against which V2 vectorization will be measured.
    """
    pydantic_request = PerformanceRequest.model_validate(large_input_data)
    engine_config = create_engine_config(pydantic_request)
    daily_data_list = [
        item.model_dump(by_alias=True) for item in pydantic_request.daily_data
    ]
    engine_df = create_engine_dataframe(daily_data_list)

    # The function to benchmark
    def run():
        run_calculations(engine_df.copy(), engine_config)

    benchmark.group = "Engine Performance"
    benchmark(run)