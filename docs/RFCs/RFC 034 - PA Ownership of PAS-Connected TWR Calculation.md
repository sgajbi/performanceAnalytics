# RFC 034 - PA Ownership of PAS-Connected TWR Calculation

## 1. Problem Statement
`/performance/twr/pas-snapshot` currently maps PAS precomputed performance from `core-snapshot`. This makes PA a pass-through instead of analytics owner.

## 2. Decision
- PA must compute PAS-connected TWR using PAS raw data, not PAS performance outputs.
- PAS is treated as a data source via integration contract only.

## 3. Contract and Behavior
- PA `pas-snapshot` mode calls PAS `performance-input` endpoint.
- PA builds a `PerformanceRequest` internally and runs the PA TWR engine.
- Response remains `PasConnectedTwrResponse` for BFF compatibility.

## 4. Impact
- Analytics ownership becomes explicit in PA.
- PAS/PA boundaries become consistent with target platform architecture.

## 5. Risks
- Input-contract mismatches can break PA calculations.
- Transitional period may require additional defensive validation in PA.

## 6. Implementation
1. Extend PAS client service in PA with `get_performance_input`.
2. Refactor `/performance/twr/pas-snapshot` to compute from PA engine.
3. Update tests to validate PA-computed output and input validation behavior.

