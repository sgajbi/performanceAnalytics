# RFC 013 — Active Analytics (Relative Benchmark Comparison) API (`/portfolio/activeAnalytics`)

**Status:** Draft 1  
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC‑006 (Attribution), RFC‑009 (Exposure Breakdown), RFC‑010 (Factor Exposures), RFC‑012 (Risk Metrics), RFC‑008 (Fixed‑Income)

---

## 1) Problem & Motivation
Portfolio managers and client advisors need a single, consistent endpoint to compare a portfolio **against its benchmark** across weights, returns, risk, and exposures. Today these views are scattered (exposure, attribution, risk metrics). This API unifies the **active view**: active weights, active share/overlap, ex‑post active return stats (TE, IR, hit ratio), **group‑level differentials**, **top over/underweights**, **active factor tilts**, **active risk decomposition** (if FCM provided), and optional **fixed‑income active duration/KRDs**. It supports **snapshot**, **timeseries**, and **rolling** windows.

**Design principles**: stateless, benchmark‑aware, multi‑asset friendly, deterministic, explicit assumptions.

---

## 2) Scope & Non‑Goals
**In scope**
- Active **weights** & **concentrations** (Active Share, Overlap metrics).  
- Active **returns** & statistics (TE, IR, alpha/beta vs benchmark, up/down capture, batting average, active drawdowns).  
- Group‑level **relative exposures** and **differentials** vs benchmark (`dimension`/`groupBy`).  
- **Top contributors** to active return (ex‑post), and **top over/underweights**.  
- **Factor tilts** Δβ and **active risk decomposition** (factor/specific) if FCM + specific vars provided.  
- **FI** deltas: active duration, DV01, and KRDs.

**Non‑Goals**
- Brinson A/S/I (covered in RFC‑006, though we expose total active contribution).  
- Data acquisition; callers supply series/holdings/benchmarks.  
- Optimization or rebalancing (covered in drift RFC).

---

## 3) Definitions & Formulas
Let instruments **j**, groups **i**, dates **t**.

### 3.1 Weights & Active Share
- Portfolio weights **w_j**, benchmark **b_j**, Σw = Σb = 1 (after normalization).  
- **Active weight**: \( a_j = w_j − b_j \).  
- **Active Share (long‑only)**: \( AS = \tfrac{1}{2} \sum_j |w_j − b_j| \) ∈ [0,1].  
  - **Generalized** (long/short): report both **AS_net** with signed nets and **AS_gross** over gross weight denominator.  
- **Weight Overlap**: \( \Omega = \sum_j \min(w_j, b_j) \).  
- **Herfindahl difference** (concentration): HHI_port − HHI_bmk.

### 3.2 Returns & Active Statistics
- Period returns **rᵖ_t**, **rᵇ_t** aligned.  
- **Active return**: **a_t = rᵖ_t − rᵇ_t**.  
- **Tracking error** (ann.): \( TE = \sqrt{A}\cdot stdev(a_t) \).  
- **Information ratio**: \( IR = \bar{a}_{ann} / TE \) (arithmetic by default).  
- **Hit ratio / batting avg**: P(a_t > 0).  
- **Up/Down capture**: mean rᵖ_t when rᵇ_t>0 / mean rᵇ_t>0, and similarly for rᵇ_t<0.  
- **Active max drawdown** using active equity curve \( E^a_t = \prod (1+a_t) \).

### 3.3 Group Differentials
For a chosen **dimension** (e.g., sector/region/currency/rating) and optional `groupBy` hierarchy:
- **Weight differential** per group i: \( Δw_i = w_i − b_i \).  
- **Return differential contribution (ex‑post)** per period: \( c_{i,t} = w_{i,t} r^p_{i,t} − b_{i,t} r^b_{i,t} \).  
- Linked across periods using **Carino** (reuse contribution linker) to **C_i**;
  total **Σ_i C_i = \sum_t a_t**.

### 3.4 Factor Tilts & Active Risk (optional)
Given factor exposures **β_p**, **β_b** and factor covariance **Σ_f**:
- **Active tilt**: **Δβ = β_p − β_b**.  
- **Active factor variance**: \( σ^2_{fac,act} = Δβ^T Σ_f Δβ \).  
- If security‑specific variances **σ²_spec,j** known: **active specific variance** \( σ^2_{spec,act} = \sum_j (w_j − b_j)^2 σ^2_{spec,j} \).  
- **Ex‑ante TE ≈ √(σ^2_{fac,act} + σ^2_{spec,act})**.

