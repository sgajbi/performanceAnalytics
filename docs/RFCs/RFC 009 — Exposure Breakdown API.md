# RFC 009 — Exposure Breakdown API (`/portfolio/exposureBreakdown`)

**Status:** Draft 1
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)
**Reviewers:** Perf Engine, Risk, Platform
**Target Release:** v0.3.x
**Related:** RFC‑006 (Attribution), RFC‑007 (Allocation Drift), RFC‑005 (Correlation), RFC‑008 (Fixed‑Income Metrics)

---

## 1) Problem & Motivation

Portfolio managers, client advisors, and clients need a clear breakdown of **what the portfolio is exposed to** across multiple classification dimensions (e.g., asset class, sector, region, currency, credit rating, issuer/counterparty, maturity bucket). This API provides a **stateless, API‑only** way to compute **gross/long/short/net exposure, weights, and optional risk‑adjusted exposures** (delta/beta/duration/DV01 adjusted) at any requested dimension, with optional **hierarchical rollups** and **timeseries** monitoring.

Use‑cases:

* Compliance/mandate checks (e.g., EM exposure ≤ 30%).
* Portfolio reviews (top sector/region/currency exposures with long/short breakdowns).
* Risk management (duration‑weighted or DV01 exposures for fixed‑income; delta‑adjusted exposures for equity derivatives).
* Drift/optimization input (pair with allocation‑drift & correlation features).

---

## 2) Goals & Non‑Goals

**Goals**

* Compute **exposures** by a chosen `dimension` and optional hierarchy `groupBy` (top→down).
* Support **gross**, **net**, **long**, **short** exposures and **weights** (percent of portfolio MV).
* Optional **risk‑adjusted** exposures: **delta‑adjusted** (equity derivatives), **beta‑adjusted** (equity beta), **duration/DV01‑weighted** (fixed‑income), **FX currency** exposure.
* Support **snapshot** (as‑of) and **timeseries** modes (D/W/M resamples).
* Provide **filters** (top‑K, thresholds) and **Other/unclassified bucket** logic.

**Non‑Goals**

* No storage, scheduling, or live position fetch.
* No factor/risk‑model estimation (handled elsewhere).
* No automatic look‑through retrieval (caller may supply look‑through vectors).

---

## 3) Definitions & Conventions

Let instruments **j** belong to groups **i** under a chosen `dimension` (e.g., sector). We operate in base currency (caller pre‑converts). Market value (dirty if available) is **MV\_j** with sign **s\_j ∈ {+1,−1}** (short is negative MV or explicit `side="short"`).

* **Long Exposure (group i):** $L_i = \sum_{j∈i} \max(MV_j, 0)$
* **Short Exposure:** $S_i = \sum_{j∈i} \max(-MV_j, 0)$
* **Gross Exposure:** $G_i = L_i + S_i$
* **Net Exposure:** $N_i = L_i - S_i = \sum_{j∈i} MV_j$
* **Weight (by MV):** $w_i = N_i / \sum_j MV_j$ (default).

  * Optionally, **gross weight** $w^{gross}_i = G_i / \sum_j |MV_j|$.

**Risk‑Adjusted Exposures** (optional if inputs provided):

* **Delta‑adjusted** (equity options, futures): $E^{Δ}_i = \sum_{j∈i} Δ_j · Notional^{underlying}_j · sign_j$
* **Beta‑adjusted** (equity): $E^{β}_i = \sum_{j∈i} β_j · MV_j$
* **Duration‑weighted** (FI): $E^{Dur}_i = \sum_{j∈i} Dur_j · MV_j$
* **DV01 exposure** (FI): $E^{DV01}_i = \sum_{j∈i} DV01_j$ (additive).
* **Currency exposure**: sum of **MV in currency c** before base conversion (caller may pass per‑instrument `local_ccy` & `fx_rate`).

**Look‑through**: if a fund position supplies a per‑dimension vector **p\_{i}** with Σ p\_i=1, then allocate MV\_j · p\_i to groups i.

