# Data Model (Canonical, snake_case)

This document defines the canonical request/response fields used across all endpoints. All names are **snake_case**. Dates are ISO‑8601 (`YYYY-MM-DD`). Numbers are decimal strings or JSON numbers depending on precision mode.

## Common Types
- **Date**: `YYYY-MM-DD`
- **Decimal**: JSON number or string (when `DECIMAL_STRICT`), rounded by API.
- **Enum**: fixed set of uppercase tokens.

## Portfolio Time Series Schema
For TWR/Contribution/Attribution inputs:

```json
{
  "portfolio": {
    "id": "string",
    "base_currency": "USD"
  },
  "series": [
    {
      "date": "2025-01-02",
      "begin_mv": 1000000.0,
      "bod_cf": 0.0,
      "fees": 0.0,
      "tx_costs": 0.0,
      "eod_cf": 0.0,
      "end_mv": 1015000.0
    }
  ]
}
```

### Field Definitions
- `begin_mv` — Market value at start of the day/period (post‑BOD CF).
- `bod_cf` — Cash flows applied at beginning of day (subscriptions/redemptions).
- `fees` — Management/advisory fees (negative for charges).
- `tx_costs` — Transaction/execution costs (negative for costs).
- `eod_cf` — Cash flows applied at end of day.
- `end_mv` — Market value at end of day after EOD CF.

> If your data separates **gross** vs **net** effects, set `fees`/`tx_costs` accordingly and choose the metric basis at request time.

## Position‑Level Series (Contribution/Attribution)
```json
{
  "positions": [
    {
      "id": "AAPL",
      "name": "Apple Inc.",
      "group_keys": { "sector": "Technology", "region": "US" },
      "series": [
        { "date": "2025-01-02", "begin_mv": 200000.0, "bod_cf": 0.0, "pnl": 2500.0, "eod_cf": 0.0, "end_mv": 202500.0 }
      ]
    }
  ]
}
```

- `pnl` — Mark‑to‑market profit/loss for the interval (used when provided; otherwise implied from begin/end flows).  
- `group_keys` — Arbitrary key→value map used for multi‑level grouping.

## Benchmarks (Attribution)
```json
{
  "benchmark": {
    "mode": "BY_GROUP",        // or "BY_INSTRUMENT"
    "group_keys": ["sector", "region"],
    "weights": [
      { "date": "2025-01-02", "key": {"sector":"Technology","region":"US"}, "weight": 0.27, "return": 0.004 }
    ]
  }
}
```

## Configuration (per request)
```json
{
  "config": {
    "precision_mode": "DECIMAL_STRICT",   // or FLOAT64
    "rounding": 6,
    "periods": { "type": "EXPLICIT", "start": "2025-01-01", "end": "2025-01-31", "frequency": "DAILY" },
    "annualization": { "enabled": true, "basis": "ACT_365" },
    "metric_basis": "NET",                // NET or GROSS
    "linking": "CARINO",                  // attribution/contribution linking
    "weighting": "BOD"                    // contribution weighting: BOD | AVG_CAPITAL | TWR_DENOM
  }
}
```

### Enums
- `precision_mode`: `DECIMAL_STRICT`, `FLOAT64`
- `periods.type`: `EXPLICIT`, `ITD`, `YTD`, `QTD`, `MTD`, `WTD`, `ROLLING_MONTHS`, `ROLLING_DAYS`
- `annualization.basis`: `BUS_252`, `ACT_365`, `ACT_ACT`
- `metric_basis`: `NET`, `GROSS`
- `linking`: `NONE`, `CARINO`, `LOG`
- `weighting`: `BOD`, `AVG_CAPITAL`, `TWR_DENOM`

## Response Envelope
```json
{
  "data": { "...depends on endpoint..." },
  "meta": {
    "request_id": "uuid",
    "as_of": "2025-09-07",
    "config": { "...echo of effective config..." }
  },
  "diagnostics": {
    "notes": ["carino_linking_applied"],
    "counts": { "rows": 31, "positions": 12 },
    "residuals": { "bp_difference": 0.02 }
  }
}
```

## Validation Rules (high level)
- Dates must be monotonic and contiguous when `frequency=DAILY`.
- `begin_mv`, `end_mv` ≥ 0; flows/fees may be negative.
- When `positions` are supplied, their sum should reconcile to portfolio totals (tolerances applied).
- Benchmarks must cover portfolio groups for attribution days, otherwise residuals will be reported.
