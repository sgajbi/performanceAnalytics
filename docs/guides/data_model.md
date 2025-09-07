# Data Model (Exact Contracts from Snapshot)

This document reflects the **actual request/response models** in `app/models/*` and the **engine column names** from `engine/schema.py`.

## Engine Column Names (single source of truth)
From `engine/schema.PortfolioColumns` (subset shown):
- Inputs: `day`, `perf_date`, `begin_mv`, `bod_cf`, `eod_cf`, `mgmt_fees` (if present), `end_mv`
- Derived/Flags: `sign`, `nip`, `perf_reset`, `nctrl_1..nctrl_4`, `effective_period_start_date`
- Returns: `daily_ror`, `temp_long_cum_ror`, `temp_short_cum_ror`, `long_cum_ror`, `short_cum_ror`, `final_cum_ror`

## Shared Request Components (`core/envelope.py`)

### Calendar
```json
{ "type": "BUSINESS", "trading_calendar": "NYSE" }
```
- `type`: `"BUSINESS"` | `"NATURAL"`

### Annualization
```json
{ "enabled": false }
```

### Periods
```json
{
  "type": "EXPLICIT",
  "explicit": { "start": "2025-01-01", "end": "2025-01-31", "frequency": "daily" }
}
```
- `type`: `"YTD" | "QTD" | "MTD" | "WTD" | "Y1" | "Y3" | "Y5" | "ITD" | "ROLLING" | "EXPLICIT"`
- `rolling`: `{ "months": <int> }` **or** `{ "days": <int> }` (required when `type="ROLLING"`)

### Output
```json
{
  "include_timeseries": false,
  "include_cumulative": false,
  "top_n": 20
}
```

### Flags
```json
{ "fail_fast": false, "compat_legacy_names": false }
```

### Base Request Fields
- `calculation_id: UUID` (auto‑generated default)
- `as_of: date` (ISO `YYYY-MM-DD`)
- `currency: string` (default `"USD"`)
- `precision_mode`: `"FLOAT64"` | `"DECIMAL_STRICT"`
- `rounding_precision: int`
- `calendar`, `annualization`, `periods`, `output`, `flags`

## Performance Request (`app/models/requests.py`)

### DailyInputData
- `day: int`, `perf_date: date`
- `begin_mv: float`
- `bod_cf: float = 0.0`, `eod_cf: float = 0.0`
- `fees`/`mgmt_fees` (if included in your build) and `tx_costs` (when enabled)

### PerformanceRequest (top‑level)
- `portfolio_number: str`
- `daily_data: List[DailyInputData]`
- `metric_basis: "NET" | "GROSS"` (see `app/core/constants.py`)
- `periods: Optional[Periods]` (if omitted, engine resolves based on `as_of` and defaults)
- Base request fields (see above)
- `fee_effect`, `reset_policy` (see their models in requests file)

### PerformanceResponse (`app/models/responses.py`)
- `calculation_id: UUID`
- `portfolio_number: str`
- `breakdowns: PerformanceBreakdown`
- Optional `reset_events: List[ResetEvent]` (emitted when `reset_policy.emit = true`)
- `meta: Meta`, `diagnostics: Diagnostics`, `audit: Audit`

## Money‑Weighted Return (MWR)

### MoneyWeightedReturnRequest (`app/models/mwr_requests.py`)
- `begin_mv: float`, `end_mv: float`
- `cash_flows: List[{amount: float, date: date}]`
- `solver: { method: "XIRR" | "MODIFIED_DIETZ" | "DIETZ", max_iterations?: int, tol?: float }`
- `emit_cashflows_used: bool = true`
- Base request fields (`as_of`, `precision_mode`, `periods`, `annualization`, etc.)

### MoneyWeightedReturnResponse (`app/models/mwr_responses.py`)
- `mwr: float`, `mwr_annualized?: float`
- `method: "XIRR" | "MODIFIED_DIETZ" | "DIETZ"`
- `convergence?: { iterations?: int, residual?: float, converged?: bool }`
- `cashflows_used?: List[CashFlow]`
- `start_date: date`, `end_date: date`, `notes: List[str]`
- `meta`, `diagnostics`, `audit`

## Contribution & Attribution Models
- Contribution request/response mirror the portfolio series + positions with `group_keys` and optional `smoothing` + `emit.timeseries` controls (see `app/models/contribution_*` and `adapters/api_adapter.py`).
- Attribution request/response include `benchmark` in `"BY_GROUP"` or `"BY_INSTRUMENT"` mode; frequency mapping is aligned to `common/enums.Frequency`.

