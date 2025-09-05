# Performance Calculation Methodology

This document details the mathematical and logical foundations of the performance calculation engine. The engine supports two distinct types of return calculation: Time-Weighted Return (TWR) and Money-Weighted Return (MWR).

---

## 1. Time-Weighted Return (TWR)

A **Time-Weighted Return** measures the compounded growth rate of a portfolio over a specified period. It is the standard for judging the performance of a portfolio manager because it **neutralizes the distorting effects of cash flows** (i.e., deposits and withdrawals). The result answers the question: "How well did the portfolio's assets perform on their own?"

The TWR calculation is a two-step process: calculating a return for each discrete sub-period (daily, in our case) and then geometrically linking them.

### Daily Return Calculation

We calculate the return for each day using a formula similar to the **Modified Dietz method**.

$$ R_{day} = \frac{EMV - BMV - CF_{net}}{BMV + CF_{bod}} $$

Where:
-   **EMV**: End of Day Market Value
-   **BMV**: Beginning of Day Market Value
-   **$CF_{net}$**: Net cash flow for the day ($CF_{bod} + CF_{eod}$).
-   **$CF_{bod}$**: Cash flow at the Beginning of the Day.

The `metric_basis` ("NET" or "GROSS") determines if management fees are included in the gain/loss calculation. For a "NET" basis, the formula effectively becomes:

$$ R_{day} (NET) = \frac{EMV - BMV - CF_{net} + Fees}{BMV + CF_{bod}} $$

### Long & Short Sleeve Calculation

To correctly handle portfolios that can flip between long and short positions, the engine maintains two independent performance streams, or "sleeves":

* **Long Sleeve ($R_{long}$):** This sleeve only accrues performance on days when the portfolio is **long** (sign = 1).
* **Short Sleeve ($R_{short}$):** This sleeve only accrues performance on days when the portfolio is **short** (sign = -1).

On days not assigned to a sleeve (e.g., a long day for the short sleeve), the previous day's cumulative return for that sleeve is carried forward.

The compounding formula is adapted for each sleeve:

-   **Long Sleeve Growth Factor**: $GF_{long} = (1 + R_{day})$
-   **Short Sleeve Growth Factor**: $GF_{short} = (1 - R_{day})$

The cumulative return for each sleeve is calculated by geometrically linking the growth factors for their respective active days. The short sleeve result is multiplied by -1 to maintain the convention that a gain is a positive number.

### Merging Sleeves for Final Cumulative Return

The independent long and short sleeves are combined at the end of each day to produce the final, total cumulative TWR for the portfolio.

The linking formula is:

$$ R_{final} = (1 + R_{long\_cumulative}) \times (1 + R_{short\_cumulative}) - 1 $$

---

## 2. Money-Weighted Return (MWR)

A **Money-Weighted Return** measures the performance of the actual capital invested by an investor. Unlike TWR, it is heavily influenced by the timing and size of cash flows. It answers the question: "What was my personal return on the money I invested?"

The engine calculates MWR using a simplified version of the Modified Dietz method for the entire period.

### MWR Formula

$$ R_{mwr} = \frac{EMV - BMV - CF_{net}}{BMV + CF_{net}} $$

Where:
-   **EMV**: Ending Market Value for the entire period.
-   **BMV**: Beginning Market Value for the entire period.
-   **$CF_{net}$**: The sum of all cash flows that occurred during the period.

---

## 3. Advanced Rules & Edge Cases

These rules handle specific scenarios to ensure calculations remain robust and meaningful.

### No Investment Period (NIP)

The **purpose** of the NIP flag is to identify days where no capital was invested, making performance calculation irrelevant. On NIP days, the previous day's cumulative return is carried forward. The engine supports two logical definitions for a NIP day:

* **V1 Rule (Legacy):** A day is flagged as NIP only if the total portfolio value for the day is zero AND the end-of-day cash flow equals the negative *sign* of the beginning-of-day cash flow. This handles a very specific legacy data condition.
* **V2 Rule (Simplified):** Available via a feature flag, this rule marks a day as NIP if the portfolio both starts and ends the day with a zero balance (`BMV + BOD_CF = 0` and `EMV + EOD_CF = 0`).

### Performance Resets (NCTRL Flags)

The **purpose** of a performance reset is to set the cumulative TWR back to zero. This is done when compounding becomes mathematically unsound, such as after a portfolio loses more than 100% of its value. A reset is only triggered on a **"significant day"** (a day with a cash flow, a month-end, etc.).

There are four conditions (`NCTRL` flags) that trigger a reset:

* **`NCTRL 1` (Long Position Wipeout):** Triggered on the day a **long position's** cumulative TWR first crosses below **-100%**.
* **`NCTRL 2` (Short Position Inversion):** Triggered on the day a **short position's** cumulative TWR first crosses above **+100%**. This signifies the short position's market value has become positive.
* **`NCTRL 3` (Complex Short Reset):** An edge case for short positions, triggering if the short TWR crosses below -100% while there's an active long TWR.
* **`NCTRL 4` (Post-Wipeout Cash Flow):** A look-back rule that triggers on the current day if the portfolio was already in a reset state on the **previous day** AND there is a cash flow event on the **current day**.