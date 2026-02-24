# RFC-0003 - PA E2E Workflow Coverage Wave 1

## Problem Statement

PA currently has a placeholder-only E2E suite, which underrepresents critical end-to-end API workflows in the test pyramid.

## Root Cause

E2E bucket was bootstrapped with a smoke placeholder and not upgraded to workflow assertions.

## Proposed Solution

Replace placeholder E2E coverage with real API workflow tests that validate:

- service readiness and integration capability contract
- core TWR and MWR performance flows
- contribution and attribution flow with lineage retrieval
- workbench analytics orchestration
- PAS-connected execution mode for TWR and positions analytics

## Architectural Impact

No production code changes. Test-only improvement for governance and reliability.

## Risks and Trade-offs

- Slightly longer test runtime for E2E bucket.
- Must keep payload fixtures concise to preserve fast CI feedback.

## High-Level Implementation

1. Remove placeholder E2E test.
2. Add meaningful workflow-driven E2E tests using `TestClient`.
3. Use controlled monkeypatching for PAS-connected modes where upstream dependency is external.
