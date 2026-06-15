"""MCP tool: clear_cache (gated)."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import DESTRUCTIVE_CLOSED_WORLD
from autopvs1_link.mcp.contracts import ClearCacheData, ClearCacheMCPEnvelope
from autopvs1_link.mcp.envelope import ToolResponse, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import DestructiveOperationDisabledError

_TOOL_NAME = "clear_cache"


def destructive_tools_enabled() -> bool:
    """Return whether destructive MCP tools should be registered."""
    return os.environ.get("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false").lower() == "true"


def register(mcp: FastMCP) -> None:
    """Register the gated clear_cache tool."""
    if not destructive_tools_enabled():
        return

    @mcp.tool(
        name="clear_cache",
        title="Clear AutoPVS1-Link Cache",
        tags={"meta", "admin"},
        output_schema=ClearCacheMCPEnvelope.model_json_schema(),
        annotations=DESTRUCTIVE_CLOSED_WORLD,
    )
    async def clear_cache() -> ToolResponse:
        """Clear all service caches.

        Disabled by default. Enable with
        AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true.
        """
        try:
            await service_adapters.clear_cache()
        except DestructiveOperationDisabledError as exc:
            return error_envelope(
                code="destructive_disabled",
                message=str(exc),
                retryable=False,
                suggestions=[
                    "Set AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true only in trusted "
                    "administrative environments."
                ],
                tool_name=_TOOL_NAME,
            )
        return ok_envelope(
            ClearCacheData(
                cleared=True,
                message="All service caches and cache statistics cleared.",
            ),
            tool_name=_TOOL_NAME,
        )
