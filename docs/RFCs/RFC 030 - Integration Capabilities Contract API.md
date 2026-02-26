# RFC 030 - Integration Capabilities Contract API

- Status: Accepted
- Date: 2026-02-23

## Summary

Add `GET /integration/capabilities` so lotus-performance publishes backend-governed feature/workflow capability metadata for lotus-gateway and cross-service integration.

## Contract

Inputs:
- `consumerSystem`
- `tenantId`

Outputs:
- `contractVersion`
- `sourceService`
- `consumerSystem`
- `tenantId`
- `policyVersion`
- `supportedInputModes`
- `features[]`
- `workflows[]`

## Rationale

1. Keeps feature control in backend service boundaries.
2. Aligns lotus-performance contract shape with lotus-core and lotus-manage capability contracts.
3. Enables lotus-gateway to aggregate platform capabilities without UI hardcoding.