### 3.5 Fixed‑Income Actives (optional)
- **ΔDuration = D_mod^p − D_mod^b**; **ΔDV01 = DV01_p − DV01_b**; **ΔKRD_t = KRD^p_t − KRD^b_t**.

---

## 4) API Design
### 4.1 Endpoint
`POST /portfolio/activeAnalytics`

### 4.2 Request Schema (Pydantic)
```jsonc
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",

  "mode": "snapshot",                            // "snapshot" | "timeseries" | "rolling"
  "frequency": "M",                               // resample target for returns-based stats

  // Holdings (for weights & exposure diffs)
  "holdings": {
    "by": "instrument",                            // "instrument" | "group"
    "series": [
      {"instrumentId": "AAPL", "meta": {"sector": "Tech", "region": "US"}, "observations": [{"date": "2025-08-31", "mv": 125000}]},
      {"instrumentId": "UST_2030", "meta": {"assetClass": "Bond", "sector": "UST"}, "observations": [{"date": "2025-08-31", "mv": 400000}], "fi": {"dv01": 2200, "duration": 6.1, "krd": {"2Y":0.12,"5Y":0.28,"10Y":0.16}}}
    ]
  },

  // Benchmark holdings (required for active weights)
  "benchmark_holdings": {
    "series": [ {"instrumentId": "SPY", "observations": [{"date": "2025-08-31", "mv": 350000}], "lookthrough": {"type": "index", "weights": {"AAPL": 0.07}} } ]
  },

  // Returns for ex-post active stats
  "returns": {
    "portfolio": [ {"date": "2024-09-30", "value": 0.006}, ... ],
    "benchmark": [ {"date": "2024-09-30", "value": 0.005}, ... ],
    "kind": "returns",                             // or "prices"
    "method": "simple"
  },

  // Factor model inputs (optional)
  "factor_model": {
    "exposures": {"portfolio": {"MKT": 1.02, "SMB": -0.31, "MOM": 0.22}, "benchmark": {"MKT": 1.00, "SMB": -0.20, "MOM": 0.10}},
    "fcm": {"labels": ["MKT","SMB","MOM"], "matrix": [[0.02,0,0],[0,0.01,0],[0,0,0.015]]},
    "specific_vars": null
  },

  // Dimensions & hierarchy
  "dimension": "sector",
  "groupBy": ["assetClass"],

  // Toggles
  "metrics": {
    "active_share": true,
    "overlap": true,
    "weights_table": true,
    "active_return_stats": true,        // TE/IR/hit/capture/active DD
    "group_differentials": true,
    "top_over_under": {"enabled": true, "k": 10},
    "contributors": {"enabled": true, "k": 10},
    "factor_tilts": true,
    "active_risk": true,
    "fixed_income_actives": true
  },

  // Rolling/timeseries
  "rolling": {"window": 36, "step": 1},
  "timeseries": {"start": "2024-09-01", "end": "2025-08-31", "frequency": "M"},

  // Output shaping & flags
  "output": {"round": 6, "include_series": true, "top_n_groups": 20, "threshold_weight": 0.005, "include_other": true},
  "flags": {"normalize_weights": true, "strict_benchmark": false, "carino_link": true}
}
```

### 4.3 Response Schema — Snapshot
```json
{
  "as_of": "2025-08-31",
  "summary": {
    "active_share": 0.34,
    "overlap": 0.66,
    "concentration_diff_hhi": 0.012,
    "te_ann": 0.052,
    "ir": 0.36,
    "hit_ratio": 0.58,
    "up_capture": 1.05,
    "down_capture": 0.92,
    "active_max_dd": -0.064
  },
  "weights": {
    "top_overweights": [ {"id": "AAPL", "w_p": 0.07, "w_b": 0.03, "delta": 0.04} ],
    "top_underweights": [ {"id": "MSFT", "w_p": 0.02, "w_b": 0.06, "delta": -0.04} ]
  },
  "groups": [
    {"key": {"assetClass": "Equity", "sector": "Tech"}, "w_p": 0.28, "w_b": 0.22, "delta_w": 0.06, "active_contribution": 0.0042}
  ],
  "contributors": {
    "top_active_return": [ {"key": {"sector": "Tech"}, "contrib": 0.0042} ],
    "bottom_active_return": [ {"key": {"sector": "Energy"}, "contrib": -0.0028} ]
  },
  "factors": {
    "tilts": {"MKT": 0.02, "SMB": -0.11, "MOM": 0.12},
    "active_risk": {"ex_ante_te": 0.048, "factor_var": 0.0021, "specific_var": 0.0002}
  },
  "fixed_income": {
    "delta_duration": 0.22,
    "delta_dv01": 1240.0,
    "delta_krd": {"2Y": 0.08, "5Y": 0.22, "10Y": -0.02}
  },
  "notes": ["weights normalized to Σ=1 on portfolio and benchmark", "Carino linking used for group contributors"]
}
```

