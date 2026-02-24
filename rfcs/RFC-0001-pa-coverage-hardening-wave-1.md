# RFC-0001: PA Coverage Hardening Wave 1

## Status

Proposed

## Date

2026-02-24

## Problem Statement

`performanceAnalytics` was below target meaningful coverage and had concentrated gaps in PAS integration adapter paths, observability helpers, and endpoint negative-path validation.

## Decision

Deliver an incremental hardening wave focused on highest-risk uncovered backend behavior without changing functional contracts.

## Scope

- Add unit tests for `PasSnapshotService` request/response contract behavior and fallback payload parsing.
- Add unit tests for observability helpers (correlation/request/trace resolution and propagation header generation).
- Add integration tests for:
  - analytics upstream failure passthrough
  - workbench analytics security-group branch
  - contribution edge paths (no resolved periods, empty period slice)
  - PAS-input TWR negative paths (missing performance start, invalid valuation shape, missing period results)

## Result

- Full test suite: `209 passed`
- Coverage improved from ~`95%` to `97%`
- `app/services/pas_snapshot_service.py`: now `100%`
- `app/observability.py`: now `100%`
- `app/api/endpoints/analytics.py`: now `100%`
- `app/api/endpoints/contribution.py`: now `100%`

## Follow-up

Wave 2 will target remaining concentrated misses in:
- `app/api/endpoints/performance.py`
- `app/services/lineage_service.py`
