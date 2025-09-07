Here is the final, implementable RFC. It has been updated to remove all citations and ensure full alignment with the Gold-Standard Implementation Guidelines.

***

# RFC-028: Unified `snake_case` API Naming & Legacy Alias Removal

**Status:** Final (Approved for Implementation)
**Owner:** Senior Architect
**Reviewers:** Platform, Performance Engine Team
**Related:** RFC-014 (Cross-Cutting Consistency)

## 1. Executive Summary

This document specifies the final plan to standardize the entire public API contract of the `performanceAnalytics` service to a strict `snake_case` naming convention. The current API supports a mix of legacy, Title-Cased names (e.g., `"Perf. Date"`, `"Begin Market Value"`) and modern `snake_case` names through a series of adapters and compatibility flags. This approach has introduced significant technical debt, increased the complexity of models and tests, and created an inconsistent developer experience.

This initiative will **remove all legacy aliases and compatibility flags**, enforcing `snake_case` for all request and response fields across the TWR, MWR, Contribution, and Attribution endpoints. This change simplifies the codebase, clarifies the API contract, eliminates a class of potential bugs, and aligns our service with modern API design standards, enabling better automated documentation and client generation. The core calculation engine's logic and numerical output will remain **unchanged**, a guarantee enforced by our existing characterization test suite.

---

## 2. Motivation & Rationale

The current hybrid naming convention is a significant source of friction and technical debt. By addressing it, we adhere to the project's principles of delivering definitive fixes, not workarounds, and maintaining a gold-standard engine.

* **Increased Complexity:** The codebase is burdened with mapping dictionaries (`API_TO_ENGINE_MAP`), model field aliases, and conditional logic (`compat_legacy_names`) that exist solely to translate between naming styles. This removal of redundant code directly improves maintainability and readability.
* **Inconsistent Developer Experience:** API consumers face a confusing mix of conventions. For example, the TWR endpoint accepts `"Begin Market Value"`, while the Attribution endpoint accepts a `groupBy` alias for `group_by`. This inconsistency violates the principle of least surprise and complicates client-side implementation.
* **Blocks Tooling:** A clean, consistent, and alias-free API contract is a prerequisite for generating high-quality OpenAPI/Swagger documentation, and by extension, reliable client SDKs. The current state hinders our ability to automate these processes effectively.
* **Redundant Tests & Docs:** We must document and test both naming conventions, doubling the effort in many cases. Sample payloads like `sampleInput.json` use legacy names that are out of step with our target architecture.

By removing this ambiguity, we will create a more robust, maintainable, and professional API that is easier for both internal teams and external clients to consume.

---

## 3. Target API Contract (Canonical Schema)

The public API contract will be standardized to the following `snake_case` format. All legacy names will be removed.

### 3.1 Common Daily Data Row

This structure will be used for all time-series inputs (TWR, Contribution, Attribution).

| Field | Type | Description |
| :--- | :--- | :--- |
| `day` | integer | Sequential day number within the request. |
| `perf_date` | string (date) | The observation date in YYYY-MM-DD format. |
| `begin_mv` | float | The market value at the beginning of the day. |
| `bod_cf` | float | Cash flow occurring at the beginning of the day. |
| `eod_cf` | float | Cash flow occurring at the end of the day. |
| `mgmt_fees` | float | Management fees for the day. |
| `end_mv` | float | The market value at the end of the day. |

### 3.2 Endpoint-Specific Changes

* **MWR (`/performance/mwr`):** The request body will use `begin_mv` and `end_mv` instead of `beginning_mv` and `ending_mv`.
* **Attribution (`/performance/attribution`):** The request body will only accept `group_by`. The `groupBy` alias will be removed.
* **Responses:** All response bodies will exclusively use `snake_case` keys (e.g., `period_return_pct`, `final_cumulative_ror`, `money_weighted_return`).

### 3.3 Legacy to New Mapping

