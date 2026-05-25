# Agentic Stack Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align AutoPVS1-Link with the sibling Link repos' modern Python stack and agentic-development conventions without changing public REST or MCP behavior.

**Architecture:** Add agent workflow files and line-budget tooling first, then make the smallest structural code splits needed to satisfy the new guardrails. Keep `AutoPVS1Client`, REST routes, and MCP tool names stable while moving implementation details into focused modules.

**Tech Stack:** Python 3.12, `uv`, `hatchling`, Ruff, mypy, pytest, FastAPI, FastMCP 3, MCP Python SDK, Pydantic v2, BeautifulSoup/lxml, Docker, Makefile-driven verification.

---

## File Structure

- Create `.claude/skills/*/SKILL.md` for recurring Claude Code workflows.
- Create `scripts/check_file_size.py` by adapting the sibling script to `autopvs1_link`.
- Create `.loc-allowlist` only if the oversized client has not yet been split.
- Modify `Makefile` to add `lint-loc` and include it in `ci-local`.
- Modify `.pre-commit-config.yaml` to add the local file-size hook.
- Modify `AGENTS.md` and `CLAUDE.md` to document file-size discipline and local skills.
- Modify `pyproject.toml` and `uv.lock` through `uv lock --upgrade`.
- Create `autopvs1_link/api/routes/cache.py` and update `autopvs1_link/server_manager.py`.
- Create `autopvs1_link/api/autopvs1_urls.py`.
- Create `autopvs1_link/api/autopvs1_validation.py`.
- Create `autopvs1_link/api/autopvs1_parsers.py`.
- Modify `autopvs1_link/api/autopvs1_client.py` to become a facade/workflow module.
- Update or add tests under `tests/unit/` and `tests/integration/`; do not create another test root.

## Task 1: Add Local Claude Workflows

**Files:**
- Create: `.claude/skills/ci-failure-triage/SKILL.md`
- Create: `.claude/skills/fastapi-route-change/SKILL.md`
- Create: `.claude/skills/mcp-tool-change/SKILL.md`
- Create: `.claude/skills/autopvs1-scraper-change/SKILL.md`
- Create: `.claude/skills/release-readiness/SKILL.md`

- [ ] **Step 1: Create `ci-failure-triage`**

```markdown
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
```

- [ ] **Step 2: Create `fastapi-route-change`**

```markdown
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
```

- [ ] **Step 3: Create `mcp-tool-change`**

```markdown
---
name: mcp-tool-change
description: Use when adding, renaming, or changing AutoPVS1-Link MCP tools, resources, prompts, or schemas.
---

# MCP Tool Change

Follow `AGENTS.md` first.

## Workflow

1. Inspect `autopvs1_link/mcp/` and reuse the existing facade, contracts, and
   service adapter patterns.
2. Keep hosted public tools research-use scoped; do not expose clinical
   decision support, destructive cache operations, or broad filesystem/network
   powers.
3. Keep `clear_cache` gated by `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`.
4. Prefer typed Pydantic inputs and stable structured error codes.
5. Update MCP tests under `tests/unit/mcp/` and docs if tool names, arguments,
   resources, or safety language change.
6. Run focused MCP tests, then `make ci-local`.
```

- [ ] **Step 4: Create `autopvs1-scraper-change`**

```markdown
---
name: autopvs1-scraper-change
description: Use when modifying AutoPVS1 HTML fetching, parsing, URL construction, or fixture-backed scraper behavior.
---

# AutoPVS1 Scraper Change

Follow `AGENTS.md` first.

## Workflow

1. Inspect `autopvs1_link/api/autopvs1_client.py` and any split parser, URL, or
   validation modules.
2. Keep the default upstream rate-limit delay at 1.0 seconds unless the user
   explicitly approves a change.
3. Treat the upstream as HTML, not a stable API. Parser changes require an HTML
   fixture under `tests/fixtures/`.
4. Prefer BeautifulSoup selectors and structured parsing helpers over ad hoc
   string slicing.
5. Validate genome builds and variant/CNV identifiers before constructing
   upstream URLs.
6. Run parser/client fixture tests, then `make ci-local`.
```

- [ ] **Step 5: Create `release-readiness`**

```markdown
---
name: release-readiness
description: Use before tagging, publishing, or promoting AutoPVS1-Link builds.
---

# Release Readiness

Follow `AGENTS.md` first.

## Workflow

1. Confirm the worktree only contains intended release changes.
2. Run `make ci-local`, `make docker-prod-config`, and `make docker-npm-config`.
3. Build the Docker image with `make docker-build`.
4. Check README, changelog, MCP safety language, and deployment docs for drift.
5. Confirm destructive MCP tools remain opt-in.
6. Record residual risks before handoff.
```

- [ ] **Step 6: Verify files are discoverable**

Run:

```bash
find .claude/skills -maxdepth 2 -name SKILL.md | sort
```

Expected: the five new `SKILL.md` files are listed.

## Task 2: Add File Size Discipline

