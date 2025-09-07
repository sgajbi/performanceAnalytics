# Contribution Methodology — Implementation-Faithful

Mirrors `engine/contribution.py` and `adapters/api_adapter.py` for TWR alignment.

## Execution Flow
1. **Prepare Portfolio TWR**: Build a portfolio DataFrame from request series; run `run_calculations` (same TWR path) to get `daily_ror` for the portfolio.
2. **Per‑Position TWR**: For each position, build its DataFrame, run `run_calculations`, and attach `position_id` + `meta` keys into the results.
3. **Alignment**: Align position and portfolio time axes by `perf_date`. Positions without data on certain days are treated as weight 0.
4. **Weights** (per day):
   - Default implemented scheme uses **BOP weight** proxy derived from results (see `_calculate_single_period_weights`):
     ```text
     weight_t(pos) ≈ begin_mv_pos_t + bod_cf_pos_t  /  (begin_mv_port_t + bod_cf_port_t)
     ```
     (The code computes a portfolio‑level denominator and loops positions to form a dict of weights per day.)
5. **Raw Daily Contribution**:
   ```text
   c_p,t = weight_t * (daily_ror_pos_t / 100)
   ```
6. **Optional Carino Smoothing** (`request.smoothing.method == "CARINO"`):
   - Precompute portfolio **daily** RoR `R_port,t` and cumulative `R_port` over the whole period.
   - Compute **Carino factors**:
     - `k_t = ln(1 + R_port,t) / R_port,t` (vector with k_t = 1 when R_port,t = 0)
     - `K_total = ln(1 + R_port) / R_port` (scalar with 1 when `R_port` = 0)
   - Adjust each daily contribution:
     ```text
     c'_p,t = c_p,t + weight_t * [ R_port,t * (K_total / k_t − 1) ]
     ```
   - Sum over t to obtain **smoothed** total contribution.
7. **NIP/Reset Handling**:
   - On dates where portfolio has `nip == 1` or `perf_reset == 1`, set `smoothed_contribution = 0.0` (daily is suppressed).
8. **Aggregation & Residuals**:
   - Aggregate by `position_id` and by arbitrary **hierarchy levels** from `meta` keys.
   - Compute `average_weight` (mean of daily weights) and `total_contribution` (×100 for percent output).
   - Residual = portfolio total RoR − sum of contributions. If smoothing is **Carino**, distribute residual **pro‑rata by average_weight**.
9. **Emission Controls** (`Emit`):
   - `emit.timeseries` → include a `timeseries` array per position with date‑wise contributions.
   - Hierarchical result assembled as `levels[{ name, parent, rows[] }]` with `weight_avg` and `%` ready for UI.

## Inputs
- Portfolio series and Positions array (each with `daily_data` matching canonical fields).
- Config: `smoothing.method`, `weighting_scheme` (BOD and variants supported), `emit.timeseries`.

## Outputs
- Summary: `portfolio_contribution` %, `coverage_mv_pct`, `weighting_scheme`
- Levels: one object per requested hierarchy level with per‑row `{id/name, total_contribution %, weight_avg %}`
- Optional `timeseries` per position when requested.

## File Pointers
- `engine/contribution.py`
- `adapters/api_adapter.py` (for response shaping)
