"""MCP capabilities presenters."""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.contracts import CompactCapabilitiesData
from autopvs1_link.mcp.server_info import SERVER_NAME, SERVER_VERSION


def present_compact_capabilities() -> CompactCapabilitiesData:
    """Return compact capabilities optimized for first-turn tool selection."""
    return CompactCapabilitiesData(
        server=SERVER_NAME,
        version=SERVER_VERSION,
        transport="streamable-http",
        endpoint="/mcp/",
        research_use_only=True,
        tool_summaries={
            "get_variant_pvs1_data": ("research-use PVS1 analysis for one AutoPVS1 SNV/indel ID."),
            "get_cnv_pvs1_data": "research-use PVS1 analysis for one AutoPVS1 CNV ID.",
            "search_variants": (
                "Search AutoPVS1 by gene symbol, partial variant ID, or upstream-supported query."
            ),
            "clear_cache": ("Opt-in destructive cache clear; disabled unless explicitly enabled."),
        },
        canonical_parameters={
            "get_variant_pvs1_data": ["genome_build", "variant_id"],
            "get_cnv_pvs1_data": ["genome_build", "cnv_id"],
            "search_variants": ["query", "genome_build", "limit", "cursor"],
            "clear_cache": [],
        },
        compact_workflow=[
            "Ask for hg19 or hg38 if the source coordinate build is unknown.",
            "Use search_variants only when the AutoPVS1 variant or CNV ID is unknown.",
            "Use get_variant_pvs1_data or get_cnv_pvs1_data for scoring.",
            "Report outputs as research-use AutoPVS1 data, not clinical decision support.",
        ],
        details_resource="autopvs1-link://capabilities",
    )


def detailed_capabilities_resource() -> dict[str, Any]:
    """Return the full application-controlled capabilities reference resource."""
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
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
        },
        "search_behavior": {
            "ordering": "upstream",
            "limit_default": 10,
            "limit_min": 1,
            "limit_max": 50,
            "cursor": "Opaque integer-offset string returned as next_cursor.",
            "deprecated_alias": ("genome_version is accepted for one release; use genome_build."),
        },
        "error_envelope": {
            "required_fields": ["ok", "data", "error", "meta"],
            "stable_error_codes": [
                "invalid_genome_build",
                "invalid_variant_id",
                "invalid_cnv_id",
                "invalid_search_query",
                "not_found",
                "upstream_unavailable",
                "upstream_timeout",
                "parse_error",
                "destructive_disabled",
                "internal_error",
            ],
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
    }
