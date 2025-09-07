# Engine Configuration

The engine is designed to be configurable through both API requests and internal `EngineConfig`. This ensures flexible behavior across TWR, MWR, Contribution, and Attribution modules.

---

## Core Parameters

### Performance Dates
- **performance_start_date** – First date from which performance is calculated (usually inception or first record).
- **report_start_date** – Start date of the reporting window.
- **report_end_date** – End date of the reporting window.

The engine always respects the reporting window when aggregating results.

---

### Precision
- **precision_mode**
  - `FLOAT64` – Fastest, uses NumPy float64.
  - `DECIMAL_STRICT` – Slower, but enforces strict decimal precision (via Python `decimal.Decimal`).
- **rounding_precision** – Number of decimals to round results to (default: 6).

**Rationale:**  
Strict precision mode is critical for regulatory reporting or reconciliation where floating-point drift is unacceptable.

---

### Metric Basis
- `NET` – Returns after fees/costs.
- `GROSS` – Returns before fees/costs.

---

### Period Type
Defines how periods are resolved (`core/periods.py`):
- **MTD/QTD/YTD** – Calendar month/quarter/year to date.
- **ITD** – Inception-to-date (from first available record).
- **ROLLING** – N-period rolling window (e.g., 12 months).
- **EXPLICIT** – Explicitly provided start and end dates.

---

### Calendar
- **type**
  - `BUSINESS` – Business days (default, assumes 252 trading days).
  - `NATURAL` – Calendar days.
- **trading_calendar** – Identifier (e.g. `NYSE`) if business-specific holiday calendars are supported.

---

### Annualization
- **enabled** – Whether to return annualized results.
- **basis**
  - `BUS/252` – Business days convention.
  - `ACT/365` – Actual/365 fixed.
  - `ACT/ACT` – Actual/Actual day count.
- **periods_per_year** – Override default divisor (e.g. 252 or 365).

---

### Flags
- **fail_fast** – Abort immediately on invalid input (otherwise engine tries to continue).
- **compat_legacy_names** – Option to emit old field names for backward compatibility.

---

## Diagnostics & Audit

All calculations emit **diagnostics** and **audit**:
- **Diagnostics**
  - `nip_days` – Non-investment period days.
  - `reset_days` – Reset days applied.
  - `notes` – Informational notes (e.g., adjustments applied).
- **Audit**
  - `sum_of_parts_vs_total_bp` – Residual between sum of contributions and total portfolio return.
  - `counts` – Input row counts, positions processed, etc.

These ensure calculations are transparent and reconcilable.

---

## Example

```json
{
  "performance_start_date": "2024-12-31",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-03-31",
  "metric_basis": "NET",
  "period_type": "YTD",
  "precision_mode": "DECIMAL_STRICT",
  "rounding_precision": 8,
  "calendar": { "type": "BUSINESS", "trading_calendar": "NYSE" },
  "annualization": { "enabled": true, "basis": "ACT/365" }
}
