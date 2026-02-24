# RFC 024: Robustness Policies Framework (Final)

**Status:** Final
**Owner:** Senior Architect
**Date:** 2025-09-08
**Related:** All core analytics endpoints, RFC-025 (Reproducibility)

## 1\. Executive Summary

This document specifies the final design for a new, uniform **Robustness Policies Framework**. Production data is often imperfect, containing known errors or anomalies that can compromise the integrity of performance calculations. This RFC moves the platform from implicit, hardcoded handling of these issues to an explicit, configurable, and fully auditable framework.

A new `data_policy` object will be added to the shared request envelope. This gives users granular, on-demand control to **manually override incorrect data points**, instruct the engine to **ignore known "noisy" days**, and **flag statistical outliers** for review. All actions taken by the policy engine will be reported in the `diagnostics` block of the response, ensuring complete transparency.

This framework empowers users to handle real-world data issues in a deterministic and auditable way, making all analytics more resilient, predictable, and defensible.

-----

## 2\. Goals & Non-Goals

### Goals

  * Introduce a single, consistent `data_policy` request object available on all major analytics endpoints.
  * Provide a mechanism for users to supply **explicit, in-memory overrides** for market values and cash flows on a per-request basis.
  * Provide a tool to **ignore specific "noisy" days** by carrying forward the prior day's state.
  * Implement a transparent system to **detect and flag statistical outliers** in returns without altering the underlying data.
  * Ensure all policy actions are counted and sampled in the response `diagnostics` block for full auditability.

### Non-Goals

  * This framework will not perform automated data correction (e.g., capping or removing outliers).
  * This framework is not a substitute for upstream data quality assurance.
  * It will not attempt to infer or handle corporate actions.

-----

## 3\. Methodology & Use Cases

The framework will apply user-defined policies as a pre-processing step before the core analytics are calculated. Below are the specific cases handled.

### Case 1: Manual Data Correction with `overrides`

  * **Problem**
    An incorrect `end_mv` for **Position\_XYZ** on `2025-03-15` and an erroneous `bod_cf` at the portfolio level on `2025-03-20` are skewing results. You need to run an accurate analysis with the correct values without modifying the source data.

  * **Handling with the Framework**
    The `data_policy` block includes an `overrides` section. The engine will apply these corrections in memory before any calculations begin.

    **Example `data_policy` Configuration:**

    ```json
    {
      "data_policy": {
        "overrides": {
          "market_values": [
            {
              "perf_date": "2025-03-15",
              "position_id": "Position_XYZ",
              "end_mv": 152340.50
            }
          ],
          "cash_flows": [
            {
              "perf_date": "2025-03-20",
              "portfolio_id": "PORT123",
              "bod_cf": 0.0
            }
          ]
        }
      }
    }
    ```

  * **Transparent Result**
    The `diagnostics` block provides a clear audit trail confirming the corrections were applied.

    ```json
    {
      "diagnostics": {
        "policy": {
          "overrides": { "applied_mv_count": 1, "applied_cf_count": 1 }
        },
        "notes": ["Applied 2 override(s) from the data_policy request."]
      }
    }
    ```

### Case 2: Ignoring "Noisy" or Corrupt Data Days

  * **Problem**
    The data for **Position\_ABC** is known to be corrupt on `2025-03-18` and `2025-03-19`. You want to exclude these days from the calculation for that position, treating it as if there were no market movement.

  * **Handling with the Framework**
    The new `ignore_days` policy instructs the engine to carry forward the prior day's state for the specified dates and entities, resulting in a 0% return for that period.

    **Example `data_policy` Configuration:**

    ```json
    {
      "data_policy": {
        "ignore_days": [
          {
            "entity_type": "POSITION",
            "entity_id": "Position_ABC",
            "dates": ["2025-03-18", "2025-03-19"]
          }
        ]
      }
    }
    ```

  * **Transparent Result**
    The engine logs the number of days that were ignored as requested.

    ```json
    {
      "diagnostics": {
        "policy": {
          "ignored_days_count": 2
        },
        "notes": ["Ignored 2 day(s) as specified in data_policy.ignore_days."]
      }
    }
    ```

