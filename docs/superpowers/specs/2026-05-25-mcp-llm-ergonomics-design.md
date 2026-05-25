# MCP LLM Ergonomics and Reliability Design

- **Status:** Draft for user review
- **Date:** 2026-05-25
- **Scope:** AutoPVS1-Link MCP output, validation, errors, observability, and docs
- **Primary evidence:** LLM-side review plus engineering review covering variant, CNV,
  search, capabilities, cache statistics, and clear-cache behavior

## Goal

Make the AutoPVS1-Link MCP surface reliable for LLM agents on both happy paths
and failure paths. The server should preserve the current core REST/scraper
behavior while giving MCP callers clean schemas, predictable errors, documented
input formats, stable cache statistics, and low-noise outputs suitable for
research-use variant interpretation.

## Research Basis

This design follows current agent-tool guidance from Anthropic, Google, and the
MCP specification:

- Anthropic's tool docs emphasize detailed descriptions, explicit parameter
  semantics, examples for format-sensitive inputs, fewer ambiguous tools, and
  high-signal responses only:
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
- Anthropic's engineering guidance recommends evaluation-driven tool design,
  pagination or truncation for large responses, useful error messages, and
  tracking runtime, token use, tool calls, and tool errors:
  https://www.anthropic.com/engineering/writing-tools-for-agents
- Google Gemini function-calling guidance converges on clear names and
  descriptions, strong typing, enums, input validation, robust error handling,
  security, and token-limit awareness:
  https://ai.google.dev/gemini-api/docs/function-calling
- Google ADK tool guidance favors fewer parameters, simple types, meaningful
  names, and async-friendly tool implementations:
  https://adk.dev/tools-custom/function-tools/
- MCP 2025-06-18 describes tools as model-controlled functions with
  `inputSchema`, optional `outputSchema`, annotations, and structured content:
  https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP resources are application-controlled context and should complement, not
  duplicate, tool discovery payloads:
  https://modelcontextprotocol.io/specification/2025-06-18/server/resources
- MCP security guidance supports minimal exposed scope and careful treatment of
  tools and resources:
  https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices

## Current State

The current MCP surface is already useful:

- server instructions steer callers to the right tools;
- `clear_cache` is gated behind `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`;
- `genome_build` uses a strict `hg19`/`hg38` enum on variant and CNV tools;
- cache hits materially improve replay latency;
- `research_use_only: true` is surfaced in discovery payloads;
- ordered `decision_tree` output preserves PVS1 explainability.

The main gaps are reliability and LLM ergonomics:

- upstream 500s and invalid identifiers leak as generic failures;
- CNV format is under-documented and common natural formats fail;
- `search_variants` accepts whitespace and returns silent empty results for
  unsupported free-text HGVS-like queries;
- `final_strength` is inconsistent and misses `VeryStrong` in some paths;
- `decision_tree[].code` can contain HTML whitespace artifacts and note markers
  without resolved note text;
- `external_links.ClinVar` can point to `/variation/na`;
- `genome_build` and `genome_version` name the same concept differently;
- cache-stat namespace and counter semantics are underspecified;
- `get_server_capabilities` and `autopvs1-link://capabilities` duplicate each
  other too closely;
- `clear_cache` accepts an awkward dummy input shape.

## Non-Goals

- Do not shorten or bypass the upstream AutoPVS1 rate-limit delay.
- Do not make AutoPVS1 output clinical decision support.
- Do not expose destructive cache operations by default.
- Do not add a database, queue, embeddings layer, or model call from the MCP
  server.
- Do not change public REST endpoint paths as part of this pass.
- Do not remove fixture-backed parser coverage.
- Do not hide upstream attribution. Outputs must continue to make clear that
  data comes from AutoPVS1.

## Design Overview

Add an MCP presentation layer between service results and tool responses:

```text
MCP tool -> validate/normalize input -> service/client/parser -> MCP presenter -> envelope
```

The parser and service remain responsible for fetching and extracting AutoPVS1
facts. The MCP presenter becomes responsible for agent-facing contract quality:

- response envelope shape;
- clean research-use metadata;
- request/correlation identifiers where available;
- server version echo;
- warnings and suggestions;
- citation fields;
- invalid-link nulling;
- search pagination;
- final-strength normalization;
- compact capabilities payloads.

This keeps core scraper behavior stable while letting MCP outputs evolve toward
agent-oriented contracts.

## MCP Response Envelope

