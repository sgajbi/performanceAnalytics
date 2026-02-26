# RFC 031 - lotus-core Connected TWR Input Mode

## Status
Implemented

## Context
lotus-performance must support two execution styles:
- Stateless analytics using directly supplied portfolio bundles.
- Integrated analytics that source governed portfolio data from lotus-core.

To align lotus-core, lotus-performance, and lotus-manage contracts, lotus-performance needs a first-class lotus-core-connected API that consumes lotus-core integration payloads without duplicating lotus-core core data logic.

## Decision
Add a lotus-core-connected TWR endpoint:
- `POST /performance/twr/pas-input`

Request contract:
- `portfolioId`
- `asOfDate`
- `includeSections` (must contain `PERFORMANCE`)
- `consumerSystem`
- optional `periods` filter

Processing model:
- Call lotus-core `POST /integration/portfolios/{portfolio_id}/core-snapshot`.
- Validate presence and shape of `snapshot.performance.summary`.
- Map lotus-core summary to lotus-performance response model (`resultsByPeriod`).
- Preserve upstream errors.
- Return `502` for malformed lotus-core payload contracts.

## Consequences
- lotus-performance now supports lotus-core as canonical source for performance summaries.
- lotus-gateway/UI can use one lotus-performance API while lotus-performance enforces lotus-core contract quality.
- Contract drift becomes test-detectable via integration tests.
- No business logic is pushed to UI/lotus-gateway.

## Tests
Added integration coverage for:
- success response mapping
- requested period filtering
- malformed lotus-core payload (`502`)
- lotus-core upstream error passthrough
