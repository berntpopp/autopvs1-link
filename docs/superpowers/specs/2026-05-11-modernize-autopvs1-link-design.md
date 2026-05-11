# Modernize autopvs1-link to mirror pubtator-link conventions

- **Status:** Draft, awaiting user approval
- **Date:** 2026-05-11
- **Reference repo:** `../pubtator-link` (May 2026)
- **Author:** Claude Code, with Bernt Popp

## 1. Goal

Modernize `autopvs1-link` so its tooling, agent files, MCP server architecture, CI, Docker, and observability mirror `../pubtator-link` as of May 2026. Skip pubtator-link's two subsystems that do not apply (benchmarks corpus, PostgreSQL review-RAG). Result: parity with the reference repo's conventions, current best-practice Python stack, and clean agent guidance.

This is a stack modernization. No upstream AutoPVS1 contract changes, no new product features.

## 2. Non-goals

- No live AutoPVS1 service contract changes.
- No new public REST endpoints or MCP tools beyond renaming/restructuring existing ones.
- No benchmark harness.
- No database layer.
- No embeddings / ML extras.
- No `ty` type checker (revisit in a later cycle).

## 3. Why this matters

- `autopvs1-link` currently targets Python 3.9, uses `pip` + `setuptools`, runs `black` + `ruff` (redundant), uses `click` and `fastmcp` 2.x, has no `AGENTS.md`, no Makefile, no pre-commit, no GitHub workflows, no Docker, and commits build artifacts (`coverage.xml`, `*.egg-info/`, `htmlcov/`, `__pycache__/`).
- `../pubtator-link` is the reference template for this developer's modern Python projects.
- Bringing `autopvs1-link` to parity lowers cognitive load when context-switching between repos and enables shared GSD/superpowers workflows.

## 4. Target stack (May 2026 best practices)

| Area                  | New                                                                          | Replaces                                |
|-----------------------|------------------------------------------------------------------------------|------------------------------------------|
| Python floor          | `>=3.12`                                                                     | `>=3.9`                                  |
| Build backend         | `hatchling`                                                                  | `setuptools`                             |
| Dep manager           | `uv` (with committed `uv.lock`)                                              | `pip`                                    |
| Format + lint         | `ruff` only (format + check)                                                 | `black` + `ruff`                         |
| Type check            | `mypy` strict, `python_version = "3.12"`                                     | `mypy` py39                              |
| CLI                   | `typer`                                                                      | `click`                                  |
| MCP                   | `fastmcp>=3.2,<4` + `mcp[cli]>=1.27,<2`                                      | `fastmcp>=2.2`                           |
| Pydantic              | `pydantic>=2.11,<3` / `pydantic-settings>=2.6,<3`                            | `>=2.7` / `>=2.2`                        |
| HTTP server           | `uvicorn[standard]>=0.46` + `gunicorn>=25` (prod CMD)                        | `uvicorn>=0.29`                          |
| Observability         | `structlog>=24.4` + `asgi-correlation-id>=4.3` + `prometheus-client>=0.21`   | `structlog>=24.1` only                   |
| XML hardening         | `defusedxml>=0.7`                                                            | none                                     |
| Tests                 | `pytest>=9` + `pytest-asyncio>=1.3` + `pytest-xdist` + `pytest-mock` + `respx`| `pytest>=8` + `pytest-asyncio>=0.23` + `respx` |
| Retry                 | Inline retry (httpx transport or hand-rolled); drop standalone `tenacity`    | `tenacity>=8`                            |

Rationale notes (from web search, May 2026):

- FastMCP 3.0 (released Jan 2026; latest 3.2.4 on Apr 14, 2026) rebuilds the framework around Components, Providers, Transforms. Functions stay functions; sync tools are auto-dispatched to a threadpool. Hot reload via `fastmcp dev`.
- `mcp` SDK 1.27.1 is current. Streamable HTTP is the supported transport (legacy SSE retired). An April 2026 stdio RCE disclosure motivates keeping stdio behind a thin entry and preferring Streamable HTTP for hosted use.
- Ruff format is `>99.9%` line-identical with Black; one fewer tool. Pre-commit hook order: ruff lint with `--fix` THEN ruff format.
- FastAPI requires Pydantic `>=2.9`. Python 3.12 / 3.13 are the safest production choice for 2026; 3.14 is supported but Pydantic v1 is deprecated.
- uv + hatchling is the current dominant stack for new projects; `uv.lock` is the source of truth for dep pinning.

