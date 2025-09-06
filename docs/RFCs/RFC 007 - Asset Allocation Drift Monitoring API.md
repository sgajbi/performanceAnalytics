# RFC 007 — Asset Allocation Drift Monitoring API (`/portfolio/allocationDrift`)

**Status:** Draft 1
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)
**Reviewers:** Perf Engine, Risk, Platform
**Target Release:** v0.3.0
**Related:** RFC‑006 (Attribution), RFC‑005 (Correlation), Contribution Engine, TWR/MWR

---

## 1) Problem & Motivation

Strategic/target asset allocation (SAA/TAA) drifts as markets move and cashflows occur. Portfolio managers and client advisors need an **API-only** way to:

1. **Measure drift** between **current weights** and **targets** across one or more hierarchy levels (e.g., Asset Class → Sector → Region).
2. **Decide** whether a rebalance is required using **tolerance bands** (per group or global).
3. **Simulate minimal-turnover rebalancing deltas** to bring the portfolio **within bands** (optionally to exact target), with practical constraints (min trade size, rounding, cash use).
4. **Monitor drift over time** (timeseries, rolling stats) and **generate alerts**.

The endpoint is **stateless** and operates on request payloads; it does not fetch external holdings.

---

## 2) Goals & Non‑Goals

**Goals**

* Robust, deterministic calculation of current weights by group and drift to target.
* Support **multi-level grouping** and **per-group tolerance bands** (upper/lower).
* Provide **rebalance recommendations** at group level (and optionally instrument level if provided).
* Support **cash as buffer** handling and simple cash constraints.
* Offer **timeseries mode** for drift history and breach periods.

**Non‑Goals**

* No trade routing/booking, tax optimization, or transaction cost modeling (optional simple cost estimates supported).
* No persistence or scheduling.

---

## 3) Definitions & Formulas

Let **i** denote a group at a given level and **t** a valuation date (post chosen resample).

* Market value of group **i** at **t**: **MV\_{i,t} = Σ\_{j∈i} MV\_{j,t}** (sum of instrument MVs).
* Total MV at **t**: **MV\_{tot,t} = Σ\_i MV\_{i,t}** (include cash unless `exclude_cash=true`).
* Current weight: **w\_{i,t} = MV\_{i,t} / MV\_{tot,t}**.
* Target weight: **τ\_{i,t}** (from request: fixed, benchmark-derived, or range).
* **Drift** (signed): **d\_{i,t} = w\_{i,t} − τ\_{i,t}**.
* Absolute drift: **|d\_{i,t}|**.
* Tolerance band: **\[L\_i, U\_i]** around target (absolute percentage points).
* **Breach** if **w\_{i,t} < τ\_{i,t} − L\_i** (underweight breach) or **w\_{i,t} > τ\_{i,t} + U\_i** (overweight breach).

**Turnover estimate** for a rebalance to new weights **w'\_{i,t}**:

* Dollar traded = **0.5 · Σ\_i |w'*{i,t} − w*{i,t}| · MV\_{tot,t}** (standard two-sided turnover).
* Optional transaction cost estimate = **cost\_rate · turnover**.

---

## 4) API Design

### 4.1 Endpoint

`POST /portfolio/allocationDrift`

### 4.2 Request Schema (Pydantic)

