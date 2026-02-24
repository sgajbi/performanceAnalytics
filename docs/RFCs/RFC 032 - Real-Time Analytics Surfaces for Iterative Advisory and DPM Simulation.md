# RFC 032 - Real-Time Analytics Surfaces for Iterative Advisory and DPM Simulation

- Status: PROPOSED
- Date: 2026-02-24
- Owners: Performance Analytics Service

## Problem Statement

Advisory and DPM iterative workflows need responsive analytics feedback (performance/risk/composition impacts) as proposal deltas are adjusted. Current integration surfaces are not explicitly optimized for iterative UX loops.

## Root Cause

- Analytics APIs are rich but not packaged for low-latency, UI-focused impact panels.
- Multi-metric refresh for each user adjustment can require multiple calls and heavy payloads.
- No explicit contract for "simulation impact cards" consumed by lifecycle workspaces.

## Proposed Solution

1. Add compact analytics panel endpoints for iterative workflows:
   - performance deltas
   - risk/exposure deltas
   - concentration and drift highlights
2. Define request mode for staged/what-if inputs (via PAS/BFF references).
3. Publish latency and payload budgets aligned to interactive frontend requirements.

## Architectural Impact

- PA becomes first-class analytics feedback engine for iterative domain workflows.
- Cleaner separation between deep analytics APIs and UX-optimized panel contracts.
- Better alignment with BFF lifecycle orchestration.

## Risks and Trade-offs

- Additional endpoint surface and versioning overhead.
- Potential duplication with existing deep analytics APIs if boundaries are unclear.
- Requires coordinated schema governance with PAS and BFF.

## High-Level Implementation Approach

1. Define minimal panel schema and benchmark latency targets.
2. Implement aggregation layer reusing existing analytics engines.
3. Add contract tests for deterministic outputs and bounded payloads.
4. Integrate with BFF lifecycle session endpoints.

## Dependencies

- Upstream/peer: PAS RFC-046, AEA RFC-0010, DPM RFC-0029.
- Downstream: AW RFC-0007.
