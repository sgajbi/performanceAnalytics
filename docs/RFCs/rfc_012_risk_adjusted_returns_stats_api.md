# RFC 012 — Risk‑Adjusted Returns & Stats API (`/analytics/riskMetrics`)

**Status:** Draft 1  
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC‑006 (Attribution), RFC‑007 (Allocation Drift), RFC‑008 (Fixed‑Income Metrics), RFC‑009 (Exposure), RFC‑011 (Scenario)

---

## 1) Problem & Motivation
Portfolio managers, client advisors, and clients need consistent, reproducible **risk‑adjusted performance statistics** for portfolios and sleeves, with optional **benchmark‑relative** metrics. This endpoint computes **returns, volatility, downside risk, drawdowns, tail risk (VaR/CVaR)**, and summary ratios (**Sharpe, Sortino, Information Ratio, Calmar, Treynor, Appraisal, Omega, etc.**) over user‑defined horizons, with **rolling windows** and **timeseries** outputs. The API is **stateless** and operates on caller‑supplied return or price series.

---

## 2) Goals & Non‑Goals
**Goals**
- Accept **returns** or **prices** and derive a complete set of risk/performance metrics.  
- Support **absolute** (vs risk‑free or MAR) and **active** (vs benchmark) statistics.  
- Provide **snapshot**, **rolling window**, and **timeseries** modes.  
- Robust missing‑data handling and annualization, with transparent assumptions.  
- Optional **confidence intervals** via bootstrap and **robust (HAC)** standard errors for alpha/beta.

**Non‑Goals**
- No persistence/scheduling.  
- No automatic data sourcing (caller supplies data).  
- No portfolio optimization (see future work).

---

## 3) Definitions & Formulas
Let period returns be **rᵖ_t** (portfolio), **rᵇ_t** (benchmark), and **rᶠ_t** (risk‑free), with **t = 1..T** after alignment.

**Compounding & Aggregation**
- **Cumulative return**: \( R_{cum} = \prod_{t=1}^{T} (1+r_t) - 1 \).  
- **CAGR** (annualized geometric mean): \( (1+R_{cum})^{A/T} - 1 \), where **A** is periods/year (252/52/12).  
- **Arithmetic mean (ann.)**: \( \bar{r}_{ann} = A \cdot \frac{1}{T}\sum_t r_t \).

**Volatility & Downside**
- **Volatility (ann.)**: \( \sigma_{ann} = \sqrt{A}\cdot \text{stdev}(r_t) \) (sample, ddof=1).  
- **Downside deviation (MAR m)**: \( D = \sqrt{ A\cdot \frac{1}{T}\sum_t \max(m - r_t, 0)^2 } \).

**Relative/Active Series**
- **Active return**: **a_t = rᵖ_t − rᵇ_t**.  
- **Tracking error (ann.)**: \( TE = \sqrt{A}\cdot \text{stdev}(a_t) \).  
- **Beta/Alpha (CAPM)** on **excess** returns y_t = rᵖ_t − rᶠ_t, x_t = rᵇ_t − rᶠ_t: OLS slope/intercept.  
- **Information Ratio**: **IR = mean(a_t)·A / TE** (or CAGR active / TE if `use_geometric=true`).

**Ratios**
- **Sharpe**: \( S = \frac{\bar{r} - \bar{r}^f}{\sigma} \) (ann. numerator/denominator).  
- **Sortino**: \( So = \frac{\bar{r} - MAR}{D} \).  
- **Calmar**: \( Ca = \frac{\text{CAGR}}{|\text{MaxDD}|} \).  
- **Treynor**: \( Tr = \frac{\bar{r} - \bar{r}^f}{\beta} \).  
- **Appraisal**: **α/TE**, where α is Jensen’s alpha (ann.).  
- **Omega (threshold θ)**: \( \Omega = \frac{\sum_t \max(r_t-\theta,0)}{\sum_t \max(\theta-r_t,0)} \) (discrete approx).

**Tail Risk**
- **Historical VaR/CVaR** at level **q**: empirical quantile of {r_t} and mean of tail below quantile.  
- **Parametric VaR/CVaR (Normal)**: \( VaR_q = \mu + \sigma \Phi^{-1}(q) \); CVaR via normal tail formula.  
- **Cornish–Fisher VaR**: adjust quantile using skew/kurtosis.

**Drawdowns**
- Equity curve **E_t = \prod_{i=1}^{t}(1+r_i)**; drawdown **DD_t = (E_t/\max_{i \le t} E_i) − 1**.  
- Report **MaxDD**, **AvgDD**, **AvgDD_Duration**, **Ulcer Index** (root‑mean‑square drawdown).

