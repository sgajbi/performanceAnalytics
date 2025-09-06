# RFC 008 — Fixed‑Income Metrics API (`/portfolio/fixedIncomeMetrics`)

**Status:** Draft 1
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)
**Reviewers:** Perf Engine, Risk, Platform
**Target Release:** v0.3.x
**Related:** RFC‑006 (Attribution), RFC‑007 (Allocation Drift), RFC‑005 (Correlation)

---

## 1) Problem & Motivation

Portfolio managers need bond‑specific risk and yield metrics at **instrument**, **group**, and **portfolio** levels to understand interest‑rate and credit sensitivity and to compare exposures across portfolios. This RFC introduces an API‑only endpoint that computes **duration (Macaulay/Modified/Effective)**, **DV01/PV01**, **convexity**, **yield measures (YTM/YTW)**, **spread measures (Z‑spread/Nominal/OAS†)**, and **key‑rate durations (KRDs)** with rollups and contributions. The design follows the project patterns (stateless request, Pydantic models, FastAPI endpoint, engine module, tests).

> †OAS requires option‑adjusted pricing via a model; v1 exposes Z‑spread and nominal spread; OAS is planned (v1.1) with a pluggable pricer.

---

## 2) Scope & Non‑Goals

**In scope (v1)**

* Bullet/fixed‑rate and zero‑coupon bonds; support floaters with simple next‑reset approximation; inflation‑linked bonds (real measures) optional flag.
* Pricing via **deterministic term structures** (zero curve) with linear or log‑linear interpolation.
* Measures: Price (clean/dirty), Accrued, YTM/YTW, Macaulay/Modified Duration, DV01(PV01), Convexity, Key‑Rate Durations, Z‑spread, Nominal spread, Weighted averages & contributions by group.

**Out of scope (v1)**

* Callable/putable amortizing bonds (OAS engine), MBS/ABS with prepayment models, CDS, IRS; multi‑curve discounting; stochastic models.
* Tax/lot‑level realization effects; transaction costs.

---

## 3) Conventions & Definitions

* **Day count**: `30/360`, `ACT/ACT`, `ACT/360`, etc.
* **Coupon frequency**: `1, 2, 4, 12` per year.
* **Price type**: **clean** (ex‑accrued) vs **dirty** (= clean + accrued).
* **Weights**: market‑value (dirty) weights unless specified.
* **Base currency**: caller supplies inputs converted to base; engine is currency‑agnostic in v1.

### 3.1 Core Formulas (bullet bond)

Let period discount rate **y\_m = y / m** for annual yield **y** and **m** coupons/year.

* Cash flow times: **t\_k = k/m** years from settlement to the k‑th coupon (k=1..N), with last at maturity **T**.
* Cash flows: **CF\_k = c/m · F** for k=1..N−1, and **CF\_N = (c/m · F + F)** at maturity, with coupon rate **c**, face **F**.
* **Dirty Price**: $P = \sum_{k=1}^{N} \frac{CF_k}{(1+y_m)^{k}}$.  Clean price **= P − Accrued**.
* **Macaulay Duration** (years): $D_{Mac} = \frac{\sum_{k=1}^{N} t_k \cdot \frac{CF_k}{(1+y_m)^{k}}}{P}$.
* **Modified Duration**: $D_{Mod} = \frac{D_{Mac}}{1+y_m}$.
* **DV01 (PV01)**: $\text{DV01} = P \cdot D_{Mod} / 10{,}000$ (price change per 1bp).
* **Convexity** (years²): $C = \frac{1}{P}\sum_{k=1}^N \frac{CF_k\, t_k (t_k+1/m)}{(1+y_m)^{k+2}}$.
* **Key‑Rate Duration (vector)**: for tenors **K = {2Y,5Y,10Y,...}**, bump the zero curve by **Δ=1bp** at each key (piecewise‑linear shock), recompute **P^+**, **P^-**, then $KRD_i = -\frac{P^+ - P^-}{2 P \cdot \Delta}$.

### 3.2 Spreads

* **Nominal spread**: YTM − Benchmark yield at maturity.
* **Z‑spread**: constant add‑on **z** to all zero rates s.t. discounted CFs equals market **P**.
* **OAS (v1.1)**: spread over spot curve in a short‑rate/tree/pricer after removing option cost.

### 3.3 Portfolio Aggregation

* **Portfolio DV01**: Σ instrument DV01 (in value units).
* **Portfolio D\_mod** (MV‑weighted): $D^{p}_{Mod} = \sum_j w_j D^{j}_{Mod}$, with **w\_j = MV\_j / Σ MV**.
* **Contribution to DV01**: **ctr\_dv01\_j = DV01\_j / Σ DV01**.
* **Group rollups**: aggregate by provided grouping keys (e.g., sector, rating, maturity bucket, currency).

