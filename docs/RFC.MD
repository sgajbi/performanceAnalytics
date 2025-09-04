Of course. Based on the provided source code and the draft RFC, here is the final, implementable RFC for hardening and accelerating the performance engine.

-----

# RFC: Performance Engine V2 - Vectorization & Architectural Refactor

**Status:** Final
**Author:** Senior Architect
**Date:** 2025-09-04

## 1\. Executive Summary

This document outlines the final specification for refactoring the Portfolio Performance Analytics engine. The current implementation, while functionally correct and validated by a strong characterization test suite, suffers from significant performance limitations and architectural tight coupling.

The V2 initiative will re-architect the core calculator into a **decoupled, high-performance, standalone library** while **guaranteeing bit-for-bit identical output** to the current version. This will be achieved primarily by replacing slow, iterative row-wise calculations with vectorized NumPy/Pandas operations. The project prioritizes correctness, scalability, and maintainability.

### Primary Goals

1.  **Preserve Correctness:** The new engine, in its default mode, must produce outputs identical to the existing implementation, passing all current characterization tests without modification. These tests represent the engine's behavioral contract.
2.  **Achieve Massive Performance Gains:** Target a **\>20x speedup** on large datasets (100,000+ rows) by eliminating iterative loops in favor of vectorized computation.
3.  **Improve Maintainability & Reusability:** Decouple the core engine from the FastAPI application, enforce clean data contracts, and organize business logic into pure, testable functions. The engine must be usable as a standalone Python library.
4.  **Enhance Robustness:** Formalize and centralize complex business rules (NIP, NCTRL flags, resets) and introduce a configurable, high-precision calculation mode for compliance and auditing.

-----

## 2\. Current State Analysis

The existing engine successfully computes a range of performance metrics. However, several architectural and implementation issues prevent it from scaling and being easily maintained.

  * **Performance Bottleneck:** The core logic in `app/services/calculator.py` is built around a `for` loop that iterates through a Pandas DataFrame, using `.at[]` for cell-by-cell updates. This is an anti-pattern in Pandas and is the primary source of performance degradation.
  * **Architectural Coupling:** The calculation logic is tightly integrated with the FastAPI framework. It directly uses configuration and data models from the `app/` directory, making it impossible to reuse in other contexts (e.g., a batch analytics job, a different API framework).
  * **Maintainability Issues:** A single, 500+ line `calculate_performance` method contains scattered and complex business logic for resets, control flags, and sign evolution. This makes debugging and enhancement difficult.
  * **Inconsistent Data Contracts:** Internal DataFrame columns use inconsistent naming conventions (e.g., `"Perf. Date"`, `"daily ror %"`), which complicates code clarity and serialization.
  * **Inflexible Precision:** The mandatory use of Python's `Decimal` type throughout the calculation path provides high precision but severely impacts performance, even when such precision is only strictly necessary for final outputs.

-----

## 3\. Design Principles

The V2 engine will be built on the following principles:

  * **Separation of Concerns:** The system will be layered: an API layer for transport, an Adapter layer for data mapping, and a pure Engine layer for computation. The Engine will have no knowledge of the API.
  * **Functional & Immutable Core:** The Engine will consist of pure functions. DataFrames will be treated as immutable inputs, and each step of the calculation will produce a new DataFrame or Series, avoiding in-place modifications and side effects.
  * **Vectorization First:** All calculations will be vectorized using NumPy and Pandas idioms by default. Iterative loops are to be avoided entirely.
  * **Clear Data Contracts:** The Engine will operate exclusively on a well-defined internal schema using `snake_case` naming. The Adapter layer will be responsible for mapping to and from external (API) contracts.
  * **Configurable Execution:** The engine's behavior (e.g., precision mode, rule versions) will be controlled by a simple, explicit configuration object, not global state.

-----

## 4\. Target Architecture

The project will be restructured to reflect a clear separation of concerns.

