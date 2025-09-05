
# Portfolio Performance Analytics API (V3 Engine)

An API for calculating portfolio performance metrics, aligned with the `portfolio-analytics-system`.

It provides two primary endpoints for calculating **Time-Weighted Return (TWR)** with frequency-based breakdowns and **Money-Weighted Return (MWR)**.

---

## Key Features

-   **High-Performance TWR Engine:** Core daily calculations are vectorized using Pandas and NumPy for maximum speed.
-   **Flexible TWR Breakdowns:** Aggregate daily performance into monthly, quarterly, or yearly summaries.
-   **MWR Endpoint:** Calculate a period's money-weighted return, ideal for analyzing investor performance.
-   **Decoupled Architecture:** The calculation engine is a standalone library that can be used independently of the API.
-   **Dual Precision Modes:** Supports fast `float64` (default) or auditable `Decimal` calculations.

---

## Project Structure

-   `app/`: The FastAPI application layer.
-   `common/`: Shared enumerations (`Frequency`, `PeriodType`) used across the project.
-   `adapters/`: A translation layer that maps data between the API and the engine.
-   `engine/`: The pure, standalone calculation library.
-   `tests/`: The complete test suite.

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

This endpoint calculates daily performance and aggregates the results into the requested frequencies.

-   **Endpoint:** `POST /performance/twr`
-   **Payload:** Use `sampleInput.json` as a template. You can specify which breakdowns you want in the `frequencies` array (`"daily"`, `"monthly"`, `"quarterly"`, `"yearly"`).

**Example `curl` command:**
```bash
curl -X POST "[http://127.0.0.1:8000/performance/twr](http://127.0.0.1:8000/performance/twr)" \
-H "Content-Type: application/json" \
-d @sampleInput.json
````

### 2\. Money-Weighted Return (MWR)

This endpoint calculates a single return figure for the entire period based on market values and cash flows.

  - **Endpoint:** `POST /performance/mwr`
  - **Payload:** Requires `beginning_mv`, `ending_mv`, and a list of `cash_flows`.

**Example `curl` command:**

```bash
curl -X POST "[http://127.0.0.1:8000/performance/mwr](http://127.0.0.1:8000/performance/mwr)" \
-H "Content-Type: application/json" \
-d '{
  "portfolio_number": "MWR_TEST_01",
  "beginning_mv": 100000.0,
  "ending_mv": 115000.0,
  "cash_flows": [
    {"amount": 10000.0, "date": "2025-03-15"},
    {"amount": -5000.0, "date": "2025-09-20"}
  ]
}'
```
