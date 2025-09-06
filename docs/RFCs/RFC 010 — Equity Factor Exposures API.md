# RFC 010 — Equity Factor Exposures API (`/portfolio/factorExposure`)

**Status:** Draft 1
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)
**Reviewers:** Perf Engine, Risk, Platform
**Target Release:** v0.3.x
**Related:** RFC‑006 (Attribution), RFC‑005 (Correlation), RFC‑009 (Exposure Breakdown)

---

## 1) Problem & Motivation

Portfolio managers and client advisors need to understand **which style and industry risk factors** the portfolio is exposed to, both **absolutely** and **relative to a benchmark**, in order to: (i) verify alignment to mandate (e.g., value tilt), (ii) control unintended bets (e.g., excessive momentum), (iii) explain performance via factor contributions, and (iv) manage active risk (tracking error) budgets.

This RFC defines an **API‑only**, stateless endpoint to compute **equity factor exposures** and (optionally) **factor risk** and **factor return contributions** via either:

* **Holdings‑based** method: aggregate security‑level factor exposures to portfolio/benchmark.
* **Time‑series regression** method: regress portfolio (or sleeve) returns on factor returns to estimate betas.
* **Hybrid**: blend holdings‑based exposures with regression shrinkage.

The endpoint supports **snapshot** (as‑of), **timeseries** (history), **active vs benchmark** deltas, **industry/region neutralization**, and **derivative mapping** (index futures/options via delta).

---

## 2) Goals & Non‑Goals

**Goals**

* Compute **portfolio and benchmark factor exposure vectors** and **active exposures**.
* Support **standard style factors** (e.g., Market, Size, Value, Momentum, Quality, Low Volatility, Growth, Investment, Profitability) and **industry/country factors**.
* Provide **time‑series regression** (OLS/Ridge) of portfolio returns on factor returns with configurable lookback/resampling.
* Optionally compute **factor risk decomposition** if factor covariance matrix (FCM) is supplied.
* Optionally compute **factor return contributions** over a period if factor return series provided.

**Non‑Goals (v1)**

* No internal estimation of risk model from scratch (user supplies factor library/exposures/FCM and/or factor returns).
* No automatic corporate action handling (caller’s holdings are assumed post‑CA).
* No multi‑asset factor model (equities only in v1).

---

## 3) Methodology & Formulas

### 3.1 Notation

* Securities indexed by **j**, factors by **k**, dates by **t**.
* Portfolio weights **w\_{j}** (net, MV‑normalized); benchmark weights **b\_{j}**.
* Security factor exposure vector **x\_{j} ∈ ℝ^K** (holdings‑based method).
* Factor returns **f\_{t} ∈ ℝ^K** (regression method).
* Factor covariance matrix **Σ\_f ∈ ℝ^{K×K}** (optional).
* Portfolio return **R\_{p,t}**, benchmark **R\_{b,t}**.

### 3.2 Holdings‑Based Exposures (HB)

Portfolio factor exposure (absolute):
$\beta^{HB}_p = \sum_j w_j \cdot x_j.$
Benchmark exposure: $\beta^{HB}_b = \sum_j b_j \cdot x_j$.
Active exposure: $\Delta\beta^{HB} = \beta^{HB}_p − \beta^{HB}_b.$

**Industry/Region neutralization** (optional): cross‑sectionally de‑mean **x\_j** within each neutralization bucket (e.g., within GICS industry and country) after **winsorization** and **z‑scoring**:

1. Winsorize raw descriptors to \[p, 1−p].
2. Standardize to z‑scores within bucket.
3. Orthogonalize target factor against control variables (e.g., regress value on size within bucket and use residuals) if `orthogonalize=true`.

### 3.3 Time‑Series Regression Exposures (TS)

Regress **excess** portfolio returns on factor returns over a lookback window of **T** periods:
$(R_{p,t} − R_{f,t}) = \alpha + \beta^{TS\top} f_t + \varepsilon_t.$
Estimate $\beta^{TS}$ via **OLS** (default) or **Ridge** (λ>0). Weights may be **EWMA** with decay **λ\_w**. Output: point estimates, standard errors, **R²**, and **α**.

