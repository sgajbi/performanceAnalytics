# RFC 025: Reproducibility & Drill-Down Framework (Final)

**Status:** Final (For Approval)
**Owner:** Senior Architect
**Reviewers:** Perf Engine, Platform, Support
**Related:** All core analytics endpoints and RFC-024 (Robustness)

## 1\. Executive Summary

This document specifies the final design for a new, platform-wide **Reproducibility & Drill-Down Framework**. To be considered enterprise-grade, our analytics must be transparent, auditable, and perfectly reproducible. This framework introduces the foundational components to achieve this, addressing the core needs of clients, auditors, and internal support teams.

The two main features are:

1.  A **Deterministic Calculation Hash**: A unique, verifiable fingerprint (`calculation_hash`) will be included in every API response. This hash is a pure function of all inputs, settings, and the engine version, providing an immutable link between a request and its result.
2.  **Standardized Drill-Down Endpoints**: A new set of secure, debug-focused endpoints (e.g., `/performance/_debug/inputs`, `/performance/_debug/weights`) will be created. These endpoints will allow users with the appropriate permissions to inspect the exact intermediate data used in any calculation, from aligned inputs to daily weights and numerators.

This framework moves our service beyond being a "black box" calculator to a transparent and trustworthy analytical engine.

## 2\. Goals & Non-Goals

### Goals

  * Ensure all calculations are deterministic and can be exactly reproduced.
  * Introduce a `calculation_hash` in all API responses for audit and caching purposes.
  * Provide a standardized set of secure, read-only drill-down endpoints to inspect intermediate calculation steps.
  * Implement privacy-aware controls for redacting sensitive identifiers in drill-down outputs.

### Non-Goals

  * The service will remain stateless; this framework will not introduce any server-side storage of calculation results or bundles.
  * The drill-down endpoints are for debugging and transparency, not for primary data retrieval.

## 3\. Methodology

The framework is built on the principle of deterministic canonicalization.

### 3.1. Canonicalization & Hashing

To guarantee that the same logical request always produces the same result and hash, all inputs are first converted into a canonical string format before hashing.

  * **Canonicalization Rules**: A strict set of rules is applied to the request payload, including sorting all keys, normalizing timestamps to UTC, standardizing number formats, and handling `null` values consistently.
  * **Calculation Hash**: The final hash is calculated as `sha256(canonical_json(request) + engine_version)`. Including the engine version ensures that if the underlying logic changes, the hash also changes, preventing false matches between versions.

### 3.2. Drill-Down

The drill-down endpoints re-run the calculation using the provided request payload but, instead of returning the final summary, they expose a specific intermediate DataFrame or data structure. This ensures that the drill-down data is always perfectly consistent with the original calculation.

## 4\. API Design

### 4.1. Request & Response Additions

The shared envelope will be extended.

  * **Request**: An optional `debug` block to control the level of detail and redaction.
  * **Response**: The `meta` block will now include the `calculation_hash` and `input_fingerprint`.

<!-- end list -->

```json
// Request Addition
{
  "debug": { "level": "OFF", "redact": { "instrument_ids": true } }
}

// Response Addition
{
  "meta": {
    "calculation_id": "uuid-v7...",
    "calculation_hash": "sha256:5a2c...",
    "input_fingerprint": "sha256:b3e1...",
    "engine_version": "0.4.1"
  }
}
```

### 4.2. Drill-Down Endpoints

A new set of endpoints will provide access to intermediate data. Access will require an elevated permission scope.

  * `POST /performance/_debug/inputs`: Returns the fully aligned and cleaned time series data used by the engine.
  * `POST /performance/_debug/twrDenoms`: For a TWR calculation, returns the daily numerators, denominators, and resulting returns.
  * `POST /performance/_debug/weights`: For a Contribution calculation, returns the daily weights used for each position.
  * `POST /performance/_debug/attribEffects`: For an Attribution calculation, returns the period-by-period A/S/I effects.

### 4.3. HTTP Semantics & Errors

  * **200 OK**: Successful retrieval of debug data.
  * **400 Bad Request**: Invalid request that would also fail on the main endpoint.
  * **403 Forbidden**: User lacks the required `analytics.debug` scope.
  * **404 Not Found**: The requested debug artifact (e.g., `attribEffects` for a TWR request) does not exist for this calculation type.

## 5\. Architecture & Implementation Plan

1.  **Create Canonicalization Module**:
      * Develop a new utility in `core/repro.py` that takes a Pydantic model and produces a canonical JSON string according to the defined rules.
2.  **Integrate Hashing**:
      * In the API endpoint layer, after validating a request, call the canonicalization utility to generate the `calculation_hash` and include it in the `meta` block of the response.
3.  **Implement Drill-Down Endpoints**:
      * Create a new router at `app/api/endpoints/debug.py`.
      * For each drill-down endpoint, re-use the main engine orchestrator but add a hook to intercept and return the specific intermediate DataFrame requested.
4.  **Phased Rollout**:
      * **Phase 1**: Implement the hashing mechanism for all endpoints.
      * **Phase 2**: Implement the `/performance/_debug/inputs` and `/performance/_debug/twrDenoms` endpoints.
      * **Phase 3**: Implement the remaining debug endpoints for Contribution and Attribution.

## 6\. Testing & Validation Strategy

  * **Unit Tests**: The new `core/repro.py` module must have **100% test coverage**, with tests to ensure the canonicalization is order-invariant and handles all data types correctly.
  * **Integration Tests**: API-level tests will be created to:
      * Assert that two identical requests produce the same `calculation_hash`.
      * Assert that a minor change to an input value produces a different `calculation_hash`.
      * Assert that the data from drill-down endpoints is numerically consistent with the final output of the main endpoint.
  * **Property-Based Testing**: Use property-based tests to confirm that shuffling the order of elements in input arrays (e.g., `daily_data`, `positions_data`) does not change the final `calculation_hash`.
  * **Overall Coverage**: Overall project test coverage must remain at or above **95%**.

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  All four primary analytics endpoints include the `calculation_hash` and other `meta` fields in their responses.
3.  The hashing logic is proven to be deterministic and order-invariant.
4.  All specified `/performance/_debug/*` endpoints are implemented, secure, and return data consistent with the main calculations.
5.  The testing and validation strategy is fully implemented, all tests are passing, and the required coverage targets are met.
6.  New documentation is added to `docs/technical/` explaining the reproducibility framework and how to use the drill-down endpoints.