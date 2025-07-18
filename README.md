# Portfolio Performance Analytics API

An API for calculating portfolio performance metrics based on daily time-series financial data.

## Project Structure

The project follows a modular FastAPI application structure:
- `main.py`: The main entry point for the FastAPI application.
- `app/`: Contains the core application logic.
    - `api/endpoints/`: Defines the API routes and their handlers (e.g., `performance.py`).
    - `core/`: Houses core configurations and utilities (e.g., `config.py` for settings).
    - `models/`: Contains Pydantic models for request and response data validation (e.g., `requests.py`, `responses.py`).
    - `services/`: Implements the business logic, such as the `PortfolioPerformanceCalculator` (e.g., `calculator.py`).
- `tests/`: Contains unit and integration tests.
- `pyproject.toml`: Manages project dependencies and metadata using Poetry.
- `sampleInput.json`: An example JSON payload for testing the API.

## Setup and Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sgajbi/performanceAnalytics

    ```


2.  **Install Poetry (if you haven't already):**
    ```bash
    pip install poetry
    ```

3.  **Install project dependencies:**
    Navigate to the project root directory and run:
    ```bash
    poetry install
    ```

4.  **Activate the Poetry shell (optional, but recommended):**
    This will activate the virtual environment created by Poetry.
    ```bash
    poetry shell
    ```

## Running the Application

Once dependencies are installed and you are in the project root directory (and optionally, in the Poetry shell):

1.  **Run the FastAPI application with Uvicorn:**
    ```bash
    uvicorn main:app --reload
    ```
    The `--reload` flag enables auto-reloading upon code changes, which is useful during development.

2.  **Access the API Documentation:**
    Once the server is running, open your web browser and go to:
    -   **Swagger UI**: `http://127.0.0.1:8000/docs`
    -   **ReDoc**: `http://127.0.0.1:8000/redoc`

    You can test the `/calculate_performance` endpoint directly from the Swagger UI.

## Testing

Tests are located in the `tests/` directory.

1.  **Run tests using Pytest:**
    Ensure you are in the Poetry shell (`poetry shell`) or activate it, then run:
    ```bash
    pytest
    ```
    To run specific tests or see more verbose output, refer to Pytest documentation.

## Example API Usage

You can use `sampleInput.json` to test the `/calculate_performance` endpoint.

Using `curl` from your Git Bash:

```bash
curl -X POST "[http://127.0.0.1:8000/calculate_performance](http://127.0.0.1:8000/calculate_performance)" \
-H "Content-Type: application/json" \
-d @sampleInput.json