### 3.4 Factor Risk (optional)

If **Σ\_f** provided, factor risk (variance) and tracking error (active) are:

* Portfolio factor variance: $\sigma^2_{fac,p} = \beta_p^{\top} Σ_f \beta_p$.
* Active factor variance: $\sigma^2_{fac,act} = (\Delta\beta)^{\top} Σ_f (\Delta\beta)$.
* Factor risk contributions (PRC): $RC_k = (\beta_p \odot (Σ_f \beta_p))_k / \sigma_{fac,p}$ (Euler allocation), similarly for active.

### 3.5 Factor Return Contributions (optional)

Given factor returns over period **t = 1..T** and fixed exposures **\hat{\beta}** (HB or TS):
$\text{FactorContrib}_k = \sum_{t=1}^{T} \hat{\beta}_k \cdot f_{k,t}.$
Active factor contribution similarly with **Δβ**. (For higher fidelity, re‑estimate exposures each period; v1 assumes fixed within report window.)

### 3.6 Derivatives Mapping

Map derivatives to equity factor exposures using **delta to underlying index/basket**. For index futures/options: exposure vector equals underlying index factor vector scaled by **delta × notional / MV\_total**; if unavailable, fallback to **benchmark factor vector** and flag.

---

## 4) API Design

### 4.1 Endpoint

`POST /portfolio/factorExposure`

### 4.2 Request Schema (Pydantic)

```jsonc
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",
  "mode": "snapshot",                           // "snapshot" | "timeseries" | "regression"

  // Model & library selection
  "model": {
    "name": "FF5+Mom",                           // e.g., FF3|FF5|Carhart4|HXZ|Vendor|Custom
    "factors": ["MKT", "SMB", "HML", "RMW", "CMA", "MOM"],
    "industry_factors": "GICS_24",               // optional: number of industries, or null
    "country_factors": true,                      // include country dummies
    "library_version": "v2025.08"                // caller/vendor schema version
  },

  // Holdings panel (for HB method and timeseries snapshot)
  "holdings": {
    "by": "instrument",                           // "instrument" | "group"
    "series": [
      {
        "instrumentId": "AAPL",
        "meta": {"country": "US", "industry": "Tech", "currency": "USD"},
        "observations": [ {"date": "2025-08-31", "mv": 125000.0 } ],
        "exposures": {                             // optional pre-computed per-security factors
          "SMB": -0.85, "HML": -0.40, "MOM": 0.35, "RMW": 0.10, "CMA": -0.25
        }
      }
    ]
  },

  // Benchmark holdings (optional, for active exposures)
  "benchmark": {
    "series": [ { "instrumentId": "SPY", "meta": {"country": "US", "industry": "Index"}, "observations": [ {"date": "2025-08-31", "mv": 350000.0 } ], "lookthrough": {"type": "index", "weights": {"AAPL": 0.07, "MSFT": 0.06}} } ]
  },

  // Security-level descriptor inputs (if server should compute x_j)
  "descriptors": {
    "winsor_p": 0.01,
    "standardize": "zscore",                      // "zscore" | "rank"
    "neutralize": { "by": ["industry", "country"], "orthogonalize": true }
  },

  // Regression mode inputs (for TS)
  "regression": {
    "returns": { "portfolio": [ {"date": "2025-01-31", "value": 0.012}, ... ], "benchmark": null },
    "factor_returns": [ {"date": "2025-01-31", "MKT": 0.01, "SMB": -0.002, ... }, ... ],
    "risk_free": [ {"date": "2025-01-31", "rf": 0.0002}, ... ],
    "frequency": "M",                            // "D"|"W"|"M"
    "lookback": 36,                               // periods
    "estimator": "ols",                          // "ols" | "ridge"
    "ridge_alpha": 5.0,
    "weights": { "type": "ewma", "lambda": 0.94 } // or {"type":"equal"}
  },

  // Factor covariance (optional) for risk decomposition
  "risk": {
    "fcm": { "matrix": [[0.02,0.0],[0.0,0.01]], "labels": ["MKT","SMB"] },
    "specific": null                               // optional map: instrumentId -> spec var
  },

  // Timeseries controls
  "timeseries": { "start": "2024-09-01", "end": "2025-08-31", "frequency": "M" },

  // Derivatives & look-through
  "derivatives": { "policy": "delta_index", "fallback": "benchmark_vector" },

  // Output & flags
  "output": {
    "include_active": true,
    "include_groups": ["industry", "country"],
    "top_factors": 10,
    "round": 6
  },
  "flags": {
    "normalize_weights": true,
    "treat_cash_zero_beta": true,
    "strict_coverage": false                       // 400 if missing x_j when true
  }
}
```