## 5. Target repo layout

```
autopvs1-link/
├── AGENTS.md                          # NEW canonical agent doc
├── CLAUDE.md                          # SHRUNK pointer to AGENTS.md
├── CHANGELOG.md                       # NEW
├── Makefile                           # NEW
├── pyproject.toml                     # REWRITTEN (hatchling, uv)
├── uv.lock                            # NEW committed
├── README.md                          # UPDATED
├── .pre-commit-config.yaml            # NEW
├── .python-version                    # NEW (3.12)
├── .editorconfig                      # NEW
├── .dockerignore                      # NEW
├── .env.example, .env.docker.example  # NEW
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # NEW
│   │   ├── docker.yml                 # NEW
│   │   ├── release.yml                # NEW
│   │   ├── security.yml               # NEW
│   │   └── container-security.yml     # NEW
│   ├── dependabot.yml                 # NEW (uv + actions + docker)
│   └── pull_request_template.md       # NEW
├── docker/
│   ├── Dockerfile                     # NEW (multi-stage, python:3.14-slim)
│   ├── gunicorn_conf.py               # NEW
│   ├── docker-compose.yml             # NEW
│   ├── docker-compose.dev.yml         # NEW
│   ├── docker-compose.prod.yml        # NEW
│   ├── docker-compose.npm.yml         # NEW
│   └── README.md                      # NEW
├── docs/
│   ├── architecture.md                # NEW (extracted from old CLAUDE.md)
│   ├── configuration.md               # NEW (extracted)
│   ├── api.md                         # NEW (extracted)
│   ├── MCP_CONNECTION_GUIDE.md        # NEW
│   ├── mcp-tool-catalog.md            # NEW (generated)
│   └── superpowers/
│       ├── specs/                     # design docs (this file)
│       └── plans/                     # implementation plans
├── scripts/
│   └── generate_mcp_tool_catalog.py   # NEW
├── .planning/                         # NEW seeded with .gitkeep
├── autopvs1_link/
│   ├── __init__.py                    # version string + defusedxml.defuse_stdlib()
│   ├── server_manager.py              # NEW app factory (FastAPI + MCP mount)
│   ├── unified_server.py              # REFACTORED transport composer
│   ├── cli.py                         # PORTED to typer
│   ├── config.py                      # AUTOPVS1_LINK_* env prefix, dual-prefix shim
│   ├── logging_config.py              # asgi-correlation-id integration
│   ├── api/
│   │   ├── routes/                    # variant.py, cnv.py, gene.py kept
│   │   ├── autopvs1_client.py         # kept
│   │   ├── client_manager.py          # kept
│   │   └── retry.py                   # NEW moved from utils/retry_handler.py
│   ├── services/
│   │   ├── autopvs1_service.py
│   │   └── service_manager.py
│   ├── mcp/                           # NEW SUBPACKAGE
│   │   ├── __init__.py
│   │   ├── tools/                     # variant_tool.py, cnv_tool.py, search_tool.py, cache_tools.py
│   │   ├── catalog.py
│   │   ├── contracts.py
│   │   ├── errors.py
│   │   ├── facade.py
│   │   ├── metadata.py
│   │   ├── resources.py
│   │   ├── prompts.py
│   │   └── service_adapters.py
│   ├── middleware/
│   │   └── logging_middleware.py      # integrates asgi-correlation-id
│   ├── observability/                 # NEW
│   │   ├── __init__.py
│   │   ├── prometheus.py              # /metrics endpoint + metric definitions
│   │   └── correlation.py
│   └── models/
│       └── autopvs1_models.py         # kept
├── server.py                          # thin typer-routed entry
├── mcp_server.py                      # thin stdio entry
└── tests/
    ├── fixtures/                      # HTML fixtures kept
    ├── unit/                          # restructured
    ├── integration/                   # marked tests
    └── conftest.py
```

