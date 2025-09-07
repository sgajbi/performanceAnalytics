# API Reference

Base path: `/performance`

All requests/returns use the **Response Envelope** described in `docs/guides/data_model.md`.

---

## POST `/performance/twr`

**Purpose**: Compute time‑weighted returns for the portfolio (and optionally positions).

### Request (example)
```json
{
  "portfolio": { "id": "PF-001", "base_currency": "USD" },
  "series": [
    { "date": "2025-01-02", "begin_mv": 1000000.0, "bod_cf": 0.0, "fees": 0.0, "tx_costs": 0.0, "eod_cf": 0.0, "end_mv": 1015000.0 },
    { "date": "2025-01-03", "begin_mv": 1015000.0, "bod_cf": 50000.0, "fees": -200.0, "tx_costs": -50.0, "eod_cf": 0.0, "end_mv": 1020000.0 }
  ],
  "config": {
    "precision_mode": "DECIMAL_STRICT",
    "rounding": 6,
    "periods": { "type": "EXPLICIT", "start": "2025-01-01", "end": "2025-01-31", "frequency": "DAILY" },
    "annualization": { "enabled": true, "basis": "ACT_365" },
    "metric_basis": "NET"
  }
}
```

### Response (shape)
```json
{
  "data": {
    "daily": [
      { "date": "2025-01-02", "ror": 0.015, "cum_ror": 0.015 },
      { "date": "2025-01-03", "ror": 0.0049, "cum_ror": 0.0199 }
    ],
    "period": {
      "start": "2025-01-01",
      "end": "2025-01-31",
      "ror": 0.0199,
      "annualized_ror": 0.2765
    }
  },
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." }
}
```

**Notes**
- Returns reflect the selected `metric_basis`.  
- Reset days and notes appear in `diagnostics` when applicable.

---

## POST `/performance/mwr`

**Purpose**: Compute money‑weighted return (IRR/XIRR) for the portfolio.

### Request (example)
```json
{
  "portfolio": { "id": "PF-001", "base_currency": "USD" },
  "series": [
    { "date": "2025-01-02", "begin_mv": 1000000.0, "bod_cf": 0.0, "eod_cf": 0.0, "end_mv": 1015000.0 },
    { "date": "2025-01-15", "begin_mv": 1015000.0, "bod_cf": 50000.0, "eod_cf": 0.0, "end_mv": 1040000.0 },
    { "date": "2025-01-31", "begin_mv": 1040000.0, "bod_cf": 0.0, "eod_cf": -20000.0, "end_mv": 1035000.0 }
  ],
  "config": {
    "precision_mode": "DECIMAL_STRICT",
    "rounding": 8,
    "periods": { "type": "EXPLICIT", "start": "2025-01-01", "end": "2025-01-31" }
  }
}
```

### Response (shape)
```json
{
  "data": {
    "period": {
      "start": "2025-01-01",
      "end": "2025-01-31",
      "mwr": 0.01873456,
      "annualized_mwr": 0.25678123
    },
    "solver": {
      "method": "XIRR",
      "iterations": 23,
      "residual": 1.2e-10
    }
  },
  "meta": { "...": "..." },
  "diagnostics": { "notes": ["xirr_converged"], "counts": { "rows": 3 } }
}
```

**Notes**
- If XIRR fails to converge, the API may fall back to Modified Dietz and emit a `diagnostics.notes` entry.

---

## POST `/performance/contribution`

**Purpose**: Compute contribution to return by position and/or group with optional smoothing/linking.

### Request (example)
```json
{
  "portfolio": { "id": "PF-001", "base_currency": "USD" },
  "positions": [
    {
      "id": "AAPL", "name": "Apple", "group_keys": { "sector": "Technology" },
      "series": [
        { "date": "2025-01-02", "begin_mv": 200000.0, "pnl": 2500.0, "end_mv": 202500.0 }
      ]
    },
    {
      "id": "MSFT", "name": "Microsoft", "group_keys": { "sector": "Technology" },
      "series": [
        { "date": "2025-01-02", "begin_mv": 150000.0, "pnl": 1000.0, "end_mv": 151000.0 }
      ]
    }
  ],
  "config": {
    "precision_mode": "DECIMAL_STRICT",
    "rounding": 6,
    "weighting": "BOD",
    "linking": "CARINO",
    "periods": { "type": "EXPLICIT", "start": "2025-01-01", "end": "2025-01-31", "frequency": "DAILY" }
  }
}
```

### Response (shape)
```json
{
  "data": {
    "by_position": [
      { "id": "AAPL", "date": "2025-01-02", "ret": 0.0125, "weight": 0.20, "contrib": 0.00250 },
      { "id": "MSFT", "date": "2025-01-02", "ret": 0.0067, "weight": 0.15, "contrib": 0.00101 }
    ],
    "by_group": [
      { "group": { "sector": "Technology" }, "date": "2025-01-02", "contrib": 0.00351 }
    ],
    "period": { "contrib": 0.00351 }
  },
  "meta": { "...": "..." },
  "diagnostics": { "notes": ["carino_linking_applied"], "residuals": { "bp_difference": 0.02 } }
}
```

**Notes**
- Multi‑level grouping is supported via `group_keys`. Missing keys fall into `other` with explicit coverage % in diagnostics.

---

## POST `/performance/attribution`

**Purpose**: Brinson‑style active return decomposition vs a benchmark.

### Request (example)
```json
{
  "portfolio": { "id": "PF-001", "base_currency": "USD" },
  "positions": [
    {
      "id": "AAPL",
      "group_keys": { "sector": "Technology" },
      "series": [
        { "date": "2025-01-02", "begin_mv": 200000.0, "pnl": 2500.0, "end_mv": 202500.0 }
      ]
    }
  ],
  "benchmark": {
    "mode": "BY_GROUP",
    "group_keys": ["sector"],
    "weights": [
      { "date": "2025-01-02", "key": { "sector": "Technology" }, "weight": 0.27, "return": 0.004 }
    ]
  },
  "config": {
    "precision_mode": "DECIMAL_STRICT",
    "rounding": 6,
    "linking": "CARINO",
    "periods": { "type": "EXPLICIT", "start": "2025-01-01", "end": "2025-01-31", "frequency": "DAILY" }
  }
}
```

### Response (shape)
```json
{
  "data": {
    "daily": [
      { "date": "2025-01-02",
        "allocation": 0.00080,
        "selection": 0.00110,
        "interaction": -0.00005,
        "active": 0.00185 }
    ],
    "period": { "allocation": 0.00080, "selection": 0.00110, "interaction": -0.00005, "active": 0.00185 }
  },
  "meta": { "...": "..." },
  "diagnostics": { "notes": ["brinson_fachler"], "residuals": { "bp_difference": 0.00 } }
}
```

**Notes**
- Supported models: Brinson‑Fachler and Brinson‑Hood‑Beebower (select via config or default).  
- Residual policy ensures period `active` equals sum of effects within tolerance.
