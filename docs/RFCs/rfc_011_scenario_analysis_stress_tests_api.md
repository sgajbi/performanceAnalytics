# RFC 011 — Scenario Analysis & Stress Tests API (`/analytics/scenario`)

**Status:** Draft 1  
**Owner:** Sandeep (Cyclops/PerformanceAnalytics)  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.0  
**Related:** RFC‑008 (Fixed‑Income Metrics), RFC‑009 (Exposure Breakdown), RFC‑010 (Factor Exposure), RFC‑007 (Allocation Drift), RFC‑005 (Correlation)

---

## 1) Problem & Motivation
Portfolio managers, advisors, and clients need to understand how portfolios would behave under **hypothetical, historical, and probabilistic shocks** to key market risk factors (rates, credit spreads, equities, FX, commodities). This API provides a **stateless** way to run **scenario analysis and stress tests** using either **first/second‑order sensitivities** (fast approximation) or **full repricing** (when inputs support it), returning portfolio‑, group‑, and instrument‑level P&L/return and **factor contributions**, plus **risk metrics** (e.g., VaR/CVaR for Monte Carlo).

Primary use cases:
- Pre‑trade and policy assessments ("what if rates +100bp?", "what if USD +5%?").
- Historical replay (e.g., **COVID‑19 selloff, Feb–Mar 2020**; **GFC 2008 week**; **Taper tantrum 2013**).
- Multi‑factor composite tests (simultaneous equity drawdown + spread widening + curve steepening).  
- Probabilistic stress (Monte Carlo) for capital adequacy / tail risk.

---

## 2) Goals & Non‑Goals
**Goals**
- Support **three scenario types**: `historical`, `hypothetical` (user‑defined shocks), and `monte_carlo` (stochastic).  
- Compute **instantaneous** (T+0) P&L via **Delta**/**DV01**/**KRD**/**beta**/**FX** sensitivities; optionally include **Gamma/Convexity** second‑order effects.  
- Optional **full repricing** for fixed income using curve/spread shifts (leveraging RFC‑008 engine).  
- Break out results **by factor**, **by group** (assetClass/sector/region/etc.), and **top/bottom contributors**.  
- Provide **return**, **value change**, and **risk** (VaR/CVaR for MC) in **base currency**.

**Non‑Goals (v1)**
- No exotic derivatives greeks beyond Δ/Γ/ρ/vega; no OAS Monte Carlo for callable MBS/ABS.  
- No automatic data sourcing; callers supply holdings, greeks/sensitivities, and curves/factor shocks.

---

## 3) Concepts & Notation
- Instruments **j** with market value **MV_j** (dirty if bonds).  
- Factor set **F** partitioned into categories: **RATES** (zero‑curve tenors), **CREDIT** (IG/HY or issuer spread), **EQUITY** (index levels or factor returns), **FX** (currency pairs), **CMDTY** (commodity fronts).  
- Sensitivities supplied per instrument:
  - **Rates**: DV01, **KRD** map `{tenor: dv01_t}`, **Convexity** (optional).  
  - **Credit**: spread DV01 (sDV01) or spread duration.  
  - **Equity**: **beta** to chosen index (or per‑index betas map). Options: **delta**, **gamma**.  
  - **FX**: **fx_delta** to base (or compute via currency meta + FX shock).  
  - **Other**: custom scalar sensitivities allowed via `custom[{name: value}]`.
- First‑order P&L (linear): **ΔV ≈ Σ_j Σ_f S_{j,f} · Δf**.  
- Second‑order: add **0.5 Σ_j Σ_f Γ_{j,f} · (Δf)^2** where available (Gamma/Convexity).

---

## 4) API Design
### 4.1 Endpoint
`POST /analytics/scenario`

