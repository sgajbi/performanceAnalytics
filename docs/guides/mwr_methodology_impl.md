# MWR Methodology — Implementation-Faithful

Mirrors `engine/mwr.py` and response models.

## Execution Flow
1. Inputs: `begin_mv`, `end_mv`, and array of dated **cash_flows** (`amount`, `date`), plus `as_of`.
2. Choose method:
   - If `calculation_method == "XIRR"` → try Brent root-finding (`scipy.optimize.brentq`) on the NPV function.
   - Else → **Simple/Modified Dietz** fallback used when XIRR fails or not selected.
3. Build dates/values for XIRR:
   - Start at **earliest cash flow date** (or `as_of` if none).  
   - Values vector: `[-begin_mv] + [-cf.amount for cf] + [end_mv]`.
   - Solve for rate `r` with Brent; if converged → `mwr = r * 100`, `annualized_mwr = r * 100` (engine returns period and annualized same unless a separate annualization config is passed through envelope).
   - If not converged → append notes and **fallback** to Dietz.
4. Dietz periodic rate:
   - `net_cash_flow = sum(cf.amount)`
   - `average_capital` computed using Dietz time weights from dates.
   - `periodic_rate = (end_mv - begin_mv - net_cash_flow) / average_capital`
   - If annualization provided (`core.envelope.Annualization` in this module’s context), scale:  
     `annualized = (1 + periodic_rate) ** (ppy / days_in_period) - 1`, where `ppy` depends on basis (`ACT/ACT` or `ACT/365`).

## Outputs
- `mwr` %, optional `mwr_annualized` %, `method` (`XIRR` or `DIETZ`), `start_date`, `end_date`
- `convergence` block when XIRR converges (iterations/residual in notes).

## Notes (as coded)
- If all cash flow values are non‑negative or non‑positive, XIRR is **undefined** → direct fallback.
- XIRR date set includes cash flow dates plus `end_date`; start date equals min(cash_flow_dates ∪ {end_date}).
- Dietz uses calendar days between dates for weighting and optional annualization.

## File Pointers
- `engine/mwr.py`