Deletions (removed from git and added to `.gitignore`):

- `autopvs1_link.egg-info/`
- `coverage.xml`
- `htmlcov/`
- All `__pycache__/`
- `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`
- `autopvs1_link/server_manager.py` (currently empty; replaced)
- `autopvs1_link/utils/cache_manager.py` if confirmed unused after the refactor

## 6. Tooling

### 6.1 Makefile targets

Adopt pubtator-link's Makefile verbatim, minus `db-init`, `db-migrate`, `benchmark-*` (N/A):

- `install`, `sync`, `lock`, `upgrade`
- `format`, `format-check`, `lint`, `lint-ci`, `lint-fix`
- `typecheck`, `typecheck-fast` (dmypy with crash-fallback), `typecheck-stop`, `typecheck-fresh`
- `test`, `test-fast` (xdist `-n auto`), `test-unit`, `test-integration`, `test-cov`, `test-all`
- `check`, `ci-local` (format-check + lint-ci + typecheck-fast + test-fast), `precommit`, `clean`
- `dev`, `mcp-serve`, `mcp-serve-http`
- `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-prod-config`, `docker-npm-config`

`ci-local` is the contract: required check before claiming completion.

### 6.2 Ruff configuration

```toml
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
```

Drop black entirely.

### 6.3 Mypy configuration

```toml
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

[[tool.mypy.overrides]]
module = ["async_lru.*", "structlog.*", "mcp.*", "fastmcp.*", "fastapi.*",
          "pydantic.*", "pydantic_settings.*", "httpx.*", "uvicorn.*",
          "bs4.*", "lxml.*"]
ignore_missing_imports = true
```

### 6.4 Pre-commit

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

Pin drift between `uv.lock` and pre-commit ruff `rev` is accepted (matches pubtator-link). Document in `AGENTS.md`.

### 6.5 Coverage

