Of course. Here is a detailed RFC for the implementation of the Position Contribution Engine, based on the methodology we've defined and the latest repository structure.

-----

# RFC-003: Position Contribution Engine

**Status:** Draft
**Author:** Gemini
**Date:** 2025-09-05

## 1\. Executive Summary

This document outlines the design and implementation plan for a new **Position Contribution Engine**. The purpose of this engine is to decompose a portfolio's total Time-Weighted Return (TWR) into the individual contributions of its underlying positions, answering the question of *what* drove the portfolio's performance.

This new engine will be built alongside the existing TWR performance engine, leveraging it to calculate the necessary position-level and portfolio-level returns. The core methodology will be based on single-period contribution (`Weight × Return`), linked over multiple periods using the **Carino Smoothing Algorithm** to ensure mathematical accuracy. The engine will also respect portfolio-level events such as No-Investment-Period (NIP) and Performance Reset days.

## 2\. Rationale

While the existing TWR engine accurately measures a portfolio's overall performance, it does not provide insight into the drivers of that performance. A contribution engine is the first step toward a full attribution model, allowing users to identify which positions added the most value and which ones detracted from it. This functionality is essential for sophisticated portfolio analysis and management.

## 3\. Proposed Architecture & Data Flow

The contribution engine will be a new, distinct module within our existing `engine/` layer. It will orchestrate calls to the TWR engine and apply the contribution-specific formulas.

**Data Flow:**

1.  **Input:** The API will receive a request containing a time series for the total portfolio and a list of time series for each individual position.
2.  **Portfolio TWR Calculation:** The portfolio-level time series is passed to our existing TWR engine (`engine.compute.run_calculations`). This yields the daily portfolio returns ($RoR\_{port,t}$), the total portfolio return ($RoR\_{port}$), and the critical portfolio-level `NIP` and `reset` flags for each day.
3.  **Position TWR Calculation:** The engine will iterate through the time series for each position, passing each one individually through the same TWR engine (`engine.compute.run_calculations`) to calculate its daily returns ($RoR\_{p,t}$).
4.  **Contribution Calculation:** A new **`engine/contribution.py`** module will take the results from steps 2 and 3 as input. It will then perform the complete contribution methodology:
      * Calculate the daily average weight ($W\_{p,t}$) for each position.
      * Calculate the daily and total-period Carino smoothing factors ($k\_t$, $K$).
      * Calculate the smoothed daily contribution ($C'\_{p,t}$) for each position.
      * Apply the portfolio-level `NIP` and `reset` rules, setting daily contributions to zero on those days.
      * Sum the daily smoothed contributions to get the final total contribution for each position.
5.  **Output:** The API will return a detailed breakdown of the contribution for each position.

## 4\. Implementation Plan

#### Phase 1: API & Data Models

1.  **Create Contribution Models** in new files under `app/models/`:
      * `contribution_requests.py`: Define `ContributionRequest` and `PositionData` Pydantic models.
      * `contribution_responses.py`: Define `ContributionResponse` and `PositionContribution` Pydantic models.
2.  **Create Contribution Endpoint**:
      * Create a new file `app/api/endpoints/contribution.py` with a `POST /performance/contribution` endpoint.

#### Phase 2: Contribution Engine

1.  **Create `engine/contribution.py`**:
      * This file will house the core logic.
      * Implement a main orchestrator function: `calculate_position_contribution()`.
      * Implement pure helper functions for each step of the methodology: calculating weights, calculating Carino factors (with exception handling for zero returns), and calculating the final smoothed contribution.
2.  **Integrate with TWR Engine**:
      * The orchestrator will import and call `engine.compute.run_calculations` as described in the data flow.

#### Phase 3: Integration & Testing

1.  **Connect Endpoint to Engine**: Update the `POST /performance/contribution` endpoint to call the `calculate_position_contribution` function and return the formatted response.
2.  **Add Unit Tests**: Create `tests/unit/engine/test_contribution.py` to test the individual calculation helpers (weights, smoothing, etc.) in isolation.
3.  **Add Characterization Test**: Create a new characterization test suite (`test_contribution_characterization.py` and `contribution_data.py`) to validate the end-to-end results of a complex, multi-period scenario against a known-good spreadsheet calculation.

## 5\. API Contract (Draft)

#### Request Body (`POST /performance/contribution`)

```json
{
  "calculation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "portfolio_number": "CONTRIB_TEST_01",
  "portfolio_data": {
    "report_start_date": "2025-01-01",
    "report_end_date": "2025-01-31",
    "daily_data": [
      {
        "Perf. Date": "2025-01-01",
        "Begin Market Value": 1000.0,
        "End Market Value": 1010.0,
        "BOD Cashflow": 0.0,
        "Eod Cashflow": 0.0,
        "Mgmt fees": 0.0
      }
    ]
  },
  "positions_data": [
    {
      "position_id": "Stock_A",
      "daily_data": [
        {
          "Perf. Date": "2025-01-01",
          "Begin Market Value": 600.0,
          "End Market Value": 612.0,
          "BOD Cashflow": 0.0,
          "Eod Cashflow": 0.0,
          "Mgmt fees": 0.0
        }
      ]
    },
    {
      "position_id": "Stock_B",
      "daily_data": [
        {
          "Perf. Date": "2025-01-01",
          "Begin Market Value": 400.0,
          "End Market Value": 398.0,
          "BOD Cashflow": 0.0,
          "Eod Cashflow": 0.0,
          "Mgmt fees": 0.0
        }
      ]
    }
  ]
}
```

#### Response Body

```json
{
  "calculation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "portfolio_number": "CONTRIB_TEST_01",
  "report_start_date": "2025-01-01",
  "report_end_date": "2025-01-31",
  "total_portfolio_return": 15.75,
  "total_contribution": 15.75,
  "position_contributions": [
    {
      "position_id": "Stock_A",
      "total_contribution": 12.25,
      "average_weight": 0.60,
      "total_return": 20.41
    },
    {
      "position_id": "Stock_B",
      "total_contribution": 3.50,
      "average_weight": 0.40,
      "total_return": 8.75
    }
  ]
}
```