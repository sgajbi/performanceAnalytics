# Durability and Consistency Standard (PA)

- Standard reference: `pbwm-platform-docs/Durability and Consistency Standard.md`
- Scope: advanced analytics with PAS-sourced canonical inputs and stateless request mode.
- Change control: RFC required for rule changes; ADR required for temporary deviations.

## Workflow Consistency Classification

- Strong consistency:
  - deterministic analytics output for same canonical input + same `as_of_date`
  - reproducibility metadata in analytics responses
- Eventual consistency:
  - external PAS data refresh cadence prior to analysis request execution

## Idempotency and Write Semantics

- PA primary APIs are analytical compute endpoints and are read-only with no core persistent business writes.
- PA does not mutate PAS core records.
- Any future write endpoint must implement `Idempotency-Key` and replay-safe dedupe rules.
- Evidence:
  - `app/api/endpoints/performance.py`
  - `app/api/endpoints/analytics.py`

## Atomicity Boundaries

- Each analytics request computes within request-local deterministic context.
- Failures return explicit error responses; partial persisted side effects are not allowed.
- Evidence:
  - `core/envelope.py`
  - `core/repro.py`

## As-Of and Reproducibility Semantics

- `as_of_date` is required in canonical request models.
- Responses include engine/config metadata for deterministic replay.
- Evidence:
  - `app/models/*requests.py`
  - `app/api/endpoints/integration_capabilities.py`
  - `core/repro.py`

## Concurrency and Conflict Policy

- No hidden mutable shared state in core analytics execution paths.
- Deterministic canonical hashing is used for reproducibility evidence.
- Evidence:
  - `core/repro.py`
  - `tests/unit/core/test_repro.py`

## Integrity Constraints

- Input schema validation and deterministic envelope normalization prevent malformed data processing.
- Evidence:
  - `app/models/*`
  - `core/envelope.py`

## Release-Gate Tests

- Unit: `tests/unit/*`
- Integration: `tests/integration/*`
- E2E: `tests/e2e/*`

## Deviations

- Any write-side mutation introduced in PA without idempotency/atomic controls requires ADR with expiry review date.
