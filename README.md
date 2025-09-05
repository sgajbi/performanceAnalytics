# Portfolio Performance Analytics API (V3 Engine)

An API for calculating portfolio performance metrics, aligned with the `portfolio-analytics-system`.

It provides two primary services:
1.  **Performance Calculation**: Endpoints for calculating **Time-Weighted Return (TWR)** with frequency-based breakdowns and **Money-Weighted Return (MWR)**.
2.  **Contribution Analysis**: An endpoint for calculating **Position Contribution** to explain the drivers of portfolio performance.

---

## Key Features

-   **High-Performance TWR Engine:** Core daily calculations are vectorized using Pandas and NumPy.
-   **Flexible TWR Breakdowns:** Aggregate daily performance into monthly, quarterly, or yearly summaries.
-   **Standard MWR Calculation:** Provides a money-weighted return for analyzing investor performance.
-   **Advanced Contribution Engine:** Uses the Carino smoothing algorithm to accurately link multi-period position contributions.
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
-   **Description:** Calculates daily performance and aggregates the results into requested frequencies.
-   **Example `curl` command:**
    ```bash
    curl -X POST "[http://127.0.0.1:8000/performance/twr](http://127.0.0.1:8000/performance/twr)" \
    -H "Content-Type: application/json" \
    -d @sampleInput.json
    ```

### 2. Money-Weighted Return (MWR)

-   **Endpoint:** `POST /performance/mwr`
-   **Description:** Calculates a single return figure for the entire period based on market values and cash flows.
-   **Example `curl` command:**
    ```bash
    curl -X POST "[http://127.0.0.1:8000/performance/mwr](http://127.0.0.1:8000/performance/mwr)" \
    -H "Content-Type: application/json" \
    -d '{
      "portfolio_number": "MWR_TEST_01",
      "beginning_mv": 100000.0,
      "ending_mv": 115000.0,
      "cash_flows": [
        {"amount": 10000.0, "date": "2025-03-15"}
      ]
    }'
    ```

### 3. Position Contribution

-   **Endpoint:** `POST /performance/contribution`
-   **Description:** Decomposes the portfolio's TWR into the contributions from its individual positions.
-   **Example `curl` command:**
    ```bash
    # (Requires a more detailed JSON payload with both portfolio and position data)
    echo "See tests/integration/test_contribution_api.py for a sample payload."
    ```