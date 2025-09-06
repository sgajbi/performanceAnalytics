# RFC 014–018 — Portfolio Performance API Enhancements

**Status:** Draft 1  
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** Existing endpoints: `/performance/twr`, `/performance/mwr`, `/contribution`, `/performance/attribution`  
**Goal:** Strengthen correctness, configurability, and consistency across the four performance endpoints without breaking existing clients. Grouped RFCs below share cross‑cutting foundations for a coherent API surface and codebase.

---

# RFC 014 — Cross‑Cutting Consistency & Diagnostics Framework

## 1) Motivation
Unify knobs (precision, annualization, calendar, periods), standardize diagnostics/audit metadata, and align error taxonomy across **TWR, MWR, Contribution, Attribution** so clients experience consistent behavior and payloads.

## 2) Shared Request Envelope (added fields)
```jsonc
{
  "as_of": "2025-08-31",
  "currency": "USD",
  "precision_mode": "FLOAT64",           // "FLOAT64" | "DECIMAL_STRICT"
  "rounding_precision": 6,

  "calendar": {                           // optional; default BUSINESS
    "type": "BUSINESS",                  // "BUSINESS" | "NATURAL"
    "trading_calendar": "NYSE"          // optional, future
  },

  "annualization": {
    "enabled": false,
    "basis": "BUS/252",                  // "BUS/252" | "ACT/365" | "ACT/ACT"
    "periods_per_year": 252               // override basis if provided
  },

  "periods": {                             // normalized period service
    "type": "EXPLICIT",                  // YTD|QTD|MTD|WTD|Y1|Y3|Y5|ITD|ROLLING|EXPLICIT
    "explicit": {"start": "2025-01-01", "end": "2025-08-31"},
    "rolling": {"months": 12}            // or {"days": 63}
  },

  "output": {
    "include_timeseries": false,
    "include_cumulative": false,          // add cumulative-to-date alongside period rows
    "top_n": 20                           // endpoints that rank items
  },

  "flags": {
    "fail_fast": false                    // convert soft warnings to 4xx when true
  }
}
```

## 3) Shared Response Footer (added blocks)
```jsonc
{
  "meta": {
    "calculation_id": "uuid",
    "engine_version": "0.4.0",
    "precision_mode": "FLOAT64",
    "annualization": {"enabled": false, "basis": "BUS/252", "periods_per_year": 252},
    "calendar": {"type": "BUSINESS", "trading_calendar": "NYSE"},
    "periods": {"type": "EXPLICIT", "start": "2025-01-01", "end": "2025-08-31"}
  },
  "diagnostics": {
    "nip_days": 2,
    "reset_days": 1,
    "effective_period_start": "2025-01-02",
    "notes": ["NIP rule V2 applied", "BMV+CF=0 on 2025-03-15"]
  },
  "audit": {
    "sum_of_parts_vs_total_bp": 0.1,
    "residual_applied_bp": 0.0,
    "counts": {"cashflow_days": 9, "fee_days": 3}
  }
}
```

## 4) Error Taxonomy (common)
- **400** Validation: schema/fields missing or inconsistent; **422** Feasible but insufficient data (e.g., IRR no convergence), **409** Conflicts (e.g., overlapping hierarchies), **500** unexpected.
- **Warnings** always echoed in `diagnostics.notes` unless `flags.fail_fast=true`.

## 5) Implementation & Tests
- Introduce `core/envelope.py` for shared Pydantic mixins; `core/periods.py` for unified period resolver; `core/annualize.py`.
- Unit: envelope validation; period resolution; calendar impacts; precision plumbing.  
- Migration: Defaults preserve current behavior.

---

# RFC 015 — TWR Enhancements

## 1) Scope
Extend `/performance/twr` with richer period types, optional annualization, clearer daily breakdown semantics, fee effect transparency, and reset governance—all using RFC‑014 envelope.

## 2) Request (additions)
```jsonc
{
  "endpoint": "/performance/twr",
  "frequencies": ["DAILY","MONTHLY","QUARTERLY","YEARLY","WEEKLY"],
  "include_cumulative": true,
  "fee_effect": {"enabled": true},
  "reset_policy": {"emit": true}          // surfaces detected resets and reasons
}
```