### 4.2 Request Schema (Pydantic)
```jsonc
{
  "portfolio_number": "PORT123",
  "as_of": "2025-08-31",
  "currency": "USD",

  "mode": "hypothetical",                         // "historical" | "hypothetical" | "monte_carlo"
  "horizon": { "type": "instant", "days": 0 },   // "instant" | "horizon"; v1 computes instant; horizon uses compounding of shocks

  // Holdings & sensitivities
  "holdings": {
    "by": "instrument",                             // "instrument" | "group"
    "series": [
      {
        "instrumentId": "UST_2030",
        "meta": {"assetClass": "Bond", "currency": "USD", "sector": "UST"},
        "observations": [ {"date": "2025-08-31", "mv": 400000.0} ],
        "sensitivities": {
          "rates": { "dv01": 2200.0, "krd": { "2Y": 80.0, "5Y": 1400.0, "10Y": 720.0 }, "convexity_dollar": 900.0 },
          "credit": { "sdv01": 0.0 },
          "fx": null,
          "equity": null
        }
      },
      {
        "instrumentId": "SPX_FUT",
        "meta": {"assetClass": "Equity Derivative", "currency": "USD", "sector": "Index"},
        "observations": [ {"date": "2025-08-31", "mv": -50000.0, "qty": -2, "price": 5200.0, "multiplier": 50 } ],
        "sensitivities": { "equity": { "beta": 1.0, "delta": 1.0, "gamma": 0.0 } }
      }
    ]
  },

  // Scenario definition
  "scenario": {
    "name": "Curve +100bp & SPX -15% & USD +5%",
    "layers": [
      {
        "type": "rates",
        "curve": "USD_OIS",
        "shock": { "style": "parallel", "bump_bp": 100, "tenors": ["2Y","5Y","10Y"] }
      },
      {
        "type": "equity",
        "index": "SPX",
        "shock": { "pct": -0.15 }
      },
      {
        "type": "fx",
        "pair": "USD:ALL",
        "shock": { "pct": 0.05 }                    // broad USD +5%; engine maps via instrument currency
      },
      {
        "type": "credit",
        "bucket": "USD_IG",
        "shock": { "bump_bp": 75 }
      }
    ]
  },

  // Historical mode parameters (if mode = historical)
  "historical": {
    "window": { "start": "2020-02-20", "end": "2020-03-23" },
    "mapping": { "equity_index": "SPX", "rates_curve": "USD_OIS", "credit_bucket": "USD_IG", "fx_base": "USD" },
    "aggregation": "peak_to_trough"                 // "first_to_last" | "peak_to_trough" | "max_drawdown" (per factor)
  },

  // Monte Carlo parameters (if mode = monte_carlo)
  "monte_carlo": {
    "n_paths": 10000,
    "distribution": "gaussian",                      // "gaussian" | "student_t"
    "df": 6,                                         // if t
    "factors": {
      "labels": ["SPX", "USD_2Y", "USD_10Y", "USD_IG"],
      "mu":      [ -0.0005, 0.0001, 0.0002, 0.0000 ],
      "sigma":   [ 0.02,    0.0007, 0.0006, 0.0008 ],
      "corr":    [[1, -0.3, -0.4, 0.2], [-0.3,1,0.8,-0.2], [-0.4,0.8,1,-0.3], [0.2,-0.2,-0.3,1]]
    },
    "horizon_days": 1,
    "seed": 42,
    "var_levels": [0.95, 0.99]
  },

  // Calculation method
  "valuation": {
    "method": "sensitivity",                         // "sensitivity" | "full_reprice"
    "order": "first",                                // "first" | "second" (include convexity/gamma)
    "fixed_income_pricer": {                          // used when method=full_reprice
      "curve": { "type": "zero", "nodes": [ {"tenor": "2Y", "zero": 0.041}, {"tenor": "5Y", "zero": 0.039}, {"tenor": "10Y", "zero": 0.038} ], "interp": "log_df" },
      "spread_curve": { "bucket": "USD_IG", "nodes": [ {"tenor": "5Y", "spread": 0.013} ] }
    }
  },

  // Grouping & output shaping
  "groupBy": ["assetClass", "sector"],
  "output": {
    "top_contributors": 10,
    "by_factor": true,
    "by_group": true,
    "include_instruments": true,
    "round": 2
  },

  // Flags & limits
  "flags": {
    "normalize_weights": true,
    "treat_cash_fx_zero": true,
    "fail_on_missing_sensi": false,                  // if true → 400 when any sensitivity missing
    "assume_zero_when_missing": true
  }
}
```