**Other Stats** (optional)
- **Hit ratio** (% positive), **avg gain**, **avg loss**, **payoff ratio** (avg gain/avg loss), **autocorr(1)**, **skew**, **excess kurtosis**.

---

## 4) API Design
### 4.1 Endpoint
`POST /analytics/riskMetrics`

### 4.2 Request Schema (Pydantic)
```jsonc
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",

  "mode": "snapshot",                          // "snapshot" | "timeseries" | "rolling"
  "timeseries_kind": "returns",                 // "returns" | "prices"
  "return_method": "simple",                    // if prices: "simple" | "log"
  "frequency": "M",                             // resample to D/W/M (default M)

  // Series inputs
  "portfolio": {
    "label": "PORT_A",
    "observations": [ {"date": "2024-01-31", "value": 0.012}, ... ]  // value=return or price depending on kind
  },
  "benchmark": {
    "label": "BMK",
    "observations": [ {"date": "2024-01-31", "value": 0.010}, ... ]
  },
  "risk_free": { "observations": [ {"date": "2024-01-31", "value": 0.0002}, ... ], "convention": "period" },

  // Alignment & data policy
  "alignment": {
    "mode": "intersection",                      // "intersection" | "union"
    "missing": "drop",                           // "drop" | "ffill" | "zero"
    "min_obs": 12                                 // minimum periods required
  },

  // Metric toggles
  "metrics": {
    "total_return": true,
    "cagr": true,
    "mean_arith": true,
    "volatility": true,
    "downside_dev": {"enabled": true, "mar": 0.0},
    "sharpe": true,
    "sortino": true,
    "calmar": true,
    "treynor": true,
    "beta_alpha": true,
    "tracking_error": true,
    "information_ratio": true,
    "appraisal_ratio": true,
    "omega": {"enabled": true, "threshold": 0.0},
    "tail": {
      "enabled": true,
      "method": "historical",                    // "historical" | "parametric" | "cornish"
      "levels": [0.95, 0.99],
      "horizon_days": 1
    },
    "drawdowns": {"enabled": true, "ulcer": true},
    "distribution": {"enabled": true, "quantiles": [0.01,0.05,0.5,0.95,0.99], "bins": 20},
    "moments": {"enabled": true}                 // skew, kurtosis, acf1
  },

  // Rolling & timeseries controls
  "rolling": { "window": 36, "step": 1 },        // periods; for mode="rolling"
  "timeseries": { "start": "2024-01-01", "end": "2025-08-31" },

  // Annualization & methods
  "conventions": {
    "annualization": {"periods_per_year": 12},
    "means": "arithmetic",                       // "arithmetic" | "geometric" for averages
    "ddof": 1,
    "winsor": {"enabled": false, "p": 0.01}
  },

  // Confidence intervals (optional)
  "inference": {
    "bootstrap": {"enabled": false, "samples": 5000, "seed": 42},
    "alpha_hac": {"enabled": false, "lags": 3}     // HAC SE for alpha/beta
  },

  // Output shaping
  "output": {
    "round": 6,
    "include_series": true,                        // include aligned series back in response
    "include_active": true
  }
}
```

### 4.3 Responses
**Snapshot**
```json
{
  "as_of": "2025-08-31",
  "window": {"start": "2024-09-30", "end": "2025-08-31", "n_obs": 12, "frequency": "M"},
  "portfolio": {
    "total_return": 0.082,
    "cagr": 0.079,
    "mean_arith_ann": 0.083,
    "vol_ann": 0.145,
    "downside_dev_ann": 0.096,
    "sharpe": 0.57,
    "sortino": 0.86,
    "calmar": 0.92,
    "treynor": 0.11,
    "beta": 1.02,
    "alpha_ann": 0.012,
    "tracking_error": 0.052,
    "information_ratio": 0.31,
    "appraisal_ratio": 0.23,
    "omega_0": 1.21,
    "tail": {"VaR": {"0.95": -0.031, "0.99": -0.055}, "CVaR": {"0.95": -0.042, "0.99": -0.070}},
    "drawdowns": {"max": -0.086, "ulcer": 0.024, "avg": -0.021, "avg_duration": 3},
    "moments": {"skew": -0.21, "ex_kurt": 0.84, "acf1": 0.05}
  },
  "active": {
    "cumulative": 0.018,
    "mean_ann": 0.019,
    "tracking_error": 0.052,
    "information_ratio": 0.36
  },
  "distribution": {"quantiles": {"p01": -0.052, "p05": -0.031, "p50": 0.007, "p95": 0.041, "p99": 0.068}, "hist": {"bins": 20, "min": -0.08, "max": 0.09}},
  "series": {"portfolio": [...], "benchmark": [...], "active": [...]},
  "notes": ["intersection alignment", "A=12", "returns interpreted as monthly"]
}
```

