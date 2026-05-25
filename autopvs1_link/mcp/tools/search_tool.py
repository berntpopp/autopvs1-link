"""MCP tool: search_variants."""

from __future__ import annotations

from typing import Annotated, Any, cast

from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import GenomeBuild
from autopvs1_link.models.autopvs1_models import AutoPVS1SearchResults


def register(mcp: FastMCP) -> None:
    """Register the search_variants tool."""

    @mcp.tool(
        name="search_variants",
        title="Search AutoPVS1 Variants",
        output_schema=AutoPVS1SearchResults.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def search_variants(
        query: Annotated[
            str,
            Field(min_length=1, description="Gene symbol, HGVS text, or partial variant string."),
        ],
        genome_version: Annotated[
            GenomeBuild,
            Field(description="Genome build for search: hg19 or hg38."),
        ] = "hg38",
    ) -> dict[str, Any]:
        """Use this to search AutoPVS1 by gene symbol or variant text."""
        result = await service_adapters.search_variants(query, genome_version)
        if hasattr(result, "model_dump"):
            return cast(dict[str, Any], result.model_dump(mode="json"))
        return dict(result)
