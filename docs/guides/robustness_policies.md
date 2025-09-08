# Handling Data Issues with Robustness Policies

The analytics engine includes a powerful **Robustness Policies Framework** to handle common, real-world data issues in a transparent and auditable way. By including a `data_policy` block in your API request, you can instruct the engine to apply specific corrections or flag anomalies for review.

-----

## Case 1: Manual Data Correction with `overrides`

### The Problem

An incorrect market value or cash flow was booked on a specific day, but resubmitting the entire historical data feed is difficult.

### The Solution

Use the `overrides` policy to provide an in-memory correction for a specific calculation run.

**Example `data_policy`:**

```json
"data_policy": {
  "overrides": {
    "market_values": [
      {
        "perf_date": "2025-03-15",
        "position_id": "Position_XYZ",
        "end_mv": 152340.50
      }
    ],
    "cash_flows": [
      {
        "perf_date": "2025-03-20",
        "portfolio_number": "PORT123",
        "bod_cf": 0.0
      }
    ]
  }
}
```

The engine applies these values before any calculations. The `diagnostics` block in the response will confirm how many overrides were applied.

-----

## Case 2: Ignoring "Noisy" or Corrupt Data Days

### The Problem

Data for a specific position is known to be corrupt for a few days. You want to exclude these days, treating the position as if it had no market movement.

### The Solution

Use the `ignore_days` policy. The engine will "freeze" the position for the specified dates by carrying forward the previous day's market value and zeroing out all flows and fees. This results in a 0% return for the ignored period.

**Example `data_policy`:**

```json
"data_policy": {
  "ignore_days": [
    {
      "entity_type": "POSITION",
      "entity_id": "Position_ABC",
      "dates": ["2025-03-18", "2025-03-19"]
    }
  ]
}
```

The `diagnostics` block will report the number of days ignored.

-----

## Case 3: Flagging Outlier Returns

### The Problem

A data error creates a massive, non-economic daily return (e.g., +900%). Your policy is to be made aware of such anomalies without automatically altering the data.

### The Solution

Use the `outliers` policy with `action: "FLAG"`. The engine uses a statistical method (like Median Absolute Deviation) to detect outliers but **does not change the data**. It proceeds with the calculation and reports its findings.

**Example `data_policy`:**

```json
"data_policy": {
  "outliers": {
    "enabled": true,
    "method": "MAD",
    "params": { "mad_k": 5.0, "window": 63 },
    "action": "FLAG"
  }
}
```

The primary result is the `diagnostics` block, which will show how many outliers were flagged and provide a sample for your review.

```json
"diagnostics": {
  "policy": { "outliers": { "flagged_rows": 1 } },
  "samples": {
    "outliers": [ { "date": "2025-03-12", "instrumentId": "XYZ", "raw_return": 900.0, "threshold": 15.0 } ]
  }
}
```