import json
from pathlib import Path

import pytest
from app.services.calculator import PortfolioPerformanceCalculator


def load_json_from_file(file_path: Path):
    """Helper function to load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


def test_short_position_flip_scenario():
    """
    Characterization test to lock in the correct behavior for a scenario
    where a short position flips to a long position.
    """
    # 1. Arrange
    # Load the input data and the expected "golden" output
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputShort.json")
    expected_output = load_json_from_file(base_path / "expected_short_position_output.json")

    # Prepare the config and daily data for the calculator
    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": input_data["metric_basis"],
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]

    # Instantiate the calculator
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    # Run the calculations
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    # Compare the actual results against the golden file
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    # Assert daily performance results row by row and field by field
    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            # Use pytest.approx for floating point numbers
            if isinstance(expected_row[key], float):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    # Assert summary performance results field by field
    for key in expected_summary:
        if isinstance(expected_summary[key], float):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"