# Money-Weighted Return (MWR) Methodology

The Money-Weighted Return (MWR) measures the performance of the actual capital an investor has deployed in a portfolio. Unlike TWR, MWR is **heavily influenced by the size and timing of cash flows**. It effectively calculates the investor's personal Internal Rate of Return (IRR) and answers the question: *"What was my actual return on the money I invested?"*

---

## Inputs

The MWR endpoint (`POST /performance/mwr`) requires the portfolio's starting and ending values, along with all intervening cash flows.

-   **`begin_mv`**: The market value at the beginning of the period.
-   **`end_mv`**: The market value at the end of the period.
-   **`cash_flows`**: A list of all cash flows, each with an `amount` and `date`. Contributions are positive, and withdrawals are negative.
-   **`as_of`**: The final date for the calculation, corresponding to `end_mv`.
-   **`mwr_method`**: The desired calculation method: `XIRR` (default), `MODIFIED_DIETZ`, or `DIETZ`.
-   **`annualization`**: Optional settings to enable and configure annualization of the result.

---

## Outputs

The response provides the calculated MWR and rich metadata about the calculation.

-   **`money_weighted_return`**: The calculated rate of return for the entire period.
-   **`mwr_annualized`**: The annualized version of the return (if requested).
-   **`method`**: The final method used for the calculation (e.g., `XIRR` or `DIETZ` if it fell back).
-   **`convergence`**: For the `XIRR` method, provides details on whether the solver converged to a solution.
-   **Shared Envelope**: Includes `meta`, `diagnostics` (with notes on fallbacks), and `audit` blocks.

---

## Methodology

The engine supports multiple methods and includes a robust fallback policy to ensure a result is always returned.

### 1. XIRR Solver (Default Method)

The primary and most accurate method is **XIRR (eXtended Internal Rate of Return)**. It finds the single discount rate (`r`) that makes the Net Present Value (NPV) of all cash flows equal to zero. The engine uses an iterative numerical solver (Brent's method) to find the root of the following equation:

$$
0 = -BMV + \frac{EMV}{(1 + r)^{T/365.25}} + \sum_{i=1}^{N} \frac{CF_i}{(1 + r)^{t_i/365.25}}
$$

Where:
-   $BMV$ and $EMV$ are the beginning and ending market values.
-   $CF_i$ is the i-th cash flow.
-   $t_i$ is the number of days from the start of the period to the date of $CF_i$.
-   $T$ is the total number of days in the period.

The result `r` is an effective periodic rate that is already annualized.

### 2. Simple Dietz (Fallback Method)

If the XIRR solver cannot find a solution (e.g., it fails to converge or there is no sign change in the cash flows), the engine automatically falls back to the **Simple Dietz** method.

$$
R_{dietz} = \frac{EMV - BMV - CF_{net}}{BMV + (CF_{net} / 2)}
$$

Where $CF_{net}$ is the sum of all cash flows. This method is less precise as it assumes, in effect, that all net cash flow occurred at the midpoint of the period.

### 3. Annualization

If annualization is enabled for the Dietz method, the periodic rate is converted to an annual rate using standard geometric compounding, respecting the chosen day-count basis.

$$
Annualized = (1 + R_{dietz})^{\frac{\text{PeriodsPerYear}}{\text{NumDays}}} - 1
$$

---

## Features

-   **Industry-Standard XIRR**: Uses a robust numerical solver for the most accurate MWR calculation.
-   **Resilient Fallback**: Automatically switches from XIRR to Simple Dietz if the solver fails, ensuring a result is always provided.
-   **Transparent Diagnostics**: The response clearly indicates which method was ultimately used and provides convergence details for XIRR.
-   **Annualization**: Optionally provides a standardized annualized return for comparison across different time horizons.

---

## API Example

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
```

### Response (Excerpt)

```json
{
  "calculation_id": "uuid-goes-here",
  "portfolio_number": "MWR_EXAMPLE_01",
  "money_weighted_return": 11.723,
  "mwr_annualized": 11.723,
  "method": "XIRR",
  "convergence": { "iterations": null, "residual": null, "converged": true },
  "start_date": "2025-03-15",
  "end_date": "2025-12-31",
  "notes": ["XIRR calculation successful."],
  "meta": { ... },
  "diagnostics": { ... },
  "audit": { "counts": { "cashflows": 2 } }
}
```