| Legacy Name | New `snake_case` Name |
| :--- | :--- |
| `Day` | `day` |
| `Perf. Date` | `perf_date` |
| `Begin Market Value` | `begin_mv` |
| `End Market Value` | `end_mv` |
| `BOD Cashflow` | `bod_cf` |
| `Eod Cashflow` | `eod_cf` |
| `Mgmt fees` | `mgmt_fees` |
| `Final Cumulative ROR %` | `final_cum_ror` |
| `beginning_mv` (MWR) | `begin_mv` |
| `ending_mv` (MWR) | `end_mv` |
| `groupBy` (Attribution) | `group_by` |

---

## 4. Scope of Changes

This refactor is primarily focused on the API contract layer and will not alter the core logic within the `engine`.

1.  **Pydantic Models (`app/models/`):**
    * Remove all `Field(alias=...)` arguments from request models like `DailyInputData` and `AttributionRequest`.
    * Rename fields directly (e.g., `beginning_mv` to `begin_mv` in `MoneyWeightedReturnRequest`).
    * Enforce strict schema validation by setting `ConfigDict(extra='forbid')` to reject any unknown (i.e., legacy) fields.
2.  **Adapters (`adapters/`):**
    * In `api_adapter.py`, remove all uses of `API_TO_ENGINE_MAP` and `ENGINE_TO_API_MAP` for renaming columns.
    * Remove the `compat_legacy_names` flag and its associated logic.
3.  **Engine Schema (`engine/schema.py`):**
    * Delete the `API_TO_ENGINE_MAP` and `ENGINE_TO_API_MAP` dictionaries. The `PortfolioColumns` enum will remain the internal source of truth.
4.  **Constants (`app/core/constants.py`):**
    * Delete all legacy string constants (e.g., `PERF_DATE_FIELD`, `BEGIN_MARKET_VALUE_FIELD`).
5.  **Tests & Sample Payloads:**
    * Update all test fixtures and API call payloads (e.g., in `tests/integration/`) to use the new `snake_case` contract.
    * Delete all legacy sample JSON files (`sampleInput.json`, `samplepayload.json`, etc.).
6.  **Documentation (`docs/`, `README.md`):**
    * Update all API references, examples, and guides to reflect the `snake_case`-only contract.

---

## 5. Testing & Validation Strategy

The primary risk of this change is accidentally altering the engine's behavior. The testing strategy is designed to prevent this while ensuring the API contract is strictly enforced.

* **Characterization Testing:** The existing characterization test suite is the cornerstone of this refactor. All test scenarios will be updated to use `snake_case` payloads. The numerical outputs of the `run_calculations` engine function must remain **identical** to the pre-refactor golden results, ensuring no business logic has been changed.
* **Schema Enforcement:** All integration tests will be validated to ensure that requests using legacy field names now correctly fail with an HTTP `422 Unprocessable Entity` error.
* **CI Validation:** A new CI job will be introduced to parse all sample JSON payloads used in documentation and validate them against the Pydantic request models. This ensures our examples can never drift out of sync with the implementation.
* **Test Coverage:** Test coverage for the `engine` module must remain at **100%**, and overall project coverage must be **≥95%**, as per existing project standards.

---

## 6. Acceptance Criteria

This RFC will be considered fully implemented when the following criteria are met:

1.  All Pydantic request and response models across the four primary endpoints (`twr`, `mwr`, `contribution`, `attribution`) have been updated to exclusively use `snake_case` naming, with legacy aliases removed.
2.  The `adapters` and `engine/schema.py` modules have been simplified by removing all mapping dictionaries and compatibility flags.
3.  All existing tests, especially the characterization suite, pass with `snake_case` payloads, producing numerically identical results to the pre-refactor baseline.
4.  New integration tests are added to confirm that requests using legacy names are rejected with a `422` status code.
5.  All documentation, including the `README.md`, `docs/guides/api_reference.md`, and all sample payloads, has been updated to reflect the `snake_case`-only API contract.
6.  A comprehensive OpenAPI 3.1 specification is generated and published, reflecting the finalized, clean API contract with detailed descriptions and examples for all attributes and endpoints.