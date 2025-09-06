# RFC 005 — Portfolio Correlation Matrix API (`/portfolio/correlationMatrix`)

**Status:** Draft 1
**Owner:** Sandeep 
**Reviewers:** Platform, Perf Engine, Risk
**Target Release:** v0.2.0
**Related:** TWR/MWR engines, Contribution engine, RFC-001/002/003/004

---

## 1) Problem & Motivation

Portfolio managers, client advisors, and clients need a quick way to assess **diversification** and **co-movement** within a portfolio. A correlation matrix over instrument/sector/asset-class returns highlights clusters (highly correlated) and diversifiers (low/negative correlation). Exposing this as an API unlocks:

* Automated diversification checks and drift signals.
* Inputs to optimizers/allocators (risk-parity, mean–variance).
* Pre-trade impact analysis ("what does adding X do to correlations?").

We will add an **API-only** endpoint to compute correlations for a supplied set of time series (prices or pre-computed returns). No persistent store is introduced; computation is **stateless per request**.

---

## 2) Goals & Non‑Goals

**Goals**

* Provide a robust, numerically stable **Pearson (default)** correlation matrix; optional **Spearman**.
* Accept time series for **instruments or groups** (sector/region/assetClass/currency buckets).
* Support **return derivation** from prices (simple/log), or accept returns directly.
* Handle missing data sensibly: alignment, trimming/pairwise NA policy, and min samples.
* Offer results as **full symmetric matrix** and **edge list** (flattened pairs) with filtering (top‑N by |corr|, thresholds).
* Provide **rolling correlation** mode (window, step) returning last-window matrix (v1) and optional history (v1.1+).

**Non‑Goals**

* No storage, scheduling, or portfolio lookup from external systems.
* No factor model or covariance shrinkage (could be future extensions).

---

## 3) API Design

### 3.1 Endpoint

`POST /portfolio/correlationMatrix`

### 3.2 Request Model (Pydantic)

```jsonc
{
  "portfolio_number": "PORT123",               // optional, passthrough for client logs
  "as_of": "2025-08-31",                       // optional, metadata only
  "timeseries_kind": "returns",                 // "returns" | "prices"
  "return_method": "simple",                    // when timeseries_kind = prices: "simple" | "log"
  "frequency": "D",                             // "D"|"W"|"M" (resample rule); default D
  "roll": {                                      // optional rolling window settings
    "enabled": false,
    "window": 60,                                // integer periods post-resample
    "min_periods": 30,                           // minimum samples to compute
    "step": 1                                    // compute every N periods; v1 returns last window only
  },
  "alignment": {                                 // alignment & NA handling
    "mode": "intersection",                    // "intersection" | "union"
    "missing": "pairwise_drop",                // "pairwise_drop" | "fill_forward" | "fill_zero"
    "max_forward_fill": 5                        // only if fill_forward
  },
  "min_overlap": 20,                             // minimum overlapping observations per pair
  "correlation": {
    "method": "pearson",                        // "pearson" | "spearman"
    "ddof": 1                                    // degrees of freedom for std (pearson path)
  },
  "grouping": {                                  // optional rollup before correlation
    "dimension": null,                           // e.g. "sector" | "assetClass" | "region"
    "aggregation": "cap_weighted"               // "equal" | "cap_weighted" | "sum"; requires weights when cap_weighted
  },
  "series": [                                    // list of labeled series
    {
      "id": "AAPL",                            // label used in output matrix
      "meta": { "sector": "Technology", "weight": 0.04 },
      "observations": [                          // either returns or prices depending on timeseries_kind
        { "date": "2025-01-02", "value": 198.32 },
        { "date": "2025-01-03", "value": 199.50 }
      ]
    },
    { "id": "MSFT", "meta": {"sector": "Technology", "weight": 0.03}, "observations": [ ... ] }
  ],
  "output": {
    "format": "matrix",                          // "matrix" | "edges"
    "abs_sort_desc": true,                        // for edges format
    "top_n": 100,                                 // for edges format
    "threshold": null,                            // for edges format; include pairs with |corr|>=threshold
    "include_self": false                         // include diagonal in edges
  }
}
```

### 3.3 Response Model

**Matrix format**

```json
{
  "as_of": "2025-08-31",
  "method": "pearson",
  "frequency": "D",
  "roll": { "enabled": false },
  "labels": ["AAPL", "MSFT", "GOOGL"],
  "matrix": [
    [ 1.0,   0.82,  0.75 ],
    [ 0.82,  1.0,   0.68 ],
    [ 0.75,  0.68,  1.0  ]
  ],
  "n_obs": [ 120, 118, 119 ],                   // per-label usable points after alignment
  "pairwise_n": [
    [ 120, 118, 117 ],
    [ 118, 118, 116 ],
    [ 117, 116, 119 ]
  ],
  "stats": { "min": -0.21, "max": 0.94, "mean": 0.37 }
}
```