### 4.3 Response Schema — Hypothetical (sensitivity, instantaneous)
```json
{
  "as_of": "2025-08-31",
  "mode": "hypothetical",
  "scenario": {"name": "Curve +100bp & SPX -15% & USD +5%"},
  "valuation": {"method": "sensitivity", "order": "first"},

  "portfolio": {
    "mv_before": 750000.0,
    "mv_after":  685000.0,
    "pnl":      -65000.0,
    "return":   -0.0867
  },

  "by_factor": [
    {"factor": "USD_OIS:parallel", "pnl": -48000.0},
    {"factor": "SPX", "pnl": -23000.0},
    {"factor": "USD:ALL", "pnl":  6000.0 },
    {"factor": "USD_IG:spread", "pnl": -0.0}
  ],

  "by_group": [
    {"key": {"assetClass": "Bond", "sector": "UST"}, "pnl": -44000.0, "return": -0.11},
    {"key": {"assetClass": "Equity Derivative", "sector": "Index"}, "pnl": -21000.0, "return": 0.42}
  ],

  "contributors": {
    "top_loss": [ {"instrumentId": "UST_2030", "pnl": -44000.0} ],
    "top_gain": [ ]
  },

  "notes": ["Missing sDV01 treated as 0 for UST_2030 credit", "USD broad FX shock applied by currency of instrument" ]
}
```

### 4.4 Response Schema — Historical
```json
{
  "mode": "historical",
  "window": {"start": "2020-02-20", "end": "2020-03-23"},
  "aggregation": "peak_to_trough",
  "factor_moves": {"SPX": -0.34, "USD_OIS:2Y": -120e-4, "USD_OIS:10Y": -140e-4, "USD_IG": 280e-4},
  "portfolio": {"pnl": -210000.0, "return": -0.12},
  "by_factor": [ ... ],
  "by_group": [ ... ]
}
```

### 4.5 Response Schema — Monte Carlo
```json
{
  "mode": "monte_carlo",
  "paths": 10000,
  "portfolio": {
    "var": {"0.95": -0.072, "0.99": -0.115},
    "cvar": {"0.95": -0.091, "0.99": -0.138},
    "mean_return": -0.006,
    "std_return": 0.028
  },
  "tail_contributors": {
    "by_factor": [ {"factor": "SPX", "avg_tail_pnl": -52000.0}, {"factor": "USD_10Y", "avg_tail_pnl": -18000.0} ],
    "by_group":  [ {"key": {"assetClass": "Bond"}, "avg_tail_pnl": -26000.0} ]
  },
  "worst_paths": [
    {"path": 8127, "return": -0.164, "by_factor": [ {"factor": "SPX", "pnl": -62000.0}, {"factor": "USD_10Y", "pnl": -23000.0} ]}
  ]
}
```

**HTTP codes**: 200 OK; 400 validation; 422 if no valid sensitivities after alignment; 413 payload too large.

---

## 5) Computation Semantics
### 5.1 Shock Application & Mapping
- **Rates**:
  - `parallel`: add **bump_bp** to all KRD tenors supplied; P&L per instrument: **ΔV ≈ −Σ_t KRD_t × Δy_t**; if only DV01 is provided and a parallel shock is requested, use **DV01 × avg(Δy)**.  
  - `bucketed`: `{tenor: bump_bp}` map.  
  - `twist`/`steepen`/`butterfly`: compute Δy_t by rules (e.g., +X at long, −X at short with linear taper).  
  - **Full repricing**: shift the discount curve per tenor, rebuild DFs, reprice CFs (RFC‑008); include convexity naturally.
- **Credit**: widen/narrow bucket or issuer spreads by **bump_bp**; P&L **≈ −sDV01 × Δs**; in full repricing, add spread to curve and reprice.  
- **Equity**: index shock **pct**; P&L **≈ beta × MV_equity × pct** (or **delta × underlying_notional** for futures/options); include **gamma × pct²/2** when provided.  
- **FX**: apply **pct** change of base vs instrument currency; P&L **≈ MV_foreign × Δfx** after base conversion.  
- **Commodities**: treat like equity delta with provided betas/deltas.