---

## 4) API Design

### 4.1 Endpoint

`POST /portfolio/fixedIncomeMetrics`

### 4.2 Request Schema (Pydantic)

```jsonc
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",
  "mode": "snapshot",                           // "snapshot" | "timeseries"

  "groupBy": ["assetClass", "sector", "rating"],

  "instruments": [
    {
      "instrumentId": "US91282CAXXX",
      "meta": {"assetClass": "Bond", "sector": "UST", "rating": "AAA"},
      "face": 1000000.0,
      "coupon_rate": 0.045,                      // 4.5% annual
      "coupon_freq": 2,                          // 2 = semiannual
      "maturity": "2030-11-15",
      "settlement": "2025-08-31",
      "day_count": "ACT/ACT",
      "price_type": "clean",                    // "clean" | "dirty"
      "price": 99.25,                            // per 100 face (clean if price_type=clean)
      "accrued_override": null,                  // optional if clean price given
      "yield_input": null,                        // optional; if given, skip solve
      "spread_input": null,                       // optional Z-spread input; else solve from price if requested
      "is_floater": false,
      "floater_index": null,                      // e.g., 3M-LIBOR/SOFR (for metadata)
      "is_linker": false,
      "index_ratio": null                         // for linkers at settlement
    }
  ],

  // Curves and settings
  "curve": {
    "type": "zero",                               // v1: single discount curve
    "nodes": [ {"tenor": "1M", "zero": 0.053}, {"tenor": "6M", "zero": 0.051}, {"tenor": "1Y", "zero": 0.048}, {"tenor": "5Y", "zero": 0.042}, {"tenor": "10Y", "zero": 0.039} ],
    "interp": "log_df"                            // "linear_zero" | "log_df"
  },

  // Key-rate settings
  "key_rates": { "tenors": ["2Y","5Y","10Y"], "bump_bp": 1.0 },

  // Measures toggle
  "measures": {
    "ytm": true,
    "ytw": false,                                 // compute to worst across calls/puts (v1=false)
    "duration": ["macaulay","modified"],
    "dv01": true,
    "convexity": true,
    "z_spread": true,
    "nominal_spread": true,
    "krd": true
  },

  // Timeseries mode controls
  "timeseries": { "start": "2025-01-01", "end": "2025-08-31", "frequency": "M" },

  // Flags & limits
  "flags": {
    "use_price_accrual_engine": true,            // compute accrued if clean price provided
    "solve_tolerance": 1e-10,
    "max_iter": 200,
    "enforce_positive_yield": false
  }
}
```

### 4.3 Response Schema (Snapshot)

```json
{
  "as_of": "2025-08-31",
  "portfolio": {
    "mv_total": 10000000.0,
    "dv01_total": 81234.5,
    "duration_modified": 5.42,
    "duration_macaulay": 5.66,
    "convexity": 62.8,
    "krd": {"2Y": 1.21, "5Y": 2.74, "10Y": 1.47}
  },
  "groups": [
    { "key": {"sector": "UST"}, "mv": 4000000.0, "dv01": 38211.2, "dur_mod": 6.10, "convexity": 72.1, "krd": {"2Y": 0.8, "5Y": 3.3, "10Y": 1.2} }
  ],
  "instruments": [
    {
      "instrumentId": "US91282CAXXX",
      "clean_price": 99.25,
      "dirty_price": 100.05,
      "accrued": 0.80,
      "ytm": 0.0467,
      "z_spread": 0.0009,
      "nominal_spread": 0.0007,
      "duration_macaulay": 5.71,
      "duration_modified": 5.44,
      "dv01": 544.2,
      "convexity": 63.0,
      "krd": {"2Y": 0.12, "5Y": 0.28, "10Y": 0.16}
    }
  ]
}
```

### 4.4 Response Schema (Timeseries)

```json
{
  "series": [
    { "date": "2025-01-31", "portfolio": {"dv01_total": 76000.0, "dur_mod": 5.2}, "groups": [/* per date group rollups */] },
    { "date": "2025-02-28", "portfolio": {"dv01_total": 77500.0, "dur_mod": 5.3} }
  ]
}
```

**HTTP codes**: 200 OK; 400 validation; 422 if infeasible/missing curve; 413 payload limits; 500 unexpected.

---

## 5) Computation Semantics

### 5.1 Accrued Interest & Day‑Count

* Compute **accrued** from last coupon to settlement using day‑count; handle ex‑coupon if provided (future flag).
* If `price_type=clean` and no `accrued_override`, derive **dirty = clean + accrued**.

### 5.2 Yield & Price

