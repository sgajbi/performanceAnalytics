# Rules & Diagnostics — Implementation-Faithful

Covers `engine/rules.py` and diagnostics collected in `engine/compute.py`.

## Flags/Columns
- `sign` (±1): trend of exposure; flips detected and forward‑filled per block.
- `nip` (0/1): No Investment Period (see below).
- `perf_reset` (0/1): reset applied today for compounding legs.
- `nctrl_1..4` (0/1): internal reset reason flags stored on the DataFrame.

## NIP
- **V2 Rule** (when `FeatureFlags.use_nip_v2_rule` is true):  
  `begin_mv + bod_cf == 0` AND `end_mv + eod_cf == 0` → `nip=1` else `0`.
- **V1 Rule**: legacy sign‑based logic on flows when all values are zero for the day.

## Resets
- **Initial resets**: derived pre‑cumulation based on rule checks and `report_end_date` boundary.
- **NCTRL‑4 reset**: when prior day cumulative legs breach ±100% and there is a cash flow (today BOD or yesterday EOD).

On **reset days**:
- `long_cum_ror`, `short_cum_ror` are zeroed; new block begins the next day.
- Contribution engine sets daily contributions to **0** for those dates.

## Diagnostics (response-level)
- `nip_days`: total count within the reporting period.
- `reset_events[]`: array of `{date, reason, impacted_rows}` (reasons drawn from NCTRL flags).
- `residuals`: bp‑level reconciliation differences.

## Precision & Rounding
- **Decimal mode**: deterministic; no rounding applied post‑compute.
- **Float mode**: rounded to `EngineConfig.rounding_precision` at the end of `run_calculations`.
