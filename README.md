# Portfolio Performance Analytics API

An API for calculating portfolio performance metrics based on daily time-series financial data.

## Project Structure

The project follows a modular FastAPI application structure:
- [cite_start]`main.py`: The main entry point for the FastAPI application. [cite: 5]
- [cite_start]`app/`: Contains the core application logic. [cite: 6]
    - [cite_start]`api/endpoints/`: Defines the API routes and their handlers (e.g., `performance.py`). [cite: 6]
    - [cite_start]`core/`: Houses core configurations and utilities (e.g., `config.py` for settings). [cite: 7]
    - [cite_start]`models/`: Contains Pydantic models for request and response data validation (e.g., `requests.py`, `responses.py`). [cite: 8]
    - [cite_start]`services/`: Implements the business logic, such as the `PortfolioPerformanceCalculator` (e.g., `calculator.py`). [cite: 9]
- `tests/`: Contains unit and integration tests.
- `requirements.txt`: Manages project dependencies.
- `sampleInput.json`: An example JSON payload for testing the API.

---

## Setup and Installation

This project uses a standard Python virtual environment to manage dependencies.

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone [https://github.com/sgajbi/performanceAnalytics](https://github.com/sgajbi/performanceAnalytics)
    cd performanceAnalytics
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Create the virtual environment
    python -m venv .venv

    # Activate it (for Git Bash on Windows)
    source .venv/Scripts/activate
    ```

3.  **Install project dependencies:**
    With the virtual environment active, run:
    ```bash
    pip install -r requirements.txt
    ```

---

## Running the Application

Once dependencies are installed and the virtual environment is active:

1.  **Run the FastAPI application with Uvicorn:**
    ```bash
    uvicorn main:app --reload
    ```
    The `--reload` flag enables auto-reloading upon code changes, which is useful during development.

2.  **Access the API Documentation:**
    Once the server is running, open your web browser and go to:
    -   **Swagger UI**: `http://127.0.0.1:8000/docs`
    -   **ReDoc**: `http://127.0.0.1:8000/redoc`

    [cite_start]You can test the `/calculate_performance` endpoint directly from the Swagger UI. [cite: 14]

---

## Testing

[cite_start]Tests are located in the `tests/` directory and are run using `pytest`. [cite: 15]

1.  **Install development dependencies:**
    This includes `pytest` and other testing tools. Ensure your virtual environment is active.
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Run tests using Pytest:**
    From the project root directory, run:
    ```bash
    pytest
    ```

---

## Example API Usage

[cite_start]You can use `sampleInput.json` or `sampleInputShort.json` to test the `/calculate_performance` endpoint. [cite: 16]

[cite_start]Using `curl` from your Git Bash: [cite: 17]
```bash
curl -X POST "[http://127.0.0.1:8000/calculate_performance](http://127.0.0.1:8000/calculate_performance)" \
-H "Content-Type: application/json" \
-d @sampleInput.json