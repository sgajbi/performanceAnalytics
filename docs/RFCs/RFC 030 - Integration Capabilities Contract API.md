# RFC 030 - Integration Capabilities Contract API

- Status: Accepted
- Date: 2026-02-23

## Summary

Add `GET /integration/capabilities` so PA publishes backend-governed feature/workflow capability metadata for BFF and cross-service integration.

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
2. Aligns PA contract shape with PAS and DPM capability contracts.
3. Enables BFF to aggregate platform capabilities without UI hardcoding.
