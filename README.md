
# Portfolio Performance Analytics API (V3 Engine)

An API for calculating portfolio performance metrics, aligned with the `portfolio-analytics-system`. It provides three primary services:
1.  **Performance Calculation**: Endpoints for calculating **Time-Weighted Return (TWR)** with frequency-based breakdowns and **Money-Weighted Return (MWR)**.
2.  **Contribution Analysis**: An endpoint for calculating **Position Contribution** to explain the drivers of portfolio performance. Supports both single-level and multi-level hierarchical breakdowns.
3.  **Attribution Analysis**: An endpoint for calculating single-level, multi-period **Performance Attribution** (Brinson-style) to explain a portfolio's active return against a benchmark.
---

## Key Features

-   **High-Performance TWR Engine:** Core daily calculations are vectorized using Pandas and NumPy.
-   **Multi-Period Analysis:** Request multiple time horizons (e.g., MTD, YTD, 1Y) in a single, efficient API call.
-   **Flexible TWR Breakdowns:** Aggregate daily performance into monthly, quarterly, or yearly summaries.
-   **Standard MWR Calculation:** Provides a money-weighted return for analyzing investor performance.
-   **Advanced Contribution Engine:** Uses the Carino smoothing algorithm to accurately link multi-period position contributions. Supports multi-level hierarchical aggregation (e.g., by sector, then by security).
-   **Brinson Attribution Engine:** Decomposes active return into Allocation, Selection, and Interaction effects using Brinson-Fachler or Brinson-Hood-Beebower models.
-   **Geometric Attribution Linking:** Uses the Menchero algorithm to ensure multi-period attribution effects correctly account for compounding.
-   **Multi-Currency Performance & Hedging**: Decomposes returns into local, FX, and base currency components. Supports modeling of currency hedging strategies. See the [Multi-Currency Guide](docs/guides/multi_currency.md).
-   **Karnosky-Singer Currency Attribution**: Decomposes active return into local market vs. currency management effects.
-   **Decoupled Architecture:** All calculation logic is in a standalone `engine` library.
---

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/sgajbi/performanceAnalytics](https://github.com/sgajbi/performanceAnalytics)
    cd performanceAnalytics
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

---

## Running the Application

1.  **Run the FastAPI app with Uvicorn:**
    ```bash
    uvicorn main:app --reload
    ```

2.  **Access API Documentation:**
    -   **Swagger UI**: `http://127.0.0.1:8000/docs`

---

## Testing & Validation

### 1. Run All Tests

To run the full suite of unit and integration tests, use the following command:
```bash
pytest -q
````

### 2\. Run Performance Benchmarks

To run only the performance benchmarks, which test the engine's speed on large datasets:

```bash
pytest --benchmark-only "tests/benchmarks/"
```

### 3\. Check Test Coverage

This project enforces high standards for test coverage to ensure correctness and maintainability. The goals are **100% coverage for the `engine` module** and **\>95% for the overall project**. To run the tests and generate a detailed coverage report, use the `pytest-cov` plugin:

```bash
pytest --cov=engine --cov=app --cov-report term-missing
```

  - `--cov=engine --cov=app`: Specifies the directories to measure coverage against.
  - `--cov-report term-missing`: Prints a summary to the terminal, including which lines are not covered by tests.

-----

## API Usage Examples

### 1\. Time-Weighted Return (TWR)

  - **Endpoint:** `POST /performance/twr`
  - **Description:** Calculates TWR for multiple periods (e.g., MTD and YTD) in a single request.
  - **Example `curl` command:**
    ```bash
    curl -X POST "[http://127.0.0.1:8000/performance/twr](http://127.0.0.1:8000/performance/twr)" \
    -H "Content-Type: application/json" \
    -d '{
      "portfolio_number": "MULTI_PERIOD_01",
      "performance_start_date": "2024-12-31",
      "as_of": "2025-02-28",
      "metric_basis": "NET",
      "periods": ["MTD", "YTD"],
      "frequencies": ["monthly"],
      "daily_data": [
        { "day": 1, "perf_date": "2025-01-15", "begin_mv": 100000, "end_mv": 102000 },
        { "day": 2, "perf_date": "2025-02-15", "begin_mv": 102000, "end_mv": 105060 }
      ]
    }'
    ```

### 2\. Money-Weighted Return (MWR)

  - **Endpoint:** `POST /performance/mwr`
  - **Example Payload:** See `docs/examples/mwr_request.json`.

### 3\. Position Contribution

  - **Endpoint:** `POST /performance/contribution`
  - **Description:** Decomposes the portfolio's TWR into the contributions from its individual positions. Can be run at a single level or as a multi-level hierarchy (e.g., by sector).
  - **Example Payload:** See `docs/examples/contribution_request.json`.

### 4\. Performance Attribution

  - **Endpoint:** `POST /performance/attribution`
  - **Description:** Decomposes the portfolio's active return against a benchmark into allocation, selection, and interaction effects.
  - **Example Payload:** See `docs/examples/attribution_request.json`.

-----

## Advanced Usage

The core calculation logic is a standalone library. For instructions on how to use it directly in your own Python scripts for batch processing or analysis, see the guide:

  - **[Using the Performance Engine as a Standalone Library](https://www.google.com/search?q=docs/guides/standalone_engine_usage.md)**

<!-- end list -->

