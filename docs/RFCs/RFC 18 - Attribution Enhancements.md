# RFC 18: Attribution Enhancements

**Status:** Final (For Approval)  
**Owner:** Senior Architect  
**Reviewers:** Perf Engine, Risk, Platform  
**Target Release:** v0.4.x  
**Related:** RFC-014 (Cross-Cutting Consistency & Diagnostics Framework), `/performance/attribution`

## 1\. Executive Summary

This document specifies a major upgrade to the `/performance/attribution` endpoint, transforming it from a single-level tool into a flexible, multi-level analytical engine. This RFC introduces support for **multiple Brinson models** (BF and BHB), **configurable linking methods** (Geometric and Arithmetic), and most importantly, **multi-level hierarchical analysis**. These enhancements provide portfolio managers with deeper, more customizable insights into the drivers of active return, allowing them to decompose performance across dimensions like sector, industry, and security in a single, coherent request.

## 2\. Current State Analysis

The existing attribution engine is functional but limited in its analytical scope.

  * **Single Model/Method:** It is hardcoded to use the Brinson-Fachler (BF) model and Menchero (geometric) linking, preventing users from applying other industry-standard variations.
  * **No Hierarchical Analysis:** The engine can only perform attribution on a single dimension (e.g., `sector`). Analyzing a `sector -> industry` hierarchy requires multiple, separate API calls that are difficult to reconcile.
  * **Implicit Edge Case Handling:** The engine does not provide explicit controls for handling common edge cases, such as when a security exists in the portfolio but has zero weight in the benchmark.

## 3\. Proposed Enhancements & Methodology

### 3.1 Brinson Model Variants

The engine will support the two primary Brinson models, selectable via a `model` parameter.

  * **Trigger:** `"model": "BF"` or `"model": "BHB"` in the `AttributionRequest`.
  * **Logic:** The `engine/attribution.py` module will implement a strategy pattern to apply the correct formulas for Allocation and Selection effects based on the chosen model. Brinson-Fachler (`BF`) will remain the default.

### 3.2 Configurable Multi-Period Linking

Users will be able to choose how single-period effects are linked over time.

  * **Trigger:** `"linking": "MENCHERO"` or `"linking": "ARITHMETIC"` in the `AttributionRequest`.
  * **Logic:** The engine will conditionally apply the Menchero algorithm for geometrically accurate linking (the default) or perform a simple arithmetic sum if requested.

### 3.3 Multi-Level Hierarchical Analysis

The endpoint will be able to compute and return attribution results for a full hierarchy in a single call.

  * **Trigger:** Providing an ordered list of dimensions in the `hierarchy` request field (e.g., `["sector", "industry", "security"]`).
  * **Logic:** The engine will perform the attribution calculation iteratively, starting from the top level. The results for each level will be returned in a structured `levels` array in the response, ensuring that totals reconcile from the bottom up.

### 3.4 Explicit Reconciliation

To improve transparency and trust, the response will include a dedicated `reconciliation` block. This block will explicitly show that the sum of the calculated attribution effects (Allocation + Selection + Interaction) equals the independently calculated active return ($TWR\_{Portfolio} - TWR\_{Benchmark}$), with any residual clearly stated in basis points.

## 4\. API Contract Changes

### 4.1 `AttributionRequest` Additions

```jsonc
{
  // ... existing fields ...
  "model": "BF",                         // "BF" | "BHB"
  "linking": "MENCHERO",                 // "MENCHERO" | "ARITHMETIC"
  "hierarchy": ["sector", "industry"],   // Ordered list for hierarchical rollup
  "zero_weight_policy": "drop",          // "drop" | "carry_forward" | "normalize"
  "emit": {
    "active_reconciliation": true,
    "by_level": true
  }
}
```

### 4.2 `AttributionResponse` Additions

```jsonc
{
  // ... existing fields ...
  "summary": { "active_return": 0.0121 },
  "components": { "allocation": 0.0048, "selection": 0.0065, "interaction": 0.0008 },
  "reconciliation": {
    "portfolio_minus_benchmark": 0.0121,
    "sum_components": 0.0121,
    "residual_bp": 0.0
  },
  "levels": [
    {
      "level": "sector",
      "rows": [ { "key": {"sector": "Tech"}, "A": 0.003, "S": 0.004, "I": 0.001 } ]
    },
    {
      "level": "industry",
      "rows": [ { "key": {"sector": "Tech", "industry": "Software"}, "A": 0.001, "S": 0.002, "I": 0.0 } ]
    }
  ]
}
```

## 5\. Testing Strategy

  * **Unit Tests:** New tests will be added to `tests/unit/engine/test_attribution.py` to:
      * Compare the outputs of the BF and BHB models on a simple, known dataset.
      * Verify that `linking: "ARITHMETIC"` produces a simple sum of single-period effects.
  * **Integration Tests:** A new integration test will be created for a multi-level `hierarchy` request. The test will assert that the sum of contributions at a lower level (e.g., `industry`) correctly rolls up to the corresponding parent key in the level above (e.g., `sector`).

## 6\. Acceptance Criteria

1.  The `/performance/attribution` endpoint is enhanced to support selectable Brinson models and linking methods.
2.  The endpoint can correctly process a `hierarchy` request and return a multi-level, nested response.
3.  The response includes a `reconciliation` block that validates the accuracy of the calculation.
4.  All new and existing unit and integration tests for the attribution feature are passing.
5.  Documentation in `docs/guides/api_reference.md` and `docs/guides/attribution_methodology.md` is updated to reflect the new hierarchical capabilities and configuration options.
6.  This RFC is formally approved before implementation begins.
