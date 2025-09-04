# Portfolio Performance Analytics API (V2 Engine)

An API for calculating portfolio performance metrics based on daily time-series financial data, powered by a high-performance, vectorized Python engine.

---

## Key Features

-   **High Performance:** Core calculations are fully vectorized using Pandas and NumPy, delivering a **~49x speedup** over traditional iterative methods on large datasets.
-   **Decoupled Architecture:** The calculation engine is a standalone library with zero dependencies on the API framework, allowing it to be used in other applications (e.g., batch jobs, research).
-   **Dual Precision Modes:**
    -   `FLOAT64` (default): For maximum speed.
    -   `DECIMAL_STRICT`: For auditable, high-precision calculations.
-   **Test Driven:** Behavior is locked in by a comprehensive suite of characterization, integration, and unit tests.

---

## Project Structure

The project is separated into three distinct layers:

-   `app/`: The FastAPI application layer. Handles HTTP requests/responses and API-specific models.
-   `adapters/`: A translation layer that maps data between the API and the engine.
-   `engine/`: The pure, standalone calculation library. It has no knowledge of the API.
-   `tests/`: Contains all tests, separated into `integration`, `unit`, and `benchmarks`.

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
    -   **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## Testing & Validation

The project has a comprehensive test suite.

1.  **Run all tests (Unit & Integration):**
    ```bash
    pytest -q
    ```

2.  **Run Performance Benchmarks:**
    This test compares the new vectorized engine against the original iterative engine on a large (~500k row) dataset.
    ```bash
    pytest --benchmark-only "tests/benchmarks/"
    ```
    The output will show the mean execution time for `test_vectorized_engine_performance`. A lower time is better.

---

## Example API Usage

You can use `curl` from Git Bash to test the endpoint. The `sampleInput.json` file provides a standard payload.

```bash
curl -X POST "[http://127.0.0.1:8000/calculate_performance](http://127.0.0.1:8000/calculate_performance)" \
-H "Content-Type: application/json" \
-d @sampleInput.json