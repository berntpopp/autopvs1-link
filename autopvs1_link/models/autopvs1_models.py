"""Pydantic data models for AutoPVS1 Link."""

from typing import Optional

from pydantic import BaseModel, Field


class VariantInfo(BaseModel):
    """Information about a genetic variant."""

    variant_id: str
    variant_type: str
    gene_symbol: str
    gene_url: Optional[str] = None
    pli_score: Optional[float] = None
    haploinsufficiency: Optional[str] = None
    haploinsufficiency_url: Optional[str] = None
    chgvs: Optional[str] = None
    phgvs: Optional[str] = None
    exon: Optional[str] = None
    intron: Optional[str] = None
    external_links: dict[str, str] = Field(default_factory=dict)


class FlowchartStep(BaseModel):
    """A step in the PVS1 decision flowchart."""

    code: str
    description: Optional[str] = None
    note_id: Optional[str] = None


class PVS1Flowchart(BaseModel):
    """PVS1 flowchart decision path and outcome."""

    preliminary_decision_path: str
    final_strength: str
    decision_tree: list[FlowchartStep] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)


class DiseaseMechanism(BaseModel):
    """Disease mechanism information from the table."""

    gene: str
    gene_url: Optional[str] = None
    disease: str
    disease_url: Optional[str] = None
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
    size: Optional[str] = None


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
