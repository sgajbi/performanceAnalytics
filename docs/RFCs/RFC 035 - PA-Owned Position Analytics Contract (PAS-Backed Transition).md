# RFC 035 - lotus-performance-Owned Position Analytics Contract (lotus-core-Backed Transition)

## 1. Problem
Position analytics is exposed from lotus-core (`/portfolios/{id}/positions-analytics`), but platform direction requires lotus-performance to become the central home for advanced analytics contracts.

## 2. Decision
- Introduce a lotus-performance-owned endpoint: `POST /analytics/positions`.
- During transition, lotus-performance orchestrates/normalizes payload from lotus-core position analytics.
- Consumer contract ownership shifts to lotus-performance now; deeper engine migration can follow incrementally.

## 3. Scope
- New lotus-performance request/response models for position analytics contract.
- New lotus-core client method for fetching position analytics payload.
- New lotus-performance endpoint under `/analytics`.

## 4. Non-Goals (This Slice)
- Re-implement all lotus-core position analytics algorithms inside lotus-performance engine in one step.
- Remove lotus-core endpoint immediately (deprecation will be phased).

## 5. Risks and Trade-Offs
- Transitional coupling remains while lotus-performance wraps lotus-core for some calculations.
- Payload-shape drift risk is mitigated by lotus-performance validation and API tests.

## 6. Next Steps
1. Add lotus-performance-native computation modules for position-level performance/risk slices.
2. Route lotus-gateway/UI consumers to lotus-performance position analytics contract.
3. Deprecate lotus-core position analytics sections owned by lotus-performance once parity is achieved.

