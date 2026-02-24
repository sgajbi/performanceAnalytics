# RFC-0002: PA Coverage Hardening Wave 2

- Status: Implemented
- Authors: Codex
- Date: 2026-02-24

## Context

Wave 1 lifted PA coverage and stabilized key API paths, but combined coverage remained below the platform target and key branch behavior was still untested in the performance and engine layers.

## Problem

- Combined PA coverage was below the 99% platform objective.
- Several edge branches in core/engine and performance API flows were not validated.
- Coverage quality needed to remain meaningful (behavioral and failure-path focused), not assertion inflation.

## Decision

Implement Wave 2 test hardening focused on:

- Endpoint negative paths and passthrough behavior in `/performance/twr`, `/performance/mwr`, and `/performance/twr/pas-input`.
- Service and core edge cases (`lineage_service`, period resolution guards).
- Engine branch coverage for attribution, contribution, breakdown, compute reset reasoning, policies, periods fallback, MWR solver failures, and Decimal sign behavior.

## Scope

- Test-only changes plus lint/format cleanup required by CI.
- No functional production logic changes to analytics computations.

## Validation

- `python -m pytest -q` passes.
- `python -m pytest --cov=app --cov=engine --cov=core --cov=adapters --cov-report=term-missing -q` reports:
  - Total: `99%` (2269 statements, 22 missed).
  - Full coverage for `engine/*` and `core/*` modules in scope.
  - Remaining misses concentrated in selected `performance.py` branches.

## Risks and Trade-offs

- Larger test surface increases execution time marginally.
- Some private-function branch tests increase coupling to internals; accepted for deterministic branch coverage and early regression detection.

## Follow-ups

- Wave 3 can target remaining `app/api/endpoints/performance.py` branches (currently 91%) and improve e2e bucket balance under the test pyramid policy.