* If `yield_input` is provided → compute clean/dirty from yield using the curve’s compounding convention alignment.
* Else **solve** for YTM from price via Newton–Raphson or bisection with `solve_tolerance`, `max_iter`.
* **Short/negative yields** allowed unless `enforce_positive_yield=true`.

### 5.3 Curve Interpolation

* `linear_zero`: linear in zero rates by maturity.
* `log_df`: linear in log discount factors (preferred).
* Bootstrapping is **out of scope**; expect curve nodes supplied.

### 5.4 Key‑Rate Construction

* Build piecewise parallel bump **only at specified tenors**, with linear tapering between adjacent nodes (bucketed bump).
* Re‑price with +bp and −bp, compute symmetric finite‑difference KRDs.
* **Sanity**: Σ KRDs should approximate D\_mod under full‑curve parallel shift (tolerance ε); report diagnostics.

### 5.5 Floaters (approximation)

* Treat coupon = index + spread; for risk, assume **duration ≈ time to next reset** (in years), DV01 ≈ price × duration / 10k.
* If `is_floater=true` and `next_reset_date` provided (future field), use exact; v1 uses approximation.

### 5.6 Inflation‑Linked (optional)

* Real cash flows discounted on **real curve** (if supplied); otherwise treat via **index\_ratio** at settlement to scale nominal flows and compute real duration measures.
* Mark in response `measure_basis: "real"`.

### 5.7 Group & Portfolio Rollups

* Use dirty MV for **weights** and add **DV01** additively.
* Duration/convexity aggregated as MV‑weighted averages; KRDs aggregated additively (in DV01‑space) or MV‑weighted approximations—v1 additive in DV01 units.

### 5.8 Validation & Diagnostics

* Verify coupon schedule generation; ensure future CFs only (post‑settlement).
* If maturity < settlement or schedule empty → 422.
* If curve tenor coverage is insufficient (e.g., last node < maturity), extrapolate flat last rate with warning flag `curve_extrapolated=true`.

---

## 6) Architecture & Files

```
engine/
  fixed_income.py                  # pricing, schedules, measures, KRDs, spreads

app/models/
  fixed_income_requests.py         # Pydantic request models
  fixed_income_responses.py        # Pydantic response models

app/api/endpoints/
  portfolio.py                     # add POST /portfolio/fixedIncomeMetrics
```

* Utilities reused: date rules, resampling, error mapping.

---

## 7) Testing Strategy

**Unit (engine/fixed\_income.py)**

* Zero‑coupon closed forms: price, duration, convexity vs analytical.
* Coupon bond sanity: price↔yield inversion; D\_mod ≈ (P+ − P−)/(2PΔy).
* DV01 consistency: DV01 ≈ P·D\_mod/10k; KRD sum ≈ D\_mod (parallel bump).
* Accrued across day‑count conventions and irregular first/last coupon.
* Curve interpolation parity (linear\_zero vs log\_df).
* Floaters approximation vs near‑reset limit.

**API**

* Schema validations; missing curve nodes; extrapolation warnings.
* Group rollups by sector/rating; timeseries aggregation.
* Large payload limits and timing (benchmarks).

**Integration**

* Synthetic UST + IG corporate portfolio; compare to Pandas/QuantLib (if available in tests guarded).
* Sanity on spread: z‑spread solving reproduces price within tolerance.

**Benchmarks**

* N={50, 500, 2k} instruments; ensure p50 latency < 1s for N≤500 on 8 vCPU dev box.

---

## 8) Observability & Limits

* Log: as\_of, instrument\_count, curve\_nodes, krd\_count, timing.
* Metrics (future): p50/p95 latency, solver iterations, extrapolation counts.
* Limits: max instruments=20k (soft 10k); payload ≤ 25 MB; max key‑rates=20.

---

## 9) Example Payloads

