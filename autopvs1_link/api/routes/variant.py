"""API endpoints for variant data."""

import re
from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Path

from autopvs1_link.api.rest_validation import (
    RestInputError,
    validate_genome_build,
    validate_variant_id,
)
from autopvs1_link.models.autopvs1_models import AutoPVS1Data
from autopvs1_link.services.autopvs1_service import AutoPVS1Service
from autopvs1_link.services.service_manager import get_managed_service

logger = structlog.get_logger()
router = APIRouter(tags=["Variant"])

# Fixed, caller-safe error details. None embeds a caller-supplied identifier or
# raw exception/upstream prose (finding F-03).
_UNRESOLVED_DETAIL = "Variant identifier could not be resolved."
_NOT_FOUND_DETAIL = "Variant not found."
_UPSTREAM_DETAIL = "Upstream service returned an error."
_INTERNAL_DETAIL = "Internal server error."

# HGVS notation patterns for detection (transcript-level only)
HGVS_PATTERNS = [
    r"^NM_\d+\.\d+:c\.",  # NM_000128.3:c.1716+1G>A
    r"^NR_\d+\.\d+:n\.",  # Non-coding RNA transcripts
    r"^g\.\d+",  # g.123A>T (genomic)
    r"^m\.\d+",  # m.123A>T (mitochondrial)
]


def _detect_hgvs_pattern(query: str) -> bool:
    """Detect if query looks like HGVS notation."""
    query = query.strip()
    return any(re.match(pattern, query, re.IGNORECASE) for pattern in HGVS_PATTERNS)


@router.get(
    "/variant/{genome_build}/{variant_id}",
    response_model=AutoPVS1Data,
    summary="Get PVS1 data for a variant",
    description="Retrieve comprehensive PVS1 analysis data for a genetic variant. "
    "Intelligently handles both standard variant IDs (e.g., 'X-83508928-A-T') "
    "and HGVS notation (e.g., 'NM_000128.3:c.1716+1G>A'). "
    "Returns complete PVS1 analysis including flowchart decision path and disease mechanisms.",
    responses={
        200: {"description": "Successful PVS1 analysis"},
        404: {"description": "Variant not found in AutoPVS1 database"},
        400: {"description": "Invalid variant identifier or HGVS notation"},
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
            description="Variant identifier or HGVS notation",
            openapi_examples={
                "standard_variant": {
                    "summary": "Standard variant ID",
                    "description": "Standard format: chr-pos-ref-alt",
                    "value": "X-83508928-A-T",
                },
                "insertion_variant": {
                    "summary": "Insertion variant",
                    "description": "Insertion variant with complex alt allele",
                    "value": "2-48033984-G-GGATT",
                },
                "hgvs_transcript": {
                    "summary": "HGVS transcript notation",
                    "description": "Transcript-level HGVS notation",
                    "value": "NM_000128.3:c.1716+1G>A",
                },
                "hgvs_genomic": {
                    "summary": "HGVS genomic notation",
                    "description": "Genomic-level HGVS notation",
                    "value": "g.123456A>T",
                },
                "hgvs_mitochondrial": {
                    "summary": "HGVS mitochondrial notation",
                    "description": "Mitochondrial HGVS notation",
                    "value": "m.8993T>G",
                },
            },
        ),
    ],
    service: AutoPVS1Service = Depends(get_managed_service),
) -> AutoPVS1Data:
    """Get comprehensive PVS1 analysis data for a genetic variant.

    This endpoint intelligently handles both standard variant identifiers and HGVS notation:

    **Standard Variant IDs:**
    - Format: chr-pos-ref-alt (e.g., "X-83508928-A-T")
    - Direct lookup in AutoPVS1 database

    **HGVS Notation (automatically detected):**
    - Transcript-level: "NM_000128.3:c.1716+1G>A"
    - Non-coding RNA: "NR_123456.2:n.456C>G"
    - Genomic: "g.123A>T"
    - Mitochondrial: "m.8993T>G"
    - Resolves to specific variant through AutoPVS1's redirect system

    Args:
        genome_build: Genome build version (hg19, hg38, etc.)
        variant_id: Variant identifier (standard format) or HGVS notation

    Returns:
        Complete PVS1 analysis including variant info, flowchart, and disease mechanisms

    Raises:
        HTTPException: 400 for invalid format, 404 if not found, 500 for server errors
    """
    # Bound + validate BEFORE any I/O, logging, or cache use. Reject
    # oversize/hostile identifiers with a FIXED caller-safe message.
    try:
        genome_build = validate_genome_build(genome_build)
        variant_id = validate_variant_id(variant_id)
    except RestInputError as exc:
        logger.warning("variant request rejected", error_code=exc.code)
        raise HTTPException(status_code=400, detail=exc.message) from None

    try:
        is_hgvs = _detect_hgvs_pattern(variant_id)

        logger.info("API request for variant", genome_build=genome_build, is_hgvs=is_hgvs)

        if is_hgvs:
            # Handle HGVS notation - resolve through enhanced search
            logger.debug("Resolving HGVS notation")
            result = await service.resolve_hgvs_notation(variant_id, genome_build)

            logger.info(
                "HGVS resolved successfully",
                genome_build=genome_build,
                final_strength=result.pvs1_flowchart.final_strength,
            )
        else:
            # Handle standard variant ID
            logger.debug("Looking up standard variant")
            result = await service.get_variant_data(genome_build, variant_id)

        return result

    except ValueError as e:
        # HGVS resolution failed or otherwise unresolvable: log class only.
        logger.warning("variant resolution failed", error_type=type(e).__name__)
        raise HTTPException(status_code=400, detail=_UNRESOLVED_DETAIL) from None
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        logger.error(
            "upstream error fetching variant",
            error_type=type(e).__name__,
            status_code=status_code,
        )
        if status_code == 404:
            raise HTTPException(status_code=404, detail=_NOT_FOUND_DETAIL) from None
        raise HTTPException(status_code=502, detail=_UPSTREAM_DETAIL) from None
    except Exception as e:
        logger.error("error fetching variant", error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=_INTERNAL_DETAIL) from None
