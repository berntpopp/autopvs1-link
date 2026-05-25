"""Pydantic input/output contracts for MCP tools and resources."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from autopvs1_link.mcp.envelope import MCPEnvelope

GenomeBuild = Literal["hg19", "hg38"]


class VariantPVS1Input(BaseModel):
    """Input for ``get_variant_pvs1_data``."""

    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    variant_id: str = Field(
        ..., min_length=1, description="AutoPVS1 variant ID, for example X-82763936-A-T."
    )


class CNVPVS1Input(BaseModel):
    """Input for ``get_cnv_pvs1_data``."""

    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    cnv_id: str = Field(
        ...,
        min_length=1,
        description="AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form.",
    )


class ClearCacheInput(BaseModel):
    """Empty input accepted by ``clear_cache``."""


class VariantMCPData(BaseModel):
    """MCP-presented variant data."""

    genome_build: str
    variant_info: dict[str, Any]
    pvs1_flowchart: dict[str, Any]
    disease_mechanisms: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"


class CNVMCPData(BaseModel):
    """MCP-presented CNV data."""

    genome_build: str
    cnv_info: dict[str, Any]
    pvs1_flowchart: dict[str, Any]
    disease_mechanisms: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"


class SearchMCPData(BaseModel):
    """MCP-presented search page."""

    query: str
    genome_build: str
    total_count: int
    returned_count: int
    next_cursor: str | None
    ordering: Literal["upstream"] = "upstream"
    results: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CompactCapabilitiesData(BaseModel):
    """Compact first-turn MCP capabilities payload."""

    server: str
    version: str
    transport: str
    endpoint: str
    research_use_only: bool
    tool_summaries: dict[str, str]
    canonical_parameters: dict[str, list[str]]
    compact_workflow: list[str]
    details_resource: str


class ClearCacheData(BaseModel):
    """Clear-cache result data."""

    cleared: bool
    message: str


class CacheStatBlock(BaseModel):
    """One cache-stat method block."""

    hits: int = 0
    misses: int = 0
    errors: int = 0
    evictions: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    average_time_ms: float = 0.0
    last_hit: float | None = None
    last_miss: float | None = None
    uptime_seconds: float = 0.0
    cache_key_shape: str
    description: str


class CacheStatisticsResource(BaseModel):
    """Read-only method-keyed cache statistics resource."""

    statistics: dict[str, CacheStatBlock]


class VariantMCPEnvelope(MCPEnvelope[VariantMCPData]):
    """Envelope schema for ``get_variant_pvs1_data``."""


class CNVMCPEnvelope(MCPEnvelope[CNVMCPData]):
    """Envelope schema for ``get_cnv_pvs1_data``."""


class SearchMCPEnvelope(MCPEnvelope[SearchMCPData]):
    """Envelope schema for ``search_variants``."""


class CompactCapabilitiesMCPEnvelope(MCPEnvelope[CompactCapabilitiesData]):
    """Envelope schema for ``get_server_capabilities``."""


class ClearCacheMCPEnvelope(MCPEnvelope[ClearCacheData]):
    """Envelope schema for ``clear_cache``."""
