"""MCP capabilities presenters.

Tool surface data (``_TOOL_SUMMARIES``, ``_CANONICAL_PARAMETERS``,
``_COMPACT_WORKFLOW``, ``_PERFORMANCE_BLOCK``) is kept as module-level
plain-dict constants so :func:`autopvs1_link.mcp.registries.capabilities_version`
can lazy-import and hash them as part of the published surface. Without
that, edits to a tool summary purpose string would slip past the
version hash and cache-aware clients would never see the change.
"""

from __future__ import annotations

from typing import Any

from autopvs1_link.config import settings
from autopvs1_link.mcp.contracts import CompactCapabilitiesData, ToolSummaryMCP, WorkflowStepMCP
from autopvs1_link.mcp.cost_tiers import (
    CHEAP_TIER as _CHEAP_TIER,
)
from autopvs1_link.mcp.cost_tiers import (
    SCRAPE_TIER as _SCRAPE_TIER,
)
from autopvs1_link.mcp.registries import (
    KNOWN_ERROR_CODES,
    KNOWN_WARNING_CODES,
    PAYLOAD_MODES,
    capabilities_version,
)
from autopvs1_link.mcp.server_info import SERVER_NAME, SERVER_VERSION

# Sourced from config so an env-tuned cache TTL
# (AUTOPVS1_LINK_CACHE_TTL_HOURS) auto-propagates here without re-edits.
# Was a hard-coded 86_400 mirror that drifted from settings under
# overrides.
_DEFAULT_CACHE_TTL_SECONDS = settings.cache.ttl_seconds


_TOOL_SUMMARIES: dict[str, dict[str, Any]] = {
    "get_variant_pvs1_data": {
        "purpose": (
            "Research-use PVS1 analysis for one AutoPVS1 SNV/indel ID. "
            "Default response_mode is 'summary' (verdict + final "
            "strength); widen to 'standard' for the decision tree."
        ),
        "example": {
            "genome_build": "hg19",
            "variant_id": "X-82763936-A-T",
        },
        "default_response_mode": "summary",
    },
    "get_cnv_pvs1_data": {
        "purpose": (
            "Research-use PVS1 analysis for one AutoPVS1 CNV ID. "
            "Default response_mode is 'summary' (verdict + final "
            "strength); widen to 'standard' for the decision tree."
        ),
        "example": {
            "genome_build": "hg19",
            "cnv_id": "17-15000000-20000000-DEL",
        },
        "default_response_mode": "summary",
    },
    "search_variants": {
        "purpose": (
            "Search AutoPVS1 by gene symbol, partial variant ID, or "
            "upstream-supported query. Default response_mode is "
            "'ids_only' (variant_id + url per row, ~40% smaller) so "
            "callers can hand the resolved id to get_variant_pvs1_data. "
            "For rsID/HGVS, skip search and call get_variant_pvs1_data "
            "directly — its built-in Ensembl Variant Recoder resolver "
            "is authoritative."
        ),
        "example": {
            "query": "BRCA1",
            "genome_build": "hg38",
            "limit": 10,
        },
        "default_response_mode": "ids_only",
    },
    "get_server_health": {
        "purpose": (
            "Read local server health and enabled feature flags "
            "without upstream calls (sub-millisecond, no cost). Pass "
            "check_upstream=true for an opt-in HEAD probe."
        ),
        "example": {},
    },
    "get_variants_pvs1_data_bulk": {
        "purpose": (
            "Bulk PVS1 scoring for 1-10 SNV/indel variants in one "
            "call. Auto-resolves rsID and HGVS inputs per item via "
            "Ensembl Variant Recoder (same as get_variant_pvs1_data). "
            "Default response_mode is 'summary' so 10 verdicts fit "
            "one turn budget."
        ),
        "example": {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
            ],
        },
        "default_response_mode": "summary",
    },
    "get_cnvs_pvs1_data_bulk": {
        "purpose": (
            "Bulk PVS1 scoring for 1-10 CNVs in one call. Default "
            "response_mode is 'summary' so 10 verdicts fit one turn "
            "budget."
        ),
        "example": {
            "items": [
                {"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"},
            ],
        },
        "default_response_mode": "summary",
    },
}