## 3) Response (key fields)
- For **DAILY** rows expose `period_return_pct` (renamed from "Final Cumulative ROR %").  
- When `include_cumulative=true`, add `cumulative_return_pct_to_date`.  
- Add `fee_effect_pct` per bucket if both gross and net series are available.  
- Add `reset_events[]`: date, reason (NCTRL code), impacted rows.

## 4) Semantics
- Linking unchanged; annualization if requested: \( (1+R)^{scale}-1 \) using basis from RFC‑014.  
- Weekly resample uses calendar choice (BUSINESS vs NATURAL).

## 5) Tests
- Daily vs Monthly parity; naming deprecation guard; fee effect math; weekly calendar.

---

# RFC 016 — MWR Enhancements (XIRR + Modified Dietz)

## 1) Scope
Upgrade `/performance/mwr` to support **XIRR** (root‑finding), **Modified Dietz** (time‑weighted CF), and retain **Dietz** as fallback; add annualization and convergence diagnostics.

## 2) Request (additions)
```jsonc
{
  "endpoint": "/performance/mwr",
  "mwr_method": "XIRR",                 // "XIRR" | "MODIFIED_DIETZ" | "DIETZ"
  "solver": {"method": "brent", "max_iter": 200, "tolerance": 1e-10},
  "annualization": {"enabled": true, "basis": "ACT/365"},
  "emit_cashflows_used": true
}
```

## 3) Response (key fields)
```jsonc
{
  "mwr": 0.0712,
  "mwr_annualized": 0.0740,
  "method": "XIRR",
  "convergence": {"iterations": 37, "residual": 1.7e-10},
  "cashflows_used": [ {"date": "2025-01-15", "amount": -100000}, ... ]
}
```

## 4) Fallback Policy
Try **XIRR** → if fail (no sign change / no convergence) fall back to **Modified Dietz** → else **Dietz**; record `method` used and reasons in `diagnostics.notes`.

## 5) Tests
- XIRR accuracy vs synthetic ground truth; edge cases (multiple flows same day, irregular spacing); fallback paths; annualization.

---

# RFC 017 — Contribution Enhancements

## 1) Scope
Improve `/contribution` by adding configurable weighting schemes, explicit smoothing controls, richer outputs (daily/group timeseries), and residual disclosure—all under RFC‑014 envelope.

## 2) Request (additions)
```jsonc
{
  "endpoint": "/contribution",
  "weighting_scheme": "BOD",               // "BOD" | "AVG_CAPITAL" | "TWR_DENOM"
  "smoothing": {"method": "CARINO"},      // "CARINO" | "NONE"
  "emit": {"timeseries": true, "group_timeseries": true, "residual_per_position": true}
}
```

## 3) Response (key fields)
```jsonc
{
  "totals": {"contribution": 0.0182},
  "timeseries": [ {"date": "2025-02-28", "contribution": 0.0019} ],
  "by_group": [ {"key": {"sector": "Tech"}, "contribution": 0.0071} ],
  "residual_allocation": [ {"instrumentId": "AAPL", "bp": 0.3} ]
}
```

## 4) Tests
- Carino reconciliation (Σ parts = portfolio linked return); weighting scheme parity checks; residual transparency.

---

# RFC 018 — Attribution Enhancements (Brinson Variants, Linking, Hierarchies)

## 1) Scope
Extend `/performance/attribution` with model/linking switches, hierarchical rollups, zero‑weight handling, and explicit active reconciliation.

## 2) Request (additions)
```jsonc
{
  "endpoint": "/performance/attribution",
  "model": "BF",                         // "BF" | "BHB"
  "linking": "MENCHERO",                 // "MENCHERO" | "ARITHMETIC"
  "hierarchy": ["sector","industry","security"],
  "zero_weight_policy": "drop",          // "drop" | "carry_forward" | "normalize"
  "emit": {"active_reconciliation": true, "by_level": true}
}
```

## 3) Response (key fields)
```jsonc
{
  "summary": {"active_return": 0.0121},
  "components": {"allocation": 0.0048, "selection": 0.0065, "interaction": 0.0008},
  "reconciliation": {"portfolio_minus_benchmark": 0.0121, "sum_components": 0.0121, "residual_bp": 0.0},
  "levels": [{"level": "sector", "rows": [ {"key": {"sector": "Tech"}, "A": 0.003, "S": 0.004, "I": 0.001} ]}]
}
```

