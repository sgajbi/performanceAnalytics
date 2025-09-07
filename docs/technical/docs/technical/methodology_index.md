# Methodology Index

This index links all methodology and technical documentation for the **performanceAnalytics** engine.

---

## Core Documents

- [Architecture](architecture.md) – System design, API layers, and data flow.
- [Data Model](data_model.md) – Input/Output schemas and envelopes.
- [Engine Config](engine_config.md) – Precision, calendars, diagnostics, audit.

---

## Performance Methodologies

- [TWR (Time-Weighted Return)](twr.md)  
  - Daily ROR calculation
  - Geometric linking
  - Breakdown by frequency (daily, monthly, quarterly, yearly)
  - Annualization

- [MWR (Money-Weighted Return)](mwr.md)  
  - Internal Rate of Return (IRR) solver
  - Modified Dietz approximation
  - Cash flow timing sensitivity
  - Annualization

- [Contribution Analysis](contribution.md)  
  - Position-level contributions
  - Carino smoothing for reconciliation
  - Hierarchical breakdown (sector → industry → security)
  - Residual tracking

- [Attribution Analysis](attribution.md)  
  - Brinson models (BHB, BF)
  - Allocation, Selection, Interaction effects
  - Menchero geometric multi-period linking
  - Reconciliation against active return

---

## Usage

- Each methodology page provides:
  - Inputs and outputs
  - Calculation steps
  - Rationale in portfolio management context
  - API request/response examples

- This ensures new developers, BAs, product, and support teams can navigate the full methodology set easily.

---

## Next Steps

- Extend documentation with **examples from `docs/examples/`**.
- Add **API endpoints summary** (see `api_structure.md`).
- Ensure docs remain in sync with engine codebase.