All MCP tools should return a predictable envelope:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "optional-request-id",
    "server_version": "1.0.0",
    "research_use_only": true,
    "recommended_citation": {
      "text": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
      "doi": "10.1002/humu.24051",
      "pmid": "32442321",
      "url": "https://pubmed.ncbi.nlm.nih.gov/32442321/"
    },
    "warnings": []
  }
}
```

Error responses use the same envelope:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "invalid_variant_id",
    "message": "Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
    "retryable": false,
    "suggestions": [
      "Use search_variants with a gene symbol if you do not know the AutoPVS1 variant ID."
    ]
  },
  "meta": {
    "server_version": "1.0.0",
    "research_use_only": true,
    "recommended_citation": {
      "text": "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1 interpretation of null variants. Human Mutation. 2020;41(9):1488-1498.",
      "doi": "10.1002/humu.24051",
      "pmid": "32442321",
      "url": "https://pubmed.ncbi.nlm.nih.gov/32442321/"
    },
    "warnings": []
  }
}
```

`ok`, `data`, `error`, and `meta` are required. `data` is non-null only when
`ok` is true. `error` is non-null only when `ok` is false.

### Error Codes

Use stable machine-readable error codes:

- `invalid_genome_build`
- `invalid_variant_id`
- `invalid_cnv_id`
- `invalid_search_query`
- `not_found`
- `upstream_error`
- `upstream_timeout`
- `parse_error`
- `destructive_operation_disabled`
- `internal_error`

Error messages must not leak raw upstream HTML, MDN URLs, stack traces, or full
low-level exception strings. Include enough detail for an LLM to decide whether
to retry, ask the user for corrected input, or report upstream unavailability.

## Input Contracts

### Genome Build Naming

`genome_build` is the canonical MCP parameter name for all variant, CNV, and
search tools.

For compatibility, `search_variants` may continue accepting `genome_version` as
a deprecated alias for one release. If both are supplied and disagree, return
`invalid_genome_build` with a clear message. Discovery docs and examples must
show only `genome_build`.

### Variant IDs

`get_variant_pvs1_data` accepts AutoPVS1 variant IDs in forms already supported
by the upstream service, such as:

- `X-82763936-A-T`
- `17-41276045-ACT-A`
- `2-48033984-G-GGATT`

The tool should trim surrounding whitespace. Empty strings and obviously invalid
strings such as `NOT-A-VARIANT` must return `invalid_variant_id` before calling
upstream.

### CNV IDs

`get_cnv_pvs1_data` must document and validate the accepted AutoPVS1 CNV ID
format:

```text
{chrom}-{start}-{end}-{TYPE}
```

Examples:

- `17-15000000-20000000-DEL`
- `X-50000000-60000000-DUP`

Validation rules:

- no `chr` prefix;
- no colon-delimited UCSC/Ensembl notation;
- chromosome is `1`-`22`, `X`, `Y`, or `MT`;
- start and end are positive integers;
- start is less than end;
- type is `DEL` or `DUP`;
- surrounding whitespace is trimmed.

Inputs such as `17:15000000-20000000:DEL` and
`chr17:15000000-20000000:DEL` must return `invalid_cnv_id` with suggestions
that show the corrected hyphenated form.

### Search Queries

`search_variants` must trim the query before validation and caching.

Rules:

- whitespace-only input returns `invalid_search_query`;
- gene symbols, partial variant IDs, and upstream-supported query strings remain
  accepted;
- unsupported free-text HGVS-like queries that return no results should include
  an empty result with warnings and suggestions rather than a silent `[]`.

For example, `BRCA1 c.5266dupC` may return no results, but the response should
include suggestions such as:

- search for `BRCA1` only;
- use a resolved AutoPVS1 variant ID when known;
- confirm genome build before scoring.

## Output Contracts

### Variant and CNV Data

MCP variant and CNV `data` should contain the parsed AutoPVS1 payload plus
agent-facing enrichments:

- `genome_build`;
- `variant_info` or `cnv_info`;
- `pvs1_flowchart`;
- `disease_mechanisms`;
- `source_url` when available;
- `upstream_service: "AutoPVS1"`.

`variant_info.pli_score` remains a JSON number. Add `pli_score_display` in MCP
outputs so very small values such as `3.29e-20` remain readable and stable for
presentation. Document that pLI is expected in the range `0.0` to `1.0`, with
very small scientific-notation values possible.

### Final Strength

`pvs1_flowchart.final_strength` is the source of truth for the final PVS1
strength in MCP outputs.

The parser and presenter must recognize all observed AutoPVS1 strength labels:

