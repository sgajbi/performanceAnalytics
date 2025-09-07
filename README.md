# Portfolio Performance Analytics API (V3 Engine)

An API for calculating portfolio performance metrics, aligned with the `portfolio-analytics-system`. It provides three primary services:
1.  **Performance Calculation**: Endpoints for calculating **Time-Weighted Return (TWR)** with frequency-based breakdowns and **Money-Weighted Return (MWR)**.
2.  **Contribution Analysis**: An endpoint for calculating **Position Contribution** to explain the drivers of portfolio performance. Supports both single-level and multi-level hierarchical breakdowns.
3.  **Attribution Analysis**: An endpoint for calculating single-level, multi-period **Performance Attribution** (Brinson-style) to explain a portfolio's active return against a benchmark.
---

## Key Features

-   **High-Performance TWR Engine:** Core daily calculations are vectorized using Pandas and NumPy.
-   **Flexible TWR Breakdowns:** Aggregate daily performance into monthly, quarterly, or yearly summaries.
-   **Standard MWR Calculation:** Provides a money-weighted return for analyzing investor performance.
-   **Advanced Contribution Engine:** Uses the Carino smoothing algorithm to accurately link multi-period position contributions. Supports multi-level hierarchical aggregation (e.g., by sector, then by security).
-   **Brinson Attribution Engine:** Decomposes active return into Allocation, Selection, and Interaction effects using Brinson-Fachler or Brinson-Hood-Beebower models.
-   **Geometric Attribution Linking:** Uses the Menchero algorithm to ensure multi-period attribution effects correctly account for compounding.
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
    source .venv/Scripts/activate
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

1.  **Run all tests (Unit & Integration):**
    ```bash
    pytest -q
    ```

2.  **Run Performance Benchmarks:**
    ```bash
    pytest --benchmark-only "tests/benchmarks/"
    ```

---

## API Usage Examples

### 1. Time-Weighted Return (TWR)

-   **Endpoint:** `POST /performance/twr`
-   **Example `curl` command:**
    ```bash
    curl -X POST "[http://127.0.0.1:8000/performance/twr](http://127.0.0.1:8000/performance/twr)" \
    -H "Content-Type: application/json" \
    -d @sampleInput.json
    ```

### 2. Money-Weighted Return (MWR)

-   **Endpoint:** `POST /performance/mwr`
-   **Example Payload:** See `tests/integration/test_mwr_api.py`.

### 3. Position Contribution

-   **Endpoint:** `POST /performance/contribution`
-   **Description:** Decomposes the portfolio's TWR into the contributions from its individual positions. Can be run at a single level or as a multi-level hierarchy (e.g., by sector).
-   **Example Payload:** See `tests/integration/test_contribution_api.py`.

### 4. Performance Attribution

-   **Endpoint:** `POST /performance/attribution`
-   **Description:** Decomposes the portfolio's active return against a benchmark into allocation, selection, and interaction effects.
-   **Example Payload:** See `tests/integration/test_attribution_api.py`.

---

## Advanced Usage

The core calculation logic is a standalone library. For instructions on how to use it directly in your own Python scripts for batch processing or analysis, see the guide:

-   **[Using the Performance Engine as a Standalone Library](./docs/guides/standalone_engine_usage.md)**