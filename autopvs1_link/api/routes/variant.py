"""API endpoints for variant data."""

from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from autopvs1_link.models.autopvs1_models import AutoPVS1Data, AutoPVS1SearchResults, EnhancedSearchResults
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


@router.get(
    "/search/enhanced",
    response_model=EnhancedSearchResults,
    summary="Enhanced search with automatic redirect detection",
    description="Intelligent search that handles both HGVS notation and gene symbols. "
    "HGVS notation queries automatically redirect to specific variant pages, "
    "while gene symbols return search results with multiple variants.",
    responses={
        200: {"description": "Enhanced search results with redirect information"},
        400: {"description": "Invalid search query format"},
        500: {"description": "Internal server error"},
    },
)
async def search_variants_enhanced(
    q: Annotated[
        str,
        Query(
            description="Search query: HGVS notation or gene symbol",
            openapi_examples={
                "hgvs_notation": {
                    "summary": "HGVS notation (redirects to variant)",
                    "description": "Searches with HGVS notation automatically redirect to specific variants",
                    "value": "NM_000128.3:c.1716+1G>A",
                },
                "gene_symbol": {
                    "summary": "Gene symbol (returns search results)",
                    "description": "Gene symbols return multiple variant search results",
                    "value": "BRCA1",
                },
                "protein_notation": {
                    "summary": "Protein-level HGVS",
                    "description": "Protein-level notation may also redirect to variants",
                    "value": "p.Arg123Ter",
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
) -> EnhancedSearchResults:
    """Enhanced search with automatic redirect detection.
    
    This endpoint provides intelligent search functionality that mimics AutoPVS1's behavior:
    
    **HGVS Notation Queries:**
    - Automatically detected and redirected to specific variant pages
    - Returns `EnhancedSearchResults` with `redirected=True` and `variant_data` populated
    - Includes redirect metadata for transparency
    
    **Gene Symbol Queries:**
    - Returns search results with multiple variants
    - Returns `EnhancedSearchResults` with `redirected=False` and `search_results` populated
    
    **Supported HGVS Formats:**
    - `NM_000128.3:c.1716+1G>A` (transcript-level)
    - `c.123A>T` (coding sequence)
    - `p.Arg123Ter` (protein-level)
    - `g.123A>T` (genomic)
    
    Args:
        q: Search query (HGVS notation or gene symbol)
        genome_version: Genome version to search (default: hg19)
        
    Returns:
        EnhancedSearchResults with either variant data (redirected) or search results
        
    Raises:
        HTTPException: 400 for invalid query format, 500 for server errors
    """
    try:
        logger.info(
            "Enhanced search request", query=q, genome_version=genome_version
        )
        result = await service.search_with_redirect_detection(q, genome_version)
        
        if result.redirected:
            logger.info(
                "Search redirected to variant",
                query=q,
                variant_id=result.redirect_info.variant_id_extracted if result.redirect_info else None,
            )
        else:
            logger.info(
                "Search returned multiple results",
                query=q,
                result_count=len(result.search_results.results) if result.search_results else 0,
            )
            
        return result
    except Exception as e:
        logger.error("Error in enhanced search", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/resolve/hgvs",
    response_model=AutoPVS1Data,
    summary="Resolve HGVS notation to variant data",
    description="Direct HGVS notation resolution endpoint. Specifically designed for "
    "converting HGVS notation to PVS1 variant analysis data.",
    responses={
        200: {"description": "Resolved variant data from HGVS notation"},
        400: {"description": "Invalid HGVS notation or resolution failed"},
        500: {"description": "Internal server error"},
    },
)
async def resolve_hgvs_notation(
    hgvs: Annotated[
        str,
        Query(
            description="HGVS notation to resolve",
            openapi_examples={
                "splice_variant": {
                    "summary": "Splice site variant",
                    "description": "Classic splice site variant with transcript notation",
                    "value": "NM_000128.3:c.1716+1G>A",
                },
                "nonsense": {
                    "summary": "Nonsense variant",
                    "description": "Stop-gain variant in protein notation",
                    "value": "p.Arg123Ter",
                },
                "frameshift": {
                    "summary": "Frameshift variant",
                    "description": "Coding sequence frameshift notation",
                    "value": "c.123delA",
                },
            },
        ),
    ],
    genome_version: Annotated[
        str,
        Query(
            description="Genome version for resolution",
        ),
    ] = "hg19",
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1Data:
    """Resolve HGVS notation directly to variant data.
    
    This endpoint is specifically designed for HGVS notation resolution.
    It expects the notation to resolve to a single variant and returns
    the complete PVS1 analysis.
    
    **Supported HGVS Formats:**
    - **Transcript-level:** `NM_000128.3:c.1716+1G>A`
    - **Coding sequence:** `c.123A>T`, `c.123delA`, `c.123_124insG`
    - **Protein-level:** `p.Arg123Ter`, `p.Val234Met`
    - **Genomic:** `g.123A>T`
    
    Args:
        hgvs: HGVS notation to resolve
        genome_version: Genome version for resolution (default: hg19)
        
    Returns:
        Complete AutoPVS1Data for the resolved variant
        
    Raises:
        HTTPException: 400 if HGVS doesn't resolve to single variant, 500 for server errors
    """
    try:
        logger.info("HGVS resolution request", hgvs=hgvs, genome_version=genome_version)
        result = await service.resolve_hgvs_notation(hgvs, genome_version)
        
        logger.info(
            "HGVS resolved successfully",
            hgvs=hgvs,
            resolved_variant=result.variant_info.variant_id,
            gene=result.variant_info.gene_symbol,
            final_strength=result.pvs1_flowchart.final_strength,
        )
        
        return result
    except ValueError as e:
        logger.warning("HGVS resolution failed", hgvs=hgvs, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error resolving HGVS notation", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
