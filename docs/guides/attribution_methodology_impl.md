# Attribution Methodology — Implementation-Faithful

Mirrors `engine/attribution.py`.

## Modes
- **BY_INSTRUMENT**: Build portfolio groups from instruments’ `meta[group_by]` and their TWR results.
- **BY_GROUP**: Accept pre‑aggregated portfolio groups directly.

## Preparation
1. Compute TWR results for instruments (same engine path as TWR) and derive **BOP weights** per instrument:
   ```text
   weight_bop = (begin_mv + bod_cf)_instrument / (begin_mv + bod_cf)_portfolio
   ```
2. Build a panel with columns: `date`, `group_keys...`, `r_p` (portfolio group return), `w_p` (group weight), and `r_b`, `w_b` from benchmark.
3. **Frequency**: Map `request.frequency` → pandas resample codes:  
   `daily→'D', monthly→'ME', quarterly→'QE', yearly→'YE'`.
   - For returns: resample by **geometric chaining** within each period: `(1 + r).prod() − 1`.
   - For weights: use **first** (BOP) weight in the period.

## Single‑Period Effects (as coded in `_calculate_single_period_effects`)  

### Brinson‑Fachler (BF)
```text
Allocation   = (w_p − w_b) * (r_b − r_b_total)
Selection    = w_b * (r_p − r_b)
Interaction  = (w_p − w_b) * (r_p − r_b)
```

### Brinson‑Hood‑Beebower (BHB)
```text
Allocation   = (w_p − w_b) * r_b
Selection    = w_p * (r_p − r_b)
Interaction  = (w_p − w_b) * (r_p − r_b)   # retained for completeness
```

Where `r_b_total` is the **benchmark total return** in the period: `sum_g (w_b_g * r_b_g)`.

## Linking Across Periods
If `request.linking != NONE`, the engine computes:
- `geometric_active_return = Geom(Portfolio) − Geom(Benchmark)`
- `arithmetic_active_return = Σ (r_p − r_b)`  
Then scales each effect **top‑down** by a constant factor:
```text
scaling_factor = geometric_active_return / arithmetic_active_return
linked_effect  = effect * scaling_factor
```
This ensures the **sum of linked effects** equals the geometric active return.

## Emission
- Build `levels[]` per dimension in `request.group_by`, each with per‑group `{allocation, selection, interaction, total_effect}`.
- Reconciliation object:
  - `total_active_return` (geometric if linking enabled, otherwise arithmetic sum)
  - `sum_of_effects`
  - `residual = total_active_return% − sum_of_effects`

## File Pointers
- `engine/attribution.py`
