---
name: fastapi-route-change
description: Use when adding, renaming, or modifying AutoPVS1-Link FastAPI routes, dependencies, middleware, or response behavior.
---

# FastAPI Route Change

Follow `AGENTS.md` first.

## Workflow

1. Inspect neighboring modules under `autopvs1_link/api/routes/`.
2. Keep route handlers thin; put business behavior in `autopvs1_link/services/`
   or existing managers.
3. Use Pydantic models from `autopvs1_link/models/` for public response shapes.
4. Validate genome builds, HGVS strings, and variant/CNV identifiers before
   routing upstream.
5. Avoid logging full HGVS strings when user input might contain PHI hints.
6. Add or update route tests under `tests/integration/` or focused unit tests.
7. Run focused route tests, then `make ci-local`.