_CANONICAL_PARAMETERS: dict[str, list[str]] = {
    "get_variant_pvs1_data": ["genome_build", "variant_id"],
    "get_cnv_pvs1_data": ["genome_build", "cnv_id"],
    "search_variants": ["query", "genome_build", "limit", "cursor"],
    "get_server_health": [],
    "get_variants_pvs1_data_bulk": ["items"],
    "get_cnvs_pvs1_data_bulk": ["items"],
}


_COMPACT_WORKFLOW: list[dict[str, str]] = [
    {
        "step": "Confirm genome build",
        "when": "The source coordinate build is unknown or absent.",
    },
    {
        "step": "Search for an AutoPVS1 ID",
        "when": ("The caller has a gene symbol, partial variant ID, or upstream-supported query."),
    },
    {
        "step": "Score one variant or CNV",
        "when": "The caller has a single normalized AutoPVS1 variant_id or cnv_id.",
    },
    {
        "step": "Score multiple variants or CNVs in one call",
        "when": (
            "The caller has 2 to 10 IDs of the same kind; use "
            "get_variants_pvs1_data_bulk or get_cnvs_pvs1_data_bulk."
        ),
    },
    {
        "step": "Report research-use output",
        "when": "Summarizing any AutoPVS1 result for a user.",
    },
]


_PERFORMANCE_BLOCK: dict[str, Any] = {
    "note": (
        "cost_tier is a coarse latency hint. AutoPVS1 scrapes upstream HTML "
        "so the first uncached call costs cold_call_seconds; subsequent calls "
        "hit the in-process cache and complete in warm_call_seconds. "
        "Plan accordingly: batch first contact, re-call freely when warm."
    ),
    "cost_tiers": [_CHEAP_TIER, "moderate", _SCRAPE_TIER],
    "get_variant_pvs1_data": {
        "cost_tier": _SCRAPE_TIER,
        "cold_call_seconds": 3.5,
        "warm_call_seconds": 0.05,
        "cache_ttl_seconds": _DEFAULT_CACHE_TTL_SECONDS,
    },
    "get_cnv_pvs1_data": {
        "cost_tier": _SCRAPE_TIER,
        "cold_call_seconds": 3.5,
        "warm_call_seconds": 0.05,
        "cache_ttl_seconds": _DEFAULT_CACHE_TTL_SECONDS,
    },
    "search_variants": {
        "cost_tier": _SCRAPE_TIER,
        "cold_call_seconds": 3.0,
        "warm_call_seconds": 0.05,
        "cache_ttl_seconds": _DEFAULT_CACHE_TTL_SECONDS,
    },
    "get_variants_pvs1_data_bulk": {
        "cost_tier": _SCRAPE_TIER,
        "cold_call_seconds": 10.0,
        "warm_call_seconds": 0.5,
        "cache_ttl_seconds": _DEFAULT_CACHE_TTL_SECONDS,
        "note": "Wall time scales linearly with cold-uncached items at ~1 req/s.",
    },
    "get_cnvs_pvs1_data_bulk": {
        "cost_tier": _SCRAPE_TIER,
        "cold_call_seconds": 10.0,
        "warm_call_seconds": 0.5,
        "cache_ttl_seconds": _DEFAULT_CACHE_TTL_SECONDS,
        "note": "Wall time scales linearly with cold-uncached items at ~1 req/s.",
    },
    "get_server_health": {
        "cost_tier": _CHEAP_TIER,
        "warm_call_seconds": 0.001,
        "note": "No upstream call; reads in-process state.",
    },
    "get_server_capabilities": {
        "cost_tier": _CHEAP_TIER,
        "warm_call_seconds": 0.001,
        "note": "No upstream call; hash-memoized capabilities_version.",
    },
}