**Files:**
- Create: `scripts/check_file_size.py`
- Create or modify: `.loc-allowlist`
- Modify: `Makefile`
- Modify: `.pre-commit-config.yaml`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create `scripts/check_file_size.py`**

Copy the sibling implementation and change default targets to:

```python
DEFAULT_TARGETS = (
    Path("autopvs1_link"),
    Path("server.py"),
    Path("mcp_server.py"),
)
```

- [ ] **Step 2: Seed `.loc-allowlist`**

If `autopvs1_link/api/autopvs1_client.py` still exceeds 600 lines, create:

```text
autopvs1_link/api/autopvs1_client.py:821
```

If it has already been split below 600 lines, leave `.loc-allowlist` absent or
empty.

- [ ] **Step 3: Add `lint-loc` to `Makefile`**

Update `.PHONY` to include `lint-loc`, add:

```make
lint-loc: ## Enforce per-file line budget (see AGENTS.md "File Size Discipline")
	uv run python scripts/check_file_size.py
```

Change:

```make
ci-local: format-check lint-ci typecheck-fast test-fast
```

to:

```make
ci-local: format-check lint-ci lint-loc typecheck-fast test-fast
```

- [ ] **Step 4: Add pre-commit hook**

Append to the local hook section:

```yaml
      - id: file-size-budget
        name: per-file line budget (see AGENTS.md "File Size Discipline")
        entry: uv run python scripts/check_file_size.py
        language: system
        pass_filenames: false
        files: ^(autopvs1_link/|server\.py$|mcp_server\.py$|\.loc-allowlist$)
```

- [ ] **Step 5: Update `AGENTS.md`**

Add a `File Size Discipline` section matching the sibling wording with
AutoPVS1 paths and the 600-line hard cap.

- [ ] **Step 6: Update `CLAUDE.md`**

Add concise Claude-specific bullets:

```markdown
- Prefer `make ci-local` before final handoff. It runs `lint-loc`, which
  enforces the 600-LOC per-file budget (see AGENTS.md "File Size Discipline").
- When planning an edit that would push an `autopvs1_link/` module past
  ~500 lines, propose a split first rather than growing the file.
- When a split is required, prefer cohesive sub-modules and keep public
  facades stable so call sites do not churn.
```

- [ ] **Step 7: Run line-budget check**

Run:

```bash
make lint-loc
```

Expected: pass if `.loc-allowlist` is seeded, or fail only on the known client
before the allowlist is added.

## Task 3: Align Dependency Bounds and Lockfile

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Align safe lower bounds**

Update AutoPVS1-Link to match the newer sibling baseline where applicable:

```toml
"uvicorn[standard]>=0.47.0,<1.0.0",
"pydantic>=2.13.4,<3.0.0",
"pydantic-settings>=2.14.1,<3.0.0",
"mcp[cli]>=1.27.1,<2.0.0",
"mypy>=2.1.0,<3.0.0",
"types-defusedxml>=0.7.0.20260504",
```

Keep project-specific dependencies and do not add database, ML, corpus, or
benchmark packages from the sibling repos.

- [ ] **Step 2: Upgrade lockfile**

Run:

```bash
uv lock --upgrade
```

Expected: `uv.lock` updates successfully.

- [ ] **Step 3: Sync environment**

Run:

```bash
uv sync --group dev --frozen
```

Expected: dependencies install from the lockfile without resolution changes.

- [ ] **Step 4: Run focused smoke checks**

Run:

```bash
make typecheck-fast
make test-fast
```

Expected: both pass or expose concrete incompatibilities to fix in later tasks.

## Task 4: Move Cache Routes Into a Router Module

**Files:**
- Create: `autopvs1_link/api/routes/cache.py`
- Modify: `autopvs1_link/server_manager.py`
- Test: `tests/integration/test_api_endpoints.py` or a new focused route test under `tests/integration/`

- [ ] **Step 1: Write or confirm cache route tests**

Add tests that call:

```python
response = client.get("/api/cache/stats")
assert response.status_code == 200

response = client.post("/api/cache/clear")
assert response.status_code == 200
```

Use existing app/client fixtures and monkeypatch service manager behavior if the
current tests already isolate service calls.

- [ ] **Step 2: Create `cache.py` router**

Implement:

```python
"""Cache management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from autopvs1_link.services.service_manager import get_service_manager

router = APIRouter(prefix="/api/cache", tags=["Cache"])


@router.get("/stats")
async def cache_stats() -> dict[str, Any]:
    manager = await get_service_manager()
    stats: dict[str, Any] = await manager.get_cache_statistics()
    return stats


@router.post("/clear")
async def cache_clear() -> dict[str, Any]:
    manager = await get_service_manager()
    result: dict[str, Any] = await manager.clear_all_caches()
    return result
```

- [ ] **Step 3: Update `server_manager.py`**

Import `cache` with the existing route modules and replace inline cache route
functions with:

```python
app.include_router(cache.router)
```

- [ ] **Step 4: Run focused route tests**

Run:

