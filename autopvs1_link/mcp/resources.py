"""MCP resources for AutoPVS1-Link."""

from __future__ import annotations

from typing import Any, cast

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters


def register(mcp: FastMCP) -> None:
    """Register read-only resources."""

    @mcp.resource("autopvs1-link://cache/statistics")
    async def cache_statistics() -> dict[str, Any]:
        """Read-only snapshot of in-memory cache statistics."""
        stats = await service_adapters.cache_statistics()
        if hasattr(stats, "model_dump"):
            return cast(dict[str, Any], stats.model_dump(mode="json"))
        return dict(stats)
