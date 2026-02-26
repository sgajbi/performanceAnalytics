# RFC 034 - lotus-performance Ownership of lotus-core-Input TWR Calculation

## 1. Problem Statement
`/performance/twr/pas-input` currently maps lotus-core precomputed performance from `core-snapshot`. This makes lotus-performance a pass-through instead of analytics owner.

## 2. Decision
- lotus-performance must compute lotus-core-connected TWR using lotus-core raw data, not lotus-core performance outputs.
- lotus-core is treated as a data source via integration contract only.

## 3. Contract and Behavior
- lotus-performance `pas-input` mode calls lotus-core `performance-input` endpoint.
- lotus-performance builds a `PerformanceRequest` internally and runs the lotus-performance TWR engine.
- Response remains `PasConnectedTwrResponse` for lotus-gateway compatibility.

## 4. Impact
- Analytics ownership becomes explicit in lotus-performance.
- lotus-core/lotus-performance boundaries become consistent with target platform architecture.

## 5. Risks
- Input-contract mismatches can break lotus-performance calculations.
- Transitional period may require additional defensive validation in lotus-performance.

## 6. Implementation
1. Extend lotus-core client service in lotus-performance with `get_performance_input`.
2. Refactor `/performance/twr/pas-input` to compute from lotus-performance engine.
3. Update tests to validate lotus-performance-computed output and input validation behavior.