### 9.1 Snapshot — UST & Corp with KRDs

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "groupBy": ["sector", "rating"],
  "instruments": [
    {"instrumentId": "T10_2030", "meta": {"sector": "UST", "rating": "AAA"}, "face": 1000000, "coupon_rate": 0.04, "coupon_freq": 2, "maturity": "2030-11-15", "settlement": "2025-08-31", "day_count": "ACT/ACT", "price_type": "clean", "price": 99.25},
    {"instrumentId": "CORP_A_2029", "meta": {"sector": "IG", "rating": "A"}, "face": 500000, "coupon_rate": 0.055, "coupon_freq": 2, "maturity": "2029-06-30", "settlement": "2025-08-31", "day_count": "30/360", "price_type": "dirty", "price": 102.1}
  ],
  "curve": {"type": "zero", "interp": "log_df", "nodes": [{"tenor": "6M", "zero": 0.051}, {"tenor": "1Y", "zero": 0.049}, {"tenor": "5Y", "zero": 0.043}, {"tenor": "10Y", "zero": 0.039}]},
  "key_rates": {"tenors": ["2Y","5Y","10Y"], "bump_bp": 1.0},
  "measures": {"ytm": true, "duration": ["modified"], "dv01": true, "convexity": true, "z_spread": true, "nominal_spread": true, "krd": true}
}
```

### 9.2 Timeseries — Monthly Portfolio DV01 and Duration

```json
{
  "mode": "timeseries",
  "groupBy": ["sector"],
  "instruments": [ /* instruments with monthly dirty MV and prices across dates (optional) */ ],
  "curve": {"type": "zero", "interp": "log_df", "nodes": [ /* supply per call (assume as-of curve each date) */ ]},
  "timeseries": {"start": "2025-01-01", "end": "2025-08-31", "frequency": "M"},
  "measures": {"ytm": true, "duration": ["modified"], "dv01": true}
}
```

---

## 10) Implementation Plan & Pseudocode

### 10.1 Files

1. `engine/fixed_income.py`
2. `app/models/fixed_income_requests.py`
3. `app/models/fixed_income_responses.py`
4. `app/api/endpoints/portfolio.py` (add route)
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)

```python
# engine/fixed_income.py

def price_from_yield(cf_schedule, y, m):
    # dirty price per 100
    disc = 1.0
    p = 0.0
    for k, (t_k, cf_k) in enumerate(cf_schedule, start=1):
        disc = (1.0 + y/m) ** (-k)
        p += cf_k * disc
    return p


def yield_from_price(cf_schedule, price, m, tol=1e-10, max_iter=200):
    # Newton with fallback bisection
    y = 0.05
    for _ in range(max_iter):
        p = price_from_yield(cf_schedule, y, m)
        # derivative dp/dy via modified duration relation
        dmac = macaulay_duration(cf_schedule, y, m, p)
        dmod = dmac / (1 + y/m)
        dp = -price * dmod  # per 1.0 change in yield
        if abs(p - price) < tol:
            return y
        y -= (p - price) / (dp if dp != 0 else 1e-12)
    return y  # last y


def measures_for_bond(inst, curve, krd_cfg, toggles):
    sched = build_cashflows(inst)
    accrued = compute_accrued(inst)
    price = inst.price
    if inst.price_type == 'clean':
        dirty = price + accrued
    else:
        dirty = price
    # Solve yield if not provided
    ytm = inst.yield_input or solve_ytm(sched, dirty, inst.coupon_freq)
    # Duration, DV01, Convexity
    dmac = macaulay_duration(sched, ytm, inst.coupon_freq, dirty)
    dmod = dmac / (1 + ytm/inst.coupon_freq)
    dv01 = dirty * dmod / 10000.0 * (inst.face/100.0)
    conv = convexity(sched, ytm, inst.coupon_freq, dirty)
    # KRDs
    krd = compute_krd(inst, curve, krd_cfg)
    # Spreads (z-spread): root-find z so PV(curve+z) = dirty
    z = solve_z_spread(sched, curve, dirty)
    return { ... }
```

---

## 11) Copy‑Paste Git Steps

```bash
git checkout -b feature/fixed-income-metrics-api

git add engine/fixed_income.py \
        app/models/fixed_income_requests.py \
        app/models/fixed_income_responses.py \
        tests/unit/engine/test_fixed_income.py \
        tests/unit/test_fixed_income_api.py \
        tests/integration/test_fixed_income_api.py \
        README.md

git commit -m "feat(api): Add /portfolio/fixedIncomeMetrics for bond risk/yield measures\n\nComputes YTM/YTW, Macaulay/Modified duration, DV01/PV01, convexity, KRDs, and spreads (Z, nominal).\nIncludes group/portfolio rollups, snapshot & timeseries modes, and full tests."

pytest -q
uvicorn main:app --reload
```

---

## 12) Risks & Mitigations

* **Curve coverage**: extrapolation flagged; advise supplying nodes ≥ max maturity.
* **Irregular schedules**: implement robust schedule builder; validate inputs.
* **Solver instability**: bisection fallback; guarded derivatives.
* **Floater approximation**: document limitations; add exact next‑reset in v1.1.
* **Performance**: vectorized schedule building; precompute discount factors for KRD bumps.

---

## 13) Future Extensions

* Full OAS pricer (call/put schedules, trees/Monte Carlo).
* Multi‑curve (OIS discounting + Libor/SOFR projection).
* Credit metrics (spread duration, hazard‑rate curve, expected loss).
* Hedge suggestions from KRDs (min‑variance barbell/butterfly).
* Bucketing by effective maturity and liquidity tiers.

---

**End of RFC**
