# tests/benchmarks/test_engine_performance.py
from datetime import date

import pytest

from adapters.api_adapter import create_engine_config, create_engine_dataframe
from app.models.requests import PerformanceRequest
from engine.compute import run_calculations


@pytest.fixture(scope="module")
def large_input_data():
    """Creates a large, realistic dataset for benchmarking per the RFC."""
    base_payload = {
        "portfolio_number": "BENCHMARK_PORT_01",
        "performance_start_date": "2023-12-31",
        "metric_basis": "NET",
        "analyses": [{"period": "YTD", "frequencies": ["daily"]}],
        "rounding_precision": 4,
    }
    original_daily_data = [
        {"day": 1, "perf_date": "2024-01-01", "begin_mv": 100000.0, "end_mv": 101000.0},
        {"day": 2, "perf_date": "2024-01-02", "begin_mv": 101000.0, "end_mv": 102500.0},
        {
            "day": 3,
            "perf_date": "2024-01-03",
            "begin_mv": 102500.0,
            "bod_cf": 5000.0,
            "mgmt_fees": -10.0,
            "end_mv": 108000.0,
        },
    ]
    extended_daily_data = []
    num_replications = 167000  # Aim for ~500k rows
    for i in range(num_replications):
        for idx, entry in enumerate(original_daily_data):
            new_entry = entry.copy()
            day_offset = (i * len(original_daily_data)) + idx + 1
            new_entry["day"] = day_offset
            extended_daily_data.append(new_entry)

    base_payload["valuation_points"] = extended_daily_data
    base_payload["report_end_date"] = original_daily_data[-1]["perf_date"]

    return base_payload


def test_vectorized_engine_performance(benchmark, large_input_data):
    """Benchmarks the new, high-performance vectorized engine (V2)."""
    pydantic_request = PerformanceRequest.model_validate(large_input_data)

    effective_start_date = date.fromisoformat(large_input_data["valuation_points"][0]["perf_date"])
    effective_end_date = date.fromisoformat(large_input_data["report_end_date"])

    engine_config = create_engine_config(pydantic_request, effective_start_date, effective_end_date)
    valuation_points_list = [item.model_dump() for item in pydantic_request.valuation_points]
    engine_df = create_engine_dataframe(valuation_points_list)

    def run():
        run_calculations(engine_df.copy(), engine_config)

    benchmark.group = "Engine Performance (500k rows)"
    benchmark(run)
