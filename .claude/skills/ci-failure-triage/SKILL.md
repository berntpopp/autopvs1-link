---
name: ci-failure-triage
description: Use when `make ci-local` fails or a GitHub Actions run reports a CI failure.
---

# CI Failure Triage

Follow `AGENTS.md` first.

## Workflow

1. Run `make ci-local` locally and identify which sub-target failed.
2. For format failures, run `make format` and re-check.
3. For lint failures, run `make lint-fix` and address remaining manual issues.
4. For line-budget failures, split the growing module or update `.loc-allowlist`
   only with a tracked decomposition reason.
5. For typecheck failures, fix the type issue rather than adding broad
   `ignore_errors` overrides.
6. For test failures, fix code or tests based on the assertion. Parser changes
   require fixture-backed coverage under `tests/fixtures/`.
7. Re-run the focused command, then `make ci-local`.