### 4.4 Response — Timeseries / Rolling
```json
{
  "mode": "timeseries",
  "series": [
    {"date": "2024-09-30", "active_share": 0.31, "te_ann": 0.051, "ir_12m": 0.28},
    {"date": "2024-10-31", "active_share": 0.33, "te_ann": 0.054, "ir_12m": 0.30}
  ]
}
```

---

## 5) Computation Semantics
### 5.1 Pre‑processing
- Build **as‑of** weights from holdings (or group weights if `by=group`), normalize to Σ=1 each side; map benchmark look‑through when provided.  
- For returns: convert prices→returns if needed; resample to `frequency`; align to intersection; ensure `min_obs` (default 12) for TE/IR.

### 5.2 Active Share & Overlap
- If any side has shorts, compute **AS_longonly** (treat negatives as 0) and **AS_gross** (over |weights| sum); report both.

### 5.3 Active Return Stats
- Compute **a_t**, TE, IR, hit ratio, up/down capture, and active drawdown on **a_t**.  
- If `rolling` requested, slide window and recompute; if `timeseries`, compute pointwise AS & Δw tables per date against benchmark weights at that date (if provided) or most recent benchmark snapshot.

### 5.4 Group Differentials & Contributors
- Aggregate portfolio and benchmark by `dimension` (and `groupBy` parents).  
- Report **Δw_i** and **C_i** using per‑period **c_{i,t}** and **Carino** linking when `flags.carino_link`.

### 5.5 Factor Tilts & Active Risk
- If `factor_model.exposures` provided: compute **Δβ**.  
- If **Σ_f** (FCM) present: active factor variance; if `specific_vars` map present: add specific variance to get ex‑ante TE.  
- If not provided, skip with note.

### 5.6 Fixed‑Income Actives
- If instrument/group FI metrics provided (from RFC‑008), aggregate to portfolio & benchmark and compute diffs.

### 5.7 Edge Cases
- **Missing benchmark**: return 400 unless `metrics.active_return_stats=false` and only absolute weights requested; but endpoint is **benchmark‑centric**.  
- **Coverage gaps**: report coverage % for weights/exposures; if `strict_benchmark=true` and a group appears in portfolio but not benchmark, treat **b_i=0** (OK) but flag.

---

## 6) Architecture & Files
```
engine/
  active.py                           # active weights/AS/overlap, TE/IR, group diffs, factor risk

app/models/
  active_requests.py                  # Pydantic request schemas
  active_responses.py                 # Pydantic response schemas

app/api/endpoints/
  portfolio.py                        # add POST /portfolio/activeAnalytics
```

- Reuse: `engine/risk.py` for TE/IR & drawdowns, `engine/exposure.py` for grouping, `engine/attribution.py` Carino linker.

---

## 7) Testing Strategy
**Unit (engine/active.py)**
- Active Share, overlap, and concentration deltas on toy weights.  
- TE/IR/hit/capture vs closed‑form on synthetic returns.  
- Group differential sums reconciling to total active return; Carino linking correctness.  
- Factor tilt & active risk with toy Σ_f and specific vars.  
- FI actives aggregation.

**API**
- Schema validation; long‑only vs long/short; missing benchmark behavior.  
- Snapshot vs timeseries vs rolling outputs.  
- Top over/under sets and contributors shaping.

**Integration**
- Equity+bond mixed portfolio vs equity benchmark with look‑through; compare against reference notebook outputs.  
- Cross‑check TE/IR with RFC‑012 risk metrics on active series.

**Benchmarks**
- N instruments={1k, 10k}; p50 latency < 300ms for snapshot; rolling TE over 60 months < 500ms on 8 vCPU.

---

