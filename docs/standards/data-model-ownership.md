# Data Model Ownership

- Service: `lotus-performance`
- Ownership status: no persisted core portfolio ledger entities.
- Responsibility: advanced analytics computation contracts.

## Boundaries

- lotus-core remains authoritative for core positions, transactions, valuations, and timeseries.
- lotus-performance consumes lotus-core API contracts and produces advanced analytics outputs.
- lotus-performance does not redefine lotus-core-owned core data terms.

## Vocabulary

- Canonical terms must align with `lotus-platform/Domain Vocabulary Glossary.md`.
- No service-local synonyms for portfolio, position, transaction, valuation, performance, risk.