```bash
uv run pytest tests/integration/test_api_endpoints.py -q
```

Expected: cache endpoint coverage passes.

## Task 5: Split AutoPVS1 Client Responsibilities

**Files:**
- Create: `autopvs1_link/api/autopvs1_urls.py`
- Create: `autopvs1_link/api/autopvs1_validation.py`
- Create: `autopvs1_link/api/autopvs1_parsers.py`
- Modify: `autopvs1_link/api/autopvs1_client.py`
- Test: existing parser/client tests under `tests/unit/`

- [ ] **Step 1: Baseline current behavior**

Run:

```bash
uv run pytest tests/unit/test_real_website_parsing.py tests/unit/test_scraper_parsers.py tests/unit/test_hgvs_redirect_functionality.py -q
```

Expected: pass before splitting.

- [ ] **Step 2: Extract URL helpers**

Move URL-building helpers into `autopvs1_urls.py`. Keep function names explicit,
for example:

```python
def variant_url(base_url: str, genome_build: str, variant_id: str) -> str:
    ...

def cnv_url(base_url: str, genome_build: str, cnv_id: str) -> str:
    ...

def search_url(base_url: str, query: str, genome_version: str) -> str:
    ...
```

Use the exact URL logic currently present in `AutoPVS1Client`.

- [ ] **Step 3: Extract validation helpers**

Move validation into `autopvs1_validation.py`. Keep existing accepted values and
error behavior stable:

```python
def validate_genome_build(genome_build: str) -> str:
    ...

def validate_variant_id(variant_id: str) -> str:
    ...

def validate_cnv_id(cnv_id: str) -> str:
    ...

def validate_search_query(query: str) -> str:
    ...
```

- [ ] **Step 4: Extract parser helpers**

Move BeautifulSoup parsing functions into `autopvs1_parsers.py`. Preserve
fixture-backed parser outputs exactly. The facade client should call parser
functions rather than holding parsing internals.

- [ ] **Step 5: Keep `AutoPVS1Client` as stable facade**

`autopvs1_client.py` should continue exporting `AutoPVS1Client` and public
methods used by services/tests. It should own HTTP lifecycle, retry calls, and
coordination only.

- [ ] **Step 6: Remove obsolete allowlist entry**

After the split:

```bash
wc -l autopvs1_link/api/autopvs1_client.py autopvs1_link/api/autopvs1_urls.py autopvs1_link/api/autopvs1_validation.py autopvs1_link/api/autopvs1_parsers.py
```

If every production file is under 600 lines, remove
`autopvs1_link/api/autopvs1_client.py:821` from `.loc-allowlist`.

- [ ] **Step 7: Re-run parser/client tests**

Run:

```bash
uv run pytest tests/unit/test_real_website_parsing.py tests/unit/test_scraper_parsers.py tests/unit/test_hgvs_redirect_functionality.py -q
```

Expected: same tests pass after the split.

## Task 6: Tighten Transitional Type and Lint Overrides

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Inspect current type failures**

Run:

```bash
uv run mypy autopvs1_link/api/autopvs1_client.py autopvs1_link/api/autopvs1_urls.py autopvs1_link/api/autopvs1_validation.py autopvs1_link/api/autopvs1_parsers.py autopvs1_link/api/routes/cache.py
```

Expected: pass or report specific errors in the modules changed by this plan.

- [ ] **Step 2: Remove fixed modules from broad mypy override**

Remove modules from the transitional `ignore_errors = true` block only after
focused mypy passes for that module. At minimum, target:

```toml
"autopvs1_link.api.autopvs1_client",
```

and do not add new broad ignore blocks.

- [ ] **Step 3: Remove stale Ruff per-file ignores**

If the split removes the `SIM105`, `RUF013`, or route `B904` issues from changed
modules, delete the corresponding per-file ignores. Keep ignores that are still
needed for untouched legacy code.

- [ ] **Step 4: Run type and lint checks**

Run:

```bash
make lint
make typecheck-fast
```

Expected: both pass.

## Task 7: Final Verification and Documentation Check

**Files:**
- Modify docs only if verification exposes drift.

- [ ] **Step 1: Run full local CI**

Run:

```bash
make ci-local
```

Expected: formatting, lint, line budget, typecheck, and tests pass.

- [ ] **Step 2: Render Docker configs**

Run:

```bash
make docker-prod-config
make docker-npm-config
```

Expected: Compose config renders without errors.

- [ ] **Step 3: Check changed files**

Run:

```bash
git status --short
git diff --stat
```

Expected: only modernization files, focused code splits, lockfile updates, and
test/docs changes are present.

- [ ] **Step 4: Record verification in handoff**

Report exact commands run and whether they passed. If any command fails, report
the exact failing command and first meaningful error.

## Self-Review

- Spec coverage: local skills, file-size discipline, stack alignment, cache
  route split, client split, type/lint tightening, and verification all map to
  tasks.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency: new helper modules use `autopvs1_*` names consistently and
  preserve `AutoPVS1Client` as the facade.

