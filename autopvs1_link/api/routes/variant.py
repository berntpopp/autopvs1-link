"""API endpoints for variant data."""

from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from autopvs1_link.models.autopvs1_models import AutoPVS1Data, AutoPVS1SearchResults
from autopvs1_link.services.autopvs1_service import AutoPVS1Service
from autopvs1_link.services.service_manager import get_managed_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["Variant"])


@router.get(
    "/variant/{genome_build}/{variant_id}",
    response_model=AutoPVS1Data,
    summary="Get PVS1 data for a specific variant",
    description="Retrieve comprehensive PVS1 analysis data for a genetic variant "
    "including flowchart decision path and disease mechanisms.",
    responses={
        200: {"description": "Successful PVS1 analysis"},
        404: {"description": "Variant not found in AutoPVS1 database"},
        500: {"description": "Internal server error"},
    },
)
async def get_variant(
    genome_build: Annotated[
        str,
        Path(
            description="Genome build version",
            openapi_examples={
                "hg19": {
                    "summary": "GRCh37/hg19",
                    "description": "Human genome build 19 (GRCh37)",
                    "value": "hg19",
                },
                "hg38": {
                    "summary": "GRCh38/hg38",
                    "description": "Human genome build 38 (GRCh38)",
                    "value": "hg38",
                },
            },
        ),
    ],
    variant_id: Annotated[
        str,
        Path(
            description="Variant identifier (format: chr-pos-ref-alt)",
            openapi_examples={
                "real_nonsense": {
                    "summary": "Real nonsense variant",
                    "description": "Working nonsense variant with PVS1 analysis",
                    "value": "X-82763936-A-T",
                },
                "real_insertion": {
                    "summary": "Real insertion variant",
                    "description": "Working insertion variant with PVS1 data",
                    "value": "2-48033984-G-GGATT",
                },
            },
        ),
    ],
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1Data:
    """Get comprehensive PVS1 analysis data for a genetic variant.

    Args:
        genome_build: Genome build version (hg19, hg38, etc.)
        variant_id: Variant identifier in format chr-pos-ref-alt (e.g., X-83508928-A-T)

    Returns:
        Complete PVS1 analysis including variant info, flowchart, and disease mechanisms

    Raises:
        HTTPException: 404 if variant not found, 500 for server errors
    """
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
    summary="Search for variants by gene symbol",
    description="Search for genetic variants by gene symbol. Supports multiple genome versions.",
    responses={
        200: {"description": "Search results with matching variants"},
        400: {"description": "Invalid search query format"},
        500: {"description": "Internal server error"},
    },
)
async def search_variants(
    q: Annotated[
        str,
        Query(
            description="Search query: gene symbol",
            openapi_examples={
                "gene_symbol": {
                    "summary": "Search by gene symbol",
                    "description": "Find variants in a specific gene using its symbol",
                    "value": "MYH9",
                },
                "brca1_gene": {
                    "summary": "BRCA1 gene variants",
                    "description": "Find all variants in the BRCA1 gene",
                    "value": "BRCA1",
                },
            },
        ),
    ],
    genome_version: Annotated[
        str,
        Query(
            description="Genome version to search",
            openapi_examples={
                "hg19": {
                    "summary": "GRCh37/hg19 (Default)",
                    "description": "Human genome build 19 (GRCh37)",
                    "value": "hg19",
                },
                "hg38": {
                    "summary": "GRCh38/hg38",
                    "description": "Human genome build 38 (GRCh38)",
                    "value": "hg38",
                },
            },
        ),
    ] = "hg19",
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1SearchResults:
    """Search for genetic variants by gene symbol.

    Args:
        q: Search query (gene symbol like 'MYH9' or 'BRCA1')
        genome_version: Genome version to search (default: hg19)

    Returns:
        Search results containing matching variants with basic information

    Raises:
        HTTPException: 400 for invalid query format, 500 for server errors
    """
    try:
        logger.info("API search request", query=q, genome_version=genome_version)
        result = await service.search_variants(q, genome_version)
        return result
    except Exception as e:
        logger.error("Error searching variants", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
