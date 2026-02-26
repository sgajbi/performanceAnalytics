# RFC 033 - lotus-core Year-History Readiness for lotus-performance and UI

## Status
Proposed

## Date
2026-02-24

## Problem Statement

lotus-performance analytics endpoints are expected to power lotus-gateway/UI workbench and portfolio views, but live integration currently shows unstable readiness:

1. lotus-performance snapshot calls can fail in platform runs.
2. lotus-core demo datasets must provide at least one year of coherent, valuation-aware history to reliably feed lotus-performance period analytics.
3. Without explicit lotus-performance readiness checks tied to lotus-core demo bootstrap, UI may render incomplete performance context.

## Root Cause (Observed)

1. Integration validation between lotus-core one-year demo data and lotus-performance analytics availability is not enforced as a deterministic startup gate.
2. lotus-performance service lacks an explicit, automated cross-service readiness contract for lotus-core-sourced historical datasets in local platform orchestration.

## Proposed Solution

1. Add a lotus-performance readiness check workflow that validates analytics responses for all lotus-core demo portfolios after lotus-core demo load completes.
2. Define required lotus-performance response invariants for `YTD` and `1Y` periods (non-empty periods, stable schema, numeric return outputs or explicit governed null semantics).
3. Add a reusable platform automation task profile to run:
   - lotus-core demo verification
   - lotus-performance analytics verification
   - lotus-gateway smoke checks consuming lotus-performance responses
4. Emit a machine-readable readiness artifact for UI/lotus-gateway consumers.

## Architectural Impact

1. Strengthens lotus-core-lotus-performance-lotus-gateway contract reliability for demo and development environments.
2. Reduces false UI regressions caused by missing cross-service readiness sequencing.
3. Improves confidence in one-year analytics behavior before UI usability iterations.

## Risks and Trade-offs

1. Adds stricter startup validation and may increase initial bootstrap time.
2. Exposes latent data-quality issues that were previously masked in downstream services.

## High-Level Implementation Approach

1. Implement lotus-performance validation script(s) against lotus-core demo portfolios.
2. Integrate into CI/local automation profiles.
3. Add contract tests for required period outputs (`YTD`, `1Y`) with clear failure diagnostics.
4. Update docs and runbook references in platform docs.
