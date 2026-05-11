"""Pydantic input/output contracts for MCP tools and resources."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GenomeBuild = Literal["hg19", "hg38"]


class VariantPVS1Input(BaseModel):
    """Input for ``get_variant_pvs1_data``."""

    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    variant_id: str = Field(
        ..., min_length=1, description="Variant identifier as accepted by AutoPVS1."
    )


class CNVPVS1Input(BaseModel):
    """Input for ``get_cnv_pvs1_data``."""

    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    cnv_id: str = Field(..., min_length=1, description="CNV identifier as accepted by AutoPVS1.")


class SearchVariantsInput(BaseModel):
    """Input for ``search_variants``."""

    query: str = Field(..., min_length=1, description="Gene symbol or partial variant string.")
    genome_version: GenomeBuild = Field("hg38", description="Genome build for the search.")


class ClearCacheInput(BaseModel):
    """No fields; included for symmetry."""


class CacheStatistics(BaseModel):
    """Read-only snapshot exposed as an MCP resource."""

    hits: int = 0
    misses: int = 0
    size: int = 0
    max_size: int = 0
    ttl_seconds: int = 0
