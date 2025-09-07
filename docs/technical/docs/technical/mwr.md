
# Money-Weighted Return (MWR)

The Money-Weighted Return (MWR) measures a portfolio’s performance by **internal rate of return (IRR)**, directly reflecting the investor’s actual experience.  
Unlike TWR, MWR accounts for the **size and timing of cash flows**.

---

## Inputs

- **begin_mv** – Beginning market value.
- **end_mv** – Ending market value.
- **cash_flows** – List of `{date, amount}` objects:
  - Positive = contributions.
  - Negative = withdrawals.
- **mwr_method** – Supported calculation methods:
  - `XIRR` – Exact IRR solver.
  - `MODIFIED_DIETZ` – Approximation with weighted cash flows.
  - `DIETZ` – Simple Dietz approximation.
- **solver** (for IRR):
  - `method` – Numerical solver (default: `brent`).
  - `max_iter` – Maximum iterations.
  - `tolerance` – Convergence tolerance.
- **annualization** – Optional, to convert to annualized return.
- **as_of** – End date of evaluation period.

---

## Outputs

- **money_weighted_return** – IRR over the period.
- **mwr_annualized** – Annualized IRR (if enabled).
- **method** – Which calculation was applied (`XIRR`, `MODIFIED_DIETZ`, `DIETZ`).
- **start_date / end_date** – Reporting window.
- **notes** – Diagnostics about solver convergence or approximations used.
- **convergence** – Details of solver iterations and residuals.
- **meta / diagnostics / audit** – Shared envelopes.

---

## Methodology

### 1. Cash Flow Normalization
All cash flows are normalized to present value relative to **begin_mv** and **end_mv**.

### 2. XIRR Solver (Default)
MWR solves for rate `r` such that:
\[
0 = \sum_{i=1}^{N} \frac{CF_i}{(1 + r)^{t_i / 365}} + \frac{EndMV}{(1 + r)^{T/365}} - BeginMV
\]
Where:
- \( CF_i \) = Cash flow at time \( i \).
- \( t_i \) = Days from start to cash flow date.
- \( T \) = Days in full evaluation period.

### 3. Modified Dietz Approximation
\[
MWR_{Dietz} = \frac{EndMV - BeginMV - \sum CF_i}{BeginMV + \sum (w_i \times CF_i)}
\]
Where \( w_i \) = fraction of period cash flow was invested.

### 4. Annualization
\[
Annualized = (1 + MWR)^{\frac{PeriodsPerYear}{N}} - 1
\]

---

## Features

- IRR solver with configurable tolerance/iterations.
- Multiple methodologies (exact vs approximations).
- Handles irregular timing of flows.
- Returns convergence diagnostics.
- Annualization supported with different bases (BUS/252, ACT/365, ACT/ACT).

---

## Example

### Request
```json
{
  "portfolio_number": "MWR_EXAMPLE_01",
  "begin_mv": 100000.0,
  "end_mv": 115000.0,
  "as_of": "2025-12-31",
  "cash_flows": [
    { "amount": 10000.0, "date": "2025-03-15" },
    { "amount": -5000.0, "date": "2025-09-20" }
  ],
  "mwr_method": "XIRR",
  "annualization": { "enabled": true }
}
````

### Response (simplified)

```json
{
  "calculation_id": "uuid",
  "portfolio_number": "MWR_EXAMPLE_01",
  "money_weighted_return": 0.145,
  "mwr_annualized": 0.148,
  "method": "XIRR",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "notes": ["Converged in 5 iterations"],
  "convergence": { "iterations": 5, "residual": 1e-9, "converged": true },
  "meta": { "...": "..." },
  "diagnostics": { "...": "..." },
  "audit": { "cashflows": 2 }
}
```
 