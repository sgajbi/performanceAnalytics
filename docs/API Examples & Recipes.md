# 🍳 API Examples & Recipes

This document provides a library of **common, real-world request payloads** for the **Performance Analytics Suite**.  
Use these examples as a starting point for your own implementations.

---

## 1. Standard Time-Weighted Return (TWR)

Calculates the **daily and monthly TWR** for a simple, single-currency portfolio.

**Endpoint:**  
```

POST /performance/twr

````

**Payload:**
```json
{
  "portfolio_number": "TWR_EXAMPLE_01",
  "performance_start_date": "2024-12-31",
  "metric_basis": "NET",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-05",
  "period_type": "YTD",
  "frequencies": ["daily", "monthly"],
  "daily_data": [
    { "day": 1, "perf_date": "2025-01-01", "begin_mv": 100000.0, "end_mv": 101000.0 },
    { "day": 2, "perf_date": "2025-01-02", "begin_mv": 101000.0, "end_mv": 102500.0 },
    { "day": 3, "perf_date": "2025-01-03", "begin_mv": 102500.0, "bod_cf": 5000.0, "end_mv": 108000.0 },
    { "day": 4, "perf_date": "2025-01-04", "begin_mv": 108000.0, "eod_cf": -2000.0, "end_mv": 106500.0 },
    { "day": 5, "perf_date": "2025-01-05", "begin_mv": 106500.0, "end_mv": 107000.0 }
  ]
}
````

---

## 2. Multi-Currency TWR with Hedging

Calculates the **TWR** for a portfolio denominated in **EUR**, reported in **USD**, with a **50% currency hedge** on the first day.

**Endpoint:**

```
POST /performance/twr
```

**Payload:**

```json
{
  "portfolio_number": "TWR_MCY_HEDGED_01",
  "performance_start_date": "2024-12-31",
  "metric_basis": "GROSS",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-02",
  "period_type": "YTD",
  "frequencies": ["daily"],
  "daily_data": [
    { "day": 1, "perf_date": "2025-01-01", "begin_mv": 100, "end_mv": 102 },
    { "day": 2, "perf_date": "2025-01-02", "begin_mv": 102, "end_mv": 103.02 }
  ],
  "currency_mode": "BOTH",
  "report_ccy": "USD",
  "fx": {
    "rates": [
      { "date": "2024-12-31", "ccy": "EUR", "rate": 1.05 },
      { "date": "2025-01-01", "ccy": "EUR", "rate": 1.08 },
      { "date": "2025-01-02", "ccy": "EUR", "rate": 1.07 }
    ]
  },
  "hedging": {
    "mode": "RATIO",
    "series": [{ "date": "2025-01-01", "ccy": "EUR", "hedge_ratio": 0.5 }]
  }
}
```

---

## 3. Multi-Currency Contribution

Calculates **contribution** for a portfolio with assets in **EUR** and **JPY**, decomposing the result into **local vs. FX effects**.

**Endpoint:**

```
POST /performance/contribution
```

**Payload:**

```json
{
  "portfolio_number": "MULTI_ASSET_MCY_01",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-01",
    "period_type": "ITD",
    "metric_basis": "GROSS",
    "daily_data": [{ "day": 1, "perf_date": "2025-01-01", "begin_mv": 10305.00, "end_mv": 10563.66 }]
  },
  "positions_data": [
    {
      "position_id": "EUR_STOCK",
      "meta": { "currency": "EUR", "sector": "Industrials" },
      "daily_data": [{ "day": 1, "perf_date": "2025-01-01", "begin_mv": 100, "end_mv": 102 }]
    },
    {
      "position_id": "JPY_STOCK",
      "meta": { "currency": "JPY", "sector": "Technology" },
      "daily_data": [{ "day": 1, "perf_date": "2025-01-01", "begin_mv": 1500000, "end_mv": 1515000 }]
    }
  ],
  "currency_mode": "BOTH",
  "report_ccy": "USD",
  "fx": {
    "rates": [
      { "date": "2024-12-31", "ccy": "EUR", "rate": 1.05 },
      { "date": "2025-01-01", "ccy": "EUR", "rate": 1.08 },
      { "date": "2024-12-31", "ccy": "JPY", "rate": 0.0068 },
      { "date": "2025-01-01", "ccy": "JPY", "rate": 0.0069 }
    ]
  }
}
```

---

## 4. Multi-Currency Attribution

Runs a **Karnosky-Singer currency attribution** to explain whether active return came from **asset selection** or **currency bets**.

**Endpoint:**

```
POST /performance/attribution
```

**Payload:**

```json
{
  "portfolio_number": "ATTRIB_MCY_01",
  "mode": "by_instrument",
  "group_by": ["currency"],
  "linking": "none",
  "frequency": "daily",
  "currency_mode": "BOTH",
  "report_ccy": "USD",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-01",
    "metric_basis": "GROSS",
    "period_type": "ITD",
    "daily_data": [{ "day": 1, "perf_date": "2025-01-01", "begin_mv": 100, "end_mv": 103.02 }]
  },
  "instruments_data": [
    {
      "instrument_id": "EUR_ASSET",
      "meta": { "currency": "EUR" },
      "daily_data": [{ "day": 1, "perf_date": "2025-01-01", "begin_mv": 100, "end_mv": 102 }]
    }
  ],
  "benchmark_groups_data": [
    {
      "key": { "currency": "EUR" },
      "observations": [
        { "date": "2025-01-01", "weight_bop": 1, "return_local": 0.015, "return_fx": 0.01, "return_base": 0.02515 }
      ]
    }
  ],
  "fx": {
    "rates": [
      { "date": "2024-12-31", "ccy": "EUR", "rate": 1 },
      { "date": "2025-01-01", "ccy": "EUR", "rate": 1.01 }
    ]
  }
}
```

 