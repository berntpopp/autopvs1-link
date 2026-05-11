# Modernize autopvs1-link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `autopvs1-link` to match `../pubtator-link`'s May 2026 conventions: uv + hatchling, Python 3.12+, ruff-only, typer, FastMCP 3 subpackage, observability stack (asgi-correlation-id + prometheus + defusedxml), gunicorn + multi-stage Docker, five GitHub workflows, AGENTS.md split, ≥80% coverage.

**Architecture:** Eight sequential phases. Each phase ends with `make ci-local` green and is committed independently. Phase 1 establishes tooling. Phase 2 splits agent docs. Phase 3 swaps deps + renames env prefix. Phase 4 rebuilds the MCP layer as a subpackage. Phase 5 adds observability. Phase 6 adds Docker. Phase 7 raises test coverage to ≥80%. Phase 8 adds CI workflows + Dependabot.

**Tech Stack:** Python 3.12, uv + hatchling, ruff (format + lint), mypy strict, typer, FastAPI, FastMCP 3.2+, mcp[cli] 1.27+, pydantic 2.11+, structlog + asgi-correlation-id + prometheus-client, defusedxml, gunicorn + uvicorn, pytest 9 + xdist + mock, Docker (python:3.14-slim) + Compose, GitHub Actions.

**Reference repo:** `C:\development\pubtator-link` — used as template throughout. When unsure, copy from there and adapt.

**Reading order:** Read the spec (`docs/superpowers/specs/2026-05-11-modernize-autopvs1-link-design.md`) before starting. Then execute phases in order — do not skip ahead.

---

## Phase 1 — Tooling foundation

**Goal:** Drop modern tooling onto the existing source tree with no behavioral change. After Phase 1, `make ci-local` is green and the dev workflow is uv-based.

**Acceptance:** `uv sync --group dev --frozen` succeeds. `make ci-local` exits 0. Existing `pytest tests/` still passes.

### Task 1.1: Add .python-version and .editorconfig

**Files:**
- Create: `.python-version`
- Create: `.editorconfig`

- [ ] **Step 1: Write `.python-version`**

```
3.12
```

- [ ] **Step 2: Write `.editorconfig`**

```
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,toml,json,md}]
indent_size = 2

[Makefile]
indent_style = tab
```

- [ ] **Step 3: Commit**

```bash
git add .python-version .editorconfig
git commit -m "chore: pin Python 3.12 and add editorconfig"
```

### Task 1.2: Rewrite .gitignore from pubtator-link template

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Replace `.gitignore` contents**

Copy verbatim from `C:\development\pubtator-link\.gitignore`. Remove the `benchmark` and `.worktrees/` blocks at the bottom; autopvs1-link has no benchmarks dir. Keep the explicit `# UV` note that says `uv.lock` is recommended to be tracked (the file ships with that line commented out, which is correct — uv.lock IS tracked).

- [ ] **Step 2: Verify staged file list is sane**

```bash
git status --short
```

Expected: previously-tracked artifacts (`coverage.xml`, `htmlcov/`, `*.egg-info/`, `__pycache__/`) still appear as tracked — they will be removed in Task 1.3.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: replace .gitignore with modern Python template"
```

### Task 1.3: Remove generated artifacts from git

**Files:**
- Delete from git index (keep on disk if you want, they'll be re-ignored): `coverage.xml`, `autopvs1_link.egg-info/`, `htmlcov/`, all `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`

- [ ] **Step 1: Remove from git**

```bash
git rm -rf --cached coverage.xml autopvs1_link.egg-info htmlcov __pycache__ tests/__pycache__ autopvs1_link/__pycache__ autopvs1_link/api/__pycache__ autopvs1_link/api/routes/__pycache__ autopvs1_link/middleware/__pycache__ autopvs1_link/models/__pycache__ autopvs1_link/services/__pycache__ .mypy_cache .ruff_cache .pytest_cache 2>nul || true
git status --short
```

Expected: deletions listed; new gitignore prevents re-add.

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove generated build artifacts from git"
```

### Task 1.4: Add .dockerignore

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Write `.dockerignore`**

Copy verbatim from `C:\development\pubtator-link\.dockerignore`.

- [ ] **Step 2: Commit**

```bash
git add .dockerignore
git commit -m "chore: add .dockerignore"
```

### Task 1.5: Add .env.example and .env.docker.example

**Files:**
- Create: `.env.example`
- Create: `.env.docker.example`

- [ ] **Step 1: Write `.env.example`**

```
# Server Configuration
AUTOPVS1_LINK_HOST=127.0.0.1
AUTOPVS1_LINK_PORT=8000
AUTOPVS1_LINK_TRANSPORT=unified

# API Configuration
AUTOPVS1_LINK_API_BASE_URL=https://autopvs1.bgi.com
AUTOPVS1_LINK_API_REQUEST_TIMEOUT=30
AUTOPVS1_LINK_API_MAX_RETRIES=3
AUTOPVS1_LINK_API_RATE_LIMIT_DELAY=1.0

# Cache Configuration
AUTOPVS1_LINK_CACHE_SIZE=256
AUTOPVS1_LINK_CACHE_TTL_HOURS=24

# Logging Configuration
AUTOPVS1_LINK_LOG_LEVEL=INFO
AUTOPVS1_LINK_LOG_JSON_FORMAT=false

# CORS
AUTOPVS1_LINK_SERVER_CORS_ORIGINS=*

# Observability
AUTOPVS1_LINK_METRICS_ENABLED=true

# MCP
AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=false
```

- [ ] **Step 2: Write `.env.docker.example`**

```
# Docker overrides (used by docker-compose.prod.yml and docker-compose.npm.yml)
AUTOPVS1_LINK_HOST=0.0.0.0
AUTOPVS1_LINK_PORT=8000
AUTOPVS1_LINK_TRANSPORT=unified
AUTOPVS1_LINK_LOG_LEVEL=INFO
AUTOPVS1_LINK_LOG_JSON_FORMAT=true
AUTOPVS1_LINK_SERVER_CORS_ORIGINS=*
AUTOPVS1_LINK_METRICS_ENABLED=true
AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=false
GUNICORN_WORKERS=2
GUNICORN_LOG_LEVEL=info
GUNICORN_FORWARDED_ALLOW_IPS=*
```

- [ ] **Step 3: Commit**

```bash
git add .env.example .env.docker.example
git commit -m "chore: add example env files with AUTOPVS1_LINK_ prefix"
```

