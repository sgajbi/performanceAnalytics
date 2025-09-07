# API Reference (Exact Endpoints & Shapes)

All endpoints live under `/performance` in `app/api/endpoints/performance.py`.

## POST /performance/twr
- **Request model**: `app/models/requests.PerformanceRequest`
- **Response model**: `app/models/responses.PerformanceResponse`

### Minimal Request
```json
{
  "portfolio_number": "PF-001",
  "daily_data": [
    { "day": 1, "perf_date": "2025-01-02", "begin_mv": 1000000.0, "bod_cf": 0.0, "eod_cf": 0.0, "end_mv": 1020000.0 }
  ],
  "metric_basis": "NET",
  "as_of": "2025-01-31",
  "precision_mode": "FLOAT64",
  "rounding_precision": 6,
  "calendar": { "type": "BUSINESS", "trading_calendar": "NYSE" },
  "periods": { "type": "EXPLICIT", "explicit": { "start": "2025-01-01", "end": "2025-01-31", "frequency": "daily" } },
  "output": { "include_timeseries": true, "include_cumulative": true }
}
```

### Response (shape excerpt)
```json
{
  "calculation_id": "uuid",
  "portfolio_number": "PF-001",
  "breakdowns": {
    "daily": [ { "perf_date": "2025-01-02", "daily_ror": 0.02, "final_cum_ror": 0.02, "long_short": "L" } ],
    "period": { "start": "2025-01-01", "end": "2025-01-31", "ror": 0.0199, "annualized_ror": 0.2765 }
  },
  "meta": { "precision_mode": "FLOAT64", "annualization": {"enabled": false}, "calendar": {"type":"BUSINESS","trading_calendar":"NYSE"}, "periods": { "...": "..." } },
  "diagnostics": { "nip_days": 0, "reset_days": 0, "effective_period_start": "2025-01-01", "notes": [] },
  "audit": { "sum_of_parts_vs_total_bp": 0.0, "residual_applied_bp": 0.0, "counts": { "rows": 1 } }
}
```

---

## POST /performance/mwr
- **Request model**: `app/models/mwr_requests.MoneyWeightedReturnRequest`
- **Response model**: `app/models/mwr_responses.MoneyWeightedReturnResponse`

### Minimal Request
```json
{
  "begin_mv": 1000000.0,
  "end_mv": 1030000.0,
  "cash_flows": [
    { "amount": 50000.0, "date": "2025-01-15" }
  ],
  "solver": { "method": "XIRR" },
  "as_of": "2025-01-31",
  "precision_mode": "FLOAT64",
  "calendar": { "type": "BUSINESS", "trading_calendar": "NYSE" }
}
```

### Response (shape excerpt)
```json
{
  "mwr": 0.01873456,
  "method": "XIRR",
  "convergence": { "iterations": 23, "residual": 1.2e-10, "converged": true },
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "notes": ["xirr_converged"],
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "...": "..." }
}
```

---

## POST /performance/contribution
- **Request model**: `app/models/contribution_requests.py` (positions + options)
- **Response model**: `app/models/contribution_responses.py`

Key controls:
- `weighting_scheme`: `"BOD" | "AVG_CAPITAL" | "TWR_DENOM"` (see `common/enums.WeightingScheme`)
- `smoothing.method`: `"carino" | "log" | "none"` (see `common/enums.LinkingMethod` where used)
- `emit.timeseries: bool`

---

## POST /performance/attribution
- **Request model**: `app/models/attribution_requests.py`
- **Response model**: `app/models/attribution_responses.py`

Key controls:
- `benchmark.mode`: `"BY_GROUP" | "BY_INSTRUMENT"`
- `frequency`: `"daily" | "weekly" | "monthly" | "quarterly" | "yearly"` (see `common/enums.Frequency`)
- `linking`: `"carino" | "log" | "none"`
