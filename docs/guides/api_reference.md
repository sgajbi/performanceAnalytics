# API Reference (Exact Endpoints & Shapes)

All endpoints live under `/performance` in `app/api/endpoints/performance.py`.
## POST /performance/twr
- **Request model**: `app/models/requests.PerformanceRequest`
- **Response model**: `app/models/responses.PerformanceResponse`

### Minimal Request
```json
{
  "portfolio_id": "PF-001",
  "performance_start_date": "2024-12-31",
  "report_end_date": "2025-01-31",
  "as_of": "2025-01-31",
  "metric_basis": "NET",
  "periods": ["MTD", "YTD"],
  "frequencies": ["monthly"],
  "daily_data": [
    { "day": 1, "perf_date": "2025-01-02", "begin_mv": 1000000.0, "end_mv": 1020000.0 }
  ],
  "precision_mode": "FLOAT64",
  "rounding_precision": 6,
  "calendar": { "type": "BUSINESS", "trading_calendar": "NYSE" },
  "output": { "include_cumulative": true }
}
````

### Response (shape excerpt)

```json
{
  "calculation_id": "uuid",
  "portfolio_id": "PF-001",
  "results_by_period": {
    "MTD": {
      "breakdowns": {
        "monthly": [ { "period": "2025-01", "summary": { "period_return_pct": 1.99, "cumulative_return_pct_to_date": 1.99 } } ]
      }
    },
    "YTD": {
       "breakdowns": {
        "monthly": [ { "period": "2025-01", "summary": { "period_return_pct": 1.99, "cumulative_return_pct_to_date": 1.99 } } ]
      }
    }
  },
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "...": "..." }
}
```

-----

## POST /performance/mwr

  - **Request model**: `app/models/mwr_requests.MoneyWeightedReturnRequest`
  - **Response model**: `app/models/mwr_responses.MoneyWeightedReturnResponse`

### Minimal Request

```json
{
  "portfolio_id": "PF-MWR-001",
  "begin_mv": 1000000.0,
  "end_mv": 1030000.0,
  "as_of": "2025-01-31",
  "cash_flows": [
    { "amount": 50000.0, "date": "2025-01-15" }
  ],
  "mwr_method": "XIRR",
  "precision_mode": "FLOAT64",
  "calendar": { "type": "BUSINESS", "trading_calendar": "NYSE" }
}
```

### Response (shape excerpt)

```json
{
  "money_weighted_return": 1.873456,
  "method": "XIRR",
  "convergence": { "iterations": 23, "residual": 1.2e-10, "converged": true },
  "start_date": "2025-01-15",
  "end_date": "2025-01-31",
  "notes": ["XIRR calculation successful."],
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "...": "..." }
}
```

-----

## POST /performance/contribution

  - **Request model**: `app/models/contribution_requests.ContributionRequest`
  - **Response model**: `app/models/contribution_responses.ContributionResponse`

Key controls:

  - `weighting_scheme`: `"BOD" | "AVG_CAPITAL" | "TWR_DENOM"` (see `common/enums.WeightingScheme`)
  - `smoothing.method`: `"CARINO" | "NONE"`
  - `emit.timeseries: bool`

-----

## POST /performance/attribution

  - **Request model**: `app/models/attribution_requests.AttributionRequest`
  - **Response model**: `app/models/attribution_responses.AttributionResponse`

Key controls:

  - `mode`: `"by_group" | "by_instrument"`
  - `frequency`: `"daily" | "weekly" | "monthly" | "quarterly" | "yearly"` (see `common/enums.Frequency`)
  - `linking`: `"carino" | "log" | "none"`

<!-- end list -->

````

**Updated File: `docs/examples/twr_request.json`**
```json
{
  "portfolio_id": "TWR_EXAMPLE_01",
  "performance_start_date": "2024-12-31",
  "metric_basis": "NET",
  "report_end_date": "2025-01-05",
  "periods": [
    "ITD"
  ],
  "frequencies": [
    "daily",
    "monthly"
  ],
  "daily_data": [
    {
      "day": 1,
      "perf_date": "2025-01-01",
      "begin_mv": 100000.0,
      "bod_cf": 0.0,
      "eod_cf": 0.0,
      "mgmt_fees": 0.0,
      "end_mv": 101000.0
    },
    {
      "day": 2,
      "perf_date": "2025-01-02",
      "begin_mv": 101000.0,
      "bod_cf": 0.0,
      "eod_cf": 0.0,
      "mgmt_fees": 0.0,
      "end_mv": 102500.0
    },
    {
      "day": 3,
      "perf_date": "2025-01-03",
      "begin_mv": 102500.0,
      "bod_cf": 5000.0,
      "eod_cf": 0.0,
      "mgmt_fees": -10.0,
      "end_mv": 108000.0
    },
    {
      "day": 4,
      "perf_date": "2025-01-04",
      "begin_mv": 108000.0,
      "bod_cf": 0.0,
      "eod_cf": -2000.0,
      "mgmt_fees": -12.0,
      "end_mv": 106500.0
    },
    {
      "day": 5,
      "perf_date": "2025-01-05",
      "begin_mv": 106500.0,
      "bod_cf": 0.0,
      "eod_cf": 0.0,
      "mgmt_fees": 0.0,
      "end_mv": 107000.0
    }
  ]
}
````

**Updated File: `docs/examples/contribution_request.json`**

```json
{
  "portfolio_id": "CONTRIB_EXAMPLE_01",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-02",
  "periods": [
    "YTD"
  ],
  "hierarchy": [
    "sector",
    "position_id"
  ],
  "portfolio_data": {
    "metric_basis": "NET",
    "daily_data": [
      {
        "day": 1,
        "perf_date": "2025-01-01",
        "begin_mv": 1000,
        "end_mv": 1020
      },
      {
        "day": 2,
        "perf_date": "2025-01-02",
        "begin_mv": 1020,
        "bod_cf": 50,
        "end_mv": 1080
      }
    ]
  },
  "positions_data": [
    {
      "position_id": "Stock_A",
      "meta": {
        "sector": "Technology"
      },
      "daily_data": [
        {
          "day": 1,
          "perf_date": "2025-01-01",
          "begin_mv": 600,
          "end_mv": 612
        },
        {
          "day": 2,
          "perf_date": "2025-01-02",
          "begin_mv": 612,
          "bod_cf": 50,
          "end_mv": 670
        }
      ]
    },
    {
      "position_id": "Stock_B",
      "meta": {
        "sector": "Healthcare"
      },
      "daily_data": [
        {
          "day": 1,
          "perf_date": "2025-01-01",
          "begin_mv": 400,
          "end_mv": 408
        },
        {
          "day": 2,
          "perf_date": "2025-01-02",
          "begin_mv": 408,
          "end_mv": 410
        }
      ]
    }
  ]
}
```

**Updated File: `docs/examples/attribution_request.json`**

```json
{
  "portfolio_id": "ATTRIB_EXAMPLE_01",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-01",
  "periods": [
    "YTD"
  ],
  "mode": "by_instrument",
  "group_by": [
    "sector"
  ],
  "linking": "none",
  "frequency": "daily",
  "portfolio_data": {
    "metric_basis": "NET",
    "daily_data": [
      {
        "day": 1,
        "perf_date": "2025-01-01",
        "begin_mv": 1000,
        "end_mv": 1018.5
      }
    ]
  },
  "instruments_data": [
    {
      "instrument_id": "AAPL",
      "meta": {
        "sector": "Tech"
      },
      "daily_data": [
        {
          "day": 1,
          "perf_date": "2025-01-01",
          "begin_mv": 600,
          "end_mv": 612
        }
      ]
    },
    {
      "instrument_id": "JNJ",
      "meta": {
        "sector": "Health"
      },
      "daily_data": [
        {
          "day": 1,
          "perf_date": "2025-01-01",
          "begin_mv": 400,
          "end_mv": 406.5
        }
      ]
    }
  ],
  "benchmark_groups_data": [
    {
      "key": {
        "sector": "Tech"
      },
      "observations": [
        {
          "date": "2025-01-01",
          "return_base": 0.015,
          "weight_bop": 0.5
        }
      ]
    },
    {
      "key": {
        "sector": "Health"
      },
      "observations": [
        {
          "date": "2025-01-01",
          "return_base": 0.02,
          "weight_bop": 0.5
        }
      ]
    }
  ]
}
```
 