```plaintext
└── sgajbi-performanceanalytics/
    ├── app/                # FastAPI application layer
    │   ├── api/
    │   │   └── endpoints/
    │   │       └── performance.py  # Handles HTTP req/res, calls Adapters
    │   └── core/
    │       ├── config.py       # API-level settings
    │       └── ...
    ├── adapters/           # Data transformation and mapping layer
    │   ├── api_adapter.py  # Maps API requests/aliases to internal schema and back
    │   └── summary.py      # Generates the summary block from engine output
    └── engine/             # Standalone, pure calculation engine
        ├── schema.py       # Defines internal column names (Enum) and data types
        ├── config.py       # Engine-specific config (PrecisionMode, FeatureFlags)
        ├── periods.py      # Vectorized logic for calculating period start dates
        ├── rules.py        # Pure functions for business rules (NIP, NCTRL, PerfReset)
        ├── ror.py          # Pure functions for daily RoR and cumulative compounding
        └── compute.py      # Main orchestrator function for the performance calculation pipeline
    └── tests/
        ├── integration/    # API-level tests
        └── unit/
            ├── engine/     # Granular unit tests for every function in the engine
            └── adapters/   # Unit tests for the adapter/mapping logic
```

-----

## 5\. Data Contracts

### 5.1 Internal Engine Schema

All calculations within the `engine/` module will use the following standardized `snake_case` column names. This is the **single source of truth** for the core logic.

  * **Inputs:** `perf_date`, `begin_mv`, `bod_cf`, `eod_cf`, `mgmt_fees`, `end_mv`
  * **Calculated:** `sign`, `daily_ror`, `nip`, `perf_reset`, `long_short`
  * **Control Flags:** `nctrl_1`, `nctrl_2`, `nctrl_3`, `nctrl_4`
  * **Cumulative Returns:** `temp_long_cum_ror`, `temp_short_cum_ror`, `long_cum_ror`, `short_cum_ror`, `final_cum_ror`

### 5.2 API Data Contract

The `api_adapter.py` module is responsible for mapping the user-facing request/response format to the internal schema. The API contract will remain unchanged to ensure backward compatibility.

  * **Example Mapping:** `perf_date` \<-\> `"Perf. Date"`, `final_cum_ror` \<-\> `"Final Cumulative ROR %"`

-----

## 6\. Core Algorithms & Implementation

The iterative loop will be replaced with a sequence of vectorized operations orchestrated by `engine/compute.py`.

### 6.1 Period Scoping (`engine/periods.py`)

A vector `effective_period_start_date` will be computed for all rows simultaneously based on the `period_type` config. This vector will be used as a mask or boundary for subsequent calculations.

### 6.2 Daily RoR (`engine/ror.py`)

The daily rate of return will be calculated in a single vectorized operation.

```python
# Psuedocode
numerator = df.end_mv - df.begin_mv - df.bod_cf - df.eod_cf
if metric_basis == 'NET':
    numerator += df.mgmt_fees

denominator = (df.begin_mv + df.bod_cf).abs()

# Safely compute RoR, defaulting to 0 where denominator is zero or date is out of period
is_safe = (denominator != 0) & (df.perf_date >= df.effective_period_start_date)
df['daily_ror'] = np.where(is_safe, numerator / denominator, 0.0)
```

### 6.3 NIP & Control Rules (`engine/rules.py`)

Each business rule will be a pure function that accepts DataFrame columns (as NumPy arrays or Pandas Series) and returns a boolean mask or integer Series.

  * **NIP Rule:** The existing logic will be preserved as `nip_v1_rule`. A clearer, proposed rule (`bmv + bod_cf == 0 & emv + eod_cf == 0`) will be implemented as `nip_v2_rule` and controlled by a feature flag.
  * **NCTRL Rules:** Each of the four NCTRL conditions will be implemented as a separate, clearly named function.
  * **Performance Reset Rule:** This will be a simple logical OR of the NCTRL masks: `reset_mask = nctrl_1_mask | nctrl_2_mask | ...`

### 6.4 Cumulative Returns (`engine/ror.py`)

This is the most critical performance enhancement. The row-by-row compounding will be replaced by a `groupby().cumprod()` approach.

