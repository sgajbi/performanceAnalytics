
# API Reference

This document provides a detailed reference for all public endpoints in the Portfolio Performance Analytics API.
---

## `GET /`

A root endpoint to verify that the service is running.
* **Method**: `GET`
* **Path**: `/`
* **Response**: A simple JSON object with a welcome message.
```json
    {
      "message": "Welcome to the Portfolio Performance Analytics API. Access /docs for API documentation."
    }
    ```

---

## `POST /performance/twr`

Calculates the Time-Weighted Return (TWR) for a portfolio, with options for breaking down the results by different time frequencies.
### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `portfolio_number` | string | A unique identifier for the portfolio. |
| `performance_start_date` | date | The first date from which performance should be calculated (YYYY-MM-DD). |
| `metric_basis` | string | The basis for return calculation. Options: `"NET"` (includes management fees) or `"GROSS"` (excludes management fees). |
| `report_start_date` | date | Optional. The start date for the returned results (YYYY-MM-DD). If omitted, defaults to `performance_start_date`. |
| `report_end_date` | date | The end date for the returned results (YYYY-MM-DD). |
| `period_type` | string | The type of period for the calculation. Options: `"MTD"`, `"QTD"`, `"YTD"`, `"ITD"`, `"Y1"`, `"Y3"`, `"Y5"`, `"EXPLICIT"`. |
| `frequencies` | array | A list of frequencies to break the results down by. Options: `"daily"`, `"monthly"`, `"quarterly"`, `"yearly"`. |
| `daily_data` | array | An array of objects, each representing one day of portfolio data. |

### `daily_data` Object Structure

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `Day` | integer | A sequential day number. |
| `Perf. Date` | date | The date of the observation (YYYY-MM-DD). |
| `Begin Market Value`| float | The market value at the start of the day. |
| `BOD Cashflow` | float | Cash flow occurring at the beginning of the day (before market open). |
| `Eod Cashflow` | float | Cash flow occurring at the end of the day (after market close). |
| `Mgmt fees` | float | Management fees for the day (typically negative). |
| `End Market Value` | float | The market value at the end of the day. |
---

## `POST /performance/mwr`

Calculates the Money-Weighted Return (MWR) for a portfolio, which measures the performance of the actual capital invested.
### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `portfolio_number` | string | A unique identifier for the portfolio. |
| `beginning_mv` | float | The market value at the start of the entire period. |
| `ending_mv` | float | The market value at the end of the entire period. |
| `cash_flows` | array | An array of all cash flows that occurred during the period. |

### `cash_flows` Object Structure

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `amount` | float | The value of the cash flow (positive for inflows, negative for outflows). |
| `date` | date | The date the cash flow occurred (YYYY-MM-DD). |

---

## `POST /performance/contribution`

Decomposes the portfolio's total TWR into the individual contributions from its underlying positions.
### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `portfolio_number` | string | A unique identifier for the portfolio. |
| `portfolio_data` | object | Contains the configuration and full time series for the total portfolio. The structure is identical to the main request body of the `/performance/twr` endpoint. |
| `positions_data` | array | An array of objects, each representing an individual position. |
| `smoothing` | object | Optional. Controls how multi-period contributions are linked. Default: `{"method": "CARINO"}`. |
| `emit` | object | Optional. Controls whether to include daily time-series data in the response. Default: `{"timeseries": false}`. |


### `positions_data` Object Structure

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `position_id` | string | A unique identifier for the position (e.g., a ticker). |
| `daily_data` | array | The full time series for this position, using the same `daily_data` object structure as the `/performance/twr` endpoint. |
---

## `POST /performance/attribution`

Decomposes the portfolio's active return against a benchmark into Allocation, Selection, and Interaction effects.

### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `mode` | string | The input mode. Options: `"by_instrument"` (provide instrument-level data to be aggregated) or `"by_group"` (provide pre-aggregated group-level data). |
| `groupBy` | array | A list of metadata keys to group by (e.g., `["sector"]`). Currently, only single-level grouping is supported. |
| `frequency` | string | The frequency to resample the data to before calculation. Options: `"daily"`, `"monthly"`, `"quarterly"`, `"yearly"`. |
| `model` | string | The attribution model to use. Options: `"BF"` (Brinson-Fachler) or `"BHB"` (Brinson-Hood-Beebower). |
| `linking` | string | The method for linking multi-period effects. Options: `"carino"` or `"log"` (both implemented as Menchero geometric linking) or `"none"` (simple arithmetic sum). |
| `portfolio_data` | object | **Required for `by_instrument` mode**. The full time series for the total portfolio, using the `/performance/twr` request structure. |
| `instruments_data`| array | **Required for `by_instrument` mode**. An array of objects, each representing an instrument. Contains `instrument_id`, `meta` (a dict for grouping keys, e.g., `{"sector": "Tech"}`), and `daily_data`. |
| `portfolio_groups_data`| array | **Required for `by_group` mode**. Pre-aggregated data for portfolio groups. |
| `benchmark_groups_data`| array | Pre-aggregated data for benchmark groups. |
````

-----

### 2\. End-to-End Test Payloads

Here are three request files for a consistent two-month portfolio containing two stocks: "SGA" (Tech) and "JBI" (Health).

### **File: `E2E_TWR_Request.json`**

