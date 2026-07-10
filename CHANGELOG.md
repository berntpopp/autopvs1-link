# Changelog

All notable changes to autopvs1-link are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## 3.0.0

**BREAKING.** Outbound variant transfer is now disabled by default. Deployments
that intentionally use the public AutoPVS1 and Ensembl services must set
`AUTOPVS1_LINK_API_EGRESS_MODE=allowlist` and provide the approved bare HTTPS
origins in `AUTOPVS1_LINK_API_ALLOWED_UPSTREAM_ORIGINS`. The production Compose
profile includes the current public-research origins; patient-data deployments
must keep egress disabled or substitute operator-approved self-hosted services.

### Security

- Enforce a default-deny, exact-origin HTTPS policy before every outbound
  request and redirect hop, with URL parsing matched to HTTPX and an absolute
  five-redirect ceiling.
- Remove client IP addresses and query parameters from the production logging
  profile and identify outbound requests with an honest project user agent.
- Fail closed when upstream result strength or response shape drifts, returning
  stable deployment-policy and upstream-format error envelopes without leaking
  submitted variants.
- Declare the public-research AutoPVS1 and build-specific Ensembl origins in
  production Compose and document the separate network-layer egress control
  required for regulated deployments.

## 2.0.3

### Changed

- Merge the consolidated Dependabot dependency sweep (#58 — fastapi, uvicorn,
  typer, mcp, fastmcp) with the security-remediation release (docker loopback
  bind + variant/query log redaction, finding M2). No behaviour change beyond
  the merged dependency bumps and security fixes.

## 2.0.2

### Security

- Loopback-bind (`127.0.0.1`) the base `docker-compose.yml` host port so
  copying it to a server never publishes the unauthenticated backend on the
  public IP; production reaches it only via the router / reverse proxy.
- Stop logging variant coordinates, CNV ids, HGVS, and free-text queries via
  a field-name log redactor (GDPR Art. 9, finding M2).
- Close the exception-string log leak: an `httpx.HTTPStatusError` stringifies
  to `... for url '<variant-url>' ...`, so `error=str(exc)` on the upstream
  fetch paths smuggled the patient variant past the field-name scrub. The
  redactor now scrubs `error`/`exception`/`exc` values, and the upstream
  failure log sites emit `error_type` (the exception class) instead.

## 2.0.1

### Security

- Harden AutoPVS1 upstream-provenance test assertion to exact source match
  (clears CodeQL `py/incomplete-url-substring-sanitization`).

## 2.0.0