- `VeryStrong`
- `Strong`
- `Moderate`
- `Supporting`
- `Not applicable`
- `Unmet`

If the HTML omits or misplaces the final-strength field but the ordered decision
tree contains a terminal strength, the presenter should populate
`final_strength` from the last terminal strength node and add a warning:

```text
final_strength was inferred from the terminal decision_tree node.
```

Callers should not need to inspect `decision_tree[-1].code` to find the verdict.

### Decision Tree and Notes

Decision tree steps must be normalized for LLM use:

- collapse internal whitespace to single spaces;
- remove HTML layout artifacts;
- preserve original ordering;
- extract `note_id` when a step references a note marker such as `#1`;
- include resolved `note_text` inline when available;
- keep `notes` as a compact map for backwards explainability.

Example step:

```json
{
  "code": "Role of region in protein function is unknown",
  "description": null,
  "note_id": "#1",
  "note_text": "2 ClinVar pathogenic missense variants and 1 benign missense variant are found in POU-specific domain."
}
```

### External Links

MCP `external_links` should allow `null` values so invalid upstream sentinel links
can be preserved without becoming false citations.

Rules:

- URLs ending in `/variation/na` are invalid ClinVar sentinel links and become
  `null`;
- empty or missing URLs become `null` or are omitted if no label exists;
- the response warning list should mention invalid links that were nulled.

### Search Result Pagination

`search_variants` should default to a bounded MCP page:

- `limit`: default `10`, minimum `1`, maximum `50`;
- `cursor`: optional opaque integer-offset string for MCP callers;
- `total_count`: count before slicing;
- `returned_count`: number returned in this response;
- `next_cursor`: string or `null`;
- `results`: page of `SearchResult`.

Ordering should remain upstream order unless the implementation has a clear
relevance signal. If no relevance signal exists, document `ordering:
"upstream"`.

## Capabilities and Resources

`get_server_capabilities` should be compact and optimized for first-turn tool
selection:

- server name, version, transport, endpoint;
- research-use flag;
- tool summaries;
- canonical parameter names;
- compact workflow;
- pointer to `autopvs1-link://capabilities` for details.

`autopvs1-link://capabilities` should be the fuller reference:

- complete tool examples;
- accepted variant and CNV formats;
- search behavior;
- error-envelope schema;
- citation;
- cache-stat semantics;
- destructive-tool gating;
- known upstream limitations.

This removes byte-for-byte duplication while keeping both discovery paths
useful.

## Cache Statistics

Keep `autopvs1-link://cache/statistics` as a read-only resource, but define
stable stat-key semantics:

- `get_variant_data`: direct variant scoring by `genome_build` and `variant_id`;
- `get_cnv_data`: direct CNV scoring by `genome_build` and `cnv_id`;
- `search_variants`: search by normalized query and `genome_build`;
- `search_with_redirect_detection`: enhanced search/HGVS redirect path when
  used by REST or future MCP tools;
- `resolve_hgvs_notation`: HGVS resolution path when used by REST or future MCP
  tools.

All configured keys should appear in the resource even when counters are zero.
This makes the resource monotonic in shape across reads.

Each block should include:

- `hits`;
- `misses`;
- `errors`;
- `evictions`;
- `total_requests`;
- `hit_rate`;
- `average_time_ms`;
- `last_hit`;
- `last_miss`;
- `uptime_seconds`;
- `cache_key_shape`, for example `variant:{genome_build}:{variant_id}`;
- `description`.

Errors should increment `errors`. Misses should increment only when the wrapped
upstream call completes successfully and populates the cache. This makes the
statistics actionable for LLM retry decisions.

## Observability

MCP responses should include:

- `meta.request_id` when available from request context;
- `meta.server_version`;
- `meta.warnings`;
- `meta.research_use_only`;
- `meta.recommended_citation`.

If the MCP runtime cannot expose an incoming request ID for stdio calls, the
server should generate a lightweight per-tool-call ID. HTTP transport should
reuse `X-Request-ID` where FastAPI/ASGI context makes it available.

Warnings are for structured, non-fatal facts an LLM should consider, such as:

- inferred final strength;
- invalid external link nulled;
- deprecated `genome_version` alias used;
- no results for a query that appears to contain unsupported free-text HGVS;
- upstream result truncated by `limit`.

## `clear_cache`

Keep the current good behavior:

- registered but disabled by default unless
  `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`;
- destructive annotation remains;
- disabled response clearly says how to enable.

Improve the input shape:

- accept `{}` cleanly;
- do not require or advertise a dummy `{"_": null}` field.

The successful response should use the same envelope and include a concise
summary of cleared caches/statistics.

## Documentation

Update:

- `docs/mcp-tool-catalog.md`;
- `docs/api.md` MCP section;
- README MCP examples if present;
- generated tool catalog if the repository expects it.

Documentation must include:

- canonical `genome_build` naming;
- variant examples;
- CNV examples;
- search pagination;
- error envelope;
- cache-stat key semantics;
- research-use disclaimer;
- citation.

## Testing

Required focused coverage:

- parser test for `VeryStrong` final-strength extraction;
- parser/presenter test for cleaned decision-tree whitespace and inline notes;
- presenter test for ClinVar `/variation/na` nulling;
- MCP runtime test for invalid variant ID returning `invalid_variant_id`;
- MCP runtime test for colon CNV formats returning `invalid_cnv_id`;
- MCP runtime test for accepted hyphenated CNV format forwarding upstream;
- MCP runtime test for whitespace search returning `invalid_search_query`;
- MCP runtime test for no-result HGVS-like search including warnings and
  suggestions;
- MCP schema test that `search_variants` advertises `genome_build`, `limit`,
  and `cursor`;
- compatibility test that deprecated `genome_version` still works for one
  release or is rejected with a clear migration message if compatibility is not
  feasible in FastMCP direct-argument schemas;
- cache-stat resource test that all configured stat keys remain present across
  reads, including zero-count keys;
- cache-stat counter test for hit/miss/error semantics;
- capabilities test proving tool and resource payloads are not byte-for-byte
  duplicates;
- clear-cache test for `{}` input and disabled clean error.

Add a small transcript-inspired MCP evaluation fixture or checklist covering:

- replayed `X-82763936-A-T` returns `Strong` with cache metadata;
- `17-41276045-ACT-A` returns `VeryStrong` and pLI display text;
- `NOT-A-VARIANT` returns `invalid_variant_id`, not raw 500 text;
- `17:15000000-20000000:DEL` returns format guidance;
- `17-15000000-20000000-DEL` succeeds when the service adapter returns CNV
  data;
- `BRCA1 c.5266dupC` search returns empty data with useful guidance;
- whitespace search is rejected;
- disabled `clear_cache` remains cleanly gated.

Completion requires `make ci-local` passing.

## Compatibility and Migration

Tool names remain stable:

- `get_variant_pvs1_data`
- `get_cnv_pvs1_data`
- `search_variants`
- `get_server_capabilities`
- `clear_cache`

The MCP response shape intentionally changes to an envelope to support
structured errors and metadata. REST response schemas should remain unchanged
unless a parser bugfix naturally improves parsed values.

`search_variants.genome_version` is a deprecated MCP alias for one release if
FastMCP can expose it cleanly. New docs and examples use `genome_build`.

## Risks

- Envelope output may break clients that hard-coded the previous flat MCP JSON.
  Mitigation: keep tool names stable, document the migration, and make the
  envelope schema explicit.
- Input validation may reject unusual upstream-supported identifiers. Mitigation:
  validate only clearly invalid forms and add fixture-backed tests for known
  valid examples.
- Final-strength inference can overreach if the decision tree contains
  non-terminal strength labels. Mitigation: scan from the end for the first
  recognized strength and add a warning when inference is used.
- Cache-stat semantics may reveal existing decorator quirks. Mitigation: define
  expected behavior in tests before changing implementation.
- Capabilities split can make first-turn discovery too terse. Mitigation: keep
  `get_server_capabilities` compact but include a clear pointer to the resource.

## Acceptance Criteria

- No tested invalid input path leaks a bare HTTP 500, MDN URL, raw HTML, or
  traceback through MCP.
- CNV format is discoverable from the tool description and capabilities
  resource.
- `final_strength` is populated for POU3F4 `Strong`, BRCA1 `VeryStrong`, and
  the tested MYO15A CNV `VeryStrong` path when fixture/service data includes
  those terminal nodes.
- Search trims input and rejects whitespace-only queries.
- Empty search results include useful warnings or suggestions when the query
  appears malformed or unsupported.
- Cache-stat keys are stable across consecutive reads.
- `search_variants` uses canonical `genome_build` in documentation and MCP
  schema, with alias handling documented.
- `external_links.ClinVar` never points to `/variation/na` in MCP output.
- `clear_cache` remains disabled by default and accepts `{}`.
- `make ci-local` passes.