```json
{
  "portfolio_number": "E2E_PORTFOLIO_01",
  "performance_start_date": "2024-12-31",
  "metric_basis": "NET",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-02-28",
  "period_type": "YTD",
  "frequencies": ["monthly"],
  "daily_data": [
    {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 100000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 102000.0},
    {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 102000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -15.0, "End Market Value": 105000.0},
    {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 105000.0, "BOD Cashflow": 10000.0, "Eod Cashflow": 0.0, "Mgmt fees": -25.0, "End Market Value": 118000.0},
    {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 118000.0, "BOD Cashflow": 0.0, "Eod Cashflow": -5000.0, "Mgmt fees": 0.0, "End Market Value": 115000.0}
  ]
}
```

### **File: `E2E_MWR_Request.json`**

```json
{
  "portfolio_number": "E2E_PORTFOLIO_01",
  "beginning_mv": 100000.0,
  "ending_mv": 115000.0,
  "cash_flows": [
    {
      "amount": 10000.0,
      "date": "2025-02-01"
    },
    {
      "amount": -5000.0,
      "date": "2025-02-02"
    }
  ]
}
```

### **File: `E2E_Contribution_Request.json`**

```json
{
  "portfolio_number": "E2E_PORTFOLIO_01",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-02-28",
    "metric_basis": "NET",
    "period_type": "YTD",
    "daily_data": [
      {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 100000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 102000.0},
      {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 102000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -15.0, "End Market Value": 105000.0},
      {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 105000.0, "BOD Cashflow": 10000.0, "Eod Cashflow": 0.0, "Mgmt fees": -25.0, "End Market Value": 118000.0},
      {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 118000.0, "BOD Cashflow": 0.0, "Eod Cashflow": -5000.0, "Mgmt fees": 0.0, "End Market Value": 115000.0}
    ]
  },
  "positions_data": [
    {
      "position_id": "SGA",
      "daily_data": [
        {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 60000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 61800.0},
        {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 61800.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -10.0, "End Market Value": 64000.0},
        {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 64000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -15.0, "End Market Value": 65000.0},
        {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 65000.0, "BOD Cashflow": 0.0, "Eod Cashflow": -5000.0, "Mgmt fees": 0.0, "End Market Value": 61000.0}
      ]
    },
    {
      "position_id": "JBI",
      "daily_data": [
        {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 40000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 40200.0},
        {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 40200.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -5.0, "End Market Value": 41000.0},
        {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 41000.0, "BOD Cashflow": 10000.0, "Eod Cashflow": 0.0, "Mgmt fees": -10.0, "End Market Value": 53000.0},
        {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 53000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 54000.0}
      ]
    }
  ]
}
```

### **File: `E2E_Attribution_Request.json`**

```json
{
  "portfolio_number": "E2E_PORTFOLIO_01",
  "mode": "by_instrument",
  "groupBy": ["sector"],
  "model": "BF",
  "linking": "carino",
  "frequency": "monthly",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-02-28",
    "metric_basis": "NET",
    "period_type": "YTD",
    "daily_data": [
      {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 100000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 102000.0},
      {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 102000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -15.0, "End Market Value": 105000.0},
      {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 105000.0, "BOD Cashflow": 10000.0, "Eod Cashflow": 0.0, "Mgmt fees": -25.0, "End Market Value": 118000.0},
      {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 118000.0, "BOD Cashflow": 0.0, "Eod Cashflow": -5000.0, "Mgmt fees": 0.0, "End Market Value": 115000.0}
    ]
  },
  "instruments_data": [
    {
      "instrument_id": "SGA",
      "meta": {"sector": "Tech"},
      "daily_data": [
        {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 60000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 61800.0},
        {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 61800.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -10.0, "End Market Value": 64000.0},
        {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 64000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -15.0, "End Market Value": 65000.0},
        {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 65000.0, "BOD Cashflow": 0.0, "Eod Cashflow": -5000.0, "Mgmt fees": 0.0, "End Market Value": 61000.0}
      ]
    },
    {
      "instrument_id": "JBI",
      "meta": {"sector": "Health"},
      "daily_data": [
        {"Day": 1, "Perf. Date": "2025-01-01", "Begin Market Value": 40000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 40200.0},
        {"Day": 2, "Perf. Date": "2025-01-02", "Begin Market Value": 40200.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": -5.0, "End Market Value": 41000.0},
        {"Day": 3, "Perf. Date": "2025-02-01", "Begin Market Value": 41000.0, "BOD Cashflow": 10000.0, "Eod Cashflow": 0.0, "Mgmt fees": -10.0, "End Market Value": 53000.0},
        {"Day": 4, "Perf. Date": "2025-02-02", "Begin Market Value": 53000.0, "BOD Cashflow": 0.0, "Eod Cashflow": 0.0, "Mgmt fees": 0.0, "End Market Value": 54000.0}
      ]
    }
  ],
  "benchmark_groups_data": [
    {
      "key": {"sector": "Tech"},
      "observations": [
        {"date": "2025-01-31", "return": 0.05, "weight_bop": 0.5},
        {"date": "2025-02-28", "return": 0.02, "weight_bop": 0.5}
      ]
    },
    {
      "key": {"sector": "Health"},
      "observations": [
        {"date": "2025-01-31", "return": 0.01, "weight_bop": 0.5},
        {"date": "2025-02-28", "return": 0.03, "weight_bop": 0.5}
      ]
    }
  ]
}
```

 