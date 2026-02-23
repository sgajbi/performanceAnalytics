# Contributing

This repository follows the platform engineering baseline used across services.

## Branch and PR Rules

- Do not push directly to `main`.
- Create a feature branch for each change.
- Open a PR to `main`.
- Merge only after required CI checks pass.

## Local Quality Gates

Use these commands before opening or updating a PR:

```bash
make check
make ci-local
```

For Linux/Python 3.11 parity in Docker:

```bash
make ci-local-docker
make ci-local-docker-down
```

## Docs-Code Sync Policy (Required)

Documentation and code must be updated together in the same PR when behavior changes.

- API behavior/shape changed: update docs and examples.
- Tooling/command changes: update README and runbooks.
- Architecture/ownership changes: update RFC/ADR docs.

PRs with stale/missing docs are blocked from merge.
