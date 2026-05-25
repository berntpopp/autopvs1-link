"""Static MCP server metadata."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel

from autopvs1_link.mcp.annotations import READ_ONLY_CLOSED_WORLD

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


class ServerCapabilitiesResponse(BaseModel):
    """Response schema for AutoPVS1-Link capability discovery."""

    server: str
    version: str
    transport: str
    endpoint: str
    research_use_only: bool
    tools: dict[str, str]
    resources: list[str]
    typical_workflow: list[str]


def get_capabilities() -> dict[str, Any]:
    """Return a compact description of the MCP surface."""
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "transport": "streamable-http",
        "endpoint": "/mcp/",
        "research_use_only": True,
        "tools": {
            "get_variant_pvs1_data": (
                "Score one SNV/indel variant ID with genome_build hg19 or hg38."
            ),
            "search_variants": "Search AutoPVS1 by gene symbol or variant text.",
            "get_cnv_pvs1_data": "Score one CNV identifier with genome_build hg19 or hg38.",
            "clear_cache": "Opt-in destructive cache clear; disabled by default.",
        },
        "resources": [
            "autopvs1-link://capabilities",
            "autopvs1-link://cache/statistics",
        ],
        "typical_workflow": [
            "If genome build is unknown, ask for hg19 or hg38.",
            "Call get_variant_pvs1_data with genome_build and variant_id.",
            "Report final_strength and key parsed evidence as research-use data only.",
        ],
    }


def register_metadata(mcp: FastMCP) -> None:
    """Register discovery tools and resources."""

    @mcp.tool(
        name="get_server_capabilities",
        title="Get AutoPVS1-Link Capabilities",
        output_schema=ServerCapabilitiesResponse.model_json_schema(),
        annotations=READ_ONLY_CLOSED_WORLD,
    )
    async def get_server_capabilities() -> dict[str, Any]:
        """Use this to discover AutoPVS1-Link MCP tools, inputs, limitations, and workflow."""
        return get_capabilities()

    @mcp.resource("autopvs1-link://capabilities")
    def capabilities() -> dict[str, Any]:
        return get_capabilities()
