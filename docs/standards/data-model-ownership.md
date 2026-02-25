# Data Model Ownership

- Service: `performanceAnalytics`
- Ownership status: no persisted core portfolio ledger entities.
- Responsibility: advanced analytics computation contracts.

## Boundaries

- PAS remains authoritative for core positions, transactions, valuations, and timeseries.
- PA consumes PAS API contracts and produces advanced analytics outputs.
- PA does not redefine PAS-owned core data terms.

## Vocabulary

- Canonical terms must align with `pbwm-platform-docs/Domain Vocabulary Glossary.md`.
- No service-local synonyms for portfolio, position, transaction, valuation, performance, risk.
