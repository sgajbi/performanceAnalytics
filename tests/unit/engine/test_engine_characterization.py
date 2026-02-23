# tests/unit/engine/test_engine_characterization.py
import pandas as pd
import pytest

from engine.compute import run_calculations
from tests.unit.engine.characterization_data import (
    cumulative_return_scenario,  # Add new import
    eod_flip_gross_scenario,
    eod_flip_net_scenario,
    long_flip_scenario,
    multi_currency_scenario,
    short_flip_scenario,
    short_growth_scenario,
    standard_growth_scenario,
    zero_value_nip_scenario,
)


@pytest.mark.parametrize(
    "scenario_func, scenario_name",
    [
        (long_flip_scenario, "long_flip"),
        (short_flip_scenario, "short_flip"),
        (zero_value_nip_scenario, "zero_value_nip"),
        (standard_growth_scenario, "standard_growth"),
        (short_growth_scenario, "short_growth"),
        (eod_flip_net_scenario, "eod_flip_net"),
        (eod_flip_gross_scenario, "eod_flip_gross"),
        (multi_currency_scenario, "multi_currency"),
        (cumulative_return_scenario, "cumulative_return"),  # Add new scenario
    ],
    ids=[
        "long_flip",
        "short_flip",
        "zero_value_nip",
        "standard_growth",
        "short_growth",
        "eod_flip_net",
        "eod_flip_gross",
        "multi_currency",
        "cumulative_return",  # Add new scenario ID
    ],
)
def test_engine_characterization_scenarios(scenario_func, scenario_name):
    """
    Characterization test for various scenarios, tied directly to the engine.
    """
    # 1. Arrange
    engine_config, input_df, expected_df = scenario_func()

    # 2. Act
    result_df, _ = run_calculations(input_df, engine_config)

    # 3. Assert
    output_columns = [col for col in expected_df.columns if col in result_df.columns]
    actual_df = result_df[output_columns].reset_index(drop=True)

    pd.testing.assert_frame_equal(
        actual_df,
        expected_df[output_columns].reset_index(drop=True),
        check_exact=False,
        atol=1e-4,
    )