**Bucketing**: numeric fields (maturity, rating score, market‑cap) can be bucketed via request rules.

---

## 4) API Design

### 4.1 Endpoint

`POST /portfolio/exposureBreakdown`
(Also supports `GET` with `dimension` query, but **POST** is canonical due to payload size.)

### 4.2 Request Schema (Pydantic)

```jsonc
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",
  "mode": "snapshot",                           // "snapshot" | "timeseries"

  // Dimension & optional hierarchy
  "dimension": "sector",                         // e.g., assetClass|sector|industry|region|country|currency|rating|maturityBucket|issuer|counterparty|instrumentType|strategy|customTag
  "groupBy": ["assetClass"],                      // optional higher-level rollup(s)

  // Holdings input (instrument- or group-level)
  "holdings": {
    "by": "instrument",                           // "instrument" | "group"
    "series": [
      {
        "instrumentId": "AAPL",
        "meta": {
          "assetClass": "Equity",
          "sector": "Tech",
          "region": "US",
          "currency": "USD",
          "rating": null,
          "issuer": "Apple Inc.",
          "maturity": null,
          "customTag": ["Sustainable"]
        },
        "observations": [
          { "date": "2025-08-31", "mv": 125000.0, "qty": 700, "price": 178.6, "side": "long", "beta": 1.10, "delta": null, "dv01": null }
        ],
        "lookthrough": null                         // optional: [{"dimension": "sector", "weights": {"Tech":0.7,"Health":0.3}}]
      },
      {
        "instrumentId": "SPX_FUT",
        "meta": {"assetClass": "Equity Derivative", "sector": "Index", "region": "US", "currency": "USD"},
        "observations": [
          { "date": "2025-08-31", "mv": -50000.0, "qty": -2, "price": 5200.0, "multiplier": 50, "side": "short", "delta": 1.0 }
        ]
      },
      {
        "instrumentId": "UST_2030",
        "meta": {"assetClass": "Bond", "sector": "UST", "currency": "USD", "rating": "AAA", "maturity": "2030-11-15"},
        "observations": [ { "date": "2025-08-31", "mv": 400000.0, "dv01": 2200.0, "duration": 6.1 } ]
      }
    ]
  },

  // Optional bucketing & taxonomy
  "bucketing": {
    "maturityBucket": { "rules": [
      {"name": "0-1Y",   "lte_years": 1},
      {"name": "1-3Y",   "gt_years": 1, "lte_years": 3},
      {"name": "3-7Y",   "gt_years": 3, "lte_years": 7},
      {"name": "7-15Y",  "gt_years": 7, "lte_years": 15},
      {"name": ">15Y",   "gt_years": 15}
    ]}
  },

  // Toggles for exposure types
  "measures": {
    "long": true,
    "short": true,
    "gross": true,
    "net": true,
    "weight_net": true,
    "weight_gross": false,
    "delta_adjusted": true,
    "beta_adjusted": true,
    "duration_weighted": true,
    "dv01": true,
    "currency_exposure": false
  },

  // Timeseries settings
  "timeseries": { "start": "2025-01-01", "end": "2025-08-31", "frequency": "M", "weight_method": "eop" },

  // Output shaping
  "output": {
    "top_n": 20,
    "threshold_weight": 0.005,                     // drop groups with |weight|<0.5% (move to "Other")
    "include_other": true,
    "include_unclassified": true,
    "sort_by": "gross",                           // one of: long|short|gross|net|weight_net|dv01|delta_adjusted|beta_adjusted
    "descending": true
  },

  // Flags & validation
  "flags": {
    "normalize_weights": true,                      // Σ net weights = 1
    "gross_denominator": "sum_abs_mv",            // for weight_gross
    "strict_dimension": false,                      // error on missing classification if true
    "derivative_policy": "delta_notional"          // how to map derivatives: "delta_notional" | "market_value" | "ignore_derivatives"
  }
}
```

