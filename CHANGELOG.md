# Changelog

All notable changes to autopvs1-link are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **PVS1 flowchart notes parser** now captures the full legend prose for each
  `#N` marker. The previous implementation read only the immediately
  neighbouring tag via `find_next_sibling()`, so `notes['#1']` collapsed to
  the next inline `<b>` token ("2") and `notes['#2']` to an empty `<br>`.
  Fixture-driven assertions now require the full text, so the regression
  cannot reappear silently.

### Changed

- **Breaking (LLM consumers):** every successful wire payload now strips null
  leaves from the inner `data` dump (`exclude_none=True` everywhere, not just
  in summary/ids_only modes). The standard-mode wire no longer ships
  `decision_tree_raw: null`, `external_links_raw: null`, per-step
  `description: null`, or per-step `note_text: null`; per-item bulk envelopes
  drop `error: null` on success and `data: null` on failure; the search
  pagination block drops `previous_cursor` on page one. The outer
  `ok`/`data`/`error`/`meta` shape is unchanged so the documented
  `required_fields` contract still holds; intentional inner nulls inside
  `external_links` (an upstream link we nulled and warned about) stay on the
  wire. Token-efficiency wins ~15-25% on a typical standard-mode call.
- The duplicative `notes` legend dict is dropped from `pvs1_flowchart` in
  summary and standard modes; each `decision_tree` step already carries the
  hoisted `note_text`. Full mode retains the dict for audit-trail use.
- Tool docstrings and the `response_mode` field descriptions now recommend
  `summary` (or `ids_only` for search) as the LLM-first response mode. The
  default response mode stays `standard` so existing callers are unaffected.

### Added

- `meta.effective_chars` on every ok envelope: the byte length of the compact
  JSON `data` dump. Lets clients calibrate against the advertised
  `payload_modes[mode].char_budget` after one call instead of relying on the
  theoretical budget alone.
- Per-tool `performance` block on the detailed capabilities resource, with
  `cost_tier` (`cheap` | `moderate` | `expensive_cold_cheap_warm`),
  `cold_call_seconds`, `warm_call_seconds`, and `cache_ttl_seconds`. Surfaces
  the HTML-scrape upstream's structural cold/warm differential so LLM clients
  can plan first-contact batching and re-call freely once cached.
- `response_mode='ids_only'` tier on every detail tool (`get_variant_pvs1_data`,
  `get_cnv_pvs1_data`, `search_variants`, plus the two bulk variants) for
  lowest-bandwidth lookup. Emits only the upstream identifier, `genome_build`,
  and `source_url` (search keeps `variant_id` + `url` per row). Documented on
  the capabilities resource via the `payload_modes.ids_only` block; clients
  can size requests off the published `char_budget`. Contract widenings
  (`VariantInfoMCP.variant_type`, `VariantInfoMCP.gene_symbol`,
  `CNVInfoMCP.cnv_type`, `CNVInfoMCP.gene_symbol`, `CNVInfoMCP.coordinates`,
  `VariantMCPData.pvs1_flowchart`, `CNVMCPData.pvs1_flowchart`, and the
  descriptive fields on `SearchResultMCP`) are purely additive — existing
  summary/standard/full payloads are unchanged.

### Changed

- **Breaking:** `search_variants` cursor is now an opaque base64url-encoded
  token instead of an integer-offset string; callers persisting offsets
  must round-trip through the returned `data.pagination.next_cursor`.
  `SearchMCPData` replaces its top-level `next_cursor` field with a
  `pagination` block exposing `previous_cursor`, `next_cursor`, `has_more`,
  `offset`, and `total_count_kind` ("upstream_page" by default). Stale
  integer-offset cursors are rejected with `error.code=invalid_search_cursor`.
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
