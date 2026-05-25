"""MCP tool: get_variant_pvs1_data."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import GenomeBuild
from autopvs1_link.models.autopvs1_models import AutoPVS1Data


def register(mcp: FastMCP) -> None:
    """Register the get_variant_pvs1_data tool."""

    @mcp.tool(
        name="get_variant_pvs1_data",
        title="Get Variant PVS1 Data",
        output_schema=AutoPVS1Data.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def get_variant_pvs1_data(
        genome_build: Annotated[GenomeBuild, Field(description="Genome build: hg19 or hg38.")],
        variant_id: Annotated[
            str,
            Field(min_length=1, description="Variant identifier, for example X-82763936-A-T."),
        ],
    ) -> dict[str, Any]:
        """Use this to score one SNV/indel variant with AutoPVS1 PVS1 rules."""
        result = await service_adapters.get_variant(genome_build, variant_id)
        if hasattr(result, "model_dump"):
            return cast(dict[str, Any], result.model_dump(mode="json"))
        return dict(result)