### 4.3 Response Schema — Snapshot

```json
{
  "as_of": "2025-08-31",
  "dimension": "sector",
  "groupBy": ["assetClass"],
  "totals": {
    "mv_net": 475000.0,
    "mv_gross": 615000.0,
    "dv01_total": 2200.0
  },
  "groups": [
    {
      "key": {"assetClass": "Equity", "sector": "Tech"},
      "long": 125000.0,
      "short": 0.0,
      "gross": 125000.0,
      "net": 125000.0,
      "weight_net": 0.2632,
      "beta_adjusted": 137500.0,
      "delta_adjusted": 125000.0,
      "duration_weighted": 0.0,
      "dv01": 0.0
    },
    {
      "key": {"assetClass": "Equity Derivative", "sector": "Index"},
      "long": 0.0,
      "short": 50000.0,
      "gross": 50000.0,
      "net": -50000.0,
      "weight_net": -0.1053,
      "delta_adjusted": -5200.0,         
      "notes": ["futures mapped by delta_notional: qty*price*multiplier"]
    },
    {
      "key": {"assetClass": "Bond", "sector": "UST"},
      "long": 400000.0,
      "short": 0.0,
      "gross": 400000.0,
      "net": 400000.0,
      "weight_net": 0.8421,
      "duration_weighted": 2440000.0,    
      "dv01": 2200.0
    }
  ],
  "other": {"weight_net": -0.0},
  "unclassified": []
}
```

### 4.4 Response Schema — Timeseries

```json
{
  "dimension": "region",
  "series": [
    {
      "key": {"region": "US"},
      "observations": [
        {"date": "2025-01-31", "net": 300000.0, "weight_net": 0.60},
        {"date": "2025-02-28", "net": 315000.0, "weight_net": 0.63}
      ],
      "stats": {"max_weight": 0.67, "min_weight": 0.58, "breach_ratio": 0.0}
    }
  ]
}
```

**HTTP codes**: 200 OK; 400 validation; 422 if no valid groups after alignment; 413 payload limits.

---

## 5) Computation Semantics

### 5.1 Input Normalization

* Build long frame of observations → pivot to **as‑of** (snapshot) or resampled **EOP** panels (timeseries).
* If `holdings.by="group"`, values already represent group MVs; ensure schema matches chosen `dimension` keys.

### 5.2 Classification Resolution

* Determine group key per instrument using `dimension` (with `bucketing` for maturity/rating if specified).
* If `strict_dimension=true` and classification missing → 400 error; else map to `"Unclassified"`.

### 5.3 Exposure Calculations

1. **MV sign**: `side="short"` or negative MV ⇒ short.
2. **Long/Short/Gross/Net** per group as in §3.
3. **Weights**: `weight_net = net / Σ net` when `normalize_weights=true` (handle Σ net≈0 edge via fallback to gross weights).
4. **Derivatives mapping** (policy):

   * `delta_notional` (default): for options/futures/swaps, compute exposure as `delta * underlying_notional * sign`.

     * Futures underlying notional = `qty * price * multiplier`.
     * Options use provided `delta` (per‑contract) × underlying notional.
     * If `delta` missing, fallback to `market_value` with warning flag.
   * `market_value`: use `MV` sign directly.
   * `ignore_derivatives`: set derivative exposures to 0 (still count MV in totals if requested).
5. **Beta‑adjusted**: sum `beta * MV` where `beta` available; else assume 1.0 if `assume_beta_one=true` (future flag) and mark.
6. **Duration/DV01**: use instrument `duration`/`dv01` if supplied; else approximate: `duration ≈ (maturity_years)` for zero‑coupon (unsafe → warn) or call Fixed‑Income Metrics endpoint (future cross‑call) when `auto_enrich=true`.
7. **Look‑through**: if present for an instrument, allocate MV (or risk metric) to `dimension` based on provided weights.

### 5.4 Hierarchical Rollups

