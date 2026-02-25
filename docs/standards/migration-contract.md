# Migration Contract Standard

- Service: `performanceAnalytics`
- Persistence mode: **no persistent schema** in current architecture.
- Migration policy: **versioned migration contract** remains mandatory as a governance control.

## Deterministic Checks

- `make migration-smoke` validates this document and required migration policy language.
- CI executes `make migration-smoke` on all PRs.

## Rollback and Forward-Fix

- No schema rollback path applies in no-schema mode.
- Contract violations are corrected through **forward-fix** and CI re-run.

## Future Upgrade Path

If storage is introduced:

1. Adopt versioned migrations.
2. Add deterministic migration apply checks in CI.
3. Keep forward-only migration policy with explicit rollback runbook.
