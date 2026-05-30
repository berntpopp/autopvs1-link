"""Pydantic data models for AutoPVS1 Link."""

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema


class VariantInfo(BaseModel):
    """Information about a genetic variant."""

    variant_id: str
    variant_type: str
    gene_symbol: str
    gene_url: str | None = None
    pli_score: float | None = None
    haploinsufficiency: str | None = None
    haploinsufficiency_url: str | None = None
    chgvs: str | None = None
    phgvs: str | None = None
    exon: str | None = None
    intron: str | None = None
    external_links: dict[str, str] = Field(default_factory=dict)
    invalid_external_links: SkipJsonSchema[dict[str, str]] = Field(
        default_factory=dict, exclude=True
    )


class FlowchartStep(BaseModel):
    """A step in the PVS1 decision flowchart."""

    code: str
    description: str | None = None
    note_id: str | None = None


class PVS1Flowchart(BaseModel):
    """PVS1 flowchart decision path and outcome."""

    preliminary_decision_path: str
    final_strength: str
    final_strength_inferred: bool = False
    decision_tree: list[FlowchartStep] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)


class DiseaseMechanism(BaseModel):
    """Disease mechanism information from the table."""

    gene: str
    gene_url: str | None = None
    disease: str
    disease_url: str | None = None
    inheritance: str
    clinical_validity: str
    consideration: str
    adjusted_strength: str


class SearchResult(BaseModel):
    """Search result item."""

    variant_id: str
    gene: str
    variant_type: str
    genome_build: str
    url: str


class CNVInfo(BaseModel):
    """Copy number variant information."""

    cnv_id: str
    cnv_type: str
    gene_symbol: str
    coordinates: str
    size: int | None = None


class AutoPVS1Data(BaseModel):
    """Complete AutoPVS1 data structure."""

    genome_build: str
    variant_info: VariantInfo
    pvs1_flowchart: PVS1Flowchart
    disease_mechanisms: list[DiseaseMechanism] = Field(default_factory=list)


class AutoPVS1SearchResults(BaseModel):
    """Search results from AutoPVS1."""

    query: str
    genome_version: str
    results: list[SearchResult] = Field(default_factory=list)


class AutoPVS1CNVData(BaseModel):
    """CNV-specific data structure."""

    genome_build: str
    cnv_info: CNVInfo
    pvs1_flowchart: PVS1Flowchart
    disease_mechanisms: list[DiseaseMechanism] = Field(default_factory=list)


class RedirectInfo(BaseModel):
    """Information about search redirects."""

    original_url: str
    final_url: str
    redirect_detected: bool = True
    variant_id_extracted: str | None = None
    genome_build_extracted: str | None = None


class EnhancedSearchResults(BaseModel):
    """Enhanced search results with redirect detection."""

    query: str
    genome_version: str
    redirected: bool = False
    variant_data: AutoPVS1Data | None = None
    search_results: AutoPVS1SearchResults | None = None
    redirect_info: RedirectInfo | None = None

    @property
    def is_single_variant(self) -> bool:
        """Check if result contains a single variant (redirected)."""
        return self.redirected and self.variant_data is not None

    @property
    def is_multiple_results(self) -> bool:
        """Check if result contains multiple search results."""
        return not self.redirected and self.search_results is not None
