"""API endpoints for CNV data."""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData
from autopvs1_link.services.autopvs1_service import AutoPVS1Service

logger = structlog.get_logger()
router = APIRouter(prefix="/cnv", tags=["CNV"])


def get_client() -> AutoPVS1Client:
    """Dependency for AutoPVS1Client."""
    return AutoPVS1Client()


def get_service(client: AutoPVS1Client = Depends(get_client)) -> AutoPVS1Service:
    """Dependency for AutoPVS1Service."""
    return AutoPVS1Service(client)


@router.get(
    "/{genome_build}/{cnv_id}",
    response_model=AutoPVS1CNVData,
    summary="Get PVS1 data for a specific CNV",
    description="Retrieve comprehensive PVS1 analysis data for a copy number variant including decision path and disease mechanisms.",
)
async def get_cnv(
    genome_build: str,
    cnv_id: str,
    service: AutoPVS1Service = Depends(get_service),
) -> AutoPVS1CNVData:
    """Get CNV PVS1 data."""
    try:
        logger.info("API request for CNV", genome_build=genome_build, cnv_id=cnv_id)
        result = await service.get_cnv_data(genome_build, cnv_id)
        return result
    except Exception as e:
        logger.error("Error fetching CNV", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