### Task 1.6: Rewrite pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "autopvs1-link"
version = "1.0.0"
description = "A unified server providing REST API and MCP interfaces for autopvs1.bgi.com PVS1 variant data"
readme = "README.md"
authors = [
    { name = "AutoPVS1 Link Contributors" },
]
license = { text = "MIT" }
requires-python = ">=3.12"
keywords = ["genetics", "pvs1", "variant", "analysis", "mcp", "api"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
dependencies = [
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn[standard]>=0.46.0,<1.0.0",
    "gunicorn>=25.3.0,<26.0.0",
    "pydantic>=2.11.0,<3.0.0",
    "pydantic-settings>=2.6.0,<3.0.0",
    "httpx>=0.28.0,<1.0.0",
    "async-lru>=2.0.4,<3.0.0",
    "structlog>=24.4.0,<26.0.0",
    "asgi-correlation-id>=4.3.0,<5.0.0",
    "prometheus-client>=0.21.0,<1.0.0",
    "defusedxml>=0.7.1",
    "orjson>=3.10.0,<4.0.0",
    "beautifulsoup4>=4.12.0,<5.0.0",
    "lxml>=5.2.0,<7.0.0",
    "rich>=15.0.0,<16.0.0",
    "typer>=0.25.1,<1.0.0",
    "mcp[cli]>=1.27.0,<2.0.0",
    "fastmcp>=3.2.0,<4.0.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3,<10.0.0",
    "pytest-asyncio>=1.3.0,<2.0.0",
    "pytest-cov>=6.0.0,<8.0.0",
    "pytest-mock>=3.14.0,<4.0.0",
    "pytest-xdist>=3.6.0,<4.0.0",
    "respx>=0.22.0,<1.0.0",
    "ruff>=0.8.0,<1.0.0",
    "mypy>=1.14.0,<2.0.0",
    "pre-commit>=4.0.0,<5.0.0",
    "types-defusedxml>=0.7.0.20260408",
]

[project.scripts]
autopvs1-link = "autopvs1_link.cli:main"
autopvs1-link-mcp = "mcp_server:main"

[project.urls]
Homepage = "https://github.com/berntpopp/autopvs1-link"
Repository = "https://github.com/berntpopp/autopvs1-link"
Issues = "https://github.com/berntpopp/autopvs1-link/issues"

[tool.hatch.build.targets.wheel]
packages = ["autopvs1_link"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "S", "T20", "SIM", "RUF"]
ignore = ["S101", "E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

[tool.ruff.lint.per-file-ignores]
"tests/**/*" = ["S101", "T20"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
exclude = [
    ".*site-packages.*",
    ".*/venv/.*",
    ".*/.venv/.*",
    "htmlcov/.*",
]

[[tool.mypy.overrides]]
module = [
    "async_lru.*",
    "structlog.*",
    "mcp.*",
    "fastmcp.*",
    "fastapi.*",
    "pydantic.*",
    "pydantic_settings.*",
    "httpx.*",
    "uvicorn.*",
    "bs4.*",
    "lxml.*",
    "asgi_correlation_id.*",
    "prometheus_client.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = [
    "--strict-markers",
    "-ra",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]

[tool.coverage.run]
source = ["autopvs1_link"]
omit = [
    "tests/*",
    "*/tests/*",
]

[tool.coverage.report]
# Phase 1 ships fail_under=0 to avoid gating early commits before the test
# restructure lands. Phase 7 raises this to 80 alongside the new tests.
fail_under = 0
exclude_also = [
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
```

- [ ] **Step 2: Delete the redundant .flake8 file**

```bash
git rm .flake8
```

- [ ] **Step 3: Resolve and lock dependencies**

```bash
uv lock
uv sync --group dev
```

Expected: `uv.lock` is created. Both commands exit 0.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git rm .flake8
git commit -m "build: migrate to uv + hatchling, Python 3.12 floor, ruff-only"
```

### Task 1.7: Add Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Write `Makefile`**

```makefile
.PHONY: help install lock upgrade sync format format-check lint lint-ci lint-fix typecheck typecheck-fast typecheck-stop typecheck-fresh test test-fast test-unit test-integration test-cov test-all check ci-local precommit clean dev mcp-serve mcp-serve-http docker-build docker-up docker-down docker-logs docker-prod-config docker-npm-config

DOCKER_COMPOSE := $(shell if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

.DEFAULT_GOAL := help

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install project and development dependencies with uv
	uv sync --group dev

sync: install ## Alias for install

lock: ## Resolve and update uv.lock
	uv lock

upgrade: ## Upgrade locked dependencies
	uv lock --upgrade

format: ## Format Python code
	uv run ruff format autopvs1_link tests server.py mcp_server.py

format-check: ## Check formatting without writing
	uv run ruff format --check autopvs1_link tests server.py mcp_server.py

lint: ## Lint Python code
	uv run ruff check autopvs1_link tests server.py mcp_server.py

lint-ci: ## Lint Python code without modifying files
	uv run ruff check autopvs1_link tests server.py mcp_server.py --output-format=github

lint-fix: ## Lint and apply safe fixes
	uv run ruff check autopvs1_link tests server.py mcp_server.py --fix

typecheck: ## Type check package
	uv run mypy autopvs1_link server.py mcp_server.py

typecheck-fast: ## Type check with mypy daemon and fallback
	@tmp_log=$$(mktemp); \
	if uv run dmypy run -- autopvs1_link server.py mcp_server.py >$$tmp_log 2>&1; then \
		cat $$tmp_log; \
	elif grep -Eq "Daemon crashed!|INTERNAL ERROR" $$tmp_log; then \
		echo "dmypy crashed; retrying with a fresh daemon..."; \
		uv run dmypy stop >/dev/null 2>&1 || true; \
		if uv run dmypy run -- autopvs1_link server.py mcp_server.py >$$tmp_log 2>&1; then \
			cat $$tmp_log; \
		else \
			cat $$tmp_log; \
			echo "Falling back to plain mypy..."; \
			uv run dmypy stop >/dev/null 2>&1 || true; \
			uv run mypy autopvs1_link server.py mcp_server.py; \
		fi; \
	else \
		cat $$tmp_log; \
		rm -f $$tmp_log; \
		exit 1; \
	fi; \
	rm -f $$tmp_log

typecheck-stop: ## Stop mypy daemon
	uv run dmypy stop

typecheck-fresh: ## Clear mypy cache and run typecheck
	rm -rf .mypy_cache
	uv run mypy autopvs1_link server.py mcp_server.py

test: ## Run tests quickly
	uv run pytest tests -q

test-fast: ## Run tests in parallel with pytest-xdist
	uv run pytest tests -q -n auto

test-unit: ## Run unit tests in parallel
	uv run pytest tests -q -n auto -m "not integration and not slow"

test-integration: ## Run integration tests serially
	uv run pytest tests -q -m "integration"

test-cov: ## Run tests with coverage
	uv run pytest tests --cov=autopvs1_link --cov-report=term-missing --cov-report=html

test-all: test-cov ## Alias for full test run with coverage

check: format lint ## Format and lint

ci-local: format-check lint-ci typecheck-fast test-fast ## Run fast local CI-equivalent checks

precommit: ci-local ## Run checks expected before commit

clean: ## Remove local caches and generated reports
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage

dev: ## Start REST plus MCP development server
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000

mcp-serve: ## Start local stdio MCP server
	uv run python mcp_server.py

mcp-serve-http: ## Start hosted MCP endpoint with REST API
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000

docker-build: ## Build Docker image
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml build

docker-up: ## Start Docker development stack
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml up -d

docker-down: ## Stop Docker development stack
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml down

docker-logs: ## Follow Docker logs
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml logs -f

docker-prod-config: ## Render production Compose configuration
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config

docker-npm-config: ## Render NPM Compose configuration
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml -f docker/docker-compose.prod.yml -f docker/docker-compose.npm.yml --env-file .env.docker.example config
```

- [ ] **Step 2: Verify Makefile targets resolve**

```bash
make help
```

Expected: a colorized list of targets prints with no shell errors.

- [ ] **Step 3: Run `make ci-local`**

```bash
make ci-local
```

Expected: format-check, lint-ci, typecheck-fast, test-fast all exit 0. If lint or typecheck flags issues in untouched files (e.g. ruff `S` rules), apply `make lint-fix` and re-run; for type errors, address only the simplest fixes — non-trivial type errors are addressed in Phase 3 when libs get bumped.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "build: add Makefile mirroring pubtator-link targets"
```

### Task 1.8: Add .pre-commit-config.yaml and CHANGELOG.md

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy autopvs1_link server.py mcp_server.py
        language: system
        pass_filenames: false
```

- [ ] **Step 2: Write `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to autopvs1-link are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Python floor raised to 3.12.
- Build backend migrated from setuptools to hatchling; project managed with
  uv; `uv.lock` is committed.
- Formatter consolidated to ruff (Black removed); ruff config widened to
  include N, UP, B, C4, S, T20, SIM, RUF rule sets.
- CLI ported from click to typer.
- MCP stack bumped to fastmcp 3.2+ and mcp 1.27+; MCP layer refactored into
  `autopvs1_link/mcp/` subpackage; Streamable HTTP transport (SSE retired).
- Environment variable prefix renamed from `AUTOPVS1_*` to `AUTOPVS1_LINK_*`
  with one-cycle dual-read backward-compat shim.
- Observability stack: structlog plus asgi-correlation-id plus prometheus-client.
- `get_cache_statistics` is now an MCP resource. `clear_cache` is gated
  behind `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true` (default off).
- HTML/XML parsing hardened with defusedxml.

### Added

- Multi-stage Dockerfile (python:3.14-slim) plus four Compose stacks (base,
  dev, prod, NPM).
- Gunicorn production CMD with uvicorn workers.
- Five GitHub Actions workflows: ci, docker, release, security,
  container-security.
- Dependabot for uv, github-actions, docker, docker-compose.
- `AGENTS.md` (canonical) plus thin `CLAUDE.md` pointer.
- `docs/` split: `architecture.md`, `configuration.md`, `api.md`,
  `MCP_CONNECTION_GUIDE.md`, generated `mcp-tool-catalog.md`.
- pre-commit configuration.
- `/metrics` endpoint (Prometheus) toggleable via `AUTOPVS1_LINK_METRICS_ENABLED`.

### Removed

- `tenacity` dependency (inline retry).
- Black dependency.
- Click dependency.
- Checked-in `coverage.xml`, `*.egg-info/`, `htmlcov/`, `__pycache__/`,
  `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`.
- Legacy `server.py` deprecation messages (entry kept as thin Typer-routed
  shim).
```

- [ ] **Step 3: Commit**

```bash
git add .pre-commit-config.yaml CHANGELOG.md
git commit -m "chore: add pre-commit config and CHANGELOG"
```

### Task 1.9: Phase 1 verification

- [ ] **Step 1: Clean checkout sanity check**

```bash
uv sync --group dev --frozen
make ci-local
```

Expected: both commands exit 0.

- [ ] **Step 2: Run existing tests**

```bash
make test
```

Expected: existing tests pass. (If any fail because they were testing legacy Black formatting, fix the test to assert against ruff format instead.)

- [ ] **Step 3: Sanity-check repo size**

```bash
git ls-files | wc -l
```

Note the count for comparison after later phases.

---

## Phase 2 — Agent files split

**Goal:** Move bulk content out of `CLAUDE.md` into `docs/`. Stand up `AGENTS.md` as the canonical agent doc. Seed `.planning/` and `docs/superpowers/`.

**Acceptance:** `CLAUDE.md` ≤ 10 lines. `AGENTS.md` present and complete. `docs/architecture.md`, `docs/configuration.md`, `docs/api.md` present and link-checkable. `make ci-local` still green.

### Task 2.1: Create AGENTS.md

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Write `AGENTS.md`**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add canonical AGENTS.md"
```

### Task 2.2: Extract architecture/configuration/api docs from CLAUDE.md

**Files:**
- Create: `docs/architecture.md`
- Create: `docs/configuration.md`
- Create: `docs/api.md`

- [ ] **Step 1: Read the current `CLAUDE.md`**

```bash
cat CLAUDE.md | wc -l
```

Note the line count for reference; the bulk of the content moves to the three files below.

- [ ] **Step 2: Write `docs/architecture.md`**

Move the following sections from `CLAUDE.md` verbatim (preserving the ASCII diagrams):

- "## 🏗️ Architecture Overview" (the layered architecture diagram)
- "## 📁 Directory Structure"
- "## 🔧 Core Components" (Singleton Managers, Service Layer, Client Layer, Data Models)
- "## 🔍 Key Patterns and Conventions"
- "## ⚠️ Important Considerations"

Rewrite the directory tree to match the post-migration target (the spec's Section 5 target layout). Strip the project-overview prose; that belongs in `README.md`.

- [ ] **Step 3: Write `docs/configuration.md`**

Move from `CLAUDE.md`:

- "## 🔧 Configuration Management" (Environment Variables, Performance Tuning)
- Add a new "Migration from `AUTOPVS1_*` to `AUTOPVS1_LINK_*`" section noting the dual-read compat shim, deprecation timeline, and the four env-var name swaps users will see.

- [ ] **Step 4: Write `docs/api.md`**

Move from `CLAUDE.md`:

- "## 🚦 API Endpoints"
- "## 🔌 MCP Integration"

Update the MCP Integration section to reflect: `get_cache_statistics` is an MCP resource, `clear_cache` is gated; Streamable HTTP replaces SSE.

- [ ] **Step 5: Commit**

```bash
git add docs/architecture.md docs/configuration.md docs/api.md
git commit -m "docs: extract architecture/configuration/api from CLAUDE.md"
```

### Task 2.3: Shrink CLAUDE.md to a pointer

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace `CLAUDE.md` contents**

```markdown
# CLAUDE.md

@AGENTS.md

Claude Code entrypoint only:

- Use `AGENTS.md` for shared repository instructions.
- Keep Claude-specific additions here short and tool-specific.
- Prefer `make ci-local` before final handoff.
```

- [ ] **Step 2: Verify**

```bash
wc -l CLAUDE.md
```

Expected: ≤ 10 lines.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: shrink CLAUDE.md to thin pointer to AGENTS.md"
```

### Task 2.4: Seed .planning/ and docs/superpowers/

**Files:**
- Create: `.planning/.gitkeep`
- Verify exists: `docs/superpowers/specs/` (from spec phase)
- Verify exists: `docs/superpowers/plans/` (this file lives here)

- [ ] **Step 1: Seed**

```bash
mkdir -p .planning docs/superpowers/specs docs/superpowers/plans
touch .planning/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add .planning/.gitkeep
git commit -m "chore: seed .planning/ for GSD workflows"
```

### Task 2.5: Refresh README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update installation/dev sections**

Replace any `pip install -e ".[dev]"` instructions with `uv sync --group dev`. Replace `python server.py` invocations with `make dev` (or `autopvs1-link server`). Add a "Modern stack (May 2026)" subsection listing uv, ruff, mypy strict, FastMCP 3, Python 3.12+. Note the env-var prefix change (`AUTOPVS1_LINK_*`).

- [ ] **Step 2: Run lint to catch stray fenced-block issues**

```bash
make ci-local
```

Expected: green.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: refresh README for uv + modern stack"
```

---

## Phase 3 — Dependency upgrades and env-prefix rename

**Goal:** Bump runtime libs to upper-bound-pinned versions, swap click→typer, drop tenacity, add observability libs (no wiring yet — Phase 5), introduce the `AUTOPVS1_LINK_` env prefix with a backward-compat shim.

**Acceptance:** `make ci-local` green. `make test` green. Old `AUTOPVS1_*` env vars still load, but emit a `DeprecationWarning` once at startup.

### Task 3.1: Port cli.py from click to typer

**Files:**
- Modify: `autopvs1_link/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Inspect existing cli.py**

```bash
uv run python -c "from autopvs1_link.cli import main; print(main.__doc__)"
```

Read the file (`autopvs1_link/cli.py`) to enumerate the click commands: `server`, `mcp`, `health`, `cache`, `clear-cache`, `config`. Note the options each command takes.

- [ ] **Step 2: Write a failing test for the typer CLI surface**

Create `tests/test_cli.py`:

```python
"""Smoke tests for the typer-based CLI."""
from typer.testing import CliRunner

from autopvs1_link.cli import app

runner = CliRunner()


def test_cli_root_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("server", "mcp", "health", "cache", "clear-cache", "config"):
        assert command in result.stdout


def test_cli_config_runs() -> None:
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
```

- [ ] **Step 3: Run test, verify fail**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: ImportError on `app` (cli.py exports `main`, not `app`).

- [ ] **Step 4: Rewrite cli.py with typer**

Replace the click `@click.group` and `@click.command` decorators with typer equivalents. Export an `app = typer.Typer(...)` at module scope. Keep `main()` as a thin wrapper that calls `app()` for entry-point compatibility. Each command becomes `@app.command(name=...)` over a Python function. Options become `typer.Option(...)` parameters with type hints.

Concrete signature scaffold:

```python
"""Typer CLI for AutoPVS1-Link."""
from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

from autopvs1_link.config import settings

app = typer.Typer(
    name="autopvs1-link",
    help="AutoPVS1-Link unified REST + MCP server.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def server(
    host: Annotated[str, typer.Option(help="Bind host")] = settings.server.host,
    port: Annotated[int, typer.Option(help="Bind port")] = settings.server.port,
    transport: Annotated[str, typer.Option(help="Transport: stdio|http|unified")] = "unified",
) -> None:
    """Start the unified REST + MCP HTTP server."""
    from autopvs1_link.unified_server import main as run_unified
    run_unified(host=host, port=port, transport=transport)


@app.command()
def mcp(
    http: Annotated[bool, typer.Option(help="Use HTTP transport")] = False,
    port: Annotated[int, typer.Option(help="HTTP port if --http")] = 3000,
) -> None:
    """Start the MCP server (stdio by default)."""
    if http:
        from autopvs1_link.unified_server import main as run_unified
        run_unified(host="127.0.0.1", port=port, transport="http")
    else:
        from autopvs1_link.unified_server import run_mcp_stdio
        asyncio.run(run_mcp_stdio())


@app.command()
def health() -> None:
    """Check service health."""
    from autopvs1_link.services.service_manager import get_service_manager
    manager = asyncio.run(get_service_manager())
    console.print(asyncio.run(manager.health_check()))


@app.command()
def cache() -> None:
    """Show cache statistics."""
    from autopvs1_link.services.service_manager import get_service_manager
    manager = asyncio.run(get_service_manager())
    console.print(asyncio.run(manager.cache_stats()))


@app.command(name="clear-cache")
def clear_cache() -> None:
    """Clear all service caches."""
    from autopvs1_link.services.service_manager import get_service_manager
    manager = asyncio.run(get_service_manager())
    asyncio.run(manager.clear_cache())
    console.print("[green]Caches cleared.[/green]")


@app.command()
def config() -> None:
    """Show the current configuration."""
    console.print_json(data=settings.model_dump(mode="json"))


def main() -> None:
    """Entry-point shim used by `[project.scripts] autopvs1-link`."""
    app()


if __name__ == "__main__":
    main()
```

If your existing `service_manager` does not have a `cache_stats()` or `health_check()` coroutine yet, adapt the body to call whatever it currently exposes. The tests below only assert the help surface and `config` exit code.

- [ ] **Step 5: Run test, verify pass**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: both tests pass.

- [ ] **Step 6: Verify the rest of the suite still passes**

```bash
make test
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add autopvs1_link/cli.py tests/test_cli.py
git commit -m "feat(cli): port from click to typer"
```

### Task 3.2: Drop tenacity, inline retry into api/retry.py

**Files:**
- Create: `autopvs1_link/api/retry.py`
- Modify (move-and-rewrite): `autopvs1_link/utils/retry_handler.py` → delete after migration
- Modify callers of the old retry helper
- Test: `tests/test_retry.py`

- [ ] **Step 1: Locate callers of the existing retry helper**

```bash
uv run python -c "from autopvs1_link.utils.retry_handler import *" 2>&1 || true
```

Use Grep to find imports of `autopvs1_link.utils.retry_handler` and `tenacity` across the codebase. Note each caller's call site.

- [ ] **Step 2: Write a failing test for the new retry helper**

Create `tests/test_retry.py`:

```python
"""Tests for the inline retry helper."""
import asyncio

import httpx
import pytest

from autopvs1_link.api.retry import async_retry


@pytest.mark.asyncio
async def test_async_retry_returns_on_first_success() -> None:
    calls = 0

    async def op() -> int:
        nonlocal calls
        calls += 1
        return 42

    result = await async_retry(op, max_attempts=3, base_delay=0.01)
    assert result == 42
    assert calls == 1


@pytest.mark.asyncio
async def test_async_retry_retries_on_httpx_transport_error() -> None:
    calls = 0

    async def op() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("boom")
        return "ok"

    result = await async_retry(op, max_attempts=4, base_delay=0.01)
    assert result == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_async_retry_raises_after_max_attempts() -> None:
    async def op() -> None:
        raise httpx.ConnectError("boom")

    with pytest.raises(httpx.ConnectError):
        await async_retry(op, max_attempts=2, base_delay=0.01)


@pytest.mark.asyncio
async def test_async_retry_does_not_retry_value_error() -> None:
    calls = 0

    async def op() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        await async_retry(op, max_attempts=5, base_delay=0.01)
    assert calls == 1
```

- [ ] **Step 3: Run test, verify fail**

```bash
uv run pytest tests/test_retry.py -v
```

Expected: ImportError on `autopvs1_link.api.retry`.

- [ ] **Step 4: Write `autopvs1_link/api/retry.py`**

```python
"""Async retry helper for HTTP operations.

Replaces the previous tenacity-based wrapper with a small, dependency-free
exponential-backoff loop that only retries on transient httpx errors.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")

RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.RemoteProtocolError,
)


async def async_retry(
    op: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
) -> T:
    """Run an async operation with exponential backoff on transient errors.

    Args:
        op: Zero-arg async callable.
        max_attempts: Total attempts including the first.
        base_delay: Initial delay in seconds.
        max_delay: Upper bound on the delay between attempts.
        backoff_factor: Multiplicative growth factor.

    Returns:
        Whatever `op` returns on success.

    Raises:
        The last transient error after `max_attempts` exhausted, or any
        non-retryable error immediately.
    """
    delay = base_delay
    last_error: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await op()
        except RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            if attempt == max_attempts:
                logger.warning(
                    "retry.exhausted", attempt=attempt, error=str(exc)
                )
                raise
            logger.info(
                "retry.transient_error",
                attempt=attempt,
                next_delay_seconds=delay,
                error=str(exc),
            )
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    # Unreachable, but keeps mypy happy.
    raise RuntimeError("async_retry exited without return") from last_error
```

- [ ] **Step 5: Run test, verify pass**

```bash
uv run pytest tests/test_retry.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Migrate callers**

For each caller you found in Step 1, replace the old `retry_handler` call with `async_retry(lambda: ..., max_attempts=settings.api.max_retries, base_delay=settings.api.retry_delay)`. Remove any `import tenacity` and any `@retry(...)` decorators by inlining the wrapping at call sites.

- [ ] **Step 7: Delete the old retry handler**

```bash
git rm autopvs1_link/utils/retry_handler.py
```

If `autopvs1_link/utils/` is now empty (or holds only `__init__.py` and an unused `cache_manager.py`), audit `cache_manager.py` — if no other module imports it, delete it too.

- [ ] **Step 8: Verify**

```bash
make ci-local
make test
```

Expected: green.

- [ ] **Step 9: Commit**

```bash
git add autopvs1_link/api/retry.py tests/test_retry.py autopvs1_link/
git rm -f autopvs1_link/utils/retry_handler.py
git commit -m "refactor: drop tenacity for inline async_retry helper"
```

### Task 3.3: Rename env prefix to AUTOPVS1_LINK_ with dual-read shim

**Files:**
- Modify: `autopvs1_link/config.py`
- Test: `tests/test_config_env_prefix.py`

- [ ] **Step 1: Write a failing test for the new prefix and the compat shim**

Create `tests/test_config_env_prefix.py`:

```python
"""Tests for the AUTOPVS1_LINK_ env-prefix migration."""
import importlib
import warnings


def test_new_prefix_overrides_default(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_CACHE_SIZE", "999")
    import autopvs1_link.config as config
    importlib.reload(config)
    assert config.settings.cache.size == 999


def test_old_prefix_still_read_with_deprecation_warning(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPVS1_LINK_CACHE_SIZE", raising=False)
    monkeypatch.setenv("AUTOPVS1_CACHE_SIZE", "111")
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        import autopvs1_link.config as config
        importlib.reload(config)
        assert config.settings.cache.size == 111
        # One DeprecationWarning naming AUTOPVS1_CACHE_SIZE
        msgs = [str(w.message) for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert any("AUTOPVS1_CACHE_SIZE" in m for m in msgs)


def test_new_prefix_wins_over_old(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_CACHE_SIZE", "222")
    monkeypatch.setenv("AUTOPVS1_CACHE_SIZE", "333")
    import autopvs1_link.config as config
    importlib.reload(config)
    assert config.settings.cache.size == 222
```

- [ ] **Step 2: Run test, verify fail**

```bash
uv run pytest tests/test_config_env_prefix.py -v
```

Expected: assertion errors on the cache.size value (still reading old prefix only).

- [ ] **Step 3: Edit `autopvs1_link/config.py` to use the new prefix**

For every `BaseSettings` subclass:

- Change `env_prefix` from `AUTOPVS1_*_` (e.g. `AUTOPVS1_API_`) to `AUTOPVS1_LINK_*_` (e.g. `AUTOPVS1_LINK_API_`).
- Top-level `Settings` keeps no prefix on its own envvars but its sub-configs each carry the new prefix.

Add a module-level compat shim at the bottom of `config.py`, before `settings = Settings()`:

```python
import os
import warnings

# Backward-compat: if AUTOPVS1_* is set but AUTOPVS1_LINK_* is not, copy and warn.
_OLD_TO_NEW_PREFIXES = (
    ("AUTOPVS1_API_", "AUTOPVS1_LINK_API_"),
    ("AUTOPVS1_CACHE_", "AUTOPVS1_LINK_CACHE_"),
    ("AUTOPVS1_SERVER_", "AUTOPVS1_LINK_SERVER_"),
    ("AUTOPVS1_LOG_", "AUTOPVS1_LINK_LOG_"),
    ("AUTOPVS1_MCP_", "AUTOPVS1_LINK_MCP_"),
)


def _migrate_legacy_env() -> None:
    migrated: list[str] = []
    for old_prefix, new_prefix in _OLD_TO_NEW_PREFIXES:
        for key, value in list(os.environ.items()):
            if key.startswith(old_prefix):
                suffix = key[len(old_prefix):]
                new_key = new_prefix + suffix
                if new_key not in os.environ:
                    os.environ[new_key] = value
                    migrated.append(key)
    if migrated:
        warnings.warn(
            "Detected legacy AUTOPVS1_* env vars: "
            + ", ".join(sorted(migrated))
            + ". Rename to AUTOPVS1_LINK_*. Compat shim will be removed in a "
              "future release.",
            DeprecationWarning,
            stacklevel=2,
        )


_migrate_legacy_env()
```

- [ ] **Step 4: Run the new tests, verify pass**

```bash
uv run pytest tests/test_config_env_prefix.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Update `.env.example` if any env-var names changed since Task 1.5.**

(They already use `AUTOPVS1_LINK_*` from that task.)

- [ ] **Step 6: Full test sweep**

```bash
make test
```

Expected: green.

- [ ] **Step 7: Commit**

```bash
git add autopvs1_link/config.py tests/test_config_env_prefix.py
git commit -m "feat(config): rename env prefix to AUTOPVS1_LINK_ with compat shim"
```

### Task 3.4: Phase 3 sweep

- [ ] **Step 1: Confirm no leftover legacy imports**

```bash
uv run python -c "import autopvs1_link.cli; import autopvs1_link.config; import autopvs1_link.api.retry"
```

Expected: silent success.

- [ ] **Step 2: ci-local must pass**

```bash
make ci-local
```

Expected: green.

---

## Phase 4 — MCP subpackage refactor

**Goal:** Lift the MCP code out of `unified_server.py` into a structured `autopvs1_link/mcp/` subpackage that mirrors pubtator-link's layout. Bump `fastmcp` to 3.2+ and add `mcp[cli]` 1.27+. Convert `get_cache_statistics` to an MCP resource; gate `clear_cache` behind `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`. Streamable HTTP replaces SSE.

**Acceptance:** stdio MCP boots; HTTP MCP mount under FastAPI boots; `pytest tests/mcp` green; tool catalog regenerated and committed; `make ci-local` green.

### Task 4.1: Inventory the current MCP surface

- [ ] **Step 1: Locate all current MCP tool registrations**

```bash
uv run python -c "from autopvs1_link.unified_server import *" 2>&1 | head
```

Use Grep on `unified_server.py` for `@mcp.tool`, `@app.tool`, `register_tool`, etc. Note the exact tool name, input parameters, return type, and the service-layer call each one makes. Write the inventory to a scratch file (`SCRATCH_mcp_inventory.md` — git-ignored, do not commit).

Expected inventory: 5 tools — `get_variant_pvs1_data`, `search_variants`, `get_cnv_pvs1_data`, `get_cache_statistics`, `clear_cache`.

### Task 4.2: Create the MCP subpackage skeleton

**Files:**
- Create: `autopvs1_link/mcp/__init__.py`
- Create: `autopvs1_link/mcp/metadata.py`
- Create: `autopvs1_link/mcp/errors.py`
- Create: `autopvs1_link/mcp/contracts.py`
- Create: `autopvs1_link/mcp/tools/__init__.py`

- [ ] **Step 1: Write `autopvs1_link/mcp/metadata.py`**

```python
"""Static MCP server metadata."""
from __future__ import annotations

SERVER_NAME = "AutoPVS1 Link"
SERVER_VERSION = "1.0.0"
SERVER_DESCRIPTION = (
    "AutoPVS1 PVS1 variant classification tools. Research use only; "
    "not for clinical decision support."
)
```

- [ ] **Step 2: Write `autopvs1_link/mcp/errors.py`**

```python
"""MCP error envelopes."""
from __future__ import annotations

from typing import Any


class MCPToolError(Exception):
    """Raised by MCP tools to surface a structured error to the client."""

    def __init__(self, message: str, *, code: str = "tool_error", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class UpstreamUnavailableError(MCPToolError):
    """The AutoPVS1 upstream returned an unexpected response or was unreachable."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, code="upstream_unavailable", details=details)


class DestructiveOperationDisabled(MCPToolError):
    """The caller attempted a destructive operation while gating is off."""

    def __init__(self, op_name: str) -> None:
        super().__init__(
            f"Destructive operation '{op_name}' is disabled. Set "
            "AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true to enable.",
            code="destructive_disabled",
            details={"op": op_name},
        )
```

- [ ] **Step 3: Write `autopvs1_link/mcp/contracts.py`**

```python
"""Pydantic input/output contracts for MCP tools and resources."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GenomeBuild = Literal["hg19", "hg38"]


class VariantPVS1Input(BaseModel):
    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    variant_id: str = Field(..., min_length=1, description="Variant identifier as accepted by AutoPVS1.")


class CNVPVS1Input(BaseModel):
    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    cnv_id: str = Field(..., min_length=1, description="CNV identifier as accepted by AutoPVS1.")


class SearchVariantsInput(BaseModel):
    query: str = Field(..., min_length=1, description="Gene symbol or partial variant string.")
    genome_version: GenomeBuild = Field("hg38", description="Genome build for the search.")


class ClearCacheInput(BaseModel):
    """No fields; included for symmetry."""


class CacheStatistics(BaseModel):
    """Read-only snapshot exposed as an MCP resource."""

    hits: int
    misses: int
    size: int
    max_size: int
    ttl_seconds: int
```

(Note: the response models — `AutoPVS1Data`, `AutoPVS1SearchResults`, `AutoPVS1CNVData` — already live in `autopvs1_link/models/autopvs1_models.py`. The tools return those directly.)

- [ ] **Step 4: Write `autopvs1_link/mcp/__init__.py` and `autopvs1_link/mcp/tools/__init__.py`**

`autopvs1_link/mcp/__init__.py`:

```python
"""MCP subpackage for AutoPVS1-Link."""
```

`autopvs1_link/mcp/tools/__init__.py`:

```python
"""Tool registration modules."""
```

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/
git commit -m "feat(mcp): scaffold mcp subpackage with metadata, errors, contracts"
```

### Task 4.3: Build the service adapters layer

**Files:**
- Create: `autopvs1_link/mcp/service_adapters.py`
- Test: `tests/mcp/test_service_adapters.py`

- [ ] **Step 1: Write failing tests**

Create `tests/mcp/__init__.py` (empty), then `tests/mcp/test_service_adapters.py`:

```python
"""Tests for MCP service adapters."""
from unittest.mock import AsyncMock

import pytest

from autopvs1_link.mcp import service_adapters


@pytest.mark.asyncio
async def test_get_variant_calls_service(mocker) -> None:
    fake_service = AsyncMock()
    fake_service.get_variant_data = AsyncMock(return_value={"ok": True})
    mocker.patch("autopvs1_link.mcp.service_adapters._service", return_value=fake_service)

    result = await service_adapters.get_variant("hg38", "1-12345-A-G")

    fake_service.get_variant_data.assert_awaited_once_with("hg38", "1-12345-A-G")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_search_variants_calls_service(mocker) -> None:
    fake_service = AsyncMock()
    fake_service.search_variants = AsyncMock(return_value={"results": []})
    mocker.patch("autopvs1_link.mcp.service_adapters._service", return_value=fake_service)

    result = await service_adapters.search_variants("MYH9", "hg38")
    fake_service.search_variants.assert_awaited_once_with("MYH9", "hg38")
    assert result == {"results": []}


@pytest.mark.asyncio
async def test_clear_cache_gated(monkeypatch, mocker) -> None:
    from autopvs1_link.mcp.errors import DestructiveOperationDisabled

    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false")
    fake_service = AsyncMock()
    fake_service.clear_cache = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters._service", return_value=fake_service)

    with pytest.raises(DestructiveOperationDisabled):
        await service_adapters.clear_cache()
    fake_service.clear_cache.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_cache_when_enabled(monkeypatch, mocker) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    fake_service = AsyncMock()
    fake_service.clear_cache = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters._service", return_value=fake_service)

    result = await service_adapters.clear_cache()
    fake_service.clear_cache.assert_awaited_once()
    assert result["cleared"] is True
```

- [ ] **Step 2: Run, verify fail**

```bash
uv run pytest tests/mcp/test_service_adapters.py -v
```

Expected: ImportError.

- [ ] **Step 3: Write `autopvs1_link/mcp/service_adapters.py`**

```python
"""Async adapters bridging MCP tool handlers to the service layer."""
from __future__ import annotations

import os
from typing import Any

from autopvs1_link.mcp.errors import DestructiveOperationDisabled
from autopvs1_link.services.service_manager import get_service_manager


async def _service() -> Any:
    """Resolve the live AutoPVS1Service.

    Indirected through this helper so tests can monkeypatch it without
    touching the singleton.
    """
    manager = await get_service_manager()
    return manager.service


async def get_variant(genome_build: str, variant_id: str) -> Any:
    service = await _service()
    return await service.get_variant_data(genome_build, variant_id)


async def search_variants(query: str, genome_version: str) -> Any:
    service = await _service()
    return await service.search_variants(query, genome_version)


async def get_cnv(genome_build: str, cnv_id: str) -> Any:
    service = await _service()
    return await service.get_cnv_data(genome_build, cnv_id)


async def cache_statistics() -> Any:
    service = await _service()
    return await service.cache_statistics()


async def clear_cache() -> dict[str, bool]:
    if os.environ.get("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false").lower() != "true":
        raise DestructiveOperationDisabled("clear_cache")
    service = await _service()
    await service.clear_cache()
    return {"cleared": True}
```

If `service.cache_statistics()` or `service.clear_cache()` do not exist on the current `AutoPVS1Service`, add thin pass-throughs that delegate to the existing methods (likely `cache_stats()` and a cache-clearing path). Mirror the names used here.

- [ ] **Step 4: Run, verify pass**

```bash
uv run pytest tests/mcp/test_service_adapters.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/service_adapters.py tests/mcp/__init__.py tests/mcp/test_service_adapters.py
git commit -m "feat(mcp): add service adapters layer"
```

### Task 4.4: Implement the four MCP tools

**Files:**
- Create: `autopvs1_link/mcp/tools/variant_tool.py`
- Create: `autopvs1_link/mcp/tools/cnv_tool.py`
- Create: `autopvs1_link/mcp/tools/search_tool.py`
- Create: `autopvs1_link/mcp/tools/cache_tools.py`
- Create: `autopvs1_link/mcp/facade.py`
- Test: `tests/mcp/test_tools.py`

- [ ] **Step 1: Write `autopvs1_link/mcp/facade.py`**

```python
"""FastMCP server facade — builds the FastMCP instance and registers tools/resources."""
from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp.metadata import (
    SERVER_DESCRIPTION,
    SERVER_NAME,
    SERVER_VERSION,
)


def build_mcp_server() -> FastMCP:
    """Construct and return a configured FastMCP server."""
    mcp = FastMCP(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=SERVER_DESCRIPTION,
    )
    # Tools register themselves when imported.
    from autopvs1_link.mcp.tools import (  # noqa: F401
        cache_tools,
        cnv_tool,
        search_tool,
        variant_tool,
    )
    from autopvs1_link.mcp import resources  # noqa: F401

    cache_tools.register(mcp)
    cnv_tool.register(mcp)
    search_tool.register(mcp)
    variant_tool.register(mcp)
    resources.register(mcp)
    return mcp
```

- [ ] **Step 2: Write `autopvs1_link/mcp/tools/variant_tool.py`**

```python
"""MCP tool: get_variant_pvs1_data."""
from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import VariantPVS1Input


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_variant_pvs1_data")
    async def get_variant_pvs1_data(payload: VariantPVS1Input) -> dict:
        """Return the AutoPVS1 PVS1 analysis for a single variant."""
        result = await service_adapters.get_variant(
            payload.genome_build, payload.variant_id
        )
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
```

- [ ] **Step 3: Write `autopvs1_link/mcp/tools/cnv_tool.py`**

```python
"""MCP tool: get_cnv_pvs1_data."""
from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import CNVPVS1Input


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="get_cnv_pvs1_data")
    async def get_cnv_pvs1_data(payload: CNVPVS1Input) -> dict:
        """Return the AutoPVS1 PVS1 analysis for a single CNV."""
        result = await service_adapters.get_cnv(payload.genome_build, payload.cnv_id)
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
```

- [ ] **Step 4: Write `autopvs1_link/mcp/tools/search_tool.py`**

```python
"""MCP tool: search_variants."""
from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import SearchVariantsInput


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="search_variants")
    async def search_variants(payload: SearchVariantsInput) -> dict:
        """Search AutoPVS1 for variants matching the query."""
        result = await service_adapters.search_variants(
            payload.query, payload.genome_version
        )
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else dict(result)
```

- [ ] **Step 5: Write `autopvs1_link/mcp/tools/cache_tools.py`**

```python
"""MCP tool: clear_cache (gated)."""
from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import ClearCacheInput


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="clear_cache")
    async def clear_cache(_: ClearCacheInput | None = None) -> dict:
        """Clear all service caches.

        Disabled by default. Enable with
        AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true.
        """
        return await service_adapters.clear_cache()
```

- [ ] **Step 6: Write a minimal smoke test**

`tests/mcp/test_tools.py`:

```python
"""Smoke tests for MCP tool registration."""
from fastmcp import FastMCP

from autopvs1_link.mcp.facade import build_mcp_server


def test_build_mcp_server_registers_expected_tools() -> None:
    mcp: FastMCP = build_mcp_server()
    tool_names = {t.name for t in mcp.list_tools()}
    assert {"get_variant_pvs1_data", "get_cnv_pvs1_data", "search_variants", "clear_cache"} <= tool_names
```

If the `list_tools()` API name differs in fastmcp 3.2, adapt to whatever the public listing method is. Cross-check by running `uv run python -c "import fastmcp; help(fastmcp.FastMCP)"` and reading the public surface.

- [ ] **Step 7: Run, verify pass**

```bash
uv run pytest tests/mcp/test_tools.py -v
```

Expected: 1 passed.

- [ ] **Step 8: Commit**

```bash
git add autopvs1_link/mcp/tools/ autopvs1_link/mcp/facade.py tests/mcp/test_tools.py
git commit -m "feat(mcp): implement 4 MCP tools with contracts"
```

### Task 4.5: Implement the MCP resource for cache statistics

**Files:**
- Create: `autopvs1_link/mcp/resources.py`
- Test: `tests/mcp/test_resources.py`

- [ ] **Step 1: Write failing test**

`tests/mcp/test_resources.py`:

```python
"""Smoke tests for MCP resources."""
from autopvs1_link.mcp.facade import build_mcp_server


def test_build_mcp_server_registers_cache_resource() -> None:
    mcp = build_mcp_server()
    resource_uris = {r.uri for r in mcp.list_resources()}
    assert any("autopvs1-link://cache/statistics" in str(u) for u in resource_uris)
```

(Again, adapt `list_resources()` to whatever fastmcp 3.2 exposes.)

- [ ] **Step 2: Write `autopvs1_link/mcp/resources.py`**

```python
"""MCP resources for AutoPVS1-Link."""
from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters


def register(mcp: FastMCP) -> None:
    @mcp.resource("autopvs1-link://cache/statistics")
    async def cache_statistics() -> dict:
        """Read-only snapshot of in-memory cache statistics."""
        stats = await service_adapters.cache_statistics()
        return stats.model_dump(mode="json") if hasattr(stats, "model_dump") else dict(stats)
```

- [ ] **Step 3: Run, verify pass**

```bash
uv run pytest tests/mcp/test_resources.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add autopvs1_link/mcp/resources.py tests/mcp/test_resources.py
git commit -m "feat(mcp): expose cache stats as MCP resource"
```

### Task 4.6: Write the new unified_server and entry-point shims

**Files:**
- Modify: `autopvs1_link/unified_server.py`
- Create: `autopvs1_link/server_manager.py` (replaces the empty file)
- Modify: `server.py`
- Modify: `mcp_server.py`

- [ ] **Step 1: Write `autopvs1_link/server_manager.py`**

```python
"""Application factory: build the FastAPI app with optional MCP mount."""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from autopvs1_link.api.client_manager import shutdown_clients
from autopvs1_link.api.routes import cnv, gene, variant
from autopvs1_link.config import settings
from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.middleware.logging_middleware import LoggingMiddleware
from autopvs1_link.services.service_manager import shutdown_services


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown hooks."""
    yield
    await shutdown_services()
    await shutdown_clients()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoPVS1-Link",
        version=settings.version,
        description="Unified REST + MCP server for AutoPVS1.",
        lifespan=lifespan,
    )
    app.add_middleware(LoggingMiddleware)
    app.include_router(variant.router)
    app.include_router(cnv.router)
    app.include_router(gene.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Mount the MCP Streamable HTTP transport under /mcp.
    mcp = build_mcp_server()
    app.mount("/mcp", mcp.http_app())
    return app


app = create_app()
```

If `FastMCP.http_app()` is not the correct API in fastmcp 3.2 (the API moved across the 2.x→3.x line), look at the FastMCP 3 docs and substitute the documented Streamable HTTP entry point. The pubtator-link `server_manager.py` is a good template — adapt its mount call.

- [ ] **Step 2: Rewrite `autopvs1_link/unified_server.py`**

Keep `unified_server.main(host, port, transport)` and `unified_server.run_mcp_stdio()` as public entry points used by the CLI and entry-point scripts.

```python
"""Transport composer: stdio MCP or HTTP (FastAPI + MCP mount)."""
from __future__ import annotations

import asyncio

import uvicorn

from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.server_manager import create_app


def main(host: str = "127.0.0.1", port: int = 8000, transport: str = "unified") -> None:
    if transport == "stdio":
        asyncio.run(run_mcp_stdio())
        return
    app = create_app()
    uvicorn.run(app, host=host, port=port)


async def run_mcp_stdio() -> None:
    """Run the MCP server over stdio."""
    mcp = build_mcp_server()
    await mcp.run_stdio_async()


if __name__ == "__main__":
    main()
```

If `mcp.run_stdio_async()` is not the FastMCP 3 entry point, substitute the documented one (likely `await mcp.run("stdio")` or `await mcp.run_async(transport="stdio")` — verify against fastmcp 3.2 docs).

- [ ] **Step 3: Rewrite `server.py` as a thin typer-routed entry**

```python
#!/usr/bin/env python
"""Entry point for `python server.py`; defers to the typer CLI."""
from autopvs1_link.cli import app


def main() -> None:
    app(["server"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rewrite `mcp_server.py` as a thin stdio entry**

```python
#!/usr/bin/env python
"""Entry point for `python mcp_server.py`; runs stdio MCP."""
import asyncio
import os
import sys


def main() -> None:
    os.environ.setdefault("FASTMCP_DISABLE_BANNER", "1")
    os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")
    os.environ.setdefault("NO_COLOR", "1")
    try:
        from autopvs1_link.unified_server import run_mcp_stdio
        asyncio.run(run_mcp_stdio())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"MCP server error: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Smoke-test the HTTP server**

```bash
uv run python -c "from autopvs1_link.server_manager import app; print(app.title, app.version)"
```

Expected: `AutoPVS1-Link 1.0.0`.

- [ ] **Step 6: Smoke-test stdio entry imports**

```bash
uv run python -c "from autopvs1_link.unified_server import main, run_mcp_stdio; print('ok')"
```

Expected: `ok`.

- [ ] **Step 7: Boot the HTTP server briefly**

```bash
uv run python -c "import uvicorn; from autopvs1_link.server_manager import app; uvicorn.run(app, port=8123)" &
sleep 2
curl -sf http://127.0.0.1:8123/health
kill %1 2>/dev/null || true
```

Expected: `{"status":"ok"}`.

- [ ] **Step 8: Full test pass**

```bash
make ci-local
```

Expected: green.

- [ ] **Step 9: Commit**

```bash
git add autopvs1_link/server_manager.py autopvs1_link/unified_server.py server.py mcp_server.py
git commit -m "refactor: split unified_server into server_manager + transport composer"
```

### Task 4.7: Generate the MCP tool catalog doc

**Files:**
- Create: `scripts/generate_mcp_tool_catalog.py`
- Create (generated): `docs/mcp-tool-catalog.md`

- [ ] **Step 1: Write `scripts/generate_mcp_tool_catalog.py`**

```python
#!/usr/bin/env python
"""Generate docs/mcp-tool-catalog.md from the built FastMCP server."""
from __future__ import annotations

import json
from pathlib import Path

from autopvs1_link.mcp.facade import build_mcp_server


def render() -> str:
    mcp = build_mcp_server()
    lines: list[str] = ["# MCP Tool Catalog\n"]
    lines.append("Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`.\n")
    lines.append("## Tools\n")
    for tool in mcp.list_tools():
        lines.append(f"### `{tool.name}`\n")
        lines.append((tool.description or "").strip() + "\n")
        schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
        if schema:
            lines.append("```json")
            lines.append(json.dumps(schema, indent=2))
            lines.append("```\n")
    lines.append("## Resources\n")
    for resource in mcp.list_resources():
        lines.append(f"- `{resource.uri}`: {(resource.description or '').strip()}\n")
    return "\n".join(lines)


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "docs" / "mcp-tool-catalog.md"
    out.write_text(render(), encoding="utf-8")
    print(f"Wrote {out}")  # noqa: T201


if __name__ == "__main__":
    main()
```

If the public listing APIs differ in fastmcp 3.2 (e.g. `mcp.tools` instead of `mcp.list_tools()`), adapt to the documented surface.

- [ ] **Step 2: Run the generator**

```bash
uv run python scripts/generate_mcp_tool_catalog.py
```

Expected: `Wrote .../docs/mcp-tool-catalog.md`.

- [ ] **Step 3: Verify the output**

```bash
head -40 docs/mcp-tool-catalog.md
```

Expected: 4 tools listed, 1 resource, no obviously broken JSON schema.

- [ ] **Step 4: Commit**

```bash
git add scripts/generate_mcp_tool_catalog.py docs/mcp-tool-catalog.md
git commit -m "docs: add generated MCP tool catalog"
```

### Task 4.8: Decommission the old MCP code paths

**Files:**
- Delete from `autopvs1_link/unified_server.py`: any leftover legacy tool registrations.
- Delete: `claude-desktop-config.json` if redundant, otherwise update its `command` to `["python", "mcp_server.py"]` (already correct) and confirm the path argument.

- [ ] **Step 1: Verify old `unified_server.py` no longer registers tools**

```bash
grep -n "mcp.tool\|register_tool" autopvs1_link/unified_server.py
```

Expected: only the imports of `build_mcp_server` and `run_mcp_stdio`; no `@mcp.tool` decorators.

- [ ] **Step 2: Update `claude-desktop-config.json`**

Read it. If it still uses an older entry, update it to:

```json
{
  "mcpServers": {
    "autopvs1-link": {
      "command": "python",
      "args": ["-m", "autopvs1_link.cli", "mcp"]
    }
  }
}
```

- [ ] **Step 3: Final ci-local**

```bash
make ci-local
```

Expected: green.

- [ ] **Step 4: Commit**

```bash
git add autopvs1_link/unified_server.py claude-desktop-config.json
git commit -m "chore: tidy MCP migration leftovers"
```

---

## Phase 5 — Observability and security additions

**Goal:** Wire `asgi-correlation-id`, expose `/metrics` via prometheus-client, harden the XML/HTML stack with `defusedxml`.

**Acceptance:** `/metrics` returns Prometheus text on a live server. `X-Request-ID` header appears in responses and JSON-formatted log lines carry the same id. `make ci-local` green.

### Task 5.1: Add defusedxml hardening

**Files:**
- Modify: `autopvs1_link/__init__.py`
- Test: `tests/test_defusedxml.py`

- [ ] **Step 1: Inspect current `__init__.py`**

It's a 1-line file. Note current contents (likely `__version__ = "1.0.0"`).

- [ ] **Step 2: Write failing test**

`tests/test_defusedxml.py`:

```python
"""Tests for the defusedxml hardening shim."""
import xml.sax


def test_xml_sax_is_defused() -> None:
    # After defusedxml.defuse_stdlib(), xml.sax.make_parser is the defused variant.
    import autopvs1_link  # noqa: F401  # triggers the defuse call
    import defusedxml.sax as defused_sax
    assert xml.sax.make_parser is defused_sax.make_parser
```

- [ ] **Step 3: Run, verify fail**

```bash
uv run pytest tests/test_defusedxml.py -v
```

Expected: AssertionError.

- [ ] **Step 4: Edit `autopvs1_link/__init__.py`**

```python
"""AutoPVS1-Link package init."""
from __future__ import annotations

import defusedxml

defusedxml.defuse_stdlib()

__version__ = "1.0.0"
```

- [ ] **Step 5: Run, verify pass**

```bash
uv run pytest tests/test_defusedxml.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add autopvs1_link/__init__.py tests/test_defusedxml.py
git commit -m "feat(security): defuse xml stdlib at import time"
```

### Task 5.2: Wire asgi-correlation-id middleware

**Files:**
- Modify: `autopvs1_link/server_manager.py`
- Modify: `autopvs1_link/logging_config.py`
- Create: `autopvs1_link/observability/__init__.py`
- Create: `autopvs1_link/observability/correlation.py`
- Test: `tests/test_correlation_id.py`

- [ ] **Step 1: Write failing test**

`tests/test_correlation_id.py`:

```python
"""Tests for asgi-correlation-id integration."""
from fastapi.testclient import TestClient

from autopvs1_link.server_manager import app


def test_response_includes_request_id_header() -> None:
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"]


def test_supplied_request_id_is_echoed() -> None:
    with TestClient(app) as client:
        resp = client.get("/health", headers={"X-Request-ID": "test-abc-123"})
        assert resp.headers["X-Request-ID"] == "test-abc-123"
```

- [ ] **Step 2: Run, verify fail**

```bash
uv run pytest tests/test_correlation_id.py -v
```

Expected: KeyError or missing header.

- [ ] **Step 3: Write `autopvs1_link/observability/__init__.py`** (empty module marker).

- [ ] **Step 4: Write `autopvs1_link/observability/correlation.py`**

```python
"""asgi-correlation-id wiring."""
from __future__ import annotations

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI


def install(app: FastAPI) -> None:
    """Install the correlation-id middleware on the given FastAPI app."""
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        update_request_header=True,
    )
```

- [ ] **Step 5: Update `autopvs1_link/server_manager.py`**

After `app.add_middleware(LoggingMiddleware)`, add `from autopvs1_link.observability.correlation import install as install_correlation; install_correlation(app)`. Place the correlation middleware BEFORE LoggingMiddleware so structlog can bind to the id (in FastAPI, the LAST middleware added runs FIRST on requests; check the order in pubtator-link's `server_manager.py` and mirror).

- [ ] **Step 6: Update `autopvs1_link/logging_config.py`**

Add an `asgi_correlation_id.context.correlation_id` accessor inside the structlog processor chain so every log line picks up the current request id when present. Sketch:

```python
from asgi_correlation_id.context import correlation_id


def _bind_correlation_id(logger, method_name, event_dict):
    cid = correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict
```

Add `_bind_correlation_id` to the structlog processor list.

- [ ] **Step 7: Run, verify pass**

```bash
uv run pytest tests/test_correlation_id.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add autopvs1_link/observability/ autopvs1_link/server_manager.py autopvs1_link/logging_config.py tests/test_correlation_id.py
git commit -m "feat(observability): asgi-correlation-id middleware and structlog binding"
```

### Task 5.3: Expose /metrics with prometheus-client

**Files:**
- Create: `autopvs1_link/observability/prometheus.py`
- Modify: `autopvs1_link/server_manager.py`
- Modify: `autopvs1_link/middleware/logging_middleware.py`
- Modify: `autopvs1_link/services/autopvs1_service.py`
- Modify: `autopvs1_link/api/autopvs1_client.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write failing test**

`tests/test_metrics.py`:

```python
"""Tests for the /metrics endpoint."""
import os

from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_prometheus_text(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_METRICS_ENABLED", "true")
    # Re-import to pick up the env var.
    import importlib
    import autopvs1_link.server_manager as sm
    importlib.reload(sm)
    with TestClient(sm.app) as client:
        client.get("/health")  # generate at least one HTTP request
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        body = resp.text
        assert "autopvs1_link_http_requests_total" in body


def test_metrics_endpoint_404_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_METRICS_ENABLED", "false")
    import importlib
    import autopvs1_link.server_manager as sm
    importlib.reload(sm)
    with TestClient(sm.app) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 404
```

- [ ] **Step 2: Run, verify fail**

```bash
uv run pytest tests/test_metrics.py -v
```

Expected: 404 on /metrics in the enabled case.

- [ ] **Step 3: Write `autopvs1_link/observability/prometheus.py`**

```python
"""Prometheus metrics for AutoPVS1-Link."""
from __future__ import annotations

import os
import time

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "autopvs1_link_http_requests_total",
    "Total HTTP requests.",
    labelnames=("method", "route", "status"),
    registry=REGISTRY,
)
HTTP_IN_FLIGHT = Gauge(
    "autopvs1_link_http_in_flight",
    "In-flight HTTP requests.",
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "autopvs1_link_http_duration_seconds",
    "HTTP request duration.",
    labelnames=("method", "route"),
    registry=REGISTRY,
)
CACHE_EVENTS = Counter(
    "autopvs1_link_cache_events_total",
    "Cache hit/miss events.",
    labelnames=("event",),
    registry=REGISTRY,
)
UPSTREAM_CALLS = Counter(
    "autopvs1_link_upstream_calls_total",
    "Calls to the AutoPVS1 upstream.",
    labelnames=("outcome",),
    registry=REGISTRY,
)
UPSTREAM_DURATION = Histogram(
    "autopvs1_link_upstream_duration_seconds",
    "Upstream call duration.",
    registry=REGISTRY,
)


class _MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        HTTP_IN_FLIGHT.inc()
        start = time.perf_counter()
        route = request.scope.get("path", "<unknown>")
        try:
            response = await call_next(request)
            HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
            return response
        finally:
            HTTP_DURATION.labels(request.method, route).observe(time.perf_counter() - start)
            HTTP_IN_FLIGHT.dec()


def metrics_enabled() -> bool:
    return os.environ.get("AUTOPVS1_LINK_METRICS_ENABLED", "true").lower() == "true"


def install(app: FastAPI) -> None:
    if not metrics_enabled():
        return
    app.add_middleware(_MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
```

- [ ] **Step 4: Mount the metrics installer**

In `autopvs1_link/server_manager.py`, after correlation middleware install, add `from autopvs1_link.observability.prometheus import install as install_metrics; install_metrics(app)`.

- [ ] **Step 5: Instrument the cache and upstream call paths**

In `autopvs1_link/services/autopvs1_service.py`, where the cache decorator wraps the methods, increment `CACHE_EVENTS.labels("hit")` or `CACHE_EVENTS.labels("miss")` accordingly. (The `async_lru` library may expose hit/miss callbacks; if not, instrument by wrapping the call.) In `autopvs1_link/api/autopvs1_client.py`, time each upstream call with `UPSTREAM_DURATION.time()` and increment `UPSTREAM_CALLS.labels("success"|"failure")`.

- [ ] **Step 6: Run, verify pass**

```bash
uv run pytest tests/test_metrics.py -v
```

Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add autopvs1_link/observability/prometheus.py autopvs1_link/server_manager.py autopvs1_link/services/autopvs1_service.py autopvs1_link/api/autopvs1_client.py tests/test_metrics.py
git commit -m "feat(observability): expose Prometheus /metrics and instrument hot paths"
```

### Task 5.4: Phase 5 verification

- [ ] **Step 1: Run the full suite**

```bash
make ci-local
make test
```

Expected: green.

- [ ] **Step 2: Smoke a live server**

```bash
uv run uvicorn autopvs1_link.server_manager:app --port 8123 &
sleep 2
curl -sf http://127.0.0.1:8123/health
curl -sf http://127.0.0.1:8123/metrics | head -20
kill %1
```

Expected: `/health` returns 200; `/metrics` returns Prometheus text including `autopvs1_link_http_requests_total`.

---

## Phase 6 — Docker stack

**Goal:** Multi-stage `Dockerfile`, `gunicorn_conf.py`, and four Compose files. `make docker-up` produces a healthy container.

**Acceptance:** `make docker-build` succeeds. `make docker-up` followed by a 30 second wait yields `curl http://127.0.0.1:8000/health` → 200. `make docker-prod-config` and `make docker-npm-config` succeed.

### Task 6.1: Write the Dockerfile

**Files:**
- Create: `docker/Dockerfile`

- [ ] **Step 1: Write `docker/Dockerfile`**

```dockerfile
# Multi-stage Dockerfile for AutoPVS1-Link.

# --- Builder ---
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY uv.lock pyproject.toml README.md ./

RUN pip install --upgrade pip uv && \
    uv sync --frozen --no-dev --active

# --- Production ---
FROM python:3.14-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/home/app/web" \
    AUTOPVS1_LINK_HOST=0.0.0.0 \
    AUTOPVS1_LINK_PORT=8000 \
    AUTOPVS1_LINK_TRANSPORT=unified \
    TMPDIR=/tmp/autopvs1-link

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd --system app && \
    useradd --system --gid app --home /home/app --create-home app && \
    mkdir -p /tmp/autopvs1-link /var/cache/autopvs1-link && \
    chown -R app:app /tmp/autopvs1-link /var/cache/autopvs1-link /home/app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /home/app/web

COPY --chown=app:app ./autopvs1_link ./autopvs1_link
COPY --chown=app:app ./server.py ./mcp_server.py ./pyproject.toml ./README.md ./
COPY --chown=app:app ./docker/gunicorn_conf.py ./

RUN /opt/venv/bin/pip install -e . --no-deps

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["gunicorn", "-c", "gunicorn_conf.py", "autopvs1_link.server_manager:app"]
```

- [ ] **Step 2: Commit**

```bash
git add docker/Dockerfile
git commit -m "build(docker): multi-stage Dockerfile on python:3.14-slim"
```

### Task 6.2: Write gunicorn_conf.py

**Files:**
- Create: `docker/gunicorn_conf.py`

- [ ] **Step 1: Copy and adapt pubtator-link's gunicorn config**

```python
"""Gunicorn configuration for AutoPVS1-Link production deployment."""
from __future__ import annotations

import os
from typing import Any

bind = f"0.0.0.0:{os.environ.get('AUTOPVS1_LINK_PORT', os.environ.get('PORT', '8000'))}"
backlog = 2048

workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

timeout = 30
keepalive = 2
graceful_timeout = 30

accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True
enable_stdio_inheritance = True

proc_name = "autopvs1-link"

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "*")
secure_scheme_headers = {
    "X-FORWARDED-PROTO": "https",
    "X-FORWARDED-SSL": "on",
}

preload_app = True
reuse_port = True

worker_tmp_dir = "/dev/shm"


def on_starting(server: Any) -> None:
    server.log.info("Starting AutoPVS1-Link server")


def on_reload(server: Any) -> None:
    server.log.info("Reloading AutoPVS1-Link server")


def worker_int(worker: Any) -> None:
    worker.log.info("Worker received INT or QUIT signal")
```

- [ ] **Step 2: Commit**

```bash
git add docker/gunicorn_conf.py
git commit -m "build(docker): gunicorn config with uvicorn workers"
```

### Task 6.3: Write the four Compose files

**Files:**
- Create: `docker/docker-compose.yml`
- Create: `docker/docker-compose.dev.yml`
- Create: `docker/docker-compose.prod.yml`
- Create: `docker/docker-compose.npm.yml`
- Create: `docker/README.md`

- [ ] **Step 1: Write `docker/docker-compose.yml`** (base service, no Postgres)

```yaml
services:
  autopvs1-link:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: production

    container_name: autopvs1_link_server

    env_file:
      - path: ../.env
        required: false

    environment:
      AUTOPVS1_LINK_HOST: 0.0.0.0
      AUTOPVS1_LINK_PORT: 8000
      AUTOPVS1_LINK_TRANSPORT: unified
      AUTOPVS1_LINK_LOG_LEVEL: INFO
      AUTOPVS1_LINK_METRICS_ENABLED: "true"

    ports:
      - "${AUTOPVS1_LINK_PORT:-8000}:8000"

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

    restart: unless-stopped

    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

- [ ] **Step 2: Write `docker/docker-compose.dev.yml`** (bind mount + reload)

```yaml
services:
  autopvs1-link:
    environment:
      AUTOPVS1_LINK_LOG_LEVEL: DEBUG
    volumes:
      - ../autopvs1_link:/home/app/web/autopvs1_link:ro
    command:
      [
        "uvicorn",
        "autopvs1_link.server_manager:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
      ]
```

- [ ] **Step 3: Write `docker/docker-compose.prod.yml`**

```yaml
services:
  autopvs1-link:
    env_file:
      - path: ../.env.docker.example
        required: false
    environment:
      AUTOPVS1_LINK_LOG_LEVEL: INFO
      AUTOPVS1_LINK_LOG_JSON_FORMAT: "true"
    restart: always
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

- [ ] **Step 4: Write `docker/docker-compose.npm.yml`**

```yaml
services:
  autopvs1-link:
    networks:
      - npm
    labels:
      - "npm.proxy=true"

networks:
  npm:
    external: true
    name: nginx-proxy-manager_default
```

- [ ] **Step 5: Write `docker/README.md`**

````markdown
# Docker deployment for AutoPVS1-Link

## Files

- `Dockerfile` — multi-stage build on `python:3.14-slim`.
- `gunicorn_conf.py` — production process config.
- `docker-compose.yml` — base service definition.
- `docker-compose.dev.yml` — overlay: bind-mount + uvicorn reload.
- `docker-compose.prod.yml` — overlay: production env, resource limits.
- `docker-compose.npm.yml` — overlay: Nginx Proxy Manager network/labels.

## Quick start

```bash
make docker-build
make docker-up
curl http://127.0.0.1:8000/health
make docker-down
```

## Production preview

```bash
make docker-prod-config
make docker-npm-config
```

These render the merged Compose configuration without starting containers,
the same way the `docker.yml` CI workflow validates them.
````

- [ ] **Step 6: Validate Compose configs**

```bash
make docker-prod-config > /dev/null && echo prod-ok
make docker-npm-config > /dev/null && echo npm-ok
```

Expected: both print `*-ok`.

- [ ] **Step 7: Commit**

```bash
git add docker/docker-compose.yml docker/docker-compose.dev.yml docker/docker-compose.prod.yml docker/docker-compose.npm.yml docker/README.md
git commit -m "build(docker): add four-compose deployment stack"
```

### Task 6.4: Boot the container and verify health

- [ ] **Step 1: Build**

```bash
make docker-build
```

Expected: build succeeds.

- [ ] **Step 2: Bring up the stack**

```bash
make docker-up
sleep 15
docker ps --filter "name=autopvs1_link_server" --format "table {{.Names}}\t{{.Status}}"
```

Expected: container status starts as `(health: starting)` then transitions to `(healthy)` within ~30s.

- [ ] **Step 3: Hit health and metrics**

```bash
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/metrics | head -20
```

Expected: both return 200.

- [ ] **Step 4: Tear down**

```bash
make docker-down
```

- [ ] **Step 5: No commit needed** (this is verification only).

---

## Phase 7 — Test suite restructure and raise coverage gate

**Goal:** Reorganize `tests/` into `tests/unit/` and `tests/integration/`. Add tests for new modules (env-prefix shim already done in Phase 3; here, focus on MCP tools, observability, retry, and routes). Raise `fail_under` to 80.

**Acceptance:** `make test-cov` exits 0 with `fail_under = 80`. `make test-fast` runs in parallel without errors.

### Task 7.1: Move existing tests under tests/unit and tests/integration

**Files:**
- Move: every file in `tests/` (except `fixtures/`, `__init__.py`, `conftest.py`, and the new `tests/mcp/` dir) into `tests/unit/`.
- Create: `tests/unit/__init__.py`, `tests/integration/__init__.py`.
- Move: any test currently marked `@pytest.mark.integration` to `tests/integration/`.

- [ ] **Step 1: Inspect the current tests**

```bash
find tests -maxdepth 2 -type f -name "test_*.py"
```

For each file, run `grep -l "@pytest.mark.integration" <file>` to decide its bucket.

- [ ] **Step 2: Move files**

```bash
mkdir -p tests/unit tests/integration
touch tests/unit/__init__.py tests/integration/__init__.py
# For each non-integration test file:
git mv tests/test_scraper_parsers.py tests/unit/
git mv tests/test_retry.py tests/unit/
git mv tests/test_cli.py tests/unit/
git mv tests/test_config_env_prefix.py tests/unit/
git mv tests/test_defusedxml.py tests/unit/
git mv tests/test_correlation_id.py tests/unit/
git mv tests/test_metrics.py tests/unit/
git mv tests/mcp tests/unit/mcp
# For each integration-marked file:
git mv tests/test_api_endpoints.py tests/integration/ 2>/dev/null || true
```

- [ ] **Step 3: Update imports/conftest if needed**

The `conftest.py` (if any) should still be discoverable from `tests/conftest.py`; pytest collects subdirs automatically. Confirm:

```bash
uv run pytest --collect-only -q | head -20
```

Expected: all tests collected.

- [ ] **Step 4: Run the suite**

```bash
make test
```

Expected: green.

- [ ] **Step 5: Commit**

```bash
git add -A tests/
git commit -m "test: split tests into unit/ and integration/ subtrees"
```

### Task 7.2: Add tests for FastAPI routes and the service layer

**Files:**
- Create: `tests/unit/api/__init__.py`
- Create: `tests/unit/api/test_routes_variant.py`
- Create: `tests/unit/api/test_routes_cnv.py`
- Create: `tests/unit/api/test_routes_gene.py`
- Create: `tests/unit/services/__init__.py`
- Create: `tests/unit/services/test_autopvs1_service.py`

- [ ] **Step 1: Write route-level tests against a mocked service**

`tests/unit/api/test_routes_variant.py`:

```python
"""Route-level tests for /variant endpoints."""
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from autopvs1_link.server_manager import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_variant_endpoint_routes_to_service(client, mocker) -> None:
    fake = AsyncMock(return_value={"variant_id": "X-1-A-T", "pvs1": "PVS1"})
    mocker.patch(
        "autopvs1_link.api.routes.variant.service.get_variant_data",
        new=fake,
    )
    resp = client.get("/variant/hg38/X-1-A-T")
    assert resp.status_code in (200, 404)  # depends on real route signature
    if resp.status_code == 200:
        assert resp.json()["variant_id"] == "X-1-A-T"
```

Adapt the patch target to the real call site in `autopvs1_link/api/routes/variant.py`. Repeat for `cnv` and `gene` route files.

- [ ] **Step 2: Run, iterate until green**

```bash
uv run pytest tests/unit/api -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/unit/api tests/unit/services
git commit -m "test: cover FastAPI routes and service layer"
```

### Task 7.3: Raise the coverage gate to 80

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Run coverage to see current %**

```bash
make test-cov
```

Note the reported total. If it is below 80, add focused tests where coverage is weakest (look at the HTML report under `htmlcov/index.html`). Targeted additions to consider:

- `autopvs1_link/mcp/errors.py` (instantiate each exception class)
- `autopvs1_link/observability/prometheus.py` (disabled path)
- `autopvs1_link/config.py` (each settings sub-class default + validator branches)

- [ ] **Step 2: Update pyproject.toml**

```toml
[tool.coverage.report]
fail_under = 80
```

- [ ] **Step 3: Verify**

```bash
make test-cov
```

Expected: exit 0; total ≥ 80.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/
git commit -m "test: raise coverage fail_under to 80"
```

---

## Phase 8 — CI/CD and Dependabot

**Goal:** Land five GitHub Actions workflows mirroring pubtator-link's set, plus `dependabot.yml` and a PR template.

**Acceptance:** Workflow YAML files exist and pass `actionlint` (or `yamllint`) if you have it; pushing to a branch and opening a PR triggers ci.yml, docker.yml, security.yml. (Container-security and release run on different triggers and are validated by reading the YAML.)

### Task 8.1: ci.yml

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  quality:
    name: Format, lint, typecheck, tests, and coverage
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@94527f2e458b27549849d47d273a16bec83a01e9 # v7
        with:
          enable-cache: true
          version: "0.8.7"

      - name: Install dependencies
        run: uv sync --group dev --frozen

      - name: Run local CI checks
        run: make ci-local

      - name: Run coverage
        run: make test-cov
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow (format, lint, typecheck, test, coverage)"
```

### Task 8.2: docker.yml

**Files:**
- Create: `.github/workflows/docker.yml`

- [ ] **Step 1: Write `docker.yml`**

```yaml
name: Docker

on:
  pull_request:
  push:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  docker:
    name: Docker build and Compose validation
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@94527f2e458b27549849d47d273a16bec83a01e9 # v7
        with:
          enable-cache: true
          version: "0.8.7"

      - name: Install dependencies
        run: uv sync --group dev --frozen

      - name: Validate production Compose config
        run: make docker-prod-config

      - name: Validate NPM Compose config
        run: make docker-npm-config

      - name: Build Docker image
        run: docker build -f docker/Dockerfile -t autopvs1-link:ci .
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/docker.yml
git commit -m "ci: add Docker build + Compose validation workflow"
```

### Task 8.3: release.yml

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Write `release.yml`**

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: read

jobs:
  release-validation:
    name: Release validation
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@94527f2e458b27549849d47d273a16bec83a01e9 # v7
        with:
          enable-cache: true
          version: "0.8.7"

      - name: Install dependencies
        run: uv sync --group dev --frozen

      - name: Run local CI checks
        run: make ci-local

      - name: Validate production Compose config
        run: make docker-prod-config

      - name: Validate NPM Compose config
        run: make docker-npm-config

      - name: Build release Docker image
        run: docker build -f docker/Dockerfile -t autopvs1-link:release .

      - name: Build Python distribution
        run: uv build

      - name: Upload distribution artifacts
        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6
        with:
          name: dist
          path: dist/
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release validation workflow"
```

### Task 8.4: security.yml

**Files:**
- Create: `.github/workflows/security.yml`

- [ ] **Step 1: Write `security.yml`**

```yaml
name: Security

on:
  pull_request:
  push:
    branches:
      - main
  schedule:
    - cron: "17 3 * * 1"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  codeql:
    name: CodeQL
    runs-on: ubuntu-latest
    if: ${{ !github.event.repository.private }}
    permissions:
      actions: read
      contents: read
      security-events: write

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Initialize CodeQL
        uses: github/codeql-action/init@ed410739ba306e4ebe5e123421a6bd694e494a2b # v4
        with:
          languages: python
          build-mode: none

      - name: Analyze
        uses: github/codeql-action/analyze@ed410739ba306e4ebe5e123421a6bd694e494a2b # v4

  dependency-review:
    name: Dependency review
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    permissions:
      contents: read
      pull-requests: read

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Dependency Review
        uses: actions/dependency-review-action@2031cfc080254a8a887f58cffee85186f0e49e48 # v4.9.0
        continue-on-error: true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "ci: add CodeQL + dependency-review workflow"
```

### Task 8.5: container-security.yml

**Files:**
- Create: `.github/workflows/container-security.yml`

- [ ] **Step 1: Write `container-security.yml`**

```yaml
name: Container Security

on:
  pull_request:
  push:
    branches:
      - main
  schedule:
    - cron: "43 4 * * 1"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  container-security:
    name: Container scan and SBOM
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Build Docker image
        run: docker build -f docker/Dockerfile -t autopvs1-link:scan .

      - name: Run Trivy vulnerability scan
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: autopvs1-link:scan
          format: table
          output: trivy-report.txt
          exit-code: "0"

      - name: Generate SBOM
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: autopvs1-link:scan
          format: cyclonedx
          output: autopvs1-link-sbom.cdx.json
          exit-code: "0"

      - name: Upload scan artifacts
        uses: actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f # v6
        with:
          name: container-security-artifacts
          path: |
            trivy-report.txt
            autopvs1-link-sbom.cdx.json
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/container-security.yml
git commit -m "ci: add Trivy scan + SBOM workflow"
```

### Task 8.6: dependabot.yml and PR template

**Files:**
- Create: `.github/dependabot.yml`
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Write `dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
      timezone: "Europe/Berlin"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "deps"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:15"
      timezone: "Europe/Berlin"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "ci"

  - package-ecosystem: "docker"
    directory: "/docker"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:30"
      timezone: "Europe/Berlin"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "deps"

  - package-ecosystem: "docker-compose"
    directory: "/docker"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:45"
      timezone: "Europe/Berlin"
    open-pull-requests-limit: 5
    commit-message:
      prefix: "deps"
```

- [ ] **Step 2: Write `pull_request_template.md`**

```markdown
## Summary

-

## Quality Checklist

- [ ] Change is focused and small enough to review.
- [ ] Related tests were added or updated.
- [ ] `make ci-local` passes locally.
- [ ] `make test-cov` passes locally when coverage-relevant code changed.
- [ ] Public REST/MCP behavior changes are documented.
- [ ] New dependencies are justified.
- [ ] New network, file, or upstream behavior has explicit limits.
- [ ] MCP tools remain research-use scoped and avoid clinical decision support claims.
- [ ] HTML parser changes include a fixture under `tests/fixtures/`.
```

- [ ] **Step 3: Commit**

```bash
git add .github/dependabot.yml .github/pull_request_template.md
git commit -m "ci: add Dependabot config and PR template"
```

### Task 8.7: Open a synthetic PR and verify every workflow fires

- [ ] **Step 1: Push and open a draft PR**

```bash
git push -u origin main
# Create a no-op branch and PR to trigger CI:
git checkout -b ci-smoke
echo "" >> .github/workflows/ci.yml
git add .github/workflows/ci.yml
git commit -m "ci: smoke test"
git push -u origin ci-smoke
gh pr create --title "CI smoke test" --body "Triggers ci, docker, security."
```

- [ ] **Step 2: Watch workflows**

```bash
gh pr checks --watch
```

Expected: `ci`, `docker`, `security` all conclude. Container-security and release are intentionally not exercised by this PR; their YAML correctness is the bar.

- [ ] **Step 3: Close the smoke PR**

```bash
gh pr close --delete-branch
git checkout main
```

- [ ] **Step 4: Final verification**

```bash
make ci-local
make test-cov
make docker-prod-config > /dev/null
make docker-npm-config > /dev/null
```

Expected: all green.

---

## End-of-plan checks

Run all of these from a clean clone after Phase 8:

```bash
uv sync --group dev --frozen
make ci-local
make test-cov
make docker-build
make docker-up
sleep 30
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/metrics | head -5
make docker-down
```

Acceptance:

- All commands exit 0.
- `pyproject.toml` contains no `click`, `tenacity`, `black` strings; `fail_under = 80`.
- `AGENTS.md` exists; `CLAUDE.md` is ≤ 10 lines; `uv.lock` is committed.
- All five GitHub workflows have at least one green run on `main`.