* If `groupBy` provided, compute exposure per tuple `(groupBy..., dimension)`; report in `groups.key`.
* Totals per higher level can be summed from child rows.

### 5.5 Filtering & Other Bucket

* Sort by `output.sort_by`; take top‑N; aggregate remainder (by sign for net or by absolute for gross) into **Other** if `include_other=true`.
* Add **Unclassified** bucket when applicable.

---

## 6) Architecture & Files

```
engine/
  exposure.py                           # core computation, bucketing, derivative mapping

app/models/
  exposure_requests.py                  # Pydantic requests (snapshot/timeseries)
  exposure_responses.py                 # Pydantic responses

app/api/endpoints/
  portfolio.py                          # add POST /portfolio/exposureBreakdown
```

* Reuse common utils: date parsing, resampling, validation, error mapping, currency guardrails.

---

## 7) Testing Strategy

**Unit (engine/exposure.py)**

* Long/short/gross/net math with mixed signs; weight normalization edge cases (Σ net≈0).
* Derivative policies (`delta_notional`, `market_value`, `ignore_derivatives`) on options/futures.
* Beta‑adjusted, delta‑adjusted, duration/DV01 aggregations.
* Bucketing (maturity → named buckets) and classification fallbacks.
* Look‑through allocation correctness (Σ allocations = MV).

**API**

* Schema validation; dimension & groupBy combinations.
* Snapshot vs timeseries outputs; top‑N and threshold/Other bucket logic.
* Unclassified handling and strict vs non‑strict behaviors.

**Integration**

* Synthetic multi‑asset portfolio (equity/derivs/bonds/FX) with expected results from a reference notebook.
* Cross‑check DV01 exposure totals vs Fixed‑Income Metrics endpoint outputs (if available in test fixture).

**Benchmarks**

* N instruments={1k, 10k, 50k}; ensure p50 < 400ms for 10k instruments on 8 vCPU dev box.

---

## 8) Observability & Limits

* Log: as\_of, dimension, #instruments, #groups, mode, derivative\_policy.
* Metrics (future): latency histogram, top‑N truncation counts, share of unclassified.
* Limits: max instruments=50k (soft 20k); payload ≤ 25 MB; max hierarchy depth=4.

---

## 9) Example Payloads

### 9.1 Snapshot — Sector (with derivative mapping)

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "dimension": "sector",
  "groupBy": ["assetClass"],
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "AAPL", "meta": {"assetClass": "Equity", "sector": "Tech"}, "observations": [{"date": "2025-08-31", "mv": 125000, "beta": 1.1}]},
    {"instrumentId": "SPX_FUT", "meta": {"assetClass": "Equity Derivative", "sector": "Index"}, "observations": [{"date": "2025-08-31", "mv": -50000, "qty": -2, "price": 5200, "multiplier": 50, "delta": 1.0}]},
    {"instrumentId": "UST_2030", "meta": {"assetClass": "Bond", "sector": "UST"}, "observations": [{"date": "2025-08-31", "mv": 400000, "dv01": 2200, "duration": 6.1}]}
  ]},
  "measures": {"long": true, "short": true, "gross": true, "net": true, "weight_net": true, "beta_adjusted": true, "delta_adjusted": true, "dv01": true},
  "output": {"top_n": 10, "include_other": true}
}
```

### 9.2 Snapshot — Currency Exposure

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "dimension": "currency",
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "HSBC.L", "meta": {"currency": "GBP"}, "observations": [{"date": "2025-08-31", "mv": 200000}]},
    {"instrumentId": "7203.T", "meta": {"currency": "JPY"}, "observations": [{"date": "2025-08-31", "mv": 150000}]}
  ]},
  "measures": {"net": true, "weight_net": true}
}
```

### 9.3 Timeseries — Region (monthly EOP)

