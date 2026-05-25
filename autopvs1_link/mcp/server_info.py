"""Shared MCP server metadata constants."""

from __future__ import annotations

SERVER_NAME = "AutoPVS1 Link"
SERVER_VERSION = "1.0.0"
SERVER_DESCRIPTION = (
    "AutoPVS1-Link exposes research-use PVS1 variant classification tools. "
    "Use get_variant_pvs1_data for SNV/indel IDs like X-82763936-A-T after "
    "choosing genome_build hg19 or hg38. Use search_variants for gene or "
    "partial variant lookup, get_cnv_pvs1_data for CNVs, and "
    "get_server_capabilities when discovering the MCP surface. Results are "
    "research-use data, not clinical decision support."
)
