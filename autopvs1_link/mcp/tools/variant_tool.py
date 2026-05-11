"""MCP tool: get_variant_pvs1_data."""

from __future__ import annotations

from typing import Any, cast

from fastmcp import FastMCP

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import VariantPVS1Input


def register(mcp: FastMCP) -> None:
    """Register the get_variant_pvs1_data tool."""

    @mcp.tool(name="get_variant_pvs1_data")
    async def get_variant_pvs1_data(payload: VariantPVS1Input) -> dict[str, Any]:
        """Return the AutoPVS1 PVS1 analysis for a single variant."""
        result = await service_adapters.get_variant(payload.genome_build, payload.variant_id)
        if hasattr(result, "model_dump"):
            return cast(dict[str, Any], result.model_dump(mode="json"))
        return dict(result)
