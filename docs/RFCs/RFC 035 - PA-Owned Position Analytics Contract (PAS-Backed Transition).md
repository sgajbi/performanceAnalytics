# RFC 035 - PA-Owned Position Analytics Contract (PAS-Backed Transition)

## 1. Problem
Position analytics is exposed from PAS (`/portfolios/{id}/positions-analytics`), but platform direction requires PA to become the central home for advanced analytics contracts.

## 2. Decision
- Introduce a PA-owned endpoint: `POST /analytics/positions`.
- During transition, PA orchestrates/normalizes payload from PAS position analytics.
- Consumer contract ownership shifts to PA now; deeper engine migration can follow incrementally.

## 3. Scope
- New PA request/response models for position analytics contract.
- New PAS client method for fetching position analytics payload.
- New PA endpoint under `/analytics`.

## 4. Non-Goals (This Slice)
- Re-implement all PAS position analytics algorithms inside PA engine in one step.
- Remove PAS endpoint immediately (deprecation will be phased).

## 5. Risks and Trade-Offs
- Transitional coupling remains while PA wraps PAS for some calculations.
- Payload-shape drift risk is mitigated by PA validation and API tests.

## 6. Next Steps
1. Add PA-native computation modules for position-level performance/risk slices.
2. Route BFF/UI consumers to PA position analytics contract.
3. Deprecate PAS position analytics sections owned by PA once parity is achieved.

