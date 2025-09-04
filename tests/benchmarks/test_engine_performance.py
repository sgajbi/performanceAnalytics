# tests/benchmarks/test_engine_performance.py
import json
from pathlib import Path

import pandas as pd
import pytest
from adapters.api_adapter import create_engine_config, create_engine_dataframe
from app.models.requests import PerformanceRequest
from engine.compute import run_calculations


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def large_input_data():
    """Creates a large, realistic dataset for benchmarking per the RFC."""
    base_path = Path(__file__).parent.parent.parent
    input_data = load_json_from_file(base_path / "sampleInputlong.json")
    original_daily_data = input_data["daily_data"]
    extended_daily_data = []
    num_replications = 3300
    for i in range(num_replications):
        for idx, entry in enumerate(original_daily_data):
            new_entry = entry.copy()
            day_offset = (i * len(original_daily_data)) + idx + 1
            new_entry["Day"] = day_offset
            extended_daily_data.append(new_entry)

    input_data["daily_data"] = extended_daily_data
    input_data["report_start_date"] = original_daily_data[0]["Perf. Date"]
    input_data["report_end_date"] = original_daily_data[-1]["Perf. Date"]
    
    input_data["rounding_precision"] = 4
    # Add new required field to the benchmark data
    input_data["frequencies"] = ["daily", "monthly", "yearly"]

    return input_data


def test_vectorized_engine_performance(benchmark, large_input_data):
    """Benchmarks the new, high-performance vectorized engine (V2)."""
    pydantic_request = PerformanceRequest.model_validate(large_input_data)
    engine_config = create_engine_config(pydantic_request)
    daily_data_list = [item.model_dump(by_alias=True) for item in pydantic_request.daily_data]
    engine_df = create_engine_dataframe(daily_data_list)

    def run():
        run_calculations(engine_df.copy(), engine_config)

    benchmark.group = "Engine Performance (500k rows)"
    benchmark(run)