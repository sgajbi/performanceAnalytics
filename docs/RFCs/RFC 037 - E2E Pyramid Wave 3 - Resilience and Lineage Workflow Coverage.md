# RFC 037 - E2E Pyramid Wave 3 - Resilience and Lineage Workflow Coverage

## Problem Statement
lotus-performance meets the 99% coverage gate but remains below the platform E2E test-pyramid target (5-10% of total tests), leaving cross-endpoint workflow and resilience paths under-validated.

## Root Cause
Most recent lotus-performance test expansion focused on unit and integration layers. End-to-end coverage did not scale at the same pace, especially for failure passthrough and lineage-backed workflow verification.

## Proposed Solution
Add a focused wave of lotus-performance E2E tests that validate:
1. lotus-core-ref workflow success and upstream failure passthrough.
2. Position analytics upstream payload validation behavior.
3. Contribution, attribution, and MWR lineage retrieval workflows.
4. Capability toggle behavior and workbench analytics response quality.

## Architectural Impact
No API contract or runtime behavior changes. This change increases confidence in lotus-performance's public contracts and integration-facing behavior under realistic workflows.

## Risks and Trade-offs
- Slightly longer E2E runtime in CI.
- Additional test maintenance as contracts evolve.

## High-Level Implementation Approach
1. Add 8 E2E tests in `tests/e2e/test_workflow_journeys.py` targeting high-value user-facing and upstream-facing flows.
2. Keep assertions behavior-focused (status, contract shape, lineage availability, passthrough semantics).
3. Run lotus-performance E2E suite and full coverage gate to verify threshold and pyramid movement.