### 5.2 Factor Contribution Decomposition
- Record P&L contribution per layer. For overlapping layers (e.g., two rate layers), sum by factor key.  
- When using second‑order, split convexity/gamma contributions to their respective factor.

### 5.3 Group Aggregation
- Aggregate instrument P&L to requested `groupBy` tuples; compute **group return** as **group_pnl / group_mv_before**.  
- Provide **top_contributors** by absolute P&L.

### 5.4 Historical Window Construction
- Pull factor moves from the request (caller computes); engine **does not fetch market data**.  
- `first_to_last`: Δ factor = value_end − value_start;  
- `peak_to_trough`: use max adverse move within window per factor;  
- `max_drawdown`: compute factor path drawdown and apply terminal Δ.

### 5.5 Monte Carlo Sampling
- Build **Σ** from `sigma` and `corr`; draw **Z ~ N(0,Σ)** (or Student‑t with ν df).  
- Scale by **mu** and **horizon_days** (√t for vol).  
- For each path, compute instrument P&L via sensitivities; accumulate portfolio return.  
- Compute **VaR/CVaR** at requested levels and tail decompositions (average P&L contributions across tail paths).

### 5.6 Currency & Base Conversion
- Assume input MV in base currency; for FX scenarios, compute synthetic revaluation using supplied **pct** moves against base.  
- If instruments specify `currency != base`, FX shock applies to their MV for P&L.

### 5.7 Missing Data Policy
- If `fail_on_missing_sensi=true`, return 400 with a list of missing instruments and fields.  
- Else, treat missing sensitivity as 0 and add a **note** entry indicating assumptions.

---

## 6) Architecture & Files
```
engine/
  scenarios.py                     # core shock mapping, P&L calc, MC engine

app/models/
  scenario_requests.py             # Pydantic request models
  scenario_responses.py            # Pydantic response models

app/api/endpoints/
  analytics.py                     # add POST /analytics/scenario
```

- Reuse RFC‑008 fixed‑income pricer for `full_reprice` path.  
- Reuse common utils: date parsing, bucketing, currency, error mapping.

---

## 7) Testing Strategy
**Unit (engine/scenarios.py)**
- Rates DV01/KRD P&L against finite‑difference checks; convexity vs second‑difference.  
- Credit sDV01 mapping; equity beta vs delta notional parity for futures.  
- FX shock correctness with mixed currencies.  
- Layer composition (order‑independent for linear first‑order).  
- Monte Carlo moments (sample mean/var vs inputs) and VaR quantile accuracy.

**API**
- Schema validation & helpful errors; missing sensitivity behavior.  
- Hypothetical vs historical vs MC parity on constructed examples.  
- Full repricing path for bonds (compare to RFC‑008 engine).  
- Grouping and top contributors shaping.

**Integration**
- Synthetic multi‑asset portfolio running: +100bp parallel, −15% equity, USD +5%, and 2013 tantrum replay; compare to reference notebook.  
- MC tail decomposition reproducibility with fixed seed.

**Benchmarks**
- N instruments={1k, 10k}; K factors={5–20}; p50 < 400ms for N=10k on sensitivity method; MC 10k paths < 2s on 8 vCPU.

---

## 8) Observability & Limits
- Log: as_of, mode, layers count, N instruments, valuation method/order, MC paths.  
- Metrics (future): latency histogram, MC throughput, missing‑sensitivity ratio.  
- Limits: payload ≤ 25 MB; max instruments 50k; MC paths ≤ 1e6 (soft 100k).

---

