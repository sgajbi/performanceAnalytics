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
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputShort.json")
    expected_output = load_json_from_file(base_path / "expected_short_position_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": input_data["metric_basis"],
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], float):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], float):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"


def test_long_position_reset_scenario():
    """
    Characterization test to lock in the correct behavior for a scenario
    where a long position's loss exceeds -100%, triggering a performance reset.
    """
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputLongFlip.json")
    expected_output = load_json_from_file(base_path / "expected_long_flip_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": input_data["metric_basis"],
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], float):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], float):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"


def test_zero_value_nip_scenario():
    """
    Characterization test for a scenario involving zero-value days, a full
    withdrawal, and a No Investment Period (NIP) day.
    """
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputZeroValueTest.json")
    expected_output = load_json_from_file(base_path / "expected_zero_value_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": input_data["metric_basis"],
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], float):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], float):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"


def test_standard_growth_scenario():
    """
    Characterization test for a standard scenario involving growth, a small dip,
    and a cash flow injection.
    """
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputStandardGrowth.json")
    expected_output = load_json_from_file(base_path / "expected_standard_growth_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": input_data["metric_basis"],
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], (float, int)) and not isinstance(expected_row[key], bool):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], (float, int)) and not isinstance(expected_summary[key], bool):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"


def test_short_growth_custom_formula_scenario():
    """
    Characterization test for a short position scenario using the custom
    compounding formula.
    """
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputShortGrowth.json")
    expected_output = load_json_from_file(base_path / "expected_short_growth_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": input_data["metric_basis"],
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], (float, int)) and not isinstance(expected_row[key], bool):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], (float, int)) and not isinstance(expected_summary[key], bool):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"


def test_eod_flip_net_scenario():
    """Characterization test for NET returns in an EOD flip scenario."""
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputEodFlip.json")
    expected_output = load_json_from_file(base_path / "expected_eod_flip_net_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": "NET",  # Explicitly testing NET
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], (float, int)) and not isinstance(expected_row[key], bool):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], (float, int)) and not isinstance(expected_summary[key], bool):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"


def test_eod_flip_gross_scenario():
    """Characterization test for GROSS returns in an EOD flip scenario."""
    # 1. Arrange
    base_path = Path(__file__).parent
    input_data = load_json_from_file(base_path / "../../sampleInputEodFlip.json")
    expected_output = load_json_from_file(base_path / "expected_eod_flip_gross_output.json")

    calculator_config = {
        "portfolio_number": input_data["portfolio_number"],
        "performance_start_date": input_data["performance_start_date"],
        "metric_basis": "GROSS",  # Explicitly testing GROSS
        "report_start_date": input_data["report_start_date"],
        "report_end_date": input_data["report_end_date"],
        "period_type": input_data["period_type"],
    }
    daily_data_list = input_data["daily_data"]
    calculator = PortfolioPerformanceCalculator(config=calculator_config)

    # 2. Act
    actual_daily_performance = calculator.calculate_performance(daily_data_list, calculator_config)
    actual_summary = calculator.get_summary_performance(actual_daily_performance)

    # 3. Assert
    expected_daily_performance = expected_output["calculated_daily_performance"]
    expected_summary = expected_output["summary_performance"]

    assert len(actual_daily_performance) == len(expected_daily_performance)
    for i, actual_row in enumerate(actual_daily_performance):
        expected_row = expected_daily_performance[i]
        for key in expected_row:
            if isinstance(expected_row[key], (float, int)) and not isinstance(expected_row[key], bool):
                assert actual_row[key] == pytest.approx(expected_row[key]), f"Mismatch in row {i} for key '{key}'"
            else:
                assert actual_row[key] == expected_row[key], f"Mismatch in row {i} for key '{key}'"

    for key in expected_summary:
        if isinstance(expected_summary[key], (float, int)) and not isinstance(expected_summary[key], bool):
            assert actual_summary[key] == pytest.approx(expected_summary[key]), f"Mismatch in summary for key '{key}'"
        else:
            assert actual_summary[key] == expected_summary[key], f"Mismatch in summary for key '{key}'"