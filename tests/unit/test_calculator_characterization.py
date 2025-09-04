# tests/unit/test_calculator_characterization.py
import json
from pathlib import Path

import pandas as pd
import pytest
from adapters.api_adapter import (
    create_engine_config,
    create_engine_dataframe,
    format_engine_output,
    format_summary_for_response,
)
from app.models.requests import PerformanceRequest
from engine.compute import run_calculations


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


def run_engine_for_test(input_data: dict) -> (list, dict):
    """Helper function to run the full engine and adapter pipeline for a test case."""
    # Use Pydantic to parse the request, which handles date conversion etc.
    pydantic_request = PerformanceRequest.model_validate(input_data)
    engine_config = create_engine_config(pydantic_request)
    daily_data_list = [
        item.model_dump(by_alias=True) for item in pydantic_request.daily_data
    ]
    engine_df = create_engine_dataframe(daily_data_list)

    # Run the calculation
    results_df = run_calculations(engine_df, engine_config)

    # Format the output
    daily_performance, summary_data = format_engine_output(results_df, engine_config)
    summary_performance = format_summary_for_response(summary_data, engine_config)

    # Convert Pydantic model back to dict for comparison
    return daily_performance, summary_performance.model_dump(by_alias=True)


@pytest.mark.parametrize(
    "input_file, expected_output_file",
    [
        (
            "../../sampleInputShort.json",
            "expected_short_position_output.json",
        ),
        (
            "../../sampleInputLongFlip.json",
            "expected_long_flip_output.json",
        ),
        (
            "../../sampleInputZeroValueTest.json",
            "expected_zero_value_output.json",
        ),
        (
            "../../sampleInputStandardGrowth.json",
            "expected_standard_growth_output.json",
        ),
        (
            "../../sampleInputShortGrowth.json",
            "expected_short_growth_output.json",
        ),
        (
            "../../sampleInputEodFlip.json",
            "expected_eod_flip_net_output.json",
        ),
    ],
)
def test_characterization_scenarios(input_file, expected_output_file):
    """
    Characterization tests to lock in the correct behavior for various scenarios.
    This test now uses the new engine/adapter architecture.
    """
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / input_file)
    expected_output = load_json_from_file(base_path / expected_output_file)

    # Run the engine
    actual_daily, actual_summary = run_engine_for_test(input_data)

    # Assert
    expected_daily = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily) == len(
        expected_daily
    ), f"Mismatch in number of rows for {input_file}"
    for i, actual_row in enumerate(actual_daily):
        expected_row = expected_daily[i]
        for key in expected_row:
            if isinstance(expected_row[key], float):
                assert actual_row[key] == pytest.approx(
                    expected_row[key]
                ), f"Mismatch in row {i} for key '{key}' in {input_file}"
            else:
                assert (
                    actual_row[key] == expected_row[key]
                ), f"Mismatch in row {i} for key '{key}' in {input_file}"

    for key in expected_summary:
        if isinstance(expected_summary[key], float):
            assert actual_summary[key] == pytest.approx(
                expected_summary[key]
            ), f"Mismatch in summary for key '{key}' in {input_file}"
        else:
            # Handle date string comparison
            if "date" in key and actual_summary[key]:
                assert (
                    str(actual_summary[key]) == expected_summary[key]
                ), f"Mismatch in summary for key '{key}' in {input_file}"
            elif "date" not in key:
                assert (
                    actual_summary[key] == expected_summary[key]
                ), f"Mismatch in summary for key '{key}' in {input_file}"


def test_eod_flip_gross_scenario():
    """Characterization test for GROSS returns in an EOD flip scenario."""
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputEodFlip.json")
    expected_output = load_json_from_file(
        base_path / "expected_eod_flip_gross_output.json"
    )

    # Override metric basis for this specific test
    input_data["metric_basis"] = "GROSS"

    # Run the engine
    actual_daily, actual_summary = run_engine_for_test(input_data)

    # Assert
    expected_daily = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily) == len(expected_daily)
    for i, actual_row in enumerate(actual_daily):
        expected_row = expected_daily[i]
        for key in expected_row:
            if isinstance(expected_row[key], (float, int)) and not isinstance(
                expected_row[key], bool
            ):
                assert actual_row[key] == pytest.approx(
                    expected_row[key]
                ), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], (float, int)) and not isinstance(
            expected_summary[key], bool
        ):
            assert actual_summary[key] == pytest.approx(
                expected_summary[key]
            ), f"Mismatch in summary for key '{key}'"
        else:
            if "date" in key and actual_summary[key]:
                assert str(actual_summary[key]) == expected_summary[key]
            elif "date" not in key:
                assert actual_summary[key] == expected_summary[key]