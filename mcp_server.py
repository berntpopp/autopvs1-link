#!/usr/bin/env python
"""MCP server for AutoPVS1 Link using FastMCP."""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastmcp import FastMCP

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.logging_config import configure_logging
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
)
from autopvs1_link.services.autopvs1_service import AutoPVS1Service

configure_logging()
logger = structlog.get_logger()

# Create MCP server
mcp = FastMCP("AutoPVS1 Link")

@asynccontextmanager
async def get_service():
    """Get managed service instance."""
    from autopvs1_link.services.service_manager import get_managed_service
    service = await get_managed_service()
    try:
        yield service
    finally:
        # Service is managed by the singleton, no cleanup needed
        pass


@mcp.tool()
async def get_variant_pvs1_data(
    genome_build: str,
    variant_id: str,
) -> AutoPVS1Data:
    """Get PVS1 analysis data for a genetic variant.

    Args:
        genome_build: The genome build (e.g., 'hg19', 'hg38')
        variant_id: The variant identifier (e.g., 'X-83508928-A-T')

    Returns:
        Complete PVS1 analysis including flowchart and disease mechanisms
    """
    async with get_service() as service:
        logger.info(
            "MCP tool: get_variant_pvs1_data",
            genome_build=genome_build,
            variant_id=variant_id,
        )
        return await service.get_variant_data(genome_build, variant_id)


@mcp.tool()
async def search_variants(
    query: str,
    genome_version: str = "hg19",
) -> AutoPVS1SearchResults:
    """Search for variants by gene symbol or other criteria.

    Args:
        query: Search query (e.g., gene symbol like 'MYH9')
        genome_version: Genome version to search in (default: 'hg19')

    Returns:
        Search results with variant information
    """
    async with get_service() as service:
        logger.info(
            "MCP tool: search_variants", query=query, genome_version=genome_version
        )
        return await service.search_variants(query, genome_version)


@mcp.tool()
async def get_cnv_pvs1_data(
    genome_build: str,
    cnv_id: str,
) -> AutoPVS1CNVData:
    """Get PVS1 analysis data for a copy number variant (CNV).

    Args:
        genome_build: The genome build (e.g., 'hg19', 'hg38')
        cnv_id: The CNV identifier (e.g., '11-2797090-2869333-DEL')

    Returns:
        Complete PVS1 analysis for CNV including flowchart and disease mechanisms
    """
    async with get_service() as service:
        logger.info(
            "MCP tool: get_cnv_pvs1_data", genome_build=genome_build, cnv_id=cnv_id
        )
        return await service.get_cnv_data(genome_build, cnv_id)


@mcp.tool()
async def get_cache_statistics() -> dict:
    """Get cache statistics for all services.

    Returns:
        Dictionary with cache hit/miss statistics
    """
    async with get_service() as service:
        logger.info("MCP tool: get_cache_statistics")
        return await service.get_cache_info()


@mcp.tool()
async def clear_cache() -> dict:
    """Clear all service caches.

    Returns:
        Confirmation message
    """
    async with get_service() as service:
        logger.info("MCP tool: clear_cache")
        await service.clear_cache()
        return {"message": "All caches cleared successfully"}


async def main():
    """Run the MCP server."""
    logger.info("Starting AutoPVS1 Link MCP server")
    await mcp.run(transport="stdio")


if __name__ == "__main__":
    asyncio.run(main())