def present_compact_capabilities() -> CompactCapabilitiesData:
    """Return compact capabilities optimized for first-turn tool selection."""
    return CompactCapabilitiesData(
        server=SERVER_NAME,
        version=SERVER_VERSION,
        capabilities_version=capabilities_version(),
        transport="streamable-http",
        endpoint="/mcp/",
        research_use_only=True,
        tool_summaries={
            name: ToolSummaryMCP(
                purpose=data["purpose"],
                example=data["example"],
                default_response_mode=data.get("default_response_mode"),
            )
            for name, data in _TOOL_SUMMARIES.items()
        },
        canonical_parameters=_CANONICAL_PARAMETERS,
        compact_workflow=[WorkflowStepMCP(**step) for step in _COMPACT_WORKFLOW],
        details_resource="autopvs1-link://capabilities",
    )


def detailed_capabilities_resource() -> dict[str, Any]:
    """Return the full application-controlled capabilities reference resource."""
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "capabilities_version": capabilities_version(),
        "research_use_only": True,
        "accepted_formats": {
            "variant_id": "{chrom}-{position}-{reference}-{alternate}",
            "cnv_id": "{chrom}-{start}-{end}-{TYPE}",
            "genome_build": ["hg19", "hg38"],
        },
        "examples": {
            "get_variant_pvs1_data": {
                "genome_build": "hg19",
                "variant_id": "X-82763936-A-T",
            },
            "get_cnv_pvs1_data": {
                "genome_build": "hg19",
                "cnv_id": "17-15000000-20000000-DEL",
            },
            "search_variants": {
                "query": "BRCA1",
                "genome_build": "hg38",
                "limit": 10,
                "cursor": None,
            },
            "get_variants_pvs1_data_bulk": {
                "items": [
                    {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
                    {"genome_build": "hg19", "variant_id": "11-2768881-C-T"},
                ],
            },
            "get_cnvs_pvs1_data_bulk": {
                "items": [
                    {"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"},
                ],
            },
        },
        "search_behavior": {
            "ordering": "upstream",
            "limit_default": 10,
            "limit_min": 1,
            "limit_max": 50,
            "cursor": (
                "Opaque pagination token returned as next_cursor; "
                "callers must pass it back unchanged."
            ),
            "cursor_opacity": (
                "Syntactic only: cursors are base64url-encoded JSON "
                '{"offset": N} so they round-trip transparently. They are '
                "NOT signed; callers must not rely on opacity for "
                "integrity or as a security boundary. AutoPVS1-Link is "
                "research-use only and the cursor surface is sized "
                "accordingly — use HTTPS for transport confidentiality."
            ),
            "pagination_block": (
                "Search results carry a pagination object with "
                "previous_cursor, next_cursor, has_more, offset, and "
                "total_count_kind."
            ),
            "deprecated_alias": ("genome_version is accepted for one release; use genome_build."),
        },
        "error_envelope": {
            "required_fields": ["ok", "data", "error", "meta"],
            "stable_error_codes": sorted(KNOWN_ERROR_CODES),
            "stable_warning_codes": sorted(KNOWN_WARNING_CODES),
            "meta_recovery_hints": (
                "Every error envelope's meta.next_actions[] is a per-code "
                "list of recovery hints so a failing LLM dispatcher can "
                "pick the next move without paying a ToolSearch round-trip "
                "to re-discover the surface. Transient codes also carry "
                "meta.retry_after_ms set to the rate-limit floor unless "
                "the caller overrides it (e.g. from a 429 Retry-After "
                "header)."
            ),
            "cost_hint_semantics": (
                "meta.cost_tier and meta.rate_limit_floor_ms appear on "
                "an error envelope ONLY when the call drove an upstream "
                "request whose retry will too — i.e. the transient codes "
                "upstream_timeout, upstream_unavailable, and "
                "external_resolver_unavailable. Permanent input errors "
                "(invalid_*, requires_disambiguation, not_found, "
                "destructive_disabled) short-circuit before upstream and "
                "drop the cost hints so callers do not budget a cost "
                "this call never paid."
            ),
        },
        "payload_modes": {
            mode: {"char_budget": spec["char_budget"], "note": spec["note"]}
            for mode, spec in PAYLOAD_MODES.items()
        },
        "tier_specific_fields": {
            "cnv_info.size": (
                "Derived end-start span. Present in standard and full tiers "
                "for get_cnv_pvs1_data and get_cnvs_pvs1_data_bulk; dropped "
                "from summary and ids_only tiers to stay under budget."
            ),
            "variant_info.external_links": (
                "Present in standard and full tiers only. ids_only and "
                "summary tiers drop the link block to stay token-cheap."
            ),
            "pvs1_flowchart.decision_tree": (
                "Empty list in summary; present in standard and full. "
                "Use standard tier when an LLM needs to explain the path."
            ),
            "pvs1_flowchart.terminal_note": (
                "Surfaced in summary mode when final_strength is "
                "ambiguous (Moderate, Supporting, Unmet, or one of the "
                "PVS1_Not_* sentinels). Hoisted from the leaf step's "
                "note_text — explains why the verdict landed where it "
                "did so summary-mode callers don't need to widen to "
                "standard just to read the rationale. Absent for "
                "Strong / Very_Strong verdicts whose path code already "
                "conveys the rationale."
            ),
            "pvs1_flowchart.path_gloss": (
                "One-line deterministic rationale: the decision-tree "
                "branch the variant traversed plus the terminal strength "
                "(ASCII '->' separated). Present for EVERY path in "
                "summary, standard, and full tiers (absent in ids_only). "
                "Built only from upstream scraped node text; lets a "
                "summary-mode caller explain the verdict without widening."
            ),
        },
        "bulk_behavior": {
            "max_items": 10,
            "execution": "sequential",
            "respects_upstream_rate_limit": True,
            "upstream_rate_limit_seconds": 1.0,
            "worst_case_latency_seconds": 10,
            "continue_on_error_default": True,
            "ordering": "preserves input order",
            "auto_resolves_per_item": True,
            "auto_resolution_note": (
                "Each item is routed through the same Ensembl Variant "
                "Recoder resolver as get_variant_pvs1_data, so rsID and "
                "HGVS inputs work uniformly across the single and bulk "
                "surfaces. Multi-candidate resolutions emit per-item "
                "requires_disambiguation; resolver outage emits per-item "
                "external_resolver_unavailable (retryable)."
            ),
            "per_item_envelope": {
                "ok": "bool",
                "input": "object",
                "data": "object|null",
                "error": "object|null",
                "meta": (
                    "object|null — {cache_status, elapsed_ms} for this "
                    "one item's upstream call; absent when the item "
                    "short-circuited before upstream."
                ),
            },
            "applies_response_mode_per_item": True,
            "applies_meta_mode_top_level_only": True,
            "accounting_invariant": "total == attempted + skipped",
            "warning_aggregation": {
                "scope": ("top-level meta.warnings only; per-item warnings are not echoed"),
                "gate": ("code aggregated only when emitted by more than one distinct item"),
                "fields": ("count and affected_indices populated; absent on single-item codes"),
                "ordering": "first-seen-code-first",
            },
            "cache_status_aggregation": (
                "Top-level meta.cache_status echoes the unanimous "
                "per-item status when every item agrees, or 'mixed' "
                "when items had varied outcomes. On 'mixed', "
                "meta.cached_count and meta.uncached_count split items "
                "by warm (hit+coalesced) vs cold (miss+bypass). "
                "Top-level meta.elapsed_ms is the SUM of per-item "
                "upstream wall-clocks (honest sequential bulk total)."
            ),
        },
        "cache_statistics": {
            "resource": "autopvs1-link://cache/statistics",
            "semantics": ("Method-keyed counters with stable keys and cache key shapes."),
            "wire_cache_status_values": ["hit", "miss", "coalesced", "bypass", "mixed"],
            "wire_cache_status_notes": (
                "meta.cache_status on each ok envelope is one of: 'hit' "
                "(cache pre-populated; instant return), 'miss' (we drove "
                "the upstream call; elapsed_ms reflects the round trip), "
                "'coalesced' (another concurrent call's miss was already "
                "in flight; we shared its future and waited — elapsed_ms "
                "reflects the populator's wait, NOT a true hit), 'bypass' "
                "(caching disabled). The bulk surfaces additionally emit "
                "'mixed' at the top level when per-item outcomes vary "
                "and pair it with cached_count + uncached_count so an "
                "LLM dispatcher can forecast cost without parsing every "
                "item. Honest 'coalesced' protects LLM consumers from "
                "concluding that hits are slow when they are really "
                "waiting on a sibling's miss."
            ),
        },
        "destructive_tools": {
            "clear_cache": (
                "Disabled by default; enable only with AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true."
            ),
        },
        "citation": {
            "doi": "10.1002/humu.24051",
            "pmid": "32442321",
            "url": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
        },
        "known_upstream_limitations": [
            "AutoPVS1 returns HTML pages rather than a stable public JSON API.",
            "Unsupported HGVS-like free-text search may return no results.",
            "Outputs are research-use data and require domain review.",
        ],
        "performance": _PERFORMANCE_BLOCK,
        "auto_resolution": _AUTO_RESOLUTION_BLOCK,
    }


