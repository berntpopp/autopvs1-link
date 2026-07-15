"""Static MCP server metadata."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from autopvs1_link.mcp.annotations import READ_ONLY_CLOSED_WORLD
from autopvs1_link.mcp.envelope import ok_envelope
from autopvs1_link.mcp.presenters.capabilities import (
    detailed_capabilities_resource,
    present_compact_capabilities,
)
from autopvs1_link.mcp.server_info import (
    SERVER_DESCRIPTION,
    SERVER_NAME,
    SERVER_VERSION,
)

__all__ = [
    "SERVER_DESCRIPTION",
    "SERVER_NAME",
    "SERVER_VERSION",
    "get_capabilities",
    "register_metadata",
]


def get_capabilities() -> dict[str, Any]:
    """Return compact MCP capabilities data as a JSON-ready dict."""
    return present_compact_capabilities().model_dump(mode="json")


def register_metadata(mcp: FastMCP) -> None:
    """Register discovery tools and resources."""

    @mcp.tool(
        name="get_server_capabilities",
        title="Get AutoPVS1-Link Capabilities",
        tags={"meta", "discovery"},
        # outputSchema suppressed (Tool-Surface Budget Standard v1, Rule 3): it is
        # optional in MCP and was 88% of this server's surface. structuredContent is
        # still emitted at runtime for the dict envelope this tool returns.
        output_schema=None,
        annotations=READ_ONLY_CLOSED_WORLD,
    )
    async def get_server_capabilities() -> dict[str, Any]:
        """Use this to discover AutoPVS1-Link MCP tools, inputs, limitations, and workflow."""
        return ok_envelope(present_compact_capabilities(), tool_name="get_server_capabilities")

    @mcp.resource(
        "autopvs1-link://capabilities",
        name="capabilities",
        title="AutoPVS1-Link Capabilities Reference",
        description=(
            "Detailed MCP usage guidance: accepted formats, examples, search "
            "behavior, error envelope, stable error and warning codes, cache "
            "statistics URI, destructive-tool gating, citation, and known "
            "upstream limitations."
        ),
        mime_type="application/json",
    )
    def capabilities() -> dict[str, Any]:
        """Detailed MCP usage guidance, examples, limitations, and citation."""
        return detailed_capabilities_resource()
