"""API endpoints for CNV (Copy Number Variant) data."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path

from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData
from autopvs1_link.services.autopvs1_service import AutoPVS1Service
from autopvs1_link.services.service_manager import get_managed_service

logger = structlog.get_logger()
router = APIRouter(tags=["CNV"])

# Fixed, caller-safe error detail: never embeds the cnv_id or exception prose
# (finding F-03; parity with the variant/gene routes).
_INTERNAL_DETAIL = "Internal server error."


@router.get(
    "/cnv/{genome_build}/{cnv_id}",
    response_model=AutoPVS1CNVData,
    summary="Get PVS1 data for a specific CNV",
    description="Retrieve comprehensive PVS1 analysis data for copy number variants (CNVs) "
    "including decision path and disease mechanisms. Supports deletions and duplications "
    "with dosage sensitivity analysis.",
    responses={
        200: {"description": "Successful CNV PVS1 analysis"},
        404: {"description": "CNV not found in AutoPVS1 database"},
        500: {"description": "Internal server error"},
    },
)
async def get_cnv(
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
    cnv_id: Annotated[
        str,
        Path(
            description="CNV identifier (format: chr-start-end-type)",
            openapi_examples={
                "real_deletion": {
                    "summary": "Real CNV deletion (72kb)",
                    "description": "Working deletion CNV with actual PVS1 analysis",
                    "value": "11-2797090-2869333-DEL",
                },
            },
        ),
    ],
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1CNVData:
    """Get comprehensive PVS1 analysis data for a copy number variant (CNV).

    Args:
        genome_build: Genome build version (hg19, hg38, etc.)
        cnv_id: CNV identifier in format chr-start-end-type (e.g., 11-2797090-2869333-DEL)

    Returns:
        Complete PVS1 analysis including CNV info, flowchart, and disease mechanisms

    Raises:
        HTTPException: 404 if CNV not found, 500 for server errors
    """
    try:
        logger.info("API request for CNV", genome_build=genome_build, cnv_id=cnv_id)
        result = await service.get_cnv_data(genome_build, cnv_id)
        return result
    except Exception as e:
        # Log the exception CLASS only and return a FIXED caller-safe detail:
        # str(exc) can embed the cnv_id / upstream URL (GDPR Art. 9 / F-03).
        logger.error("error fetching CNV", error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=_INTERNAL_DETAIL) from None