## 9) Example Payloads
### 9.1 Hypothetical — Composite Shock (first‑order)
```json
{
  "as_of": "2025-08-31",
  "mode": "hypothetical",
  "holdings": {"by": "instrument", "series": [
    {"instrumentId": "UST_2030", "meta": {"assetClass": "Bond"}, "observations": [{"date": "2025-08-31", "mv": 400000}], "sensitivities": {"rates": {"dv01": 2200, "krd": {"2Y": 80, "5Y": 1400, "10Y": 720}}}},
    {"instrumentId": "SPX_FUT", "meta": {"assetClass": "Equity Derivative"}, "observations": [{"date": "2025-08-31", "mv": -50000, "qty": -2, "price": 5200, "multiplier": 50 }], "sensitivities": {"equity": {"beta": 1.0, "delta": 1.0}}}
  ]},
  "scenario": {"name": "Rates+100bp, SPX-15%", "layers": [
    {"type": "rates", "curve": "USD_OIS", "shock": {"style": "parallel", "bump_bp": 100, "tenors": ["2Y","5Y","10Y"]}},
    {"type": "equity", "index": "SPX", "shock": {"pct": -0.15}}
  ]},
  "valuation": {"method": "sensitivity", "order": "first"},
  "groupBy": ["assetClass"]
}
```

### 9.2 Historical — COVID Window (peak‑to‑trough)
```json
{
  "mode": "historical",
  "holdings": { /* as above */ },
  "historical": {
    "window": {"start": "2020-02-20", "end": "2020-03-23"},
    "mapping": {"equity_index": "SPX", "rates_curve": "USD_OIS", "credit_bucket": "USD_IG", "fx_base": "USD"},
    "aggregation": "peak_to_trough"
  },
  "valuation": {"method": "sensitivity", "order": "second"}
}
```

### 9.3 Monte Carlo — 10k one‑day shocks
```json
{
  "mode": "monte_carlo",
  "holdings": { /* as above */ },
  "monte_carlo": {
    "n_paths": 10000,
    "distribution": "gaussian",
    "factors": {
      "labels": ["SPX","USD_2Y","USD_10Y","USD_IG"],
      "mu": [0,0,0,0],
      "sigma": [0.02,0.0007,0.0006,0.0008],
      "corr": [[1,-0.3,-0.4,0.2],[-0.3,1,0.8,-0.2],[-0.4,0.8,1,-0.3],[0.2,-0.2,-0.3,1]]
    },
    "horizon_days": 1,
    "seed": 123,
    "var_levels": [0.95,0.99]
  },
  "valuation": {"method": "sensitivity", "order": "first"},
  "output": {"by_factor": true, "by_group": true, "top_contributors": 10}
}
```

---

## 10) Implementation Plan & Pseudocode
### 10.1 Files
1. `engine/scenarios.py`  
2. `app/models/scenario_requests.py`  
3. `app/models/scenario_responses.py`  
4. `app/api/endpoints/analytics.py` (router & endpoint)  
5. Tests under `tests/unit/engine/`, `tests/unit/`, `tests/integration/`

### 10.2 Engine Core (pseudocode)
```python
# engine/scenarios.py

def run_scenario(req: ScenarioRequest) -> ScenarioResult:
    panel = build_holdings_panel(req.holdings)  # date x instrument -> MV & sensi
    row = select_as_of(panel, req.as_of)
    shocks = build_shocks(req)  # flatten layers -> factor->delta

    if req.mode == 'monte_carlo':
        returns, by_factor_tail, worst = mc_paths(row, shocks, req.monte_carlo, req.valuation)
        return build_mc_response(returns, by_factor_tail, worst)

    # deterministic (historical/hypothetical)
    pnl_by_inst, pnl_by_factor = apply_shocks(row, shocks, req.valuation)
    agg = aggregate(pnl_by_inst, req.groupBy)
    return build_deterministic_response(agg, pnl_by_factor, req)
```

---

## 11) Risks & Mitigations
- **Missing/incorrect sensitivities** → explicit flags, fail‑fast option, detailed notes in response.
- **Curve mismatch** in full repricing → validate tenor coverage & extrapolation flags.  
- **Double counting across layers** → factor key canonicalization; sum by unique key.  
- **MC numerical stability** → Cholesky with jitter; seed control; path batching.

---

## 12) Future Extensions
- Path‑dependent horizons (multi‑step scenarios), liquidity haircuts, and funding/financing costs.  
- Options vega/vanna/vomma layers; volatility surface shocks.  
- Integrated optimizer: recommend hedges to reduce scenario loss (linear program).

---

**End of RFC**

