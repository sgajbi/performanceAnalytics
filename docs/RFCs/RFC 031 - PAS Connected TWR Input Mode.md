# RFC 031 - PAS Connected TWR Input Mode

## Status
Implemented

## Context
PA must support two execution styles:
- Stateless analytics using directly supplied portfolio bundles.
- Integrated analytics that source governed portfolio data from PAS.

To align PAS, PA, and DPM contracts, PA needs a first-class PAS-connected API that consumes PAS integration payloads without duplicating PAS core data logic.

## Decision
Add a PAS-connected TWR endpoint:
- `POST /performance/twr/pas-snapshot`

Request contract:
- `portfolioId`
- `asOfDate`
- `includeSections` (must contain `PERFORMANCE`)
- `consumerSystem`
- optional `periods` filter

Processing model:
- Call PAS `POST /integration/portfolios/{portfolio_id}/core-snapshot`.
- Validate presence and shape of `snapshot.performance.summary`.
- Map PAS summary to PA response model (`resultsByPeriod`).
- Preserve upstream errors.
- Return `502` for malformed PAS payload contracts.

## Consequences
- PA now supports PAS as canonical source for performance summaries.
- BFF/UI can use one PA API while PA enforces PAS contract quality.
- Contract drift becomes test-detectable via integration tests.
- No business logic is pushed to UI/BFF.

## Tests
Added integration coverage for:
- success response mapping
- requested period filtering
- malformed PAS payload (`502`)
- PAS upstream error passthrough
