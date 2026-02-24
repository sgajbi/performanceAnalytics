# RFC 033 - PAS Year-History Readiness for PA and UI

## Status
Proposed

## Date
2026-02-24

## Problem Statement

PA analytics endpoints are expected to power BFF/UI workbench and portfolio views, but live integration currently shows unstable readiness:

1. PA snapshot calls can fail in platform runs.
2. PAS demo datasets must provide at least one year of coherent, valuation-aware history to reliably feed PA period analytics.
3. Without explicit PA readiness checks tied to PAS demo bootstrap, UI may render incomplete performance context.

## Root Cause (Observed)

1. Integration validation between PAS one-year demo data and PA analytics availability is not enforced as a deterministic startup gate.
2. PA service lacks an explicit, automated cross-service readiness contract for PAS-sourced historical datasets in local platform orchestration.

## Proposed Solution

1. Add a PA readiness check workflow that validates analytics responses for all PAS demo portfolios after PAS demo load completes.
2. Define required PA response invariants for `YTD` and `1Y` periods (non-empty periods, stable schema, numeric return outputs or explicit governed null semantics).
3. Add a reusable platform automation task profile to run:
   - PAS demo verification
   - PA analytics verification
   - BFF smoke checks consuming PA responses
4. Emit a machine-readable readiness artifact for UI/BFF consumers.

## Architectural Impact

1. Strengthens PAS-PA-BFF contract reliability for demo and development environments.
2. Reduces false UI regressions caused by missing cross-service readiness sequencing.
3. Improves confidence in one-year analytics behavior before UI usability iterations.

## Risks and Trade-offs

1. Adds stricter startup validation and may increase initial bootstrap time.
2. Exposes latent data-quality issues that were previously masked in downstream services.

## High-Level Implementation Approach

1. Implement PA validation script(s) against PAS demo portfolios.
2. Integrate into CI/local automation profiles.
3. Add contract tests for required period outputs (`YTD`, `1Y`) with clear failure diagnostics.
4. Update docs and runbook references in platform docs.
