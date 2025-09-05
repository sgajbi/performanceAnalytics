# Using the Performance Engine as a Standalone Library

One of the primary goals of the V2 engine refactor was to decouple the core calculation logic from the FastAPI web application. This allows the `engine` module to be used as a standalone Python library in other contexts, such as batch processing jobs, data analysis scripts, or Jupyter notebooks.

This guide provides a practical example of how to use it.

---

## Example Usage

The following script demonstrates the complete end-to-end flow: preparing data, configuring the engine, running calculations, and inspecting the results.

### 1. Full Python Script

```python
# standalone_example.py
from datetime import date
import pandas as pd

# 1. Import necessary components from the engine
from engine.config import EngineConfig
from engine.compute import run_calculations
from engine.schema import PortfolioColumns
from common.enums import PeriodType

def main():
    """
    Runs a standalone performance calculation.
    """
    print("--- Preparing Input Data ---")
    
    # 2. Prepare input data as a Pandas DataFrame
    # Note: The engine expects snake_case column names as defined in `engine.schema.PortfolioColumns`
    input_data = [
        {
            PortfolioColumns.PERF_DATE: date(2025, 1, 1),
            PortfolioColumns.BEGIN_MV: 100000.0,
            PortfolioColumns.END_MV: 101000.0,
            PortfolioColumns.BOD_CF: 0.0,
            PortfolioColumns.EOD_CF: 0.0,
            PortfolioColumns.MGMT_FEES: 0.0,
        },
        {
            PortfolioColumns.PERF_DATE: date(2025, 1, 2),
            PortfolioColumns.BEGIN_MV: 101000.0,
            PortfolioColumns.END_MV: 103000.0,
            PortfolioColumns.BOD_CF: 1000.0,
            PortfolioColumns.EOD_CF: 0.0,
            PortfolioColumns.MGMT_FEES: -15.0,
        },
    ]
    input_df = pd.DataFrame(input_data)
    print("Input DataFrame:\n", input_df.head())
    
    print("\n--- Configuring the Engine ---")
    
    # 3. Create an EngineConfig object to control the calculation
    engine_config = EngineConfig(
        performance_start_date=date(2024, 12, 31),
        report_end_date=date(2025, 1, 2),
        metric_basis="NET",
        period_type=PeriodType.YTD,
    )
    print("Engine Config:", engine_config)

    print("\n--- Running Calculations ---")
    
    # 4. Run the calculation by passing the DataFrame and config
    results_df = run_calculations(input_df, engine_config)
    
    print("\n--- Calculation Results ---")
    
    # 5. The result is a new DataFrame with all calculated columns
    print("Output DataFrame:\n", results_df.head())
    
    # You can now access any calculated column directly
    final_returns = results_df[[PortfolioColumns.PERF_DATE, PortfolioColumns.FINAL_CUM_ROR]]
    print("\nFinal Cumulative Returns:\n", final_returns)


if __name__ == "__main__":
    main()

````

### 2\. How to Run the Example

1.  Save the code above as `standalone_example.py` in the root of the project directory.
2.  Ensure your virtual environment is activated (`source .venv/Scripts/activate`).
3.  Run the script from your terminal:
    ```bash
    python standalone_example.py
    ```

This demonstrates how any Python process can leverage the high-performance, vectorized engine completely independently of the API.