```jsonc
{
  "portfolio_number": "PORT123",                  // optional passthrough for logs
  "as_of": "2025-08-31",                         // required in snapshot mode; optional in timeseries mode
  "currency": "USD",                              // base currency for MV; caller pre-converts if multi-ccy
  "mode": "snapshot",                             // "snapshot" | "timeseries"

  // Input holdings (either instruments with MV or pre-aggregated groups)
  "holdings": {
    "by": "instrument",                            // "instrument" | "group"
    "series": [
      {
        "instrumentId": "AAPL",
        "meta": {"assetClass": "Equity", "sector": "Tech"},
        "observations": [ {"date": "2025-08-31", "mv": 125000.0} ]
      }
    ]
  },

  // Grouping & hierarchy (top→down)
  "groupBy": ["assetClass", "sector"],

  // Target definition (choose one of target modes)
  "target": {
    "mode": "fixed",                               // "fixed" | "benchmark" | "ranges"

    // fixed: explicit target weights at a specific level
    "fixed": {
      "level": "assetClass",                        // level in groupBy where targets apply
      "weights": [ {"key": {"assetClass": "Equity"}, "weight": 0.60},
                    {"key": {"assetClass": "Bond"},   "weight": 0.35},
                    {"key": {"assetClass": "Cash"},   "weight": 0.05} ]
    },

    // benchmark: use benchmark weights as τ (sliced to same key schema)
    "benchmark": {
      "groups": [ {"key": {"assetClass": "Equity"}, "weight": 0.62}, ... ]
    },

    // ranges: lower/upper bounds without point targets (τ becomes mid by default)
    "ranges": {
      "level": "assetClass",
      "bounds": [ {"key": {"assetClass": "Equity"}, "lower": 0.55, "upper": 0.65}, ... ]
    }
  },

  // Tolerance bands (defaults if not specified per group)
  "tolerance": {
    "default": {"lower": 0.02, "upper": 0.02},     // ±2pp bands
    "overrides": [ {"key": {"assetClass": "Cash"}, "lower": 0.01, "upper": 0.05} ]
  },

  // Rebalance simulation controls (snapshot mode)
  "rebalance": {
    "enabled": true,
    "to": "bands",                                  // "bands" | "target" | "ranges"
    "min_trade": 1000.0,                             // notional in base ccy
    "lot_size": 1.0,                                 // rounding to nearest lot
    "use_cash": "buffer_first",                     // "buffer_first" | "proportional" | "none"
    "respect_bounds": true,                          // do not violate per-group bounds
    "cost_rate": 0.0005                              // optional est. cost per $ traded (5 bps)
  },

  // Timeseries controls (timeseries mode)
  "timeseries": {
    "start": "2025-01-01",
    "end":   "2025-08-31",
    "frequency": "M"                                 // "D"|"W"|"M"; default M
  },

  // Behavior flags
  "flags": {
    "exclude_cash": false,
    "normalize_weights": true,                       // renormalize Σ w_i = 1 per period
    "strict_targets": false                          // error if missing target for an observed group
  }
}
```

### 4.3 Response Schema

**Snapshot mode**

```json
{
  "as_of": "2025-08-31",
  "level": "assetClass",
  "totals": {
    "mv_total": 1000000.0,
    "turnover_est": 12000.0,
    "cost_est": 6.0
  },
  "groups": [
    {
      "key": {"assetClass": "Equity"},
      "current_weight": 0.67,
      "target_weight": 0.60,
      "lower": 0.58,
      "upper": 0.62,
      "drift": 0.07,
      "breach": {"type": "over", "amount": 0.05},
      "delta_weight": -0.05,                         // suggested change to reach band/target
      "delta_value": -50000.0,
      "notes": ["reduced to upper band"]
    }
  ],
  "rebalancing": {
    "objective": "bands",
    "solution": "greedy_min_turnover",
    "feasible": true,
    "constraints": {"min_trade": 1000.0, "lot_size": 1.0},
    "residual_cash": 2500.0
  }
}
```

**Timeseries mode**

```json
{
  "level": "assetClass",
  "series": [
    {
      "key": {"assetClass": "Equity"},
      "observations": [ {"date": "2025-01-31", "weight": 0.64, "drift": 0.04, "breach": false}, ... ],
      "stats": {"max_abs_drift": 0.09, "breach_ratio": 0.25}
    }
  ],
  "breach_windows": [ {"start": "2025-05-31", "end": "2025-07-31", "groups": ["Equity"]} ]
}
```

**HTTP Codes**

* 200 OK; 400 validation; 422 when no valid groups/targets after alignment; 413 if payload too large.

---

## 5) Computation Semantics

### 5.1 Input Normalization

* Convert observations to a long frame → pivot wide panel by date × instrument/group.
* For snapshot mode, require exactly one observation per instrument/group on `as_of` date.
* For timeseries, resample MV by `timeseries.frequency` (last-of-period sum for MV by group).

### 5.2 Weight Construction

* At each date, compute **MV\_{i}** and **MV\_tot** (including cash unless `exclude_cash`).
* **normalize\_weights**: scale weights so Σ\_i w\_i = 1 within numerical tolerance.
* If some groups are missing targets:

  * `strict_targets=true` → 400 error.
  * else → treat missing target as τ\_i = 0 with infinite band (no breach) unless in `ranges` mode (error).

### 5.3 Tolerance Resolution

* Effective band for group i: start from `tolerance.default`, then apply any per‑group override.
* In `ranges` target mode, if no explicit band provided, band = \[lower, upper] − τ (mid) for reporting.

### 5.4 Breach Detection & Scoring

* Compute **d\_i = w\_i − τ\_i**.
* Breach flags and **breach amount** = distance to nearest band edge.
* Portfolio **drift score** (optional): Σ\_i max(0, |d\_i| − band\_i) to quantify excess drift.

### 5.5 Rebalancing (Snapshot)

* Objective `to`:

  * **"bands"**: find new weights w'\_i inside \[τ\_i−L\_i, τ\_i+U\_i] with **minimum turnover**.
  * **"target"**: set w'\_i = τ\_i (exact rebalance).
  * **"ranges"**: choose any w'\_i within \[lower\_i, upper\_i] minimizing turnover.
