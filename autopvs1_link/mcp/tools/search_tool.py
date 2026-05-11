"""MCP tool: search_variants."""

from __future__ import annotations

from typing import Any, cast

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import SearchVariantsInput


def register(mcp: FastMCP) -> None:
    """Register the search_variants tool."""

    @mcp.tool(name="search_variants")
    async def search_variants(payload: SearchVariantsInput) -> dict[str, Any]:
        """Search AutoPVS1 for variants matching the query."""
        result = await service_adapters.search_variants(payload.query, payload.genome_version)
        if hasattr(result, "model_dump"):
            return cast(dict[str, Any], result.model_dump(mode="json"))
        return dict(result)
