"""Validation and identifier helpers for AutoPVS1 requests."""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger()

GenomeBuild = str

HGVS_PATTERNS = [
    r"^NM_\d+\.\d+:c\.",  # NM_000128.3:c.1716+1G>A
    r"^NR_\d+\.\d+:n\.",  # Non-coding RNA transcripts
    r"^g\.\d+",  # g.123A>T (genomic)
    r"^m\.\d+",  # m.123A>T (mitochondrial)
]


def validate_genome_build(genome_build: str) -> GenomeBuild:
    """Validate and return an AutoPVS1 genome build."""
    value = genome_build.strip()
    if value not in {"hg19", "hg38"}:
        raise ValueError("Genome build must be 'hg19' or 'hg38'")
    return value


def validate_variant_id(variant_id: str) -> str:
    """Validate and return an AutoPVS1 variant identifier."""
    value = variant_id.strip()
    if not value:
        raise ValueError("Variant identifier must not be empty")
    return value


def validate_cnv_id(cnv_id: str) -> str:
    """Validate and return an AutoPVS1 CNV identifier."""
    value = cnv_id.strip()
    if not value:
        raise ValueError("CNV identifier must not be empty")
    return value


def validate_search_query(query: str) -> str:
    """Validate and return a search query."""
    value = query.strip()
    if not value:
        raise ValueError("Search query must not be empty")
    return value


def detect_hgvs_pattern(query: str) -> bool:
    """Return true when the query looks like HGVS notation."""
    value = query.strip()
    for pattern in HGVS_PATTERNS:
        if re.match(pattern, value, re.IGNORECASE):
            logger.debug("HGVS pattern detected", query=query, pattern=pattern)
            return True

    logger.debug("No HGVS pattern detected", query=query)
    return False


def extract_variant_from_redirect_url(url: str) -> tuple[str | None, str | None]:
    """Extract genome build and variant id from an AutoPVS1 variant URL."""
    match = re.search(r"/variant/([^/]+)/([^/?]+)", url)
    if match:
        genome_build, variant_id = match.groups()
        logger.debug(
            "Extracted variant info from URL",
            url=url,
            genome_build=genome_build,
            variant_id=variant_id,
        )
        return genome_build, variant_id

    logger.warning("Failed to extract variant info from URL", url=url)
    return None, None
