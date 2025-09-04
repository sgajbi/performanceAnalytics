# tests/unit/engine/test_engine_characterization.py
import pandas as pd
from engine.compute import run_calculations
from tests.unit.engine.characterization_data import long_flip_scenario


def test_long_flip_scenario():
    """
    Characterization test for the long flip scenario, tied directly to the engine.
    """
    # 1. Arrange
    engine_config, input_df, expected_df = long_flip_scenario()

    # 2. Act
    result_df = run_calculations(input_df, engine_config)

    # 3. Assert
    # Select only the columns we want to compare from the result
    output_columns = expected_df.columns
    actual_df = result_df[output_columns].reset_index(drop=True)

    # Use pandas testing utility to compare DataFrames
    pd.testing.assert_frame_equal(
        actual_df,
        expected_df.reset_index(drop=True),
        check_exact=False,
        atol=1e-9,  # Set a tolerance for floating point comparisons
    )