### Case 3: Flagging Outlier Returns without Correction

  * **Problem**
    A data feed error causes a security's calculated daily return to be `+900%`. Your firm's policy requires you to be aware of such anomalies but not to alter the source data.

  * **Handling with the Framework**
    The `outliers` policy is used as a detection and reporting tool. It identifies anomalies but proceeds with calculations using the raw, unaltered data.

    **Example `data_policy` Configuration:**

    ```json
    {
      "data_policy": {
        "outliers": {
          "enabled": true,
          "scope": ["SECURITY_RETURNS"],
          "method": "MAD",
          "params": { "mad_k": 5.0, "window": 63 },
          "action": "FLAG"
        }
      }
    }
    ```

  * **Transparent Result**
    The primary output of this policy is the `diagnostics` block, which alerts you to the specific data point that was flagged as anomalous.

    ```json
    {
      "diagnostics": {
        "policy": {
          "outliers": { "flagged_rows": 1 }
        },
        "samples": {
          "outliers": [ { "date": "2025-03-12", "instrumentId": "XYZ", "raw_return": 900.0, "threshold": 15.0 } ]
        }
      }
    }
    ```

-----

## 4\. API Design

The following shows the complete `data_policy` block in the request and the extended `diagnostics` block in the response.

### Request Additions (`data_policy` block)

```json
{
  "data_policy": {
    "overrides": {
      "market_values": [],
      "cash_flows": []
    },
    "ignore_days": [],
    "outliers": {
      "enabled": false,
      "scope": ["SECURITY_RETURNS"],
      "method": "MAD",
      "params": { "mad_k": 5.0, "window": 63 },
      "action": "FLAG"
    }
  }
}
```

### Response Additions (`diagnostics` block)

```json
{
  "diagnostics": {
    "nip_days": 1,
    "reset_days": 0,
    "policy": {
      "overrides": { "applied_mv_count": 0, "applied_cf_count": 0 },
      "ignored_days_count": 0,
      "outliers": { "flagged_rows": 0 }
    },
    "samples": {
      "outliers": []
    },
    "notes": []
  }
}
```

### HTTP Semantics & Errors

  * **200 OK**: Successful computation.
  * **400 Bad Request**: Invalid `data_policy` configuration.
  * **422 Unprocessable Entity**: Request is valid, but an override refers to a date or entity not found in the input data.

-----

## 5\. Architecture & Implementation Plan

1.  **Create New Module**:
      * `engine/policies.py`: To house the logic for applying overrides, handling ignored days, and detecting outliers.
2.  **Integrate into Orchestrator**:
      * Modify `engine/compute.py` and other engine entry points to call the policy engine as the first step after data loading.
3.  **Update Diagnostics**:
      * Enhance the diagnostics collector to track and return the counts and samples from all policy actions.
4.  **Phased Rollout**:
      * **Phase 1**: Implement the `overrides` and `ignore_days` logic.
      * **Phase 2**: Implement the `outliers` flagging mechanism.

-----

## 6\. Testing & Validation Strategy

  * **Unit Tests**: The new `engine/policies.py` module must achieve **100% test coverage**. This includes tests for applying overrides correctly, the carry-forward logic for `ignore_days`, and the MAD outlier detection algorithm.
  * **Integration Tests**: API-level tests will be created to verify that a request with each type of `data_policy` results in the expected numerical output and the correct diagnostic report.
  * **Overall Coverage**: The overall project test coverage must remain at or above **95%**.

-----

## 7\. Acceptance Criteria

The implementation of this RFC is complete when:

1.  This RFC is formally approved by all stakeholders.
2.  The `data_policy` block is added to the shared request envelope and is fully functional, supporting `overrides`, `ignore_days`, and `outliers` as specified.
3.  The response `diagnostics` block is extended to transparently report all policy actions.
4.  The testing and validation strategy is fully implemented, all tests are passing, and the required coverage targets (**100% for engine**, **≥95% for project**) are met.
5.  All default policies are set to be disabled, ensuring full backward compatibility for clients not providing the `data_policy` block.
6.  New documentation is added to `docs/guides/` and `docs/technical/` explaining the robustness framework and how to configure it, ensuring project documentation remains current with the codebase.