### 4.3 Response Schema — Snapshot (HB)

```json
{
  "as_of": "2025-08-31",
  "model": {"name": "FF5+Mom", "library_version": "v2025.08"},
  "method": "holdings",
  "portfolio": {
    "exposures": {"MKT": 1.02, "SMB": -0.31, "HML": -0.18, "MOM": 0.22, "RMW": 0.05, "CMA": -0.09},
    "risk": {"fac_var": 0.0142, "rc": {"MKT": 0.72, "SMB": 0.09, "HML": 0.04, "MOM": 0.10, "RMW": 0.03, "CMA": 0.02}},
    "notes": ["industry+country neutralized z-scores", "delta-mapped derivatives"]
  },
  "benchmark": {
    "exposures": {"MKT": 1.00, "SMB": -0.20, "HML": -0.25, "MOM": 0.10, "RMW": 0.02, "CMA": -0.10}
  },
  "active": {"exposures": {"MKT": 0.02, "SMB": -0.11, "HML": 0.07, "MOM": 0.12, "RMW": 0.03, "CMA": 0.01}},
  "groups": [
    {"key": {"industry": "Tech"}, "exposures": {"MOM": 0.35, "SMB": -0.70}, "weight": 0.28}
  ]
}
```

### 4.4 Response Schema — Regression (TS)

```json
{
  "method": "regression",
  "frequency": "M",
  "lookback": 36,
  "betas": {"MKT": 1.05, "SMB": -0.25, "HML": -0.12, "MOM": 0.30},
  "alpha": 0.0012,
  "stderr": {"MKT": 0.08, "SMB": 0.10, "HML": 0.09, "MOM": 0.07},
  "r2": 0.82,
  "diagnostics": {"dw": 1.9, "cond": 18.2}
}
```

### 4.5 Response Schema — Timeseries (HB)

```json
{
  "method": "holdings",
  "series": [
    {"date": "2025-01-31", "exposures": {"MKT": 1.01, "SMB": -0.28, "MOM": 0.18}},
    {"date": "2025-02-28", "exposures": {"MKT": 1.03, "SMB": -0.30, "MOM": 0.20}}
  ]
}
```

**HTTP codes**: 200 OK; 400 validation; 422 when insufficient data to compute exposures; 413 payload too large.

---

## 5) Computation Semantics

### 5.1 Coverage & Inputs

* **Holdings‑based** requires either security **exposures x\_j** supplied in request, or **descriptors** plus a **factor library** mapping descriptors → exposures (z‑score, neutralization, orthogonalization).
* **Regression** requires aligned **portfolio return series**, **factor returns**, and **risk‑free** (optional) with at least **lookback** periods. Missing values dropped pairwise.

### 5.2 Descriptor Pipeline (if computing x\_j)

1. Gather raw descriptors (e.g., ln(MktCap), B/P, past‑12‑2 momentum, ROE, leverage, volatility, investment growth).
2. **Winsorize** at `winsor_p`.
3. **Standardize** (z‑score or rank to \[−0.5,0.5]).
4. **Neutralize** within `by` buckets; if `orthogonalize=true`, regress target descriptor on controls (e.g., size) and use residuals.
5. Map standardized descriptors to **factor exposures x\_j** (1:1 unless provided by vendor schema).

### 5.3 Weight Construction

* Use **net MV** weights normalized to Σ=1 (exclude cash if `treat_cash_zero_beta=true`).
* For derivatives, apply `derivatives.policy` mapping.
* For benchmark active exposures, build **b\_j** similarly (with look‑through if provided).