1.  **Identify Calculation Blocks:** Create a "block ID" for each row by calculating the cumulative sum of period start changes and performance resets. All rows with the same block ID will be compounded together.
2.  **Vectorized Compounding:**
    ```python
    # Psuedocode
    df['block_id'] = (df.is_period_start | df.perf_reset).cumsum()

    # Calculate growth factor (1 + R)
    df['long_growth_factor'] = np.where(df.sign == 1, 1 + df.daily_ror, 1)

    # Group by block and compound
    grouped = df.groupby('block_id')['long_growth_factor']
    df['long_cum_ror'] = (grouped.cumprod() - 1)
    ```
3.  **Final Linking:** The final cumulative return will be a simple vectorized operation: `(1 + long_cum_ror) * (1 + short_cum_ror) - 1`.

-----

## 7\. Configuration & Execution Modes

An `engine/config.py` module will define a configuration object.

  * `PrecisionMode`: An Enum with values `FLOAT64` (default) and `DECIMAL_STRICT`.
      * `FLOAT64`: All intermediate calculations are done using `np.float64` for maximum speed. Final outputs are rounded to a standard number of decimal places.
      * `DECIMAL_STRICT`: All calculations use Python's `Decimal` type. This will be slower but provides auditable, arbitrary precision.
  * `FeatureFlags`: A simple dataclass to control features like `use_nip_v2_rule: bool = False`.

-----

## 8\. Testing & Validation Strategy

The existing test suite is the foundation of this refactor's success.

1.  **Characterization Tests:** All existing tests in `tests/unit/test_calculator_characterization.py` must be moved to test the new engine orchestrator and **must pass without modification** in the default `FLOAT64` mode.
2.  **Unit Tests:** New, isolated unit tests must be written for every individual function in `engine/rules.py`, `engine/ror.py`, and `engine/periods.py`.
3.  **Performance Benchmarks:** A new benchmark test file will be created. It will generate a large (500k rows) synthetic dataset and assert that the new engine's execution time is at least **20 times faster** than the old implementation.
4.  **Dual-Mode Precision Tests:** Tests will be added to run key calculations in both `FLOAT64` and `DECIMAL_STRICT` modes, asserting that the float-based results are equal to the decimal-based results within a tight tolerance (e.g., `1e-9`).

-----

## 9\. Implementation Plan

The project will be executed in phases to manage risk and ensure correctness at each step.

  * **Phase 1: Foundational Refactor**

    1.  Create the new `engine/` and `adapters/` directory structures.
    2.  Define the `engine/schema.py` and `engine/config.py` files.
    3.  Move the existing logic from `calculator.py` into the `engine/compute.py` and other modules *without* vectorizing it yet. The goal is to get the old logic working within the new structure.
    4.  All tests should still pass.

  * **Phase 2: Vectorization**

    1.  Systematically replace the iterative logic for Daily RoR, Cumulative Returns, and other rules with the vectorized implementations described in Section 6.
    2.  After each major component is vectorized, run the full test suite and performance benchmarks to validate correctness and measure speedup.

  * **Phase 3: Finalization & Enhancement**

    1.  Implement the `PrecisionMode` logic to allow switching between `FLOAT64` and `DECIMAL_STRICT` execution paths.
    2.  Implement the `nip_v2_rule` behind a feature flag.
    3.  Clean up the API layer (`performance.py`) to be a thin wrapper around the adapter and engine.

-----

## 10\. Acceptance Criteria

The V2 engine refactor will be considered complete when the following criteria are met:

1.  All existing characterization tests pass against the new engine in its default configuration.
2.  The performance benchmark test passes, demonstrating a speedup of **\>20x** over the original implementation on a 500k-row dataset.
3.  Unit test coverage for the `engine/` module is above 95%.
4.  The `engine` module is fully decoupled and can be imported and run in a separate Python script without any dependencies on `app/` or `fastapi`.
5.  A new `docs/` directory is created containing markdown documentation covering:
      * The V2 architecture and data flow.
      * The internal engine schema.
      * Instructions on how to use the engine as a standalone library.
6.  This RFC is formally approved by project stakeholders via a pull request review **before** the first line of code for Phase 1 is merged.