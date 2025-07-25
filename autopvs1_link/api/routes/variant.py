"""API endpoints for variant data."""

from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from autopvs1_link.models.autopvs1_models import AutoPVS1Data, AutoPVS1SearchResults
from autopvs1_link.services.autopvs1_service import AutoPVS1Service
from autopvs1_link.services.service_manager import get_managed_service

logger = structlog.get_logger()
router = APIRouter(prefix="/variant", tags=["Variant"])


@router.get(
    "/{genome_build}/{variant_id}",
    response_model=AutoPVS1Data,
    summary="Get PVS1 data for a specific variant",
    description="Retrieve comprehensive PVS1 analysis data for a genetic variant including flowchart decision path and disease mechanisms.",
)
async def get_variant(
    genome_build: str,
    variant_id: str,
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1Data:
    """Get variant PVS1 data."""
    try:
        logger.info(
            "API request for variant", genome_build=genome_build, variant_id=variant_id
        )
        result = await service.get_variant_data(genome_build, variant_id)
        return result
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error fetching variant",
            error=str(e),
            status_code=e.response.status_code,
        )
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404, detail=f"Variant {variant_id} not found"
            )
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error("Error fetching variant", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/search",
    response_model=AutoPVS1SearchResults,
    summary="Search for variants",
    description="Search for variants by gene symbol or other criteria.",
)
async def search_variants(
    q: Annotated[str, Query(description="Search query (e.g., gene symbol)")],
    genome_version: Annotated[str, Query(description="Genome version")] = "hg19",
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1SearchResults:
    """Search for variants."""
    try:
        logger.info("API search request", query=q, genome_version=genome_version)
        result = await service.search_variants(q, genome_version)
        return result
    except Exception as e:
        logger.error("Error searching variants", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
