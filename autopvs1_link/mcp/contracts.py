"""Pydantic input/output contracts for MCP tools and resources."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from autopvs1_link.mcp.envelope import MCPEnvelope

GenomeBuild = Literal["hg19", "hg38"]
ExampleValue = str | int | None


class MCPContractModel(BaseModel):
    """Base model for typed MCP payload fragments."""

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


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


class VariantInfoMCP(MCPContractModel):
    """Typed variant information exposed through MCP."""

    variant_id: str
    variant_type: str
    gene_symbol: str
    gene_url: str | None = None
    pli_score: float | None = None
    pli_score_display: str | None = None
    haploinsufficiency: str | None = None
    haploinsufficiency_url: str | None = None
    chgvs: str | None = None
    phgvs: str | None = None
    exon: str | None = None
    intron: str | None = None
    external_links: dict[str, str | None] = Field(default_factory=dict)


class CNVInfoMCP(MCPContractModel):
    """Typed copy-number variant information exposed through MCP."""

    cnv_id: str
    cnv_type: str
    gene_symbol: str
    coordinates: str
    size: str | None = None


class FlowchartStepMCP(MCPContractModel):
    """One typed step in the PVS1 decision flowchart."""

    code: str
    description: str | None = None
    note_id: str | None = None
    note_text: str | None = None


class PVS1FlowchartMCP(MCPContractModel):
    """Typed PVS1 flowchart decision path and outcome."""

    preliminary_decision_path: str
    final_strength: str
    final_strength_source: Literal["asserted", "inferred"] = "asserted"
    decision_tree: list[FlowchartStepMCP] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)


class DiseaseMechanismMCP(MCPContractModel):
    """Typed disease mechanism row from AutoPVS1."""

    gene: str
    gene_url: str | None = None
    disease: str
    disease_url: str | None = None
    inheritance: str
    clinical_validity: str
    consideration: str
    adjusted_strength: str


class SearchResultMCP(MCPContractModel):
    """Typed AutoPVS1 search result row."""

    variant_id: str
    gene: str
    variant_type: str
    genome_build: str
    url: str


class ToolSummaryMCP(BaseModel):
    """Compact MCP tool summary for first-turn discovery."""

    purpose: str
    example: dict[str, ExampleValue] = Field(default_factory=dict)


class WorkflowStepMCP(BaseModel):
    """Compact ordered workflow guidance for first-turn discovery."""

    step: str
    when: str


class VariantMCPData(BaseModel):
    """MCP-presented variant data."""

    genome_build: str
    variant_info: VariantInfoMCP
    pvs1_flowchart: PVS1FlowchartMCP
    disease_mechanisms: list[DiseaseMechanismMCP] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"

    def __init__(
        self,
        *,
        genome_build: str,
        variant_info: VariantInfoMCP | dict[str, Any],
        pvs1_flowchart: PVS1FlowchartMCP | dict[str, Any],
        disease_mechanisms: Sequence[DiseaseMechanismMCP | dict[str, Any]] | None = None,
        source_url: str | None = None,
        upstream_service: str = "AutoPVS1",
    ) -> None:
        payload: dict[str, Any] = {
            "genome_build": genome_build,
            "variant_info": variant_info,
            "pvs1_flowchart": pvs1_flowchart,
            "source_url": source_url,
            "upstream_service": upstream_service,
        }
        if disease_mechanisms is not None:
            payload["disease_mechanisms"] = disease_mechanisms
        super().__init__(**payload)


class CNVMCPData(BaseModel):
    """MCP-presented CNV data."""

    genome_build: str
    cnv_info: CNVInfoMCP
    pvs1_flowchart: PVS1FlowchartMCP
    disease_mechanisms: list[DiseaseMechanismMCP] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"

    def __init__(
        self,
        *,
        genome_build: str,
        cnv_info: CNVInfoMCP | dict[str, Any],
        pvs1_flowchart: PVS1FlowchartMCP | dict[str, Any],
        disease_mechanisms: Sequence[DiseaseMechanismMCP | dict[str, Any]] | None = None,
        source_url: str | None = None,
        upstream_service: str = "AutoPVS1",
    ) -> None:
        payload: dict[str, Any] = {
            "genome_build": genome_build,
            "cnv_info": cnv_info,
            "pvs1_flowchart": pvs1_flowchart,
            "source_url": source_url,
            "upstream_service": upstream_service,
        }
        if disease_mechanisms is not None:
            payload["disease_mechanisms"] = disease_mechanisms
        super().__init__(**payload)


class SearchMCPData(BaseModel):
    """MCP-presented search page."""

    query: str
    genome_build: str
    total_count: int
    returned_count: int
    next_cursor: str | None
    ordering: Literal["upstream"] = "upstream"
    results: list[SearchResultMCP] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    def __init__(
        self,
        *,
        query: str,
        genome_build: str,
        total_count: int,
        returned_count: int,
        next_cursor: str | None,
        ordering: Literal["upstream"] = "upstream",
        results: Sequence[SearchResultMCP | dict[str, Any]] | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "query": query,
            "genome_build": genome_build,
            "total_count": total_count,
            "returned_count": returned_count,
            "next_cursor": next_cursor,
            "ordering": ordering,
        }
        if results is not None:
            payload["results"] = results
        if suggestions is not None:
            payload["suggestions"] = suggestions
        super().__init__(**payload)


class CompactCapabilitiesData(BaseModel):
    """Compact first-turn MCP capabilities payload."""

    server: str
    version: str
    transport: str
    endpoint: str
    research_use_only: bool
    tool_summaries: dict[str, ToolSummaryMCP]
    canonical_parameters: dict[str, list[str]]
    compact_workflow: list[WorkflowStepMCP]
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