```json
{
  "mode": "timeseries",
  "dimension": "region",
  "timeseries": {"start": "2025-01-01", "end": "2025-08-31", "frequency": "M"},
  "holdings": {"by": "group", "series": [
    {"key": {"region": "US"}, "observations": [{"date": "2025-01-31", "mv": 600000}, {"date": "2025-02-28", "mv": 615000}]},
    {"key": {"region": "EM"}, "observations": [{"date": "2025-01-31", "mv": 200000}, {"date": "2025-02-28", "mv": 195000}]}
  ]},
  "measures": {"net": true, "weight_net": true}
}
```

### 9.4 Snapshot — Maturity Buckets with DV01

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "dimension": "maturityBucket",
  "bucketing": {"maturityBucket": {"rules": [{"name": "0-1Y", "lte_years": 1}, {"name": "1-3Y", "gt_years": 1, "lte_years": 3}, {"name": "3-7Y", "gt_years": 3, "lte_years": 7}, {"name": ">7Y", "gt_years": 7}]}},
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "Corp_2027", "meta": {"maturity": "2027-06-30"}, "observations": [{"date": "2025-08-31", "mv": 300000, "dv01": 1600}]},
    {"instrumentId": "Corp_2035", "meta": {"maturity": "2035-12-31"}, "observations": [{"date": "2025-08-31", "mv": 250000, "dv01": 2100}]}
  ]},
  "measures": {"net": true, "dv01": true, "duration_weighted": true}
}
```

---

## 10) Implementation Plan & Pseudocode

### 10.1 Files

1. `engine/exposure.py`
2. `app/models/exposure_requests.py`
3. `app/models/exposure_responses.py`
4. `app/api/endpoints/portfolio.py` (add route)
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)

```python
# engine/exposure.py

def compute_exposure(req: ExposureRequest) -> ExposureResult:
    # 1) Build panel
    panel = build_panel(req.holdings)  # date x instrument -> MV (+ fields)

    if req.mode == 'snapshot':
        row = select_as_of(panel, req.as_of)
        tbl = classify(row, req.dimension, req.bucketing, req.flags)
        tbl = apply_lookthrough(tbl)
        agg = aggregate(tbl, req.groupBy, req.measures, req.flags, req.output, derivative_policy=req.flags.derivative_policy)
        return build_snapshot_response(agg)

    else:  # timeseries
        out = []
        for date, row in resample(panel, req.timeseries.frequency):
            tbl = classify(row, req.dimension, req.bucketing, req.flags)
            agg = aggregate(tbl, req.groupBy, req.measures, req.flags, req.output)
            out.append((date, agg))
        return build_timeseries_response(out)
```

---

## 11) Copy‑Paste Git Steps

```bash
git checkout -b feature/exposure-breakdown-api

git add engine/exposure.py \
        app/models/exposure_requests.py \
        app/models/exposure_responses.py \
        tests/unit/engine/test_exposure.py \
        tests/unit/test_exposure_api.py \
        tests/integration/test_exposure_api.py \
        README.md

git commit -m "feat(api): Add /portfolio/exposureBreakdown with gross/net/long/short and risk-adjusted exposures\n\nSupports dimension & multi-level groupBy, derivatives mapping policies, look-through, bucketing,\n snapshot & timeseries modes, and top-N/Other shaping. Includes tests & docs."

pytest -q
uvicorn main:app --reload
```

---

## 12) Risks & Mitigations

* **Σ net ≈ 0**: weight normalization becomes unstable → fallback to gross denominator with explicit flag.
* **Derivative mapping ambiguity**: policy flag + notes in response; require `delta`/`multiplier` for futures/options.
* **Classification gaps**: Unclassified bucket + `strict_dimension` to fail fast if desired.
* **Look‑through double‑count**: validate Σ p\_i=1; otherwise scale & warn.

---

## 13) Future Extensions

* Factor/risk‑model exposures (style, macro).
* Automatic enrichment via Fixed‑Income Metrics for missing duration/DV01.
* FX overlay decomposition (local vs base currency effects).
* Webhook alerts for threshold breaches.

 