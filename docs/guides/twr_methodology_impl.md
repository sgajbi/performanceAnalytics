# TWR Methodology — Implementation-Faithful

This document mirrors the **actual code** in `engine/ror.py`, `engine/compute.py`, `engine/rules.py`, and `engine/periods.py`.

## Execution Flow (as implemented)
1. **Adapter → Engine DataFrame**: API layer converts request rows into an engine DataFrame using canonical column names from `engine/schema.PortfolioColumns`.
2. **Type Mode**: If `EngineConfig.precision_mode == DECIMAL_STRICT`, columns are `object` dtype with `Decimal`; otherwise `float64`.
3. **Pre-Compute** (`engine.compute.run_calculations`):
   - Validate/normalize columns, coerce dates (`perf_date`) to datetime.
   - Compute **effective period start** per row (`engine.periods.get_effective_period_start_dates`) based on `PeriodType` (EXPLICIT/YTD/QTD/ITD).
   - Initialize flags: `perf_reset = 0`; compute `sign`, `nip` (No Investment Period) via `engine.rules`.
4. **Daily RoR** (`engine.ror.calculate_daily_ror`):
   - **Formula (percent, ×100):**  
     ```text
     numerator   = end_mv - begin_mv - bod_cf - eod_cf (+ mgmt_fees if metric_basis == "NET")
     denominator = abs(begin_mv + bod_cf)
     daily_ror%  = 100 * numerator / denominator   (only where denom != 0 and perf_date >= effective_period_start_date)
     otherwise   = 0
     ```
     - In **Decimal** mode all arithmetic uses `Decimal`; in **float** mode uses NumPy.
5. **Cumulative RoR & Resets** (`engine.ror.calculate_cumulative_ror`):
   - Compute **temp legs** (without resets): `temp_long_cum_ror`, `temp_short_cum_ror` via `_compound_ror(df, daily_ror, leg, use_resets=False)`.
   - Set `perf_reset` using **initial reset rules** `engine.rules.calculate_initial_resets(df, report_end_ts)`.  
   - Recompute **final legs** with resets: `long_cum_ror`, `short_cum_ror` using `use_resets=True`.
   - Zero-out legs on initial reset days.
   - Apply **NCTRL‑4 reset** (`engine.rules.calculate_nctrl4_reset`) and OR it into `perf_reset`.
   - Produce **final_cum_ror** = `long_cum_ror` for long days and `-short_cum_ror` for short days; forward-fill within blocks.
   - Grouping for compounding uses **block ids** that restart on period start or the day **after** a reset.  
     Growth factor per day:  
     ```text
     is_long  -> (1 + daily_ror/100)
     is_short -> (1 - daily_ror/100)   # sign-aware
     ```
     Cumprod within each block, then minus 1 and ×100; short leg multiplied by −1.
   - Decimal path uses per-block manual cumprod to avoid pandas object cumprod limits.
6. **Post-Compute**:
   - Derive `long_short` = `"S"` if `sign == -1` else `"L"`.
   - Filter rows to reporting window (effective start to report_end_date).
   - Round **float** columns to `rounding_precision` (no rounding in Decimal mode).
   - Build **diagnostics**: nip day count, reset events with reasons (NCTRL_1..4), and residuals (see Rules below).

## Inputs (canonical)
- `begin_mv`, `bod_cf`, `eod_cf`, `mgmt_fees`, `end_mv`, `perf_date`
- Derived per-engine:
  - `effective_period_start_date`
  - `sign` (see Rules), `nip` (see Rules), `perf_reset`

## Outputs
- `daily_ror` (%), `long_cum_ror` (%), `short_cum_ror` (%), `final_cum_ror` (%), `sign`, `perf_reset`, `nip`, `long_short`
- Diagnostics: `reset_events[]`, `nip_days`, `residuals`

## Period Resolution (as implemented)
`engine.periods.get_effective_period_start_dates`:
- `YTD` → Jan‑1 of `perf_date.year`, clamped to `performance_start_date`
- `QTD` → first day of current quarter, clamped
- `ITD` → `performance_start_date`
- `EXPLICIT` → `report_start_date` if provided else `performance_start_date`

## Rules, Flags & Diagnostics (as implemented)

### SIGN (`engine.rules.calculate_sign`)
- Computes position **sign** per day using flips detected from net exposures (implementation maintains sign sequences with forward fill across non-flip days). Emitted as `+1` (long) or `−1` (short).

### NIP — No Investment Period (`engine.rules.calculate_nip`)
- **V2 rule (default if feature flag on)**: `begin_mv + bod_cf == 0` AND `end_mv + eod_cf == 0` → `nip=1` else `0`.
- **Legacy V1 rule**: If *all* of `begin_mv + bod_cf + end_mv + eod_cf == 0`, then evaluate flows’ signs to decide NIP.
- NIP days force **daily_ror = 0** and are counted into diagnostics. Contributions are zeroed on NIP and Reset days.

### Resets
- **Initial resets**: `engine.rules.calculate_initial_resets(df, report_end_ts)` (NCTRL_1..3 reasons computed internally) set `perf_reset=1` on boundary conditions.
- **NCTRL‑4**: Triggered when **prior** cumulative legs breach ±100% and there is a cash flow (BOD or prior EOD). If true, `perf_reset=1`.
- On reset days, legs are **zeroed** and compounding block restarts the **next** day.

### Residuals
- Diagnostics include a bp-level residual check that reconciles linked returns vs. nav‑ratio implied return within tolerance.

## Metric Basis (`NET` vs `GROSS`)
- `NET` **adds** `mgmt_fees` into the numerator (fees should be negative for charges).  
- `GROSS` ignores fees (and any tx costs if they exist in your schema).

## Edge Behavior (coded)
- Denominator uses **absolute value** `abs(begin_mv + bod_cf)` to stabilize when BOD flows invert sign.
- Division only when denom != 0 and date ≥ effective period start; otherwise daily_ror = 0.
- Short legs are treated via **separate compounding** and `long_short` labelling.

## Worked Micro‑Example (aligned with code path)
Day t values (NET basis):
```
begin_mv=1,020,000, bod_cf=50,000, eod_cf=0, mgmt_fees=-250, end_mv=1,080,000
numerator   = 1,080,000 - 1,020,000 - 50,000 - 0 + (-250) = -250
denominator = abs(1,020,000 + 50,000) = 1,070,000
daily_ror%  = 100 * (-250 / 1,070,000) = -0.02336%
```
Cumulative legs then compound per **block** as above.

## File Pointers
- `engine/ror.py`
- `engine/compute.py`
- `engine/rules.py`
- `engine/periods.py`
