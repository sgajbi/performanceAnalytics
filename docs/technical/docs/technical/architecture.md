# Engine Architecture & API Structure

The performanceAnalytics system is split into two main layers:

1. **API Layer (`app/`)**
   - Implemented in FastAPI (`app/api/endpoints/`).
   - Handles request validation using Pydantic models.
   - Routes requests to the appropriate engine function.
   - Wraps results with `Meta`, `Diagnostics`, and `Audit` envelopes.

2. **Engine Layer (`engine/`)**
   - Implements all calculation logic (vectorized Pandas/NumPy).
   - Core modules:
     - `engine.ror` – daily return calculations.
     - `engine.compute` – orchestration of portfolio vs. position runs.
     - `engine.breakdown` – frequency-based rollups (daily, monthly, etc.).
     - `engine.mwr` – internal rate of return solvers.
     - `engine.contribution` – Carino smoothing & multi-level contribution.
     - `engine.attribution` – Brinson decomposition & Menchero linking.

3. **Adapters Layer (`adapters/`)**
   - Translates API request objects to `EngineConfig` and Pandas DataFrames.
   - Formats raw engine results back into Pydantic response objects.

4. **Core Utilities (`core/`)**
   - `periods.py` – resolves explicit, rolling, YTD, ITD windows.
   - `annualize.py` – converts returns to annualized basis.
   - `errors.py` / `exceptions.py` – domain-specific error classes.
   - `envelope.py` – shared request/response envelopes (meta, diagnostics, audit).

---

## Data Flow

1. API receives JSON request.
2. Pydantic validates → adapter converts to `EngineConfig` and DataFrame.
3. Engine executes calculations.
4. Results returned as DataFrame/dict.
5. Adapter formats into response Pydantic models with envelopes.
6. API returns JSON response.

This separation ensures:
- **Testability** – engine can run standalone.
- **Reusability** – same engine usable for APIs, batch jobs, simulations.
- **Scalability** – vectorized operations for large portfolios.