_AUTO_RESOLUTION_BLOCK: dict[str, Any] = {
    "tool": "get_variant_pvs1_data",
    "summary": (
        "Auto-resolves non-canonical variant_id inputs (rsID, HGVS c./p./g.) "
        "to canonical CHROM-POS-REF-ALT via Ensembl Variant Recoder REST "
        "before scoring. Build-scoped: GRCh37 host for hg19, GRCh38 host "
        "for hg38."
    ),
    "resolver": {
        "source": "ensembl_variant_recoder",
        "hosts": {
            "hg19": "https://grch37.rest.ensembl.org",
            "hg38": "https://rest.ensembl.org",
        },
        "endpoint": "/variant_recoder/human/{id}",
        "rate_limit": "Ensembl REST: ~15 req/s shared across all endpoints",
        "result_cache_ttl_seconds": _DEFAULT_CACHE_TTL_SECONDS,
    },
    "accepted_forms": {
        "canonical": "CHROM-POS-REF-ALT (e.g. X-82763936-A-T) — no extra upstream call",
        "rsid": "rs<digits> (lowercase rs required, e.g. rs80357906)",
        "hgvs_c": "NM_*/NR_*/ENST*:c.* or :n.* (e.g. NM_007294.4(BRCA1):c.5266dup)",
        "hgvs_p": "NP_*/ENSP*:p.* (e.g. NP_000050.2:p.Glu1756fs)",
        "hgvs_g": "NC_*:g.* (e.g. NC_000017.11:g.43091983C>A)",
    },
    "outcomes": {
        "single_hit": (
            "Scored with the resolved canonical id; auto_resolved warning "
            "carries the original input, resolved id, resolver source, "
            "detected form, and Ensembl allele key."
        ),
        "zero_hits": (
            "error.code='not_found' with concrete suggestions (confirm rsID "
            "exists in current dbSNP; confirm genome_build; or supply a "
            "canonical CHROM-POS-REF-ALT directly to skip resolution)."
        ),
        "multi_hit": (
            "error.code='requires_disambiguation' with candidates list in "
            "details.candidates. Each candidate: id, spdi, allele_key, "
            "synonym_ids, genome_build, resource_uri. Caller picks one "
            "and re-calls. Server never silently best-guesses to avoid "
            "multi-allelic mis-scoring (Ensembl VEP #989 failure mode)."
        ),
        "resolver_unavailable": (
            "error.code='external_resolver_unavailable' (retryable=true) "
            "when Ensembl REST times out, rate-limits, or returns 5xx. "
            "Distinguishes transient failure from permanent not_found."
        ),
    },
    "build_safety": (
        "Resolver call is build-scoped to caller's genome_build so "
        "resolution and scoring share the same coordinate frame. The "
        "SAME rsID returns DIFFERENT coordinates between GRCh37 and "
        "GRCh38 hosts — the resolver picks the correct host."
    ),
}