**Rolling**
```json
{
  "mode": "rolling",
  "rolling": {"window": 36, "step": 1},
  "series": [
    {"date": "2025-02-28", "sharpe": 0.48, "vol_ann": 0.151, "ir": 0.29},
    {"date": "2025-03-31", "sharpe": 0.50, "vol_ann": 0.149, "ir": 0.31}
  ]
}
```

**Timeseries**
```json
{
  "mode": "timeseries",
  "series": [
    {"date": "2024-09-30", "return": 0.006, "active": 0.001},
    {"date": "2024-10-31", "return": -0.012, "active": -0.007}
  ]
}
```

**HTTP codes**: 200 OK; 400 validation (schema/insufficient obs); 422 (inconsistent frequencies); 413 payload too large.

---

## 5) Computation Semantics
### 5.1 Pre‑processing
- Normalize dates; sort; de‑duplicate.  
- If `timeseries_kind=prices`, convert to returns per `return_method` then **compound** within resample buckets (D→M/W).  
- Align series by `alignment.mode`; resolve missing per `alignment.missing`.  
- Validate `n_obs ≥ min_obs` after alignment.

### 5.2 Annualization Conventions
- **A = periods_per_year** derived from output frequency unless overridden.  
- Use **sample stdev** (ddof=1).  
- When computing **mean_ann**, default to arithmetic mean × A; if `means="geometric"`, use CAGR.

### 5.3 Risk‑free & MAR
- Interpret risk‑free as **period rate** unless `convention` specifies annual and needs downscaling.  
- If risk‑free missing for a date, fill per `alignment.missing`; else treat as 0.

### 5.4 VaR/CVaR
- **Historical**: compute empirical quantiles on aligned portfolio returns; for horizon **h** days, scale σ by √h for parametric; for historical, if h>1, use block aggregation (future enhancement; v1 documents √h approximation for simplicity).  
- **Parametric**: fit mean/σ; compute VaR and CVaR closed‑form (Normal).  
- **Cornish–Fisher**: compute skew/kurt and adjust quantiles.

### 5.5 Drawdowns
- Build equity curve from **portfolio returns** only (not active).  
- Track peak, trough, depth, and duration; compute Ulcer Index over the window.

### 5.6 Inference
- **Bootstrap** (if enabled): resample returns with replacement (block bootstrap for autocorrelation in v1.1) to derive CI for Sharpe/IR/CAGR.  
- **HAC**: Newey–West variance for alpha/beta with `lags`.

### 5.7 Multi‑label Support (optional)
- If caller passes multiple portfolios (array), compute metrics per label and include a comparative table (v1 shape supported in models).

---

## 6) Architecture & Files
```
engine/
  risk.py                               # core metrics, windows, tails, drawdowns

app/models/
  risk_requests.py                       # Pydantic request models
  risk_responses.py                      # Pydantic response models

app/api/endpoints/
  analytics.py                           # add POST /analytics/riskMetrics
```

- Reuse shared utils: resampling, alignment, errors, math guards.

---

## 7) Testing Strategy
**Unit (engine/risk.py)**
- Price→return conversion; resampling; intersection/union alignment.  
- Volatility/mean annualization checks vs known results.  
- Downside deviation with MAR; Sharpe/Sortino on toy data.  
- Beta/alpha/TE/IR against closed‑form OLS computations.  
- Historical/parametric/Cornish VaR parity on synthetic distributions.  
- Drawdown and Ulcer Index correctness on constructed path.  
- Omega ratio thresholds.  
- Bootstrap CI reproducibility with fixed seed.

**API**
- Schema validation; min_obs enforcement; missing handling.  
- Rolling outputs shape and windowing edges.  
- Large payload performance within limits.

**Integration**
- Realistic monthly portfolio+benchmark+risk‑free across 5 years; compare to notebook ground truth.  
- Spot check active stats vs attribution/TE outputs.

**Benchmarks**
- T={60, 120, 600}; p50 latency < 150ms for single series T≤600 on 8‑vCPU dev box.

