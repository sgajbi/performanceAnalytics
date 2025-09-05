# Performance Calculation Methodology

This document details the mathematical and logical foundations of the performance calculation engine. The engine supports two distinct types of return calculation: Time-Weighted Return (TWR) and Money-Weighted Return (MWR).

---

## 1. Time-Weighted Return (TWR)

A **Time-Weighted Return** measures the compounded growth rate of a portfolio over a specified period. It is the standard for judging the performance of a portfolio manager because it **neutralizes the distorting effects of cash flows** (i.e., deposits and withdrawals). The result answers the question: "How well did the portfolio's assets perform on their own?"

The TWR calculation is a two-step process: calculating a return for each discrete sub-period (daily, in our case) and then geometrically linking them.

### Daily Return Calculation

We calculate the return for each day using a formula similar to the **Modified Dietz method**. This formula accounts for the market value and any cash flows that occurred.

The formula for the daily rate of return ($R_{day}$) is:

$$ R_{day} = \frac{EMV - BMV - CF_{net}}{BMV + CF_{bod}} $$

Where:
-   **EMV**: End of Day Market Value
-   **BMV**: Beginning of Day Market Value
-   **$CF_{net}$**: Net cash flow for the day ($CF_{bod} + CF_{eod}$).
-   **$CF_{bod}$**: Cash flow at the Beginning of the Day.

The `metric_basis` ("NET" or "GROSS") determines if management fees are included in the gain/loss calculation. For a "NET" basis, the formula effectively becomes:

$$ R_{day} (NET) = \frac{EMV - BMV - CF_{net} + Fees}{BMV + CF_{bod}} $$

### Geometric Linking (Compounding)

Daily returns are chained together to produce a running cumulative return for a given period.

$$ R_{cumulative} = (1 + R_1) \times (1 + R_2) \times \dots \times (1 + R_n) - 1 $$

### Special Logic

-   **Long vs. Short Positions:** The engine determines if a position is long (`sign = 1`) or short (`sign = -1`). For short positions, where a decrease in market value represents a gain, the growth factor is calculated as `(1 - R_{day})` instead of `(1 + R_{day})`.

-   **Performance Resets:** To handle cases where compounding becomes mathematically unsound (e.g., after a total loss of -100%), the cumulative return is "reset" to zero. This occurs when a cumulative return breaches a threshold (e.g., -100%) and a significant portfolio event (like a cash flow or month-end) occurs.

-   **Breakdowns:** This daily TWR stream is the foundation for the aggregated **monthly, quarterly, and yearly** breakdowns. The return for an aggregated period is calculated by geometrically linking all the daily returns within that period.

---

## 2. Money-Weighted Return (MWR)

A **Money-Weighted Return** measures the performance of the actual capital invested by an investor. Unlike TWR, it is heavily influenced by the timing and size of cash flows. It answers the question: "What was my personal return on the money I invested?"

The engine calculates MWR using a simplified version of the Modified Dietz method for the entire period.

### MWR Formula

The formula for the Money-Weighted Return ($R_{mwr}$) over the whole period is:

$$ R_{mwr} = \frac{EMV - BMV - CF_{net}}{BMV + CF_{net}} $$

Where:
-   **EMV**: Ending Market Value for the entire period.
-   **BMV**: Beginning Market Value for the entire period.
-   **$CF_{net}$**: The sum of all cash flows that occurred during the period.

This implementation, mirroring the `portfolio-analytics-system`, uses a direct sum for cash flows. A more complex implementation would time-weight each cash flow based on when it occurred during the period.