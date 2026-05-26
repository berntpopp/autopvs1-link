"""MCP resources for AutoPVS1-Link."""

from __future__ import annotations

from typing import Any, cast

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.presenters.cache import present_cache_statistics


def register(mcp: FastMCP) -> None:
    """Register read-only resources."""

    @mcp.resource("autopvs1-link://cache/statistics")
    async def cache_statistics() -> dict[str, Any]:
        """Read-only snapshot of in-memory cache statistics."""
        stats = await service_adapters.cache_statistics()
        raw = (
            cast(dict[str, Any], stats.model_dump(mode="json"))
            if hasattr(stats, "model_dump")
            else dict(stats)
        )
        return present_cache_statistics(raw).model_dump(mode="json")
