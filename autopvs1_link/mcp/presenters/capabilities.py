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

from autopvs1_link.mcp.contracts import CompactCapabilitiesData, ToolSummaryMCP, WorkflowStepMCP
from autopvs1_link.mcp.registries import (
    KNOWN_ERROR_CODES,
    KNOWN_WARNING_CODES,
    PAYLOAD_MODES,
    capabilities_version,
)
from autopvs1_link.mcp.server_info import SERVER_NAME, SERVER_VERSION

_SCRAPE_TIER = "expensive_cold_cheap_warm"
_CHEAP_TIER = "cheap"
_DEFAULT_CACHE_TTL_SECONDS = 86_400


_TOOL_SUMMARIES: dict[str, dict[str, Any]] = {
    "get_variant_pvs1_data": {
        "purpose": (
            "Research-use PVS1 analysis for one AutoPVS1 SNV/indel ID. "
            "LLM-first: pass response_mode='summary' for the verdict."
        ),
        "example": {
            "genome_build": "hg19",
            "variant_id": "X-82763936-A-T",
            "response_mode": "summary",
        },
    },
    "get_cnv_pvs1_data": {
        "purpose": (
            "Research-use PVS1 analysis for one AutoPVS1 CNV ID. "
            "LLM-first: pass response_mode='summary' for the verdict."
        ),
        "example": {
            "genome_build": "hg19",
            "cnv_id": "17-15000000-20000000-DEL",
            "response_mode": "summary",
        },
    },
    "search_variants": {
        "purpose": (
            "Search AutoPVS1 by gene symbol, partial variant ID, or "
            "upstream-supported query. Use response_mode='ids_only' "
            "to resolve to a variant_id with minimum bytes."
        ),
        "example": {
            "query": "BRCA1",
            "genome_build": "hg38",
            "limit": 10,
            "response_mode": "ids_only",
        },
    },
    "get_server_health": {
        "purpose": (
            "Read local server health and enabled feature flags "
            "without upstream calls (sub-millisecond, no cost)."
        ),
        "example": {},
    },
    "get_variants_pvs1_data_bulk": {
        "purpose": (
            "Bulk PVS1 scoring for 1-10 SNV/indel variants in one "
            "call. Default response_mode='summary' to keep 10 "
            "verdicts inside one turn budget."
        ),
        "example": {
            "items": [
                {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
            ],
            "response_mode": "summary",
        },
    },
    "get_cnvs_pvs1_data_bulk": {
        "purpose": (
            "Bulk PVS1 scoring for 1-10 CNVs in one call. Default "
            "response_mode='summary' to keep 10 verdicts inside one "
            "turn budget."
        ),
        "example": {
            "items": [
                {"genome_build": "hg19", "cnv_id": "11-2797090-2869333-DEL"},
            ],
            "response_mode": "summary",
        },
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
            name: ToolSummaryMCP(purpose=data["purpose"], example=data["example"])
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
        },
        "payload_modes": {
            mode: {"char_budget": spec["char_budget"], "note": spec["note"]}
            for mode, spec in PAYLOAD_MODES.items()
        },
        "bulk_behavior": {
            "max_items": 10,
            "execution": "sequential",
            "respects_upstream_rate_limit": True,
            "upstream_rate_limit_seconds": 1.0,
            "worst_case_latency_seconds": 10,
            "continue_on_error_default": True,
            "ordering": "preserves input order",
            "per_item_envelope": {
                "ok": "bool",
                "input": "object",
                "data": "object|null",
                "error": "object|null",
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
        },
        "cache_statistics": {
            "resource": "autopvs1-link://cache/statistics",
            "semantics": ("Method-keyed counters with stable keys and cache key shapes."),
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
    }
