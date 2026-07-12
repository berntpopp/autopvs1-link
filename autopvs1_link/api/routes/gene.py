"""API endpoints for gene-related operations."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from autopvs1_link.api.rest_validation import (
    RestInputError,
    validate_gene_query,
    validate_genome_build,
)
from autopvs1_link.models.autopvs1_models import AutoPVS1SearchResults
from autopvs1_link.services.autopvs1_service import AutoPVS1Service
from autopvs1_link.services.service_manager import get_managed_service

logger = structlog.get_logger()
router = APIRouter(tags=["Gene"])

# Fixed, caller-safe error detail (finding F-03).
_INTERNAL_DETAIL = "Internal server error."


@router.get(
    "/gene/search",
    response_model=AutoPVS1SearchResults,
    summary="Search for variants by gene symbol",
    description="Search for genetic variants associated with a specific gene. "
    "Returns a list of variants found in the AutoPVS1 database for the given gene symbol.",
    responses={
        200: {"description": "Search results with matching variants"},
        400: {"description": "Invalid search query format"},
        500: {"description": "Internal server error"},
    },
)
async def search_gene_variants(
    q: Annotated[
        str,
        Query(
            description="Gene symbol to search for",
            openapi_examples={
                "myh9_gene": {
                    "summary": "MYH9 gene variants",
                    "description": "Find variants in the MYH9 gene",
                    "value": "MYH9",
                },
                "brca1_gene": {
                    "summary": "BRCA1 gene variants",
                    "description": "Find variants in the BRCA1 gene",
                    "value": "BRCA1",
                },
                "pou3f4_gene": {
                    "summary": "POU3F4 gene variants",
                    "description": "Find variants in the POU3F4 gene",
                    "value": "POU3F4",
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

    This endpoint searches the AutoPVS1 database for variants associated with
    a specific gene symbol. It returns basic information about each variant
    found, which can then be used with the variant endpoint for detailed analysis.

    Args:
        q: Gene symbol to search for (e.g., 'MYH9', 'BRCA1', 'POU3F4')
        genome_version: Genome version to search (default: hg19)

    Returns:
        Search results containing matching variants with basic information including:
        - Variant IDs that can be used with /variant/{genome_build}/{variant_id}
        - Gene symbol and variant type
        - Genome build information
        - Direct links to variant pages

    Raises:
        HTTPException: 400 for invalid query format, 500 for server errors
    """
    # Bound + validate BEFORE any I/O, logging, or cache use.
    try:
        genome_version = validate_genome_build(genome_version)
        q = validate_gene_query(q)
    except RestInputError as exc:
        logger.warning("gene search rejected", error_code=exc.code)
        raise HTTPException(status_code=400, detail=exc.message) from None

    try:
        logger.info("gene search request", genome_version=genome_version)
        result = await service.search_variants(q, genome_version)

        logger.info(
            "gene search completed",
            genome_version=genome_version,
            result_count=len(result.results),
        )

        return result
    except Exception as e:
        logger.error("error searching gene variants", error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=_INTERNAL_DETAIL) from None