---

## 8) Observability & Limits
- Log: mode, frequency, A, n_obs, metrics_enabled, tail_method.  
- Metrics (future): latency histograms, bootstrap runtime, VaR coverage backtests.  
- Limits: payload ≤ 25 MB; max series labels=200; max observations per label=50k.

---

## 9) Example Payloads
### 9.1 Snapshot — Monthly, full metrics
```json
{
  "as_of": "2025-08-31",
  "mode": "snapshot",
  "timeseries_kind": "returns",
  "frequency": "M",
  "portfolio": {"label": "PORT_A", "observations": [
    {"date": "2024-09-30", "value": 0.006}, {"date": "2024-10-31", "value": -0.012}, {"date": "2024-11-30", "value": 0.018}, {"date": "2024-12-31", "value": 0.009}
  ]},
  "benchmark": {"label": "BMK", "observations": [
    {"date": "2024-09-30", "value": 0.005}, {"date": "2024-10-31", "value": -0.005}, {"date": "2024-11-30", "value": 0.017}, {"date": "2024-12-31", "value": 0.010}
  ]},
  "risk_free": {"observations": [{"date": "2024-09-30", "value": 0.0002}]},
  "metrics": {"sharpe": true, "sortino": true, "beta_alpha": true, "tracking_error": true, "information_ratio": true, "tail": {"enabled": true, "method": "historical", "levels": [0.95,0.99]}, "drawdowns": {"enabled": true, "ulcer": true}},
  "output": {"include_series": true, "include_active": true}
}
```

### 9.2 Rolling — 36M Sharpe/IR
```json
{
  "mode": "rolling",
  "rolling": {"window": 36, "step": 1},
  "timeseries_kind": "returns",
  "frequency": "M",
  "portfolio": {"label": "PORT_A", "observations": [ /* ≥36 monthly returns */ ]},
  "benchmark": {"label": "BMK", "observations": [ /* aligned */ ]},
  "metrics": {"sharpe": true, "information_ratio": true}
}
```

### 9.3 Prices — Daily with parametric VaR
```json
{
  "mode": "snapshot",
  "timeseries_kind": "prices",
  "return_method": "log",
  "frequency": "D",
  "portfolio": {"label": "PORT_A", "observations": [ {"date": "2025-08-25", "value": 100.0}, {"date": "2025-08-26", "value": 100.8}, ... ]},
  "metrics": {"tail": {"enabled": true, "method": "parametric", "levels": [0.975], "horizon_days": 10}},
  "conventions": {"annualization": {"periods_per_year": 252}}
}
```

---

## 10) Implementation Plan & Pseudocode
### 10.1 Files
1. `engine/risk.py`  
2. `app/models/risk_requests.py`  
3. `app/models/risk_responses.py`  
4. `app/api/endpoints/analytics.py` (add route)  
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)
```python
# engine/risk.py

def compute_risk_metrics(req: RiskRequest) -> RiskResult:
    p = to_series(req.portfolio)
    b = to_series(req.benchmark) if req.benchmark else None
    rf = to_series(req.risk_free) if req.risk_free else None

    # prices -> returns, resample, align
    p, b, rf = preprocess(p, b, rf, req)
    ensure_min_obs(p, req.alignment.min_obs)

    if req.mode == 'snapshot':
        stats = snapshot_metrics(p, b, rf, req)
        return build_snapshot_response(stats, req)

    elif req.mode == 'rolling':
        roll = []
        for end in rolling_ends(p.index, req.rolling.window, req.rolling.step):
            s = slice_series(p, b, rf, end, req.rolling.window)
            roll.append((end, snapshot_metrics(*s, req, rolling=True)))
        return build_rolling_response(roll, req)

    else:  # timeseries
        return build_timeseries_response(p, b, req)
```

---

## 11) Risks & Mitigations
- **Small samples**: enforce `min_obs`; report when statistic is unreliable (e.g., Sortino with few downside obs).  
- **Non‑normal returns**: offer Cornish–Fisher VaR, Omega ratio, and historical CVaR.  
- **Autocorrelation**: document annualization caveats; HAC option for alpha.  
- **Outliers**: optional winsorization; explicit flags in response.

---

## 12) Future Extensions
- Block bootstrap for VaR horizon scaling and CIs.  
- Bayesian shrinkage of TE and alpha estimates.  
- Multi‑portfolio comparison endpoint with ranking and quartile bands.  
- Backtesting module for VaR exceptions and Kupiec test.

---

**End of RFC**