### 5.4 Regression Estimation

* Form y\_t = portfolio excess return; X\_t = factor returns matrix.
* Apply weights (EWMA or equal).
* Compute OLS: $\hat{\beta} = (X^T W X)^{-1} X^T W y$.
* **Ridge**: $(X^T W X + λ I)^{-1} X^T W y$.
* Return **β**, **α**, **stderr** via Newey‑West (future) or homoskedastic (v1), **R²**.

### 5.5 Risk & Contributions

* If **FCM Σ\_f** provided, compute factor variance and **risk contributions** (Euler):
  $RC_k = \beta_k (Σ_f \beta)_k / (\beta^T Σ_f \beta)$.
* If **factor returns** for period provided, compute **factor return contributions** via §3.5.

### 5.6 Groups & Hierarchies

* If `include_groups` includes industry/country, compute group‑level exposures by re‑normalizing weights within group and aggregating **x\_j**.

### 5.7 Validation & Edge Cases

* If **coverage < threshold** (e.g., <90% of MV has exposures), add warning or `strict_coverage` → 400.
* If Σ weights ≈ 0 (long‑short near market neutral), allow but note; regression may require **benchmark** to form excess returns.
* For **collinearity** (regression): report condition number; ridge recommended.

---

## 6) Architecture & Files

```
engine/
  factors.py                        # HB aggregation, descriptor pipeline, regression, risk

app/models/
  factor_requests.py                # Pydantic: request schemas
  factor_responses.py               # Pydantic: response schemas

app/api/endpoints/
  portfolio.py                      # add POST /portfolio/factorExposure
```

* Reuse utilities (dates, resampling, errors, math guards).

---

## 7) Testing Strategy

**Unit (engine/factors.py)**

* HB aggregation correctness with/without derivatives & benchmark.
* Descriptor pipeline: winsorize, z‑score, neutralize, orthogonalize.
* Regression: OLS closed‑form on synthetic data; ridge shrinkage behavior; EWMA weights.
* Risk decomposition with toy Σ\_f (check Euler decomposition sums to 1).
* Factor contribution arithmetic given factor returns.

**API**

* Schema validation & helpful error messages.
* Snapshot vs timeseries vs regression modes.
* Coverage thresholds and strict\_coverage behavior.
* Large factor sets (K up to 100) and industries (up to 48) within limits.

**Integration**

* Synthetic portfolio with known x\_j; compare HB Δβ to hand‑calc.
* Reproduce known betas on simulated data with planted β and noise.

**Benchmarks**

* N securities={500, 5000}, K factors={10, 50}; ensure p50 < 600ms for N=5000, K=10 on 8 vCPU dev box.

---

## 8) Observability & Limits

* Log: as\_of, method, K factors, N securities, lookback, estimator, coverage %.
* Metrics (future): latency histograms, coverage distribution, regression condition numbers.
* Limits: K≤200, N≤50k (soft 20k), payload ≤25 MB.

---

## 9) Example Payloads

### 9.1 Snapshot — HB against benchmark with industry neutralization

```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "model": {"name": "FF5+Mom", "factors": ["MKT","SMB","HML","RMW","CMA","MOM"], "industry_factors": "GICS_24"},
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "AAPL", "meta": {"industry": "Tech", "country": "US"}, "observations": [{"date": "2025-08-31", "mv": 125000}], "exposures": {"SMB": -0.85, "HML": -0.4, "MOM": 0.35, "RMW": 0.1, "CMA": -0.25}},
    {"instrumentId": "MSFT", "meta": {"industry": "Tech", "country": "US"}, "observations": [{"date": "2025-08-31", "mv": 110000}], "exposures": {"SMB": -0.90, "HML": -0.5, "MOM": 0.30, "RMW": 0.2, "CMA": -0.20}}
  ]},
  "benchmark": {"series": [{"instrumentId": "SPY", "observations": [{"date": "2025-08-31", "mv": 350000}], "lookthrough": {"type": "index", "weights": {"AAPL": 0.07, "MSFT": 0.06}}}]},
  "descriptors": {"winsor_p": 0.01, "standardize": "zscore", "neutralize": {"by": ["industry","country"], "orthogonalize": true}},
  "output": {"include_active": true, "include_groups": ["industry","country"], "top_factors": 10}
}
```