* **Greedy minimal-turnover algorithm (default)**:

  1. Compute overweights O = {i | w\_i > τ\_i+U\_i} and underweights U = {i | w\_i < τ\_i−L\_i}.
  2. Sort O by (w\_i − (τ\_i+U\_i)) desc; sort U by ((τ\_i−L\_i) − w\_i) desc.
  3. Iteratively transfer weight Δ = min(over\_excess, under\_gap) between top of O and U.
  4. Enforce `min_trade` and `lot_size` rounding in **value space** using MV\_tot.
  5. Adjust **cash** according to `use_cash`:

     * `buffer_first`: consume/add cash before cross-asset transfers when available.
     * `proportional`: split net flows proportionally across groups.
     * `none`: do not use cash; transfers strictly between groups.
  6. Respect `respect_bounds` and do not violate any group’s lower/upper bounds.
  7. Stop when all breaches resolved or no feasible transfer remains.
* Output **delta\_weight/value per group**, turnover and cost estimates.

### 5.6 Instrument‑Level Suggestions (Optional)

* If instrument constituents are provided with **proportional mapping** from group deltas (e.g., trim within group by market‑cap proportion), return an **instrument-level** suggestion block:

  * For group i with delta\_value ΔV\_i < 0, distribute across its instruments j proportionally to MV\_{j}.
  * Apply `lot_size` per instrument if supplied via metadata.

### 5.7 Timeseries Mode

* Resample MV by frequency and recompute weights and drifts for each period.
* Return group series with `breach` booleans per period and summary stats (max abs drift, share of periods in breach).
* Optional **rolling drift** metric (future): moving average of |d\_i|.

---

## 6) Architecture & Files

```
engine/
  allocation.py                         # drift, bands, rebalancing, timeseries helpers

app/models/
  allocation_drift_requests.py          # Pydantic request models
  allocation_drift_responses.py         # Pydantic response models

app/api/endpoints/
  portfolio.py                          # add POST /portfolio/allocationDrift
```

* Reuse: existing util patterns (period parsing, validation, errors) from `app/core/*` and engine modules.

---

## 7) Testing Strategy

**Unit (engine/allocation.py)**

* Weight computation correctness with/without cash; normalization edge cases.
* Breach detection for various bands; global vs per‑group overrides.
* Greedy rebalancer convergence on small examples; min\_trade and lot rounding effects.
* Feasibility cases (e.g., tight bounds → infeasible).
* Instrument-level distribution fidelity.

**API**

* Schema validation and helpful error messages.
* Snapshot vs timeseries behavior.
* `target.mode` variants (fixed, benchmark, ranges).
* Flags: exclude\_cash, strict\_targets, normalize\_weights.

**Integration**

* Realistic multi-asset portfolio (Equity/Bond/Alt/Cash) with SAA and bands; verify deltas and turnover against a Pandas reference notebook.
* Multi-level groupBy behavior (assetClass→sector), ensure level isolation and correct totals.

**Benchmarks**

* N groups={10, 50, 200}, check p50 latency on 8‑vCPU box; ensure <200ms for N≤50.

---

## 8) Observability & Limits

* Log: as\_of, N instruments, N groups, level, mode, turnover\_est.
* Metrics (future): request latency histogram, breach count distribution, rebalancer iterations.
* Limits: max instruments=20k (soft 10k), max groups per level=2k, payload ≤25 MB.

---

## 9) Example Payloads

### 9.1 Snapshot, fixed targets, band rebalance

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "holdings": {
    "by": "instrument",
    "series": [
      {"instrumentId": "AAA", "meta": {"assetClass": "Equity"}, "observations": [{"date": "2025-08-31", "mv": 670000}]},
      {"instrumentId": "BBB", "meta": {"assetClass": "Bond"},   "observations": [{"date": "2025-08-31", "mv": 290000}]},
      {"instrumentId": "CASH", "meta": {"assetClass": "Cash"},   "observations": [{"date": "2025-08-31", "mv": 40000}]}
    ]
  },
  "groupBy": ["assetClass"],
  "target": {"mode": "fixed", "fixed": {"level": "assetClass", "weights": [
    {"key": {"assetClass": "Equity"}, "weight": 0.60},
    {"key": {"assetClass": "Bond"},   "weight": 0.35},
    {"key": {"assetClass": "Cash"},   "weight": 0.05}
  ]}},
  "tolerance": {"default": {"lower": 0.02, "upper": 0.02}},
  "rebalance": {"enabled": true, "to": "bands", "min_trade": 1000.0, "use_cash": "buffer_first"}
}
```

### 9.2 Snapshot, ranges (no point targets), proportional cash

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "holdings": {"by": "group", "series": [
    {"key": {"assetClass": "Equity"}, "observations": [{"date": "2025-08-31", "mv": 640000}]},
    {"key": {"assetClass": "Bond"},   "observations": [{"date": "2025-08-31", "mv": 310000}]},
    {"key": {"assetClass": "Cash"},   "observations": [{"date": "2025-08-31", "mv": 50000}]}
  ]},
  "groupBy": ["assetClass"],
  "target": {"mode": "ranges", "ranges": {"level": "assetClass", "bounds": [
    {"key": {"assetClass": "Equity"}, "lower": 0.55, "upper": 0.65},
    {"key": {"assetClass": "Bond"},   "lower": 0.30, "upper": 0.40},
    {"key": {"assetClass": "Cash"},   "lower": 0.03, "upper": 0.07}
  ]}},
  "rebalance": {"enabled": true, "to": "ranges", "use_cash": "proportional"}
}
```