**BREAKING.** Adopts the [GeneFoundry Response-Envelope Standard v1](https://github.com/berntpopp/genefoundry-router/blob/main/docs/RESPONSE-ENVELOPE-STANDARD-v1.md)
flat banner. Every MCP tool's `structuredContent` shape changed; there is no
compatibility shim (pre-alpha fleet standard). Migration: replace `ok` reads
with `success`; replace `data` reads with `result` (single-item tools:
`get_variant_pvs1_data`, `get_cnv_pvs1_data`, `get_server_health`,
`get_server_capabilities`, `clear_cache`) or `results` plus sibling
top-level keys (collection tools: `search_variants` — `pagination`,
`total_count`, etc. move to the top level; the bulk tools — `total`,
`attempted`, `succeeded`, `failed` move to the top level, and the aggregate
list is renamed `items` -> `results`); replace `error.code` /
`error.message` / `error.retryable` / `error.suggestions` /
`error.details` reads with the flat top-level `error_code`, `message`,
`retryable`, `suggestions`, `details`, plus a new `recovery_action` hint;
replace `meta` reads with `_meta` (`meta.research_use_only` is now
`_meta.unsafe_for_clinical_use`; `_meta` gains `tool` and
`capabilities_version`). Per-item bulk envelopes (`results[i]` ->
`{ok, input, data, error, meta}`) are unchanged — the standard governs the
outer MCP result frame only.

### Security

Closes issue #41 — PII / GDPR Art. 9 hardening.

- **Variant IDs never appear in logs.** `_request_log_context` now applies
  `_sanitize_path` before binding the `path` field: `/variant/{genome}/{id}`
  and `/cnv/{genome}/{id}` paths are logged as `/variant/<genome>/<redacted>`
  and `/cnv/<genome>/<redacted>`.  Covers both the INFO (incoming request) and
  ERROR (request failed) branches.  `error=str(e)` is also omitted from the
  error event — exception messages can echo patient-derived identifiers;
  `error_type` + `exc_info=True` provide equivalent debugging signal.
- **`query_params` never logged** (variant IDs can appear in query strings);
  `client_ip` and `user_agent` logged only when `log_client_ip=True` opt-in is
  set (controlled by `settings.debug`; off in production).
- **`AUTOPVS1_LINK_ENVIRONMENT=production`** set in `docker/docker-compose.prod.yml`
  so the production logging profile (JSON format, WARNING level) activates
  without manual override.
- **Honest `User-Agent`** — the HTTP client no longer spoofs a browser string;
  outbound requests now identify themselves as `autopvs1-link/<version>`.
- **`upstream_format_unrecognized` warning code** registered for scraped
  PVS1 strength values that don't match the known set, plus provenance note
  on scrape-tier envelopes so callers can assess data freshness.

### Fixed
- MCP Streamable-HTTP endpoint now serves `POST /mcp` directly (200) instead of
  issuing a 307 redirect to `/mcp/`. The MCP route is now baked into the ASGI
  sub-app (`http_app(path="/mcp")`) and the sub-app is mounted at root (`/`),
  matching the rest of the GeneFoundry `-link` fleet. FastAPI routes
  (`/health`, `/api/...`) still take precedence over the catch-all mount.

### Changed
- `serverInfo.name` standardized from `AutoPVS1 Link` to **`autopvs1-link`**
  (lowercase, hyphenated, matching the `autopvs1` namespace token), per
  Tool-Naming Standard v1 Rule 5.

## 1.3.1

Adopts the GeneFoundry Container & Deployment Hardening Standard v1. Security/chore
release, no API changes.

### Security
- Digest-pinned the `python:3.14-slim` base image (build now byte-reproducible).
- Wired the previously dead `cors_origins` setting into the FastAPI app via
  `CORSMiddleware`, and made it never pair wildcard origins with
  `allow_credentials=True`.
- Dev compose no longer runs as `root`: it now builds the production stage and
  runs as the non-root `app` user (no stage runs as root).
- `container-security` CI workflow now **fails on fixable HIGH/CRITICAL** Trivy
  findings (in addition to the existing report + CycloneDX SBOM artifact).
- Prod overlay log rotation raised to 50m x 5.

## 1.3.0

Adopts the [GeneFoundry Tool-Naming & Normalization Standard v1](https://github.com/berntpopp/autopvs1-link/issues/24)
(closes #24). **No tool renames** — every tool name was already unprefixed,
`verb_noun` snake_case, canonical-verb, and ≤ 50 chars, so this is a
non-breaking MINOR release.

### Added
- Domain `tags` on every MCP tool (`variant`, `cnv`/`copy-number`,
  `classification`, `discovery`, `bulk`, `meta`, `health`, `admin`) so the
  `genefoundry-router` gateway can filter and curate the surfaced toolset.
- `tests/unit/mcp/test_tool_names.py`: CI guard asserting every registered
  tool name matches `^[a-z0-9_]{1,50}$`, starts with a canonical verb
  (`get`/`search`/`list`/`resolve`/`find`/`compare`/`compute`), and never
  self-prefixes the `autopvs1` namespace token. The gated, off-by-default
  `clear_cache` (`clear` verb) is encoded as a documented exception.

### Documentation
- README now documents the canonical gateway **namespace token `autopvs1`**
  (tools surface as `autopvs1_<tool>`) and the stable `serverInfo.name`
  (`AutoPVS1 Link`), per Tool-Naming Standard v1 Rule 5.

### Notes
- `clear_cache` keeps the non-canonical `clear` verb as an approved
  gated-destructive exception (off by default; never on the standard surface).
- The `response_mode` enum (`ids_only|summary|standard|full`) and the
  deprecated `genome_version` alias on `search_variants` are unchanged; both
  are deferred to a future fleet-level decision / breaking release per #24.

## 1.2.0

### Changed (BREAKING)
- Default `meta_mode` is now `compact` (was `full`) on every MCP tool.
  Responses that omit `meta_mode` now carry `recommended_citation` as
  `{doi, pmid}` only. Request `meta_mode=full` for the verbatim citation
  `text` + `url`. Rationale: the full metadata block out-weighed the data
  payload by default; trimming follows Anthropic ("return only high-signal
  information") and Google ("trim ceremony, never trim grounding data").

### Added
- `pvs1_flowchart.path_gloss`: a deterministic one-line rationale (the
  traversed decision-tree branch + terminal strength) on every PVS1
  verdict in summary/standard/full modes — closes the bare-code
  groundedness gap without widening to standard.
- `meta.next_commands`: machine-executable `{tool, arguments, reason}`
  next steps on variant/cnv/search/bulk success envelopes and on
  `requires_disambiguation` errors.
- `meta.expected_cold_latency_ms`: per-response cold-call latency hint on
  cold scrape-tier envelopes.

### Documentation
- Cursor contract corrected: `next_cursor` is a base64url-encoded offset
  (not opaque, not authenticated), documented honestly.

## [Unreleased]

### Breaking

- **MCP default `response_mode` flipped to LLM-first sizing
  (v1.1.0).** `get_variant_pvs1_data`, `get_cnv_pvs1_data`, and both
  bulk variants now default to `"summary"` (verdict + final strength,
  ~1.5 KB); `search_variants` defaults to `"ids_only"` (variant_id +
  url per row). Anthropic's Tool Search docs and the Pydantic /
  Codilime "ruthless brevity" engineering write-ups (research
  2026-05-30) put consensus behind smaller-by-default for
  LLM-consumed MCPs; the prior `"standard"` default shipped the full
  decision tree on every first-turn call, wasting ~70% of the typical
  token budget when the caller only needed the verdict. Pass
  `response_mode="standard"` to opt back into the decision tree or
  `"full"` for the audit-trail `*_raw` fields. `capabilities_version`
  invalidates automatically (the `_TOOL_SUMMARIES` purpose strings
  carry the new defaults and were edited) and `SERVER_VERSION` ticks
  1.0.0 → 1.1.0 so cache-aware clients pick the change up.

### Added

- **`meta.cost_tier` + `meta.rate_limit_floor_ms` +
  `meta.next_call_earliest_at` on every envelope.** Scrape-tier tools
  advertise `"expensive_cold_cheap_warm"` and the configured upstream
  floor in milliseconds (default 1000); cheap tools advertise
  `"cheap"` and omit the floor. `next_call_earliest_at` is an
  ISO-8601 UTC instant populated only when the call drove an upstream
  request (`cache_status in {"miss", "coalesced"}`) so LLM clients
  know exactly when the rate-limit clock will release. The new
  `autopvs1_link/mcp/cost_tiers.py` registry is the single source of
  truth shared by the wire and the detailed capabilities resource so
  the two cannot drift; a unit test enforces lockstep.
- **`meta.retry_after_ms` on transient errors.** Defaulted to the
  rate-limit floor for `upstream_timeout`, `upstream_unavailable`,
  and `external_resolver_unavailable` so an LLM retrying immediately
  does not just block on the floor; callers can override (e.g. from
  an upstream `Retry-After` header).
- **`meta.next_actions[]` recovery hints on every error envelope.**
  Sourced from a new `ERROR_NEXT_ACTIONS` registry alongside
  `KNOWN_ERROR_CODES` in `autopvs1_link/mcp/registries.py`. Every
  documented code carries a 1-2 item list of specific recovery
  actions so a failing LLM dispatcher can pick the next move without
  paying a ToolSearch round-trip to re-discover the surface. Pinned
  tests assert every code has hints, every hint is non-empty, and no
  orphaned hints exist for deleted codes.
- **Rewritten server `instructions=` string.** Trimmed to ~1725 bytes
  / ~431 tokens (under the 2 KB Claude Code truncation cliff) and
  restructured into a five-block template (purpose → canonical
  workflow arrows → deferred-tool fallback list → error-code legend
  → safety language). Names all six core entry-point tools verbatim
  (`get_variant_pvs1_data`, `get_cnv_pvs1_data`, `search_variants`,
  `get_variants_pvs1_data_bulk`, `get_cnvs_pvs1_data_bulk`,
  `get_server_capabilities`) so cold-start clients can skip the
  deferred-tool ToolSearch round-trip — Anthropic Tool Search docs
  cite 27-40% first-turn cost for that hop. Snapshot byte-length and
  tool-coverage tests guard the string against future drift.
- **`ToolSummaryMCP.default_response_mode`** on the compact
  capabilities tool so cached discovery clients can plan bandwidth
  without parsing the per-tool description.
- **`error_envelope.meta_recovery_hints`** description on the
  detailed capabilities resource explaining the new
  `meta.next_actions[]` and `meta.retry_after_ms` shapes.

### Fixed

- **`ClientManager._request_delay` now reads from
  `settings.api.rate_limit_delay`.** Previously hard-coded to `1.0`
  while the env var `AUTOPVS1_LINK_API_RATE_LIMIT_DELAY` silently
  diverged when tuned — latent bug flagged in the v9.7 codebase
  audit. The MCP envelope now reads the SAME settings value for
  `meta.rate_limit_floor_ms`, so the wire hint and the applied
  behaviour stay in lockstep.
- **Hard-coded cache TTL mirror in
  `presenters/capabilities.py`** replaced with
  `settings.cache.ttl_seconds`, so an env-tuned cache TTL
  (`AUTOPVS1_LINK_CACHE_TTL_HOURS`) auto-propagates to the
  capabilities resource without further edits.

### Changed

- **`SERVER_VERSION` ticked 1.0.0 → 1.1.0** (also
  `autopvs1_link/__init__.py:__version__`, `pyproject.toml`, and the
  `MCPConfig` / `Settings` defaults). MCP-spec-compliant clients
  caching `serverInfo` see the bump; `capabilities_version`
  invalidates via the hash.

### Added

- **Real rsID / HGVS auto-resolution via Ensembl Variant Recoder REST**
  in `get_variant_pvs1_data`. The previous implementation tried to
  resolve non-canonical inputs by calling AutoPVS1's own search box,
  but AutoPVS1 does not index dbSNP rsIDs and only partially handles
  HGVS via redirect, so the documented examples (`rs80357906`,
  `NM_007294.4:c.5266dup`) returned `not_found`. The new resolver
  delegates to Ensembl's authoritative recoder (build-scoped:
  `rest.ensembl.org` for hg38, `grch37.rest.ensembl.org` for hg19) and
  uses the returned `vcf_string` (already in `CHROM-POS-REF-ALT`
  format) as the canonical id sent to AutoPVS1 for PVS1 scoring.
  Recoder results are cached with the same `enhanced_cache` wrapper
  used for AutoPVS1 calls. Live verification: `rs80357906` resolves
  to `17-43057065-G-GG` (BRCA1 c.5266dup on hg38) and scores cleanly.
  Multi-allelic inputs (e.g. `rs56116432`) surface every allele key
  in `details.candidates` (with `id`, `spdi`, `allele_key`,
  `synonym_ids`, `genome_build`, `resource_uri`) and force the caller
  to disambiguate — never silently best-guess. Recoder timeout / 5xx
  / rate-limit returns the new error code `external_resolver_unavailable`
  (retryable=true), distinguishing transient upstream failure from
  permanent `not_found`.
- **Honest `cache_status="coalesced"`** for concurrent same-key
  callers. The previous wrapper used `cache_info().hits` deltas as
  the hit/miss signal, but `async_lru` increments hits synchronously
  for every waiter that joins an in-flight populator's future — so
  the populator AND every coalesced waiter both observed
  `cache_info_after.hits > cache_info_before.hits` and were labelled
  `hit`, even though one drove the upstream call and the others
  waited multi-seconds. The wrapper now maintains a per-method
  in-flight key set and uses miss-delta detection: the originator
  reports `miss` (true upstream work), latecomers report `coalesced`
  (waited on someone else's miss), and post-population callers
  report `hit` (genuine instant cache return). `bypass` is unchanged.
  Documented on the detailed capabilities resource under
  `cache_statistics.wire_cache_status_values`.
- **`get_server_health(check_upstream: bool = False)`** opt-in HEAD
  probe against the AutoPVS1 base URL. Default `False` preserves the
  sub-millisecond cheap-tool contract; explicit `True` returns
  `data.upstream_reachable` + `data.upstream_status` ∈
  `{reachable, unreachable}` so an LLM agent can confirm AutoPVS1 is
  up before scheduling a cold scoring call. Network failures degrade
  to `unreachable` rather than raising.
- **Auto-resolution of non-canonical `variant_id` inputs** in
  `get_variant_pvs1_data` was originally added in this release with a
  search-based fallback; that path has now been superseded by the
  Variant Recoder integration above. The sniffer (`classify_variant_input`)
  and the surface contract (`auto_resolved` warning,
  `requires_disambiguation` on multi-hit, canonical-bypass) are
  retained; only the resolver backend changed. Documented on the
  detailed capabilities resource under `auto_resolution`.
- **`meta.elapsed_ms` and `meta.cache_status`** echoed on every ok
  envelope when an upstream call ran. The cache wrapper records into
  a task-local `ContextVar`; the envelope reads it when assembling
  meta. `cache_status` is one of `hit | miss | bypass`. Both fields
  default `None` and drop from the wire for cheap tools
  (`get_server_health`, `get_server_capabilities`) so LLM consumers
  don't read misleading 0 ms readings.

### Fixed

- **`search_variants` was completely broken on page 1.** The new
  `exclude_none=True` wire-compaction pass stripped `pagination.previous_cursor`
  on the first page, but `SearchPaginationMCP.previous_cursor: str | None` had
  no default — the published JSON schema marked it required and the MCP client
  rejected every call with `Output validation error: 'previous_cursor' is a
  required property`. Adds `= None` defaults to `previous_cursor` and
  `next_cursor` so the schema marks them non-required (consistent with the
  wire strip). Adds a meta-test that calls every tool through `mcp.call_tool`
  and validates the resulting `structured_content` against the tool's own
  published `output_schema` using `jsonschema` — this seam was missing.
- **`capabilities_version` was a stale hash.** It covered only the static
  registries (`KNOWN_ERROR_CODES`, `KNOWN_WARNING_CODES`, `PAYLOAD_MODES`,
  `SERVER_VERSION`) so edits to `tool_summaries` purpose strings or examples
  slipped past the hash; cache-aware clients keyed on it never saw the
  change. Refactors `capabilities.py` to expose the surface as module-level
  plain-dict constants and extends `capabilities_version()` to lazy-import
  and blend `_TOOL_SUMMARIES`, `_CANONICAL_PARAMETERS`, `_COMPACT_WORKFLOW`,
  and `_PERFORMANCE_BLOCK` into the sha256 input.
- **`summary` mode emitted a warning about a suppressed field.** The
  `invalid_external_link` warning rode along even after the wire stripped
  `external_links` from `variant_info`, leaving callers staring at a code
  pointing at a field they could not see. Drops the warning in summary mode.
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