## 4) Semantics
- Menchero linking kept default for geometric consistency; arithmetic sum as opt‑in.  
- Hierarchies computed top‑down with consistent parent keys; totals reconcile at each level.

## 5) Tests
- BF vs BHB parity on toy data; linking equivalence; hierarchy correctness; zero‑weight policy effects; explicit reconciliation equality.

---

# Code Architecture & Consistency Plan

```
core/
  envelope.py           # shared request/response mixins (RFC‑014)
  periods.py            # normalized period engine (YTD/QTD/WTD/ROLLING/EXPLICIT)
  annualize.py          # common annualization helpers
  errors.py             # shared error taxonomy

app/models/
  twr.py                # updated requests/responses + imports from core
  mwr.py
  contribution.py
  attribution.py

engine/
  twr.py                # minimal changes, adopts new names & emits diagnostics
  mwr.py                # XIRR/ModDietz/Dietz strategy + fallbacks
  contribution.py       # weighting & smoothing strategies
  attribution.py        # model/linking strategies & hierarchies
```

- **Strategy pattern** in engines for: MWR solver, Contribution weighting, Attribution model/linking.  
- **Feature flags** from envelope flow through engines via typed `Context` object.

---

# Backward Compatibility & Versioning
- All new fields are **optional**; defaults replicate existing behavior.  
- Deprecated response name (TWR daily `Final Cumulative ROR %`) continues for one minor version behind a feature flag `compat_legacy_names=true`; new name is primary.  
- Bump `engine_version` to `0.4.0` upon merge.

---

# Observability & Limits (all endpoints)
- Log: calculation_id, periods, basis, precision_mode, runtime ms, warnings count.  
- Emit metrics: p50/p95 latency; fallback counters (e.g., XIRR→ModDietz).  
- Payload limit unchanged (≤ 25 MB).

---

# Example Requests (Unified)

### TWR (YTD, weekly + monthly, annualized, cumulative)
```json
{
  "as_of": "2025-08-31",
  "periods": {"type": "YTD"},
  "frequencies": ["WEEKLY","MONTHLY"],
  "annualization": {"enabled": true, "basis": "BUS/252"},
  "output": {"include_cumulative": true}
}
```

### MWR (XIRR with fallback)
```json
{
  "as_of": "2025-08-31",
  "mwr_method": "XIRR",
  "solver": {"method": "brent", "max_iter": 200, "tolerance": 1e-10},
  "annualization": {"enabled": true, "basis": "ACT/365"},
  "emit_cashflows_used": true
}
```

### Contribution (Carino, group timeseries)
```json
{
  "as_of": "2025-08-31",
  "weighting_scheme": "BOD",
  "smoothing": {"method": "CARINO"},
  "output": {"include_timeseries": true},
  "emit": {"group_timeseries": true, "residual_per_position": true}
}
```

### Attribution (BF+Menchero, 3‑level hierarchy)
```json
{
  "as_of": "2025-08-31",
  "model": "BF",
  "linking": "MENCHERO",
  "hierarchy": ["sector","industry","security"],
  "emit": {"active_reconciliation": true}
}
```

---

# Testing & Rollout Checklist
- **Unit**: each strategy branch; annualization math; weekly resample; diagnostics population.  
- **Integration**: end‑to‑end corpus with known outputs (golden files).  
- **Backward‑compat**: snapshots of current responses vs v0.4 (only additions/renames where flagged).  
- **Docs**: upgrade guide (1–2 pages) showing new fields and compatibility toggles.  
- **Perf**: no regression >5% p95.

---

# Copy‑Paste Git Steps
```bash
git checkout -b feature/v0.4-performance-enhancements

# Core shared foundations
mkdir -p core app/models engine
git add core/envelope.py core/periods.py core/annualize.py core/errors.py

# Endpoint model & engine updates
git add app/models/{twr.py,mwr.py,contribution.py,attribution.py} \
        engine/{twr.py,mwr.py,contribution.py,attribution.py}

# Tests & docs
git add tests/unit/core tests/unit/engine tests/integration docs/perf_v0_4_upgrade.md

git commit -m "perf(v0.4): unify envelope + enhance TWR/MWR/Contribution/Attribution\n\nAdds diagnostics/audit, annualization, period engine, XIRR/ModDietz,\n weighting & smoothing options, model/linking switches, and hierarchical outputs."
```

---

**End of RFCs 014–018**