```toml
[tool.coverage.run]
source = ["autopvs1_link"]
omit = ["tests/*", "*/tests/*"]

[tool.coverage.report]
# Set to 0 in Phase 1 to avoid gating early commits before the test
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

## 7. MCP module structure (`autopvs1_link/mcp/`)

Adopt pubtator-link's contracts-driven pattern. Each MCP tool gets:

1. A pure async function in `services/` that returns a typed Pydantic model.
2. A contract (input + output Pydantic model) in `mcp/contracts.py`.
3. A `@mcp.tool` registration in `mcp/tools/<name>.py` that calls a `service_adapter`, normalizes input, and wraps errors via `mcp/errors.py`.
4. A row in `mcp/catalog.py` for the generated tool catalog doc (`docs/mcp-tool-catalog.md` produced by `scripts/generate_mcp_tool_catalog.py`).

Tools to migrate (autopvs1-link currently exposes 5):

| Current tool                          | New surface                                                                                |
|---------------------------------------|---------------------------------------------------------------------------------------------|
| `get_variant_pvs1_data`               | Tool. Inputs: `genome_build`, `variant_id`. Output: `AutoPVS1Data`.                         |
| `search_variants`                     | Tool. Inputs: `query`, `genome_version`. Output: `AutoPVS1SearchResults`.                   |
| `get_cnv_pvs1_data`                   | Tool. Inputs: `genome_build`, `cnv_id`. Output: `AutoPVS1CNVData`.                          |
| `get_cache_statistics`                | **MCP resource** (read-only state, not a tool).                                             |
| `clear_cache`                         | Tool, **gated** behind `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`. Default disabled.     |

FastMCP 3 transports: stdio + Streamable HTTP. SSE is retired. `mcp_server.py` stays a thin entry that calls `run_mcp_stdio()`. `server.py` becomes a Typer-routed entry to `unified_server.py`, which composes FastAPI + the Streamable HTTP MCP mount.

## 8. Observability and security additions

- **asgi-correlation-id**: middleware injects `X-Request-ID` (configurable), binds it to structlog via contextvar. Replaces bespoke correlation handling in `middleware/logging_middleware.py`.
- **prometheus-client**: `/metrics` endpoint. Counters/histograms for:
  - HTTP request total by route + status
  - In-flight gauge
  - Request duration histogram
  - Cache hit / miss counter
  - AutoPVS1 upstream call counter + latency histogram

  Toggle via `AUTOPVS1_LINK_METRICS_ENABLED` (default `true` for `server`, `false` for stdio MCP).
- **defusedxml**: `defusedxml.defuse_stdlib()` called at import in `autopvs1_link/__init__.py`. Belt-and-braces hardening for the BS4/lxml stack.
- **Drop `tenacity`** as a top-level dep. Existing retry needs (max retries, retry delay) are covered by either an httpx retry transport or a small hand-rolled async retry helper. If a planning task discovers retry logic is non-trivial, re-add `tenacity`.

### 8.1 Env-prefix rename

Migrate from `AUTOPVS1_*` to `AUTOPVS1_LINK_*` to match pubtator-link's `PUBTATOR_LINK_*` convention.

Backward-compat: for one release cycle, settings reads both prefixes. If the old prefix is set, log a single `DeprecationWarning` at startup naming each old-prefixed variable.

## 9. Docker stack

- `docker/Dockerfile`: multi-stage, `python:3.14-slim` base. Builder stage installs `uv` and runs `uv sync --frozen --no-dev --active` into `/opt/venv`. Production stage copies the venv, runs as non-root `app`, `HEALTHCHECK` curls `/health`. Default CMD: `gunicorn -c gunicorn_conf.py autopvs1_link.server_manager:app`.
- `docker/gunicorn_conf.py`: Uvicorn workers, `workers = (2 * cores) + 1` capped, graceful timeout, structlog-aware access logging, `forwarded_allow_ips` from env.
- Four Compose files, mirroring pubtator-link:
  - `docker-compose.yml` — base service.
  - `docker-compose.dev.yml` — bind-mounts + reload.
  - `docker-compose.prod.yml` — production env, restart policy, resource limits.
  - `docker-compose.npm.yml` — Nginx Proxy Manager overlay.
- No Postgres service (no DB).
- `.dockerignore` excludes `.git`, caches, `htmlcov`, `tests/`, `.planning/`.
- `.env.docker.example` documents Docker-only env (PORT, transport, log level, metrics toggle, CORS).

## 10. CI/CD

Five workflows, all with SHA-pinned third-party actions (matches pubtator-link's supply-chain hardening), `permissions: contents: read` baseline, and `concurrency` cancel-in-progress:

1. **ci.yml** — push + PR. `checkout@v6` → `setup-python@v6` py3.12 → `astral-sh/setup-uv@v7` → `uv sync --group dev --frozen` → `make ci-local` → `make test-cov`.
2. **docker.yml** — push to main + tags. Multi-arch (`linux/amd64`, `linux/arm64`) via `docker/setup-buildx-action`. Push to `ghcr.io/<owner>/autopvs1-link`. `metadata-action` semver + sha + branch tagging.
3. **release.yml** — on tag `v*`. `uv build` wheel + sdist. Attest provenance. Publish to PyPI via Trusted Publishing (OIDC, no API tokens). Upload artifacts to release. Generate release notes from `CHANGELOG.md`.
4. **security.yml** — weekly + on PRs touching deps. `uv-audit` (or `pip-audit` against the locked deps). CodeQL Python. Ruff `S` rule report → SARIF.
5. **container-security.yml** — on docker.yml success + nightly. Trivy scan of the freshly published image, `HIGH,CRITICAL`, fail on `CRITICAL`. SARIF upload to code-scanning.

`.github/dependabot.yml` — weekly Monday morning Berlin time:

- `package-ecosystem: uv` — `/`, prefix `deps`
- `package-ecosystem: github-actions` — `/`, prefix `ci`
- `package-ecosystem: docker` — `/docker`, prefix `deps`
- `package-ecosystem: docker-compose` — `/docker`, prefix `deps`

`pull_request_template.md` mirrors pubtator-link: summary, test plan, risk, rollback.

## 11. Agent files

- **CLAUDE.md** shrinks from ~17 KB to ~6 lines: `@AGENTS.md` reference + 1-2 Claude-specific notes (prefer `make ci-local` before final handoff, use repo-local `.claude/skills/` workflows where they exist).
- **AGENTS.md** is the new canonical doc. Adapted from pubtator-link's structure:
  - Project overview
  - Source Of Truth (this file, Makefile, uv.lock)
  - Working Rules (scoped edits, ASCII default, MCP destructive-op policy)
  - Commands (every `make` target)
  - Coding Standards (uv, modern typing, ruff, mypy py3.12, route + service test coverage)
  - Testing Notes
  - Autopvs1-link-specific block: HTML parsing fragility, respectful upstream rate-limiting, fixture-driven parser tests.
- Architecture, dir-structure, env-vars, endpoint reference move from the old `CLAUDE.md` into `docs/architecture.md`, `docs/configuration.md`, `docs/api.md` — discoverable, not loaded into every agent context.
- `.planning/.gitkeep` seeds the GSD directory so `/gsd:new-milestone` etc. work from day one.
- `.claude/skills/` left as-is; no new repo-local skill identified.
- Update `claude-desktop-config.json` to use the new stdio entry and Streamable HTTP URL — or remove if redundant.

## 12. Phasing

Eight phases. Each phase commits independently. After each phase, `make ci-local` is green and the previous behavior is preserved.

### Phase 1 — Tooling foundation (no behavior change)

- Add `.python-version` (3.12), `.editorconfig`, `.gitignore` (rebuilt from pubtator-link), `.dockerignore`, `.env.example`.
- Delete from git: `coverage.xml`, `autopvs1_link.egg-info/`, `htmlcov/`, all `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`.
- Rewrite `pyproject.toml`: hatchling backend, `requires-python = ">=3.12"`, `[dependency-groups] dev`, drop black, ruff format+lint, mypy strict py312, coverage block. Add `uv.lock`.
- Add `Makefile`, `.pre-commit-config.yaml`, minimal `CHANGELOG.md`.
- **Acceptance:** `make ci-local` green on existing source.

### Phase 2 — Agent files split (no code change)

- Extract architecture / structure / env / endpoint sections from `CLAUDE.md` into `docs/architecture.md`, `docs/configuration.md`, `docs/api.md`.
- Write new `AGENTS.md`. Shrink `CLAUDE.md` to a pointer.
- Seed `docs/superpowers/{specs,plans}/`, `.planning/.gitkeep`.
- Update `README.md` for uv install + modern commands.
- **Acceptance:** Files committed, link-check clean, `make ci-local` still green.

### Phase 3 — Dependency + env-prefix bump

- Bump `fastapi`, `pydantic`, `pydantic-settings`, `httpx`, `structlog`, `lxml`, `beautifulsoup4`, `orjson`, `rich` to upper-bound-pinned ranges.
- Swap `click` → `typer` in `cli.py`. Drop `tenacity` (inline retry).
- Add `asgi-correlation-id`, `prometheus-client`, `defusedxml`, `gunicorn`.
- Rename env prefix `AUTOPVS1_*` → `AUTOPVS1_LINK_*` with dual-read compat shim + one-time `DeprecationWarning`.
- Update `config.py`, `logging_config.py`, `middleware/logging_middleware.py`.
- **Acceptance:** all existing tests pass; `pytest tests` green.

### Phase 4 — MCP subpackage refactor

- Bump `fastmcp>=3.2,<4`, add `mcp[cli]>=1.27,<2`.
- Create `autopvs1_link/mcp/` subpackage and populate per Section 7.
- Migrate the 5 tools out of `unified_server.py`. Convert `get_cache_statistics` to an MCP resource; gate `clear_cache` behind `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`.
- Rewrite `unified_server.py` as the transport composer (FastAPI + Streamable HTTP MCP mount). `server.py` and `mcp_server.py` become thin entries.
- Remove or rewrite `claude-desktop-config.json`.
- Add `scripts/generate_mcp_tool_catalog.py`; commit `docs/mcp-tool-catalog.md`.
- **Acceptance:** stdio MCP smoke test + HTTP MCP smoke test pass; FastAPI `/health` returns 200; tool catalog matches expected.

### Phase 5 — Observability + new code paths

- Wire `asgi-correlation-id` middleware.
- Add `autopvs1_link/observability/prometheus.py` with HTTP + cache + upstream-call metrics. Mount `/metrics`. Toggle via `AUTOPVS1_LINK_METRICS_ENABLED`.
- Call `defusedxml.defuse_stdlib()` in `__init__.py`.
- **Acceptance:** `/metrics` returns Prometheus text, correlation IDs appear in JSON logs, BS4 parser uses defused XML stack.

### Phase 6 — Docker stack

- Author `docker/Dockerfile`, `gunicorn_conf.py`, four Compose files, `docker/README.md`.
- **Acceptance:** `make docker-build && make docker-up` healthy; `curl localhost:8000/health` → 200.

### Phase 7 — Test suite restructure

- Split `tests/` into `tests/unit/` and `tests/integration/` with proper markers.
- Use `pytest-xdist` + `pytest-mock` where useful.
- `make test-fast` covers unit tests in parallel.
- Add tests for the new MCP subpackage (tools, contracts, errors, facade), the observability endpoint, and the env-prefix compat shim.
- **Acceptance:** coverage `>=80%` (`fail_under = 80`). Phases 1-6 are committed with `fail_under = 0` in `pyproject.toml`; this phase raises it to `80` in the same commit that lands the new tests.

### Phase 8 — CI/CD + Dependabot

- Add five workflows with SHA-pinned actions.
- Add `dependabot.yml`.
- Add `pull_request_template.md`.
- **Acceptance:** a synthetic PR exercises every workflow green (coverage gate from Phase 7 already passes).

## 13. Success criteria

Verifiable after Phase 8:

- `make ci-local` passes locally and in CI.
- `make test-cov` reports `>=80%` coverage.
- `uv sync --frozen` succeeds from a clean clone.
- `make docker-up` brings up a healthy container.
- `curl localhost:8000/health` → 200; `/metrics` returns Prometheus text; stdio MCP smoke test returns the tool catalog.
- `pyproject.toml` contains no `click`, `tenacity`, `black` strings, and `fail_under = 80`.
- `AGENTS.md` exists, `CLAUDE.md` is `<=10` lines, `uv.lock` is committed.
- All five GitHub workflows have at least one green run on `main`.

## 14. Out of scope

Explicitly not brought over from pubtator-link:

- `benchmarks/` (PubMedQA / BioASQ).
- `pubtator_link/db/`, asyncpg, PostgreSQL migrations.
- `pubtator_link/services/review_context/`, repositories, review-RAG resources.
- Embeddings extras (`sentence-transformers`, `torch`, `numpy`).
- `ty` type checker.
- AutoPVS1 upstream contract changes.

## 15. Risks and mitigations

- **Python 3.12 floor breaks existing users.** Loud `README` + `CHANGELOG` entry. `autopvs1-link` is `1.0.0` with low public adoption; acceptable. Tag a final `0.9.x` from the current `main` before phase 1 if extra safety is wanted.
- **Env-prefix rename surprises deployments.** One release of dual-prefix support with a logged `DeprecationWarning`.
- **FastMCP 3 has breaking API changes from 2.x.** "Functions stay functions" semantic change. Per-tool migration with one small commit each.
- **Gunicorn + uvicorn workers add prod complexity.** Keep `uvicorn server:app --reload` working for dev (`make dev`). Gunicorn is only the Docker CMD.
- **Stdio MCP RCE (April 2026 disclosure).** Prefer Streamable HTTP for hosted deployments; keep stdio entry minimal and patched against the affected `mcp` SDK versions (`>=1.27`).
- **HTML parsing fragility from upstream `autopvs1.bgi.com`.** Out of scope for this work, but the AGENTS.md note + fixture-driven parser tests stay as-is to catch regressions.

## 16. Open questions

None at spec time. The four high-level decisions are locked in:

- Full mirror modernization.
- Python `>=3.12` floor.
- Full MCP subpackage refactor.
- Clean break on entry points and generated artifacts.

If unknowns surface during planning, they are addressed in the per-phase plan files in `docs/superpowers/plans/`.