## 8) Observability & Limits
- Log: as_of, N instruments, dimension, TE, AS, coverage %.  
- Metrics (future): latency histograms, coverage distribution, Δβ magnitude distribution.  
- Limits: payload ≤ 25 MB; max instruments 50k; hierarchy depth ≤ 4.

---

## 9) Example Payloads
### 9.1 Snapshot — Sector actives with factor tilts & FI deltas
```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "dimension": "sector",
  "groupBy": ["assetClass"],
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "AAPL", "meta": {"sector": "Tech"}, "observations": [{"date": "2025-08-31", "mv": 125000}]},
    {"instrumentId": "UST_2030", "meta": {"assetClass": "Bond", "sector": "UST"}, "observations": [{"date": "2025-08-31", "mv": 400000}], "fi": {"dv01": 2200, "duration": 6.1}}
  ]},
  "benchmark_holdings": {"series": [ {"instrumentId": "SPY", "observations": [{"date": "2025-08-31", "mv": 350000}], "lookthrough": {"type": "index", "weights": {"AAPL": 0.07}} } ]},
  "returns": {"portfolio": [ {"date": "2024-09-30", "value": 0.006} ], "benchmark": [ {"date": "2024-09-30", "value": 0.005} ], "kind": "returns"},
  "factor_model": {"exposures": {"portfolio": {"MKT": 1.02, "SMB": -0.31, "MOM": 0.22}, "benchmark": {"MKT": 1.00, "SMB": -0.20, "MOM": 0.10}}, "fcm": {"labels": ["MKT","SMB","MOM"], "matrix": [[0.02,0,0],[0,0.01,0],[0,0,0.015]]}},
  "metrics": {"active_share": true, "overlap": true, "active_return_stats": true, "group_differentials": true, "factor_tilts": true, "active_risk": true, "fixed_income_actives": true}
}
```

### 9.2 Rolling — 36M TE & IR; timeseries AS
```json
{
  "mode": "rolling",
  "rolling": {"window": 36, "step": 1},
  "returns": {"portfolio": [ /* ≥36 points */ ], "benchmark": [ /* aligned */ ], "kind": "returns"},
  "metrics": {"active_return_stats": true}
}
```

---

## 10) Implementation Plan & Pseudocode
### 10.1 Files
1. `engine/active.py`  
2. `app/models/active_requests.py`  
3. `app/models/active_responses.py`  
4. `app/api/endpoints/portfolio.py` (add route)  
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)
```python
# engine/active.py

def compute_active(req: ActiveRequest) -> ActiveResult:
    # Weights path
    w_p, w_b, coverage = build_weights(req.holdings, req.benchmark_holdings, req.flags)
    active_share, overlap, conc = active_weight_stats(w_p, w_b)

    # Returns path
    a_series, te_ir = None, None
    if req.returns:
        r_p, r_b = preprocess_returns(req.returns, req.frequency)
        a = r_p.align(r_b, join='inner')[0] - r_b.align(r_p, join='inner')[0]
        te_ir = compute_te_ir_and_more(a, r_b)

    # Group diffs & contributors
    groups = None
    if req.metrics.group_differentials:
        groups = compute_group_diffs(req, link_carino=req.flags.carino_link)

    # Factor tilts
    factors = None
    if req.metrics.factor_tilts and req.factor_model and req.factor_model.exposures:
        factors = compute_factor_tilts_and_risk(req.factor_model)

    # FI actives
    fixed_income = None
    if req.metrics.fixed_income_actives:
        fixed_income = compute_fi_actives(req)

    return build_response(active_share, overlap, conc, te_ir, groups, factors, fixed_income)
```

---

## 11) Risks & Mitigations
- **Benchmark gaps / look‑through**: require explicit look‑through weights or treat unknowns as 0 and flag.  
- **Mixed long/short**: report both AS variants; document interpretation.  
- **Factor model mismatch**: validate factor labels vs Σ_f; otherwise skip with diagnostics.  
- **Double counting in groups**: ensure each instrument maps to exactly one bucket per dimension or use look‑through vectors summing to 1.

---

## 12) Future Extensions
- Ex‑ante TE via full risk model adapter (vendor).  
- Overlap by **names**, **sectors**, and **countries** with Jaccard/weight‑overlap matrices.  
- **Attribution bridge** deep‑link: drill from active differential to A/S/I attribution for the same period.  
- **Alerting** when AS/TE exceed thresholds.

---

**End of RFC**

