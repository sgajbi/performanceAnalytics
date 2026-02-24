# Money-Weighted Return (MWR) Methodology

[cite_start]The Money-Weighted Return (MWR) measures the performance of the actual capital an investor has deployed in a portfolio[cite: 292]. [cite_start]Unlike TWR, MWR is **heavily influenced by the size and timing of cash flows**[cite: 293]. [cite_start]It effectively calculates the investor's personal Internal Rate of Return (IRR) and answers the question: *"What was my actual return on the money I invested?"* [cite: 294]

---

## Inputs

[cite_start]The MWR endpoint (`POST /performance/mwr`) requires the portfolio's starting and ending values, along with all intervening cash flows[cite: 295].
-   [cite_start]**`begin_mv`**: The market value at the beginning of the period[cite: 295].
-   [cite_start]**`end_mv`**: The market value at the end of the period[cite: 296].
-   [cite_start]**`cash_flows`**: A list of all cash flows, each with an `amount` and `date`[cite: 297]. [cite_start]Contributions are positive, and withdrawals are negative[cite: 298].
-   [cite_start]**`as_of`**: The final date for the calculation, corresponding to `end_mv`[cite: 299].
-   [cite_start]**`mwr_method`**: The desired calculation method: `XIRR` (default), `MODIFIED_DIETZ`, or `DIETZ`[cite: 300].
-   [cite_start]**`annualization`**: Optional settings to enable and configure annualization of the result[cite: 301].

---

## Multi-Currency Portfolios

To calculate a money-weighted return for a multi-currency portfolio, the caller is responsible for providing all monetary values (`begin_mv`, `end_mv`, and `cash_flows`) pre-converted into a **single, consistent base currency**. The engine will then calculate the MWR in that base currency.

The `report_ccy` field should be used to specify the currency of the inputs and the final calculation. Unlike TWR or Contribution, the MWR is a single, period-level metric and is not decomposed into local and FX components.

---

## Outputs

[cite_start]The response provides the calculated MWR and rich metadata about the calculation[cite: 302].
-   [cite_start]**`money_weighted_return`**: The calculated rate of return for the entire period[cite: 303].
-   [cite_start]**`mwr_annualized`**: The annualized version of the return (if requested)[cite: 304].
-   [cite_start]**`method`**: The final method used for the calculation (e.g., `XIRR` or `DIETZ` if it fell back)[cite: 305].
-   [cite_start]**`convergence`**: For the `XIRR` method, provides details on whether the solver converged to a solution[cite: 306].
-   [cite_start]**Shared Envelope**: Includes `meta`, `diagnostics` (with notes on fallbacks), and `audit` blocks[cite: 307].

---

## Methodology

[cite_start]The engine supports multiple methods and includes a robust fallback policy to ensure a result is always returned[cite: 308].
### 1. XIRR Solver (Default Method)

[cite_start]The primary and most accurate method is **XIRR (eXtended Internal Rate of Return)**[cite: 309]. [cite_start]It finds the single discount rate (`r`) that makes the Net Present Value (NPV) of all cash flows equal to zero[cite: 310]. [cite_start]The engine uses an iterative numerical solver (Brent's method) to find the root of the following equation: [cite: 310]

$$
0 = -BMV + \frac{EMV}{(1 + r)^{T/365.25}} + \sum_{i=1}^{N} \frac{CF_i}{(1 + r)^{t_i/365.25}}
$$

Where:
-   [cite_start]$BMV$ and $EMV$ are the beginning and ending market values[cite: 311].
-   [cite_start]$CF_i$ is the i-th cash flow[cite: 311].
-   $t_i$ is the number of days from the start of the period to the date of $CF_i$.
-   [cite_start]$T$ is the total number of days in the period[cite: 312].
[cite_start]The result `r` is an effective periodic rate that is already annualized[cite: 313].
### 2. Simple Dietz (Fallback Method)

[cite_start]If the XIRR solver cannot find a solution (e.g., it fails to converge or there is no sign change in the cash flows), the engine automatically falls back to the **Simple Dietz** method[cite: 314].
$$
R_{dietz} = \frac{EMV - BMV - CF_{net}}{BMV + (CF_{net} / 2)}
$$

[cite_start]Where $CF_{net}$ is the sum of all cash flows[cite: 315]. [cite_start]This method is less precise as it assumes, in effect, that all net cash flow occurred at the midpoint of the period[cite: 316].
### 3. Annualization

[cite_start]If annualization is enabled for the Dietz method, the periodic rate is converted to an annual rate using standard geometric compounding, respecting the chosen day-count basis[cite: 317].
$$
Annualized = (1 + R_{dietz})^{\frac{\text{PeriodsPerYear}}{\text{NumDays}}} - 1
$$

---

## Features

-   [cite_start]**Industry-Standard XIRR**: Uses a robust numerical solver for the most accurate MWR calculation[cite: 319].
-   [cite_start]**Resilient Fallback**: Automatically switches from XIRR to Simple Dietz if the solver fails, ensuring a result is always provided[cite: 320].
-   [cite_start]**Transparent Diagnostics**: The response clearly indicates which method was ultimately used and provides convergence details for XIRR[cite: 321].
-   [cite_start]**Annualization**: Optionally provides a standardized annualized return for comparison across different time horizons[cite: 322].

---

## API Example

### Request

```json
{
  "portfolio_id": "MWR_EXAMPLE_01",
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
  "portfolio_id": "MWR_EXAMPLE_01",
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
