"""MCP capabilities presenters."""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.contracts import CompactCapabilitiesData, ToolSummaryMCP, WorkflowStepMCP
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
            "get_variant_pvs1_data": ToolSummaryMCP(
                purpose="research-use PVS1 analysis for one AutoPVS1 SNV/indel ID.",
                example={
                    "genome_build": "hg19",
                    "variant_id": "X-82763936-A-T",
                },
            ),
            "get_cnv_pvs1_data": ToolSummaryMCP(
                purpose="research-use PVS1 analysis for one AutoPVS1 CNV ID.",
                example={
                    "genome_build": "hg19",
                    "cnv_id": "17-15000000-20000000-DEL",
                },
            ),
            "search_variants": ToolSummaryMCP(
                purpose=(
                    "Search AutoPVS1 by gene symbol, partial variant ID, or "
                    "upstream-supported query."
                ),
                example={
                    "query": "BRCA1",
                    "genome_build": "hg38",
                    "limit": 10,
                    "cursor": None,
                },
            ),
            "clear_cache": ToolSummaryMCP(
                purpose="Opt-in destructive cache clear; disabled unless explicitly enabled.",
                example={},
            ),
        },
        canonical_parameters={
            "get_variant_pvs1_data": ["genome_build", "variant_id"],
            "get_cnv_pvs1_data": ["genome_build", "cnv_id"],
            "search_variants": ["query", "genome_build", "limit", "cursor"],
            "clear_cache": [],
        },
        compact_workflow=[
            WorkflowStepMCP(
                step="Confirm genome build",
                when="The source coordinate build is unknown or absent.",
            ),
            WorkflowStepMCP(
                step="Search for an AutoPVS1 ID",
                when=(
                    "The caller has a gene symbol, partial variant ID, or upstream-supported query."
                ),
            ),
            WorkflowStepMCP(
                step="Score one variant or CNV",
                when="The caller has a normalized AutoPVS1 variant_id or cnv_id.",
            ),
            WorkflowStepMCP(
                step="Report research-use output",
                when="Summarizing any AutoPVS1 result for a user.",
            ),
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
