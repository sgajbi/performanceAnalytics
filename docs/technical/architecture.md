# Engine Architecture & API Structure

The performanceAnalytics system is designed with a clean separation of concerns, split into distinct layers to ensure testability, reusability, and maintainability.

1.  **API Layer (`app/`)**
    -   Implemented in FastAPI and located in `app/api/endpoints/`.
    -   Handles all incoming HTTP requests and validates their structure using Pydantic models defined in `app/models/`.
    -   Orchestrates the calls to the adapter and engine layers.
    -   Wraps the final engine results with the shared response envelope containing `Meta`, `Diagnostics`, and `Audit` blocks before sending the JSON response.

2.  **Adapters Layer (`adapters/`)**
    -   Serves as the translation layer between the public-facing API contract and the internal engine's data structures.
    -   Converts API request objects into an `EngineConfig` object and a Pandas DataFrame that the engine can process.
    -   Formats the raw DataFrames and dictionaries returned by the engine back into the Pydantic response models expected by the API.

3.  **Engine Layer (`engine/`)**
    -   A standalone library containing all core calculation logic, with no dependencies on the API framework.
    -   All computations are vectorized using Pandas and NumPy for high performance.
    -   Core modules include:
        -   `engine/compute.py`: The main orchestrator that runs the TWR calculation pipeline.
        -   `engine/ror.py`: Pure functions for calculating daily and cumulative Time-Weighted Returns.
        -   `engine/mwr.py`: Solvers for calculating Money-Weighted Return (XIRR and Dietz).
        -   `engine/contribution.py`: Logic for Carino smoothing and multi-level hierarchical contribution.
        -   `engine/attribution.py`: Logic for Brinson decomposition and Menchero linking.
        -   `engine/breakdown.py`: Post-processing logic to aggregate daily results into frequencies like monthly, quarterly, etc.
        -   `engine/rules.py`: Pure functions for complex business logic like performance resets (NCTRL flags) and No-Investment-Period (NIP) days.

4.  **Core Utilities (`core/`)**
    -   A top-level directory containing shared, application-agnostic utilities.
    -   `core/envelope.py`: Defines the Pydantic models for the shared request and response structures (`Meta`, `Diagnostics`, `Audit`).
    -   `core/periods.py`: Resolves period definitions (e.g., YTD, ITD, rolling) into concrete start and end dates.
    -   `core/annualize.py`: Provides common helper functions for annualizing returns.
    -   `core/errors.py`: Defines a shared taxonomy of custom API error exceptions.

---

## Data Flow

The data flow for a typical request is executed as follows:

1.  The FastAPI application receives a JSON request at an endpoint (e.g., `POST /performance/twr`).
2.  The raw JSON is validated and parsed into a Pydantic request model (e.g., `PerformanceRequest`).
3.  The `api_adapter` is called, which converts the Pydantic model into an `EngineConfig` object and a snake_case Pandas DataFrame.
4.  The main engine orchestrator (`engine.compute.run_calculations`) is invoked with the config and DataFrame. It executes the entire vectorized calculation pipeline.
5.  The engine returns a results DataFrame and a diagnostics dictionary.
6.  The `api_adapter` formats the results back into the Pydantic response models, including the shared envelope.
7.  The API layer returns the final, serialized JSON response to the client.

This decoupled architecture ensures the core engine is highly reusable and can be run independently in different contexts, such as batch jobs or notebooks.