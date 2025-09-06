# Performance API v0.4 Upgrade Guide

**Target Release:** v0.4.x

This document outlines the major enhancements introduced to the performance analytics APIs (`/performance/twr`, `/performance/mwr`, `/contribution`, `/performance/attribution`) as part of the v0.4 release.

The primary goal of this release is to strengthen correctness, configurability, and consistency across all endpoints without breaking existing clients.

## 1. Unified API Envelope

All four performance endpoints now share a common request and response structure, providing a consistent experience.

### Shared Request Fields

All new fields are **optional**. If you do not provide them, the API will behave exactly as it did before. These fields allow for powerful new control over the calculations.

*(Details to be added as features are integrated)*

### Shared Response Footer

All responses from these endpoints will now include a shared footer containing `meta`, `diagnostics`, and `audit` blocks. This provides rich context about the calculation performed.

*(Details to be added as features are integrated)*

## 2. Backward Compatibility

**No breaking changes have been introduced.**

- All new request fields are optional and have defaults that preserve the previous behavior.
- Existing request payloads will continue to work as expected.
- Responses are purely additive; the new footer is added, but existing fields remain.