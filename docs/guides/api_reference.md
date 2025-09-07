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
| `day` | integer | A sequential day number. |
| `perf_date` | date | The date of the observation (YYYY-MM-DD). |
| `begin_mv`| float | The market value at the start of the day. |
| `bod_cf` | float | Cash flow occurring at the beginning of the day (before market open). |
| `eod_cf` | float | Cash flow occurring at the end of the day (after market close). |
| `mgmt_fees` | float | Management fees for the day (typically negative). |
| `end_mv` | float | The market value at the end of the day. |
---

## `POST /performance/mwr`

Calculates the Money-Weighted Return (MWR) for a portfolio, which measures the performance of the actual capital invested.
### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `portfolio_number` | string | A unique identifier for the portfolio. |
| `begin_mv` | float | The market value at the start of the entire period. |
| `end_mv` | float | The market value at the end of the entire period. |
| `cash_flows` | array | An array of all cash flows that occurred during the period. |

### `cash_flows` Object Structure

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `amount` | float | The value of the cash flow (positive for inflows, negative for outflows). |
| `date` | date | The date the cash flow occurred (YYYY-MM-DD). |

---

## `POST /performance/contribution`

Decomposes the portfolio's total TWR into the individual contributions from its underlying positions. Supports both single-level and multi-level hierarchical breakdowns.
### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `portfolio_number` | string | A unique identifier for the portfolio. |
| `hierarchy` | array | Optional. An ordered list of metadata keys to group by (e.g., `["sector", "position_id"]`). If provided, triggers a multi-level calculation. |
| `portfolio_data` | object | Contains the configuration and full time series for the total portfolio. The structure is identical to the main request body of the `/performance/twr` endpoint. |
| `positions_data` | array | An array of objects, each representing an individual position. |
| `smoothing` | object | Optional. Controls how multi-period contributions are linked. Default: `{"method": "CARINO"}`. |
| `emit` | object | Optional. Controls whether to include daily time-series data in the response. Default: `{"timeseries": false}`. |


### `positions_data` Object Structure

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `position_id` | string | A unique identifier for the position (e.g., a ticker). |
| `meta` | object | Optional. A dictionary of key-value pairs for hierarchical grouping (e.g., `{"sector": "Technology"}`). |
| `daily_data` | array | The full time series for this position, using the same `daily_data` object structure as the `/performance/twr` endpoint. |
---

## `POST /performance/attribution`

Decomposes the portfolio's active return against a benchmark into Allocation, Selection, and Interaction effects, with support for multi-level hierarchical analysis.
### Request Body

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `mode` | string | The input mode. Options: `"by_instrument"` (provide instrument-level data to be aggregated) or `"by_group"` (provide pre-aggregated group-level data). |
| `group_by` | array | An ordered list of metadata keys to group by (e.g., `["assetClass", "sector"]`). This defines the hierarchy for the analysis, from top to bottom. |
| `frequency` | string | The frequency to resample the data to before calculation. Options: `"daily"`, `"monthly"`, `"quarterly"`, `"yearly"`. |
| `model` | string | The attribution model to use. Options: `"BF"` (Brinson-Fachler) or `"BHB"` (Brinson-Hood-Beebower). |
| `linking` | string | The method for linking multi-period effects. Options: `"carino"` (geometric linking) or `"none"` (simple arithmetic sum). |
| `portfolio_data` | object | **Required for `by_instrument` mode**. The full time series for the total portfolio, using the `/performance/twr` request structure. |
| `instruments_data`| array | **Required for `by_instrument` mode**. An array of objects, each representing an instrument. Contains `instrument_id`, `meta` (a dict for grouping keys, e.g., `{"sector": "Tech"}`), and `daily_data`. |
| `portfolio_groups_data`| array | **Required for `by_group` mode**. Pre-aggregated data for portfolio groups. |
| `benchmark_groups_data`| array | Pre-aggregated data for benchmark groups. |
````
