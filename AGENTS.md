# AGENTS.md

Shared repository instructions for agentic coding tools working in
AutoPVS1-Link.

## Project

AutoPVS1-Link is a Python FastAPI plus MCP server that wraps the
AutoPVS1 PVS1 variant classification web service (https://autopvs1.bgi.com).
It scrapes HTML pages, caches parsed results, and exposes them as REST
endpoints and MCP tools/resources.

Primary areas:

- `autopvs1_link/` - Python package: FastAPI routes, services, client, MCP
- `tests/` - unit and integration tests with HTML fixtures
- `docker/` - Dockerfile and Compose deployment files
- `docs/superpowers/plans/` - implementation plans for agentic workers
- `docs/superpowers/specs/` - approved designs
- `.claude/skills/` - repo-local Claude Code workflows when present

## Source Of Truth

- Use this file for shared repo-wide agent guidance.
- Keep `CLAUDE.md` lean and Claude-specific; it should reference this file.
- Use repo-local `.claude/skills/` workflows when a task matches their scope.
- Prefer `Makefile` targets over ad hoc commands.
- Use `uv.lock` as the dependency lock source of truth.

## Working Rules

- Do not revert or overwrite changes you did not make unless explicitly asked.
- Keep edits scoped to the task and avoid unrelated refactors.
- Prefer existing code patterns over new abstractions.
- Put tests under `tests/`; do not create alternate test roots.
- Use ASCII unless a file already requires non-ASCII content.
- For MCP work, keep public hosted tools research-use scoped and avoid
  exposing destructive cache operations on the default surface
  (`AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS` must be opt-in).

## AutoPVS1-Link-specific Rules

- The upstream service returns HTML, not a stable API. Parser changes must
  be backed by an HTML fixture under `tests/fixtures/` to catch regressions.
- Respect upstream rate limits (default 1.0s between requests). Do not
  remove or shorten the rate-limit delay without explicit user confirmation.
- HGVS strings and genome builds are user input. Validate before routing
  upstream. Avoid logging full HGVS strings if they contain PHI hints.
- AutoPVS1 returns clinical interpretations. Treat them as research-use
  data; never present as clinical decision support.

## Commands

Required checks before claiming completion:

- `make ci-local`

Useful focused commands:

- `make install`
- `make lock`
- `make format`
- `make lint`
- `make lint-fix`
- `make typecheck`
- `make typecheck-fast`
- `make test`
- `make test-fast`
- `make test-unit`
- `make test-integration`
- `make test-cov`
- `make precommit`
- `make dev`
- `make mcp-serve`
- `make mcp-serve-http`
- `make docker-build`
- `make docker-up`
- `make docker-down`

## Coding Standards

- Use `uv` for dependency management; do not use direct `pip` installs.
- Use modern Python typing: `list[str]`, `dict[str, int]`, `str | None`.
- Format and lint Python with Ruff.
- Type check with mypy targeting Python 3.12.
- Keep FastAPI route behavior covered by route tests, service behavior
  covered by unit tests, and HTML parsing covered by fixture-driven tests.
- Pre-commit ruff `rev` may drift from `uv.lock` ruff version. Accept the
  drift; CI uses `uv` and is authoritative.

## File Size Discipline

Hard cap: **600 lines per Python module** in `autopvs1_link/`, `server.py`,
and `mcp_server.py`. Enforced by `make lint-loc` (wired into `ci-local` and
pre-commit). Tests are exempt.

Why: large modules concentrate complexity, slow mypy and import cost, and
degrade LLM-assisted refactors because a single edit risks unrelated breakage.
When a file approaches 500 lines, plan its split.

How:

- New files MUST stay under 600 lines.
- Existing oversized files are grandfathered in `.loc-allowlist` with their
  current line count as the ceiling. They may shrink but not grow. Removing an
  entry after a successful split is the goal.
- Prefer cohesive splits: one module per responsibility, not random
  partitioning to slip under the cap.
- Keep the public facade stable across splits so call sites do not churn.
- If you must add to an allowlisted file as part of an unrelated fix, raise the
  ceiling explicitly in `.loc-allowlist` in the same commit and link the
  decomposition plan in the message.

## Testing Notes

- `make test` is the fast default.
- `make test-cov` runs coverage. Coverage gate is `fail_under=80`.
- `make ci-local` runs formatting, linting, type checking, and tests.
- Treat failing checks as real issues unless you have clear evidence
  otherwise.
- New parser logic requires an HTML fixture committed under `tests/fixtures/`.

## Environment

- Default env-var prefix is `AUTOPVS1_LINK_`. The legacy `AUTOPVS1_` prefix
  is read with a `DeprecationWarning` for one release.
- `AUTOPVS1_LINK_TRANSPORT` accepts `stdio`, `http`, `unified`.
- `AUTOPVS1_LINK_METRICS_ENABLED` toggles the `/metrics` endpoint.
- `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS` gates `clear_cache` as an MCP tool.
