# RFC 038 - PA Domain Vocabulary Alignment with Platform Glossary

## Status
Proposed

## Date
2026-02-25

## Problem Statement

`lotus-performance` still uses legacy shared terms (`portfolio_id`, `pas-input`) in API contracts, models, tests, and documentation.
This conflicts with the platform glossary in `lotus-platform/Domain Vocabulary Glossary.md`, which mandates canonical cross-service terms such as `portfolio_id`, `as_of_date`, and `pas-input` terminology.

Current measurable drift (baseline from `Validate-Domain-Vocabulary.ps1`):
- `portfolio_id`: 121 findings
- `pas-input`: 5 findings

## Decision

Perform a phased vocabulary migration in PA to align with platform glossary while preserving service stability during rollout.

1. Canonical request/response field names use `snake_case` internally and canonical cross-service aliases (`portfolioId`, `asOfDate`) at BFF-facing integration boundaries where required.
2. Remove `portfolio_id` from PA public contracts and replace with `portfolio_id`.
3. Deprecate `pas-input` naming and replace with `pas-input` terminology in endpoints/docs/contracts.
4. Keep compatibility shims only for an explicitly time-boxed transition window (if needed), with clear removal milestones.

## Scope

- PA API contracts and model fields.
- PA endpoint naming and docs references.
- PA tests and fixtures.
- PA docs/examples/RFC references in this repository.

## Out of Scope

- Cross-service consumer migrations in the same PR.
- PAS/DPM/BFF contract changes beyond PA-owned surface.

## Implementation Plan

### Phase A - Contract Surface Alignment
- Introduce canonical PA models using `portfolio_id`.
- Replace `/performance/twr/pas-input` naming with `pas-input` terminology.
- Keep temporary alias compatibility only where required by existing tests.

### Phase B - Test and Fixture Migration
- Rename all fixtures/assertions from `portfolio_id` to `portfolio_id`.
- Update integration/e2e tests to canonical terminology.
- Ensure no behavior regression.

### Phase C - Documentation and RFC Alignment
- Update README, guides, examples, and PA RFC references.
- Replace deprecated terms in public examples and OpenAPI descriptions.

### Phase D - Compatibility Removal
- Remove temporary alias support.
- Enforce zero prohibited terms in PA conformance baseline.

## Risks and Trade-offs

- Broad rename impacts many files and tests; high change surface.
- Temporary dual-term support may increase short-term complexity.

Mitigation:
- Execute in small PR waves (A-D).
- Keep strict contract tests and OpenAPI gate active in each wave.

## Acceptance Criteria

1. PA has zero `portfolio_id` and zero `pas-input` occurrences in active code/contracts/docs.
2. OpenAPI reflects canonical vocabulary.
3. All PA CI gates remain green (`lint`, `typecheck`, `openapi-gate`, tests, coverage, security).
4. Platform vocabulary conformance report marks PA as `ok`.


