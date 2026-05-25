# Agentic Stack Alignment Design

- **Status:** Approved for implementation
- **Date:** 2026-05-25
- **Reference repos:** `../pubtator-link`, `../genereviews-link`
- **Scope:** AutoPVS1-Link second-pass modernization

## Goal

Bring AutoPVS1-Link into closer structural and agentic-development parity with
the sibling Link projects while preserving the current REST and MCP behavior.
This pass focuses on the remaining differences after the earlier modernization:
local Claude workflows, file-size discipline, dependency bound alignment, route
structure, the oversized AutoPVS1 HTML client, and transitional mypy relaxations.

## Current State

AutoPVS1-Link already has the main modern stack: Python 3.12, `uv`,
`hatchling`, Ruff, mypy, FastAPI, FastMCP 3, Docker, GitHub Actions,
`AGENTS.md`, and a minimal `CLAUDE.md`.

The remaining gaps against the sibling repos are:

- no repo-local `.claude/skills/` workflows;
- no `lint-loc` line-budget target, `.loc-allowlist`, or pre-commit hook;
- `autopvs1_link/api/autopvs1_client.py` is 821 lines and mixes HTTP,
  URL-building, HTML fetching, parsing, and response shaping;
- cache REST routes live inline in `server_manager.py`;
- `pyproject.toml` still has broad transitional mypy `ignore_errors` overrides;
- dependency lower bounds lag `../pubtator-link` for FastAPI-adjacent packages;
- docs mention modern agent workflows, but do not yet encode the line-budget
  and local-skill conventions used in the sibling projects.

## Non-Goals

- Do not change public REST paths, MCP tool names, or response schemas.
- Do not shorten the upstream AutoPVS1 rate-limit delay.
- Do not add database, embeddings, benchmark, or hosted destructive-tool
  features.
- Do not present AutoPVS1 output as clinical decision support.
- Do not remove fixture-backed parser coverage.

## Design

### Agentic Development Surface

Add `.claude/skills/` workflows adapted from the sibling repos:

- `ci-failure-triage`
- `fastapi-route-change`
- `mcp-tool-change`
- `autopvs1-scraper-change`
- `release-readiness`

Each skill must defer to `AGENTS.md`, name AutoPVS1-specific guardrails, and
point contributors to the relevant tests. `CLAUDE.md` stays minimal and keeps
`AGENTS.md` as the source of truth.

### File Size Discipline

Adopt the sibling `scripts/check_file_size.py` pattern with AutoPVS1 paths.
Wire it into:

- `make lint-loc`
- `make ci-local`
- `.pre-commit-config.yaml`

Add `.loc-allowlist` with only the current oversized file:

```text
autopvs1_link/api/autopvs1_client.py:821
```

The implementation should split that file in this same modernization pass, then
remove the allowlist entry if the split brings all production modules below the
600-line budget.

### Stack Alignment

Keep the existing stack shape and align bounds to the sibling examples where
they are safe for this project:

- FastAPI remains `<1.0.0`; lower bound should match the newer sibling baseline
  if lock resolution and tests pass.
- `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `mcp[cli]`, `fastmcp`,
  `gunicorn`, `pytest`, `mypy`, and `types-defusedxml` should be refreshed
  through `uv lock --upgrade` and reflected in `pyproject.toml` only where a
  deliberate lower-bound bump is useful.
- Do not add optional ML, database, or corpus dependencies from the sibling
  projects because they do not apply to AutoPVS1-Link.

The authoritative compatibility proof is `make ci-local`, not package metadata
alone.

### Route Structure

Move cache REST endpoints from inline functions in `server_manager.py` to a
dedicated `autopvs1_link/api/routes/cache.py` router. Keep:

- `GET /api/cache/stats`
- `POST /api/cache/clear`

The public behavior stays the same. The new route module should use the same
dependency/service-manager style as existing routes.

### AutoPVS1 Client Split

Split `autopvs1_link/api/autopvs1_client.py` by responsibility while keeping
the public `AutoPVS1Client` import stable:

- `autopvs1_link/api/autopvs1_client.py` remains the facade and HTTP workflow.
- `autopvs1_link/api/autopvs1_urls.py` owns URL/query construction.
- `autopvs1_link/api/autopvs1_parsers.py` owns BeautifulSoup parsing helpers.
- `autopvs1_link/api/autopvs1_validation.py` owns genome-build, variant, CNV,
  and search input validation.

Parser behavior remains fixture-backed. The split must not introduce network
requirements into unit tests.

### Type and Lint Tightening

After the client and cache route splits, remove mypy/ruff transitional ignores
only for modules fixed in this pass. Do not force a repo-wide typing rewrite.
The expected target is narrower overrides, not necessarily zero overrides.

### Verification

Focused checks:

- route tests for cache endpoints;
- parser/client fixture tests around the split;
- MCP tests for tool surface and destructive-cache gating;
- `make lint-loc`;
- `make ci-local`.

Completion requires `make ci-local` passing or a clear report of the exact
remaining failure and why it is outside this pass.

## Risks

- The client split can accidentally change parsing behavior. Mitigation:
  fixture-driven tests before and after the split.
- Dependency upgrades can surface type or runtime incompatibilities. Mitigation:
  upgrade through `uv lock --upgrade`, then fix forward or keep bounds
  conservative.
- File-size enforcement can block future small fixes if the allowlist is not
  maintained. Mitigation: split the 821-line client during this pass and keep
  `.loc-allowlist` empty or minimal.

