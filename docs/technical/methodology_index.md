# Methodology Index

This index provides a central navigation point for all detailed methodology and technical documentation for the **performanceAnalytics** engine and API. It is designed to help new developers, business analysts, and product teams quickly find the information they need.

---

## Core Technical Documents

These documents describe the foundational architecture and data contracts of the system.

-   [**Architecture**](architecture.md): An overview of the system's layered design, component responsibilities, and the end-to-end data flow from API request to response.
-   [**Data Model**](data_model.md): The canonical reference for all input/output schemas, the shared API envelope (`meta`, `diagnostics`, `audit`), and common enums.
-   [**Engine Config**](engine_config.md): A detailed guide to all configurable parameters, including precision modes, period types, calendars, and diagnostics.

---

## Performance Methodologies

These documents provide in-depth explanations of the financial logic and calculation steps for each of the core analytical functions.

-   [**TWR (Time-Weighted Return)**](twr.md)
    -   Daily Rate of Return Calculation
    -   Geometric Linking for Compounding
    -   Breakdown by Frequency (Daily, Monthly, etc.)
    -   Annualization

-   [**MWR (Money-Weighted Return)**](mwr.md)
    -   Internal Rate of Return (XIRR) Solver
    -   Modified Dietz Approximation and Fallback Policy
    -   Handling of Cash Flow Size and Timing
    -   Annualization

-   [**Contribution Analysis**](contribution.md)
    -   Single-Period Position-Level Contributions
    -   Multi-Period Linking with Carino Smoothing
    -   Hierarchical Breakdown and Bottom-Up Aggregation
    -   Residual Tracking and Distribution

-   [**Attribution Analysis**](attribution.md)
    -   Brinson Models (Brinson-Fachler & Brinson-Hood-Beebower)
    -   Decomposition into Allocation, Selection, & Interaction Effects
    -   Multi-Period Geometric Linking with Menchero Algorithm
    -   Reconciliation Against Total Active Return

---

## Usage

Each methodology page is structured to include:

-   **Inputs & Outputs**: The specific API request and response fields.
-   **Methodology**: A detailed, step-by-step breakdown of the calculation logic, suitable for a business audience.
-   **Features**: A list of supported options, toggles, and configurations.
-   **Examples**: Complete JSON request and response samples.