### 9.3 Timeseries monitoring (monthly)

```json
{
  "mode": "timeseries",
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "AAA", "meta": {"assetClass": "Equity"}, "observations": [
      {"date": "2025-01-31", "mv": 600000}, {"date": "2025-02-28", "mv": 612000}, ... ]},
    {"instrumentId": "BBB", "meta": {"assetClass": "Bond"},   "observations": [
      {"date": "2025-01-31", "mv": 350000}, {"date": "2025-02-28", "mv": 348000}, ... ]},
    {"instrumentId": "CASH", "meta": {"assetClass": "Cash"},   "observations": [
      {"date": "2025-01-31", "mv": 50000},  {"date": "2025-02-28", "mv": 40000}, ... ]}
  ]},
  "groupBy": ["assetClass"],
  "target": {"mode": "fixed", "fixed": {"level": "assetClass", "weights": [
    {"key": {"assetClass": "Equity"}, "weight": 0.60},
    {"key": {"assetClass": "Bond"},   "weight": 0.35},
    {"key": {"assetClass": "Cash"},   "weight": 0.05}
  ]}},
  "timeseries": {"start": "2025-01-01", "end": "2025-08-31", "frequency": "M"}
}
```

---

## 10) Implementation Plan & Pseudocode

### 10.1 Files

1. `engine/allocation.py`
2. `app/models/allocation_drift_requests.py`
3. `app/models/allocation_drift_responses.py`
4. `app/api/endpoints/portfolio.py` (add route)
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)

```python
# engine/allocation.py

def compute_drift(req: DriftRequest) -> DriftResult:
    panel = build_mv_panel(req.holdings)              # date x entity (inst or group) -> MV
    grouped = aggregate_by_group(panel, req.groupBy)  # date x group -> MV

    if req.mode == 'snapshot':
        df = grouped.loc[req.as_of]
        weights = df / df.sum()
        targets, bands = resolve_targets_and_bands(req, weights.index)
        drifts = weights - targets
        breaches = compute_breaches(weights, targets, bands)

        if req.rebalance.enabled:
            deltas = greedy_rebalance(weights, targets, bands, req.rebalance, req.flags)
        else:
            deltas = None
        return build_snapshot_response(...)

    else:  # timeseries
        res = []
        for date, row in grouped.resample(req.timeseries.frequency).last():
            w = row / row.sum()
            targets, bands = resolve_targets_and_bands(req, w.index)
            d = w - targets
            res.append((date, w, d, breaches(...)))
        return build_timeseries_response(res)
```

---

## 11) Copy‑Paste Git Steps

```bash
git checkout -b feature/allocation-drift-api

git add engine/allocation.py \
        app/models/allocation_drift_requests.py \
        app/models/allocation_drift_responses.py \
        tests/unit/engine/test_allocation.py \
        tests/unit/test_allocation_drift_api.py \
        tests/integration/test_allocation_drift_api.py \
        README.md

git commit -m "feat(api): Add /portfolio/allocationDrift for drift measurement and band rebalancing\n\nSupports fixed/benchmark/range targets, per-group bands, greedy minimal-turnover rebalance,\n snapshot and timeseries modes, and instrument-level suggestions."

pytest -q
uvicorn main:app --reload
```

---

## 12) Risks & Mitigations

* **Infeasible constraints** (tight bounds/min\_trade): return `feasible=false` with diagnostics; suggest relaxations.
* **Currency mix**: require caller to pre-convert MVs; document clearly.
* **Rounding/lot artifacts**: report residuals and cash usage explicitly.

---

## 13) Future Extensions

* Transaction‑cost aware optimization (QP/LP) objective.
* Multi‑level simultaneous rebalance with parent/child constraints.
* Tax‑aware lot selection and realized gain limits.
* Alert webhook integration and SLA thresholds per mandate.

---
 