# Data Model (Inputs & Outputs)

This document defines canonical request/response schemas across all modules.

---

## Shared Components

### DailyInputData
```json
{
  "day": 1,
  "perf_date": "2025-01-01",
  "begin_mv": 100000.0,
  "bod_cf": 0.0,
  "eod_cf": 0.0,
  "mgmt_fees": 0.0,
  "end_mv": 101000.0
}
````

* **begin\_mv** – Beginning market value.
* **end\_mv** – Ending market value.
* **bod\_cf / eod\_cf** – Cash flows at start/end of day.
* **mgmt\_fees** – Management fees for the day.

---

### Enums

* **Frequency** – `daily`, `monthly`, `quarterly`, `yearly`.
* **PeriodType** – `MTD`, `QTD`, `YTD`, `ITD`, `ROLLING`, `EXPLICIT`.
* **MetricBasis** – `NET`, `GROSS`.
* **PrecisionMode** – `FLOAT64`, `DECIMAL_STRICT`.

---

### Response Envelope

All responses include:

* **Meta** – calculation\_id, version, precision, calendar, periods.
* **Diagnostics** – reset days, NIP days, notes.
* **Audit** – reconciliation checks (e.g., sum of parts vs total).

---

## Example Response (TWR)

```json
{
  "calculation_id": "uuid",
  "portfolio_number": "TWR_EXAMPLE_01",
  "breakdowns": {
    "daily": [
      {
        "period": "2025-01-01",
        "summary": {
          "begin_mv": 100000.0,
          "end_mv": 101000.0,
          "net_cash_flow": 0.0,
          "period_return_pct": 1.0,
          "cumulative_return_pct_to_date": 1.0
        }
      }
    ]
  },
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "...": "..." }
}
```