**Edges format**

```json
{
  "as_of": "2025-08-31",
  "method": "pearson",
  "edges": [
    { "i": "AAPL", "j": "MSFT", "corr": 0.82, "n": 118 },
    { "i": "AAPL", "j": "GOOGL", "corr": 0.75, "n": 117 }
  ]
}
```

### 3.4 HTTP Semantics & Errors

* **200 OK** — successful computation.
* **400 Bad Request** — schema/validation errors (e.g., empty series, insufficient observations, unknown modes).
* **422 Unprocessable Entity** — after alignment, pair overlaps < `min_overlap` for all pairs.
* **413 Payload Too Large** — enforce size guardrails (see §9).
* **500 Internal Server Error** — unexpected.

Error payload shape:

```json
{ "error": { "code": "MIN_OVERLAP_VIOLATION", "message": "No pair has >= min_overlap=20 observations" } }
```

---

## 4) Data & Computation Semantics

### 4.1 Returns vs Prices

* If `timeseries_kind = returns`, values are treated as period returns already aligned to provided `frequency`.
* If `timeseries_kind = prices`, compute returns using `return_method`:

  * **simple:** r\_t = P\_t / P\_{t-1} - 1
  * **log:**    r\_t = ln(P\_t) - ln(P\_{t-1})

### 4.2 Resampling

* Resample by `frequency` using **last** observation within bucket for prices, **sum** (or **mean**) for returns (configurable later; v1 = sum for arithmetic chainability). Drop buckets with <1 observation.

### 4.3 Alignment & Missing Data

* Build a common date index using `alignment.mode`:

  * **intersection**: only dates present in **all** series.
  * **union**: all dates across series (use NA where missing).
* Handle missing per `alignment.missing`:

  * **pairwise\_drop**: for each pair, drop rows where either is NA (maximizes usable overlap per pair).
  * **fill\_forward**: forward-fill up to `max_forward_fill` gaps; then drop remaining NA pairwise.
  * **fill\_zero**: fill NA with 0 (use with caution; documents bias).
* Enforce `min_overlap` AFTER pairwise NA policy. Pairs below threshold are excluded (matrix entry = null) or the entire request fails (v1 behavior: fail if **all** pairs below; otherwise set nulls and report in `pairwise_n`).

### 4.4 Correlation Method

* **Pearson (default)**: corr(x,y) = cov(x,y)/(σ\_x σ\_y), with `ddof` for std.
* **Spearman**: rank-transform each series with average ranks for ties, then Pearson on ranks.
* Numerical guards: if σ\_x==0 or σ\_y==0 post-trim, corr is `null` (or 0 if explicitly requested later).

### 4.5 Grouping/Aggregation

* If `grouping.dimension` provided and the `series[].meta` contains that key, first **aggregate** to group-level series:

  * **equal**: arithmetic mean of member returns per date.
  * **cap\_weighted**: weighted mean using `meta.weight` (weights normalized per group per date; if missing, fall back to equal).
  * **sum**: sum of member returns (for contribution-like inputs).
* After aggregation, proceed with correlation on group series.

### 4.6 Rolling Correlation (v1)

* When `roll.enabled=true`, build a trailing window of length `roll.window` over the aligned panel (post NA policy) and compute correlations for the **last** window.
* Validate `roll.min_periods <= roll.window` and `roll.window <= total_samples`.
* v1 only returns the terminal window matrix; history output is a future enhancement (v1.1).

---

## 5) Architecture & Implementation

### 5.1 New Modules

```
engine/
  correlations.py           # core algorithms & helpers

app/models/
  correlation_requests.py   # Pydantic request models
  correlation_responses.py  # Pydantic response models

app/api/endpoints/
  portfolio.py              # router for /portfolio/* (correlationMatrix)
```

### 5.2 Engine (`engine/correlations.py`)

Responsibilities:

* Parse/validate to DataFrame: pivot to wide format (index=date, columns=series id, values=returns/prices).
* Resample per frequency.
* Convert prices→returns if needed.
* Apply alignment and NA policy.
* Compute correlation matrix and auxiliary stats (n per label, pairwise\_n, min/max/mean).
* Optional grouping: aggregate to groups prior to correlation.
* Optional rolling computation.

Performance considerations:

* Use `pandas.DataFrame.corr(method="pearson"|"spearman", min_periods=...)` when pairwise policy is used; or implement pairwise loops for `min_overlap` enforcement and `pairwise_n` accounting.
* For large N (series count), memory dominates (O(N^2)). Provide guardrails (see §9).

### 5.3 API Layer

* **Router**: `app/api/endpoints/portfolio.py` with `router = APIRouter(prefix="/portfolio")`.
* Endpoint function: `@router.post("/correlationMatrix", response_model=CorrelationMatrixResponse)`.
* Input validation: ensure ≥2 series; ensure sufficient observations after alignment; enforce limits.
* Exceptions mapped to `PerformanceCalculatorError` for consistent handler.

### 5.4 Configuration

* No new global settings required; use request-scoped parameters.
* Introduce constants for hard limits (max series, max observations) in `app/core/constants.py` (or reuse if already present).

---

## 6) Testing Strategy

**Unit Tests (engine)**

* Price→return conversion correctness (simple & log).
* Resampling behavior (D→W/M).
* Alignment modes (intersection/union) + NA policies (drop/fill).
* Pearson vs Spearman parity on monotonic transforms.
* Grouping aggregation correctness (equal, cap\_weighted).
* Rolling correlation window edges (min\_periods, terminal window selection).
* Numerical edge cases: constant series (σ=0), disjoint date ranges, insufficient overlap.

**Unit Tests (API)**

* Schema validation errors, helpful messages.
* Enforced guardrails (series count, payload size).
* Response shapes for matrix vs edges, top‑N and threshold filters.

**Integration Tests**

* Small synthetic portfolio (5–10 series) across 100–250 days; verify spot correlations against NumPy/Pandas ground truth.
* Grouping by sector end-to-end.
* Rolling window end-to-end.

**Benchmarks**

* N={50, 250, 500} series, T={252, 1000} days; record latency and memory; ensure within targets (see §9).

---

## 7) Observability & Errors

* Log request metadata: series\_count, total\_points, frequency, method, roll.enabled.
* Metrics (future): histogram of runtime, gauge of N and T, error counters per error code.
* Deterministic error codes/messages (see §3.4) for client handling.

---

## 8) Security & Compliance

* Stateless computation; no persistence of payloads.
* Size limits prevent abuse and memory pressure.
* Consider optional request hashing for dedupe in upstream layers (external concern).

---

## 9) Limits & Performance Targets

* **Max series (labels):** 1000 (soft), 2000 (hard reject).
* **Max observations per series:** 10,000 (post-resample).
* **Max payload size:** 25 MB (413 if exceeded).
* **Latency targets (p50 on 8 vCPU dev box):**

  * N≤250, T≤252: < 300ms
  * N≤500, T≤252: < 1s
  * N≤1000, T≤252: < 3s
* Memory: O(N²) for matrix; advise `output.format=edges` for large N.

---

## 10) Backward & Forward Compatibility

* New endpoint; no breaking changes.
* Optional fields have sensible defaults.
* Future: covariance matrix endpoint; shrinkage estimators; factor correlations; history for rolling.

---

## 11) Example Payloads

### 11.1 Returns, Matrix

```json
{
  "timeseries_kind": "returns",
  "frequency": "D",
  "series": [
    {"id": "AAPL", "observations": [{"date": "2025-01-02", "value": 0.012}, {"date": "2025-01-03", "value": -0.004}]},
    {"id": "MSFT", "observations": [{"date": "2025-01-02", "value": 0.010}, {"date": "2025-01-03", "value": -0.006}]}
  ]
}
```

### 11.2 Prices→Returns, Edges, Spearman

```json
{
  "timeseries_kind": "prices",
  "return_method": "log",
  "output": { "format": "edges", "top_n": 10, "abs_sort_desc": true },
  "correlation": { "method": "spearman" },
  "series": [
    {"id": "AAPL", "observations": [{"date": "2025-01-02", "value": 198.32}, {"date": "2025-01-03", "value": 199.50}]},
    {"id": "MSFT", "observations": [{"date": "2025-01-02", "value": 405.10}, {"date": "2025-01-03", "value": 406.00}]}
  ]
}
```

### 11.3 Grouping by Sector (Cap‑Weighted)

```json
{
  "timeseries_kind": "returns",
  "grouping": {"dimension": "sector", "aggregation": "cap_weighted"},
  "series": [
    {"id": "AAPL", "meta": {"sector": "Tech", "weight": 0.04}, "observations": [...]},
    {"id": "MSFT", "meta": {"sector": "Tech", "weight": 0.03}, "observations": [...]},
    {"id": "JNJ",  "meta": {"sector": "Health", "weight": 0.02}, "observations": [...]}
  ]
}
```

### 11.4 Rolling Correlation (60D window)

```json
{
  "timeseries_kind": "returns",
  "roll": {"enabled": true, "window": 60, "min_periods": 40},
  "series": [ /* ≥60 daily returns per series */ ]
}
```

---

## 12) Implementation Plan (Files & Full Paths)

1. **`engine/correlations.py`** — implement helpers:

   * `_pivot_series_to_wide(df)`, `_resample_panel(panel)`, `_prices_to_returns(panel, method)`, `_apply_alignment(panel, mode, missing, max_ffill)`, `_aggregate_groups(panel, meta, dimension, aggregation)`, `_corr_pairwise(panel, method, min_overlap, ddof)`.
   * `compute_correlation_matrix(request: CorrelationMatrixRequest) -> CorrelationMatrixResult`.

2. **`app/models/correlation_requests.py`** — Pydantic models mirroring §3.2.

3. **`app/models/correlation_responses.py`** — Pydantic models for matrix/edges.

4. **`app/api/endpoints/portfolio.py`** — FastAPI endpoint and router registration (added in `main.py`).

5. **Tests**

   * `tests/unit/engine/test_correlations.py`
   * `tests/unit/test_portfolio_correlation_api.py`
   * `tests/integration/test_correlation_api.py`

6. **`app/core/constants.py`** — (if not present) add limits; otherwise create `app/core/constants.py` with correlation-specific caps.

7. **`README.md`** — add quick usage example under Advanced Usage.

---

## 13) Pseudocode (Engine Core)

```python
# engine/correlations.py

def compute_correlation_matrix(req: CorrelationMatrixRequest) -> CorrelationMatrixResult:
    # 1) to long-frame
    rows = []
    meta = {}
    for s in req.series:
        meta[s.id] = s.meta or {}
        for obs in s.observations:
            rows.append((obs.date, s.id, obs.value))
    df = pd.DataFrame(rows, columns=["date", "id", "value"]).dropna()
    df["date"] = pd.to_datetime(df["date"])  # normalize dates

    # 2) pivot to wide
    panel = df.pivot(index="date", columns="id", values="value").sort_index()

    # 3) resample
    panel = resample_panel(panel, req.frequency, req.timeseries_kind)

    # 4) prices -> returns
    if req.timeseries_kind == "prices":
        panel = prices_to_returns(panel, method=req.return_method)

    # 5) grouping
    if req.grouping.dimension:
        panel = aggregate_groups(panel, meta, req.grouping)

    # 6) alignment/NA policy
    panel = apply_alignment(panel, req.alignment)

    # 7) rolling window selection
    if req.roll.enabled:
        panel = panel.iloc[-req.roll.window:]
        if len(panel) < req.roll.min_periods:
            raise MinOverlapViolation("Insufficient samples for rolling window")

    # 8) compute pairwise corr and pairwise_n
    matrix, pairwise_n = corr_pairwise(panel, method=req.correlation.method, min_overlap=req.min_overlap, ddof=req.correlation.ddof)

    # 9) build response (matrix or edges)
    if req.output.format == "matrix":
        return build_matrix_response(panel.columns, matrix, pairwise_n)
    else:
        return build_edges_response(panel.columns, matrix, pairwise_n, req.output)
```

---

## 14) Copy‑Paste Git Steps (once code is generated)

```bash
# from repo root
git checkout -b feature/correlation-matrix-api

# add engine + models + endpoint + tests
git add engine/correlations.py \
        app/models/correlation_requests.py \
        app/models/correlation_responses.py \
        app/api/endpoints/portfolio.py \
        app/core/constants.py \
        tests/unit/engine/test_correlations.py \
        tests/unit/test_portfolio_correlation_api.py \
        tests/integration/test_correlation_api.py \
        README.md

git commit -m "feat(api): Add /portfolio/correlationMatrix endpoint with engine + tests\n\nProvides Pearson/Spearman correlation matrix with robust alignment/NA policy, grouping,\nrolling window, and edges/matrix outputs. Includes unit+integration tests and limits."

pytest -q
uvicorn main:app --reload
```

---

## 15) Risks & Mitigations

* **Large N (O(N²))**: provide guardrails, recommend `edges` output, and enable label filtering server-side.
* **Data quality**: explicit policies for NA handling and min-overlap to avoid misleading correlations.
* **Misuse of fill\_zero**: documented as biasing; default remains pairwise-drop.

---

## 16) Future Extensions

* Covariance matrix + shrinkage (Ledoit–Wolf) and risk model integration.
* Factor correlations and cross-asset block structure outputs.
* Rolling correlation history with change-point detection.
* On-demand covariance → minimum-variance weights helper endpoint.

---

 