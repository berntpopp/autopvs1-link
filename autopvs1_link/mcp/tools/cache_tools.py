"""MCP tool: clear_cache (gated)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import DESTRUCTIVE_CLOSED_WORLD
from autopvs1_link.mcp.contracts import ClearCacheInput


def register(mcp: FastMCP) -> None:
    """Register the gated clear_cache tool."""

    @mcp.tool(
        name="clear_cache",
        title="Clear AutoPVS1-Link Cache",
        annotations=DESTRUCTIVE_CLOSED_WORLD,
    )
    async def clear_cache(_: ClearCacheInput | None = None) -> dict[str, Any]:
        """Clear all service caches.

        Disabled by default. Enable with
        AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true.
        """
        return await service_adapters.clear_cache()