### 9.2 Regression — 36M monthly OLS betas

```json
{
  "mode": "regression",
  "model": {"name": "Carhart4", "factors": ["MKT","SMB","HML","MOM"]},
  "regression": {
    "returns": {"portfolio": [ {"date": "2022-09-30", "value": 0.012}, ... 36 points ... ]},
    "factor_returns": [ {"date": "2022-09-30", "MKT": 0.01, "SMB": -0.002, "HML": 0.001, "MOM": 0.004}, ... ],
    "risk_free": [ {"date": "2022-09-30", "rf": 0.0002}, ... ],
    "frequency": "M", "lookback": 36, "estimator": "ols", "weights": {"type": "ewma", "lambda": 0.94}
  },
  "risk": {"fcm": {"labels": ["MKT","SMB","HML","MOM"], "matrix": [[0.02,0,0,0],[0,0.01,0,0],[0,0,0.01,0],[0,0,0,0.015]]}},
  "output": {"include_active": false}
}
```

### 9.3 Timeseries — Monthly HB exposures

```json
{
  "mode": "timeseries",
  "model": {"name": "Vendor", "factors": ["MKT","SIZE","VALUE","MOM","QUALITY","LOWVOL"]},
  "holdings": {"by": "instrument", "series": [ /* instruments with monthly MVs and x_j (per date or static) */ ]},
  "timeseries": {"start": "2024-09-01", "end": "2025-08-31", "frequency": "M"},
  "output": {"include_active": true}
}
```

---

## 10) Implementation Plan & Pseudocode

### 10.1 Files

1. `engine/factors.py`
2. `app/models/factor_requests.py`
3. `app/models/factor_responses.py`
4. `app/api/endpoints/portfolio.py` (add route)
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)

```python
# engine/factors.py

def compute_factor_exposure(req: FactorExposureRequest) -> FactorExposureResult:
    if req.mode in ("snapshot", "timeseries"):
        # holdings-based path
        panel = build_holdings_panel(req.holdings)               # date x instrument -> MV
        x = resolve_security_exposures(req)                      # dict[instrument][factor] from inputs or descriptors
        if req.mode == "snapshot":
            asof = req.as_of
            w = build_weights(panel.loc[asof], req.flags)
            beta_p = aggregate_exposures(w, x)
            beta_b = aggregate_benchmark(req, asof, x)
            out = build_snapshot(beta_p, beta_b, req, risk=req.risk)
            return out
        else:
            series = []
            for date, row in resample(panel, req.timeseries.frequency):
                w = build_weights(row, req.flags)
                beta_p = aggregate_exposures(w, x, date=date)
                beta_b = aggregate_benchmark(req, date, x)
                series.append((date, beta_p, beta_b))
            return build_timeseries(series, req, risk=req.risk)

    else:  # regression
        y, X, rf = align_returns(req.regression)
        betas, alpha, stderr, r2, diag = regress(y, X, req.regression)
        risk = factor_risk(betas, req.risk.fcm) if req.risk and req.risk.fcm else None
        return build_regression_response(betas, alpha, stderr, r2, diag, risk)
```

---

## 11) Risks & Mitigations

* **Coverage gaps** in x\_j: expose coverage %, allow `strict_coverage`, and support look‑through; fallback to regression when holdings HB is incomplete.
* **Multicollinearity** in regression: ridge option; report condition numbers.
* **Model mismatch** (factor library vs descriptors): embed `library_version` and validate factor set.
* **Derivative mapping ambiguity**: explicit policy and notes; require delta & notional when using `delta_index`.

---

## 12) Future Extensions

* Automatic enrichment from vendor risk model (Barra‑like) via adapter.
* Bayesian blending of HB and TS betas (Kalman).
* Style drift detection alarms (change‑point on Δβ).
* Multi‑asset factors (rates, credit, commodities) and cross‑asset model.
* Factor timing attribution (time‑varying β\_t).

---

**End of RFC**
