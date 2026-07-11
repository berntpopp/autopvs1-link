"""Pydantic input/output contracts for MCP tools and resources."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from autopvs1_link.mcp.envelope import MCPError
from autopvs1_link.mcp.untrusted_content import UntrustedText

GenomeBuild = Literal["hg19", "hg38"]
ExampleValue = Any


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
    """Typed variant information exposed through MCP.

    Only ``variant_id`` is required at the contract level. ``variant_type``
    and ``gene_symbol`` are populated for summary/standard/full but absent
    when ``response_mode='ids_only'`` returns just the upstream identifier.
    """

    variant_id: str
    variant_type: str | None = None
    gene_symbol: str | None = None
    gene_url: str | None = None
    pli_score: float | None = None
    pli_score_display: str | None = None
    haploinsufficiency: str | None = None
    haploinsufficiency_url: str | None = None
    chgvs: str | None = None
    phgvs: str | None = None
    exon: str | None = None
    intron: str | None = None
    external_links: dict[str, str | None] | None = None
    external_links_raw: dict[str, str | None] | None = None


class CNVInfoMCP(MCPContractModel):
    """Typed copy-number variant information exposed through MCP.

    Only ``cnv_id`` is required at the contract level; the other fields
    are dropped when ``response_mode='ids_only'``.
    """

    cnv_id: str
    cnv_type: str | None = None
    gene_symbol: str | None = None
    coordinates: str | None = None
    size: int | None = None


class FlowchartStepMCP(MCPContractModel):
    """One typed step in the PVS1 decision flowchart.

    ``code``, ``description``, and ``note_text`` are AutoPVS1's own scraped
    HTML prose (low-trust provenance: autopvs1.bgi.com) and ship as the
    Response-Envelope v1.1 ``untrusted_text`` object, never a bare string.
    ``note_id`` is a short upstream marker (``#1``, ``#2``, ...), not prose.
    """

    code: UntrustedText
    description: UntrustedText | None = None
    note_id: str | None = None
    note_text: UntrustedText | None = None


class PVS1FlowchartMCP(MCPContractModel):
    """Typed PVS1 flowchart decision path and outcome.

    ``decision_tree`` is the single canonical carrier of every scraped
    criterion description (``code``) and its hoisted footnote
    (``note_text``). Response-Envelope v1.1 forbids the same upstream
    prose in more than one field (even when both copies are fenced), so
    there is deliberately no ``notes`` legend dict and no
    ``decision_tree_raw`` audit copy — both re-embedded prose that
    ``decision_tree`` already carries. A caller that needs the raw
    ``#N -> prose`` legend reads it off ``decision_tree[*].note_id`` +
    ``note_text``.

    ``terminal_note`` is the one-line rationale for the verdict, hoisted
    from the leaf step's note_text (or ``notes[preliminary_decision_path]``
    when the decision tree is empty). Populated ONLY in ``summary`` mode
    (where ``decision_tree`` is stripped, so it duplicates nothing) for
    callers that need to explain non-Strong / non-Very-Strong outcomes
    without re-fetching the full decision tree. Absent when the upstream
    note is empty or the verdict is unambiguous (PVS1_Strong /
    PVS1_Very_Strong).

    ``path_gloss`` is a one-line, deterministic compression of the
    decision-tree branch the variant traversed plus the terminal strength
    (ASCII ``->`` separated). It embeds the scraped node text, so to avoid
    duplicating ``decision_tree[*].code`` it is emitted ONLY in ``summary``
    mode — the tier where ``decision_tree`` is absent and the gloss is the
    sole prose carrier. Built only from upstream scraped node text — no
    hand-authored clinical mappings.

    ``terminal_note`` and ``path_gloss`` ship as ``untrusted_text`` objects
    (Response-Envelope v1.1), the same as each ``decision_tree`` step's
    ``code`` / ``note_text``.
    """

    preliminary_decision_path: str
    final_strength: str
    final_strength_source: Literal["asserted", "inferred"] = "asserted"
    decision_tree: list[FlowchartStepMCP] = Field(default_factory=list)
    terminal_note: UntrustedText | None = None
    path_gloss: UntrustedText | None = None


class DiseaseMechanismMCP(MCPContractModel):
    """Typed disease mechanism row from AutoPVS1.

    ``disease`` is a scraped free-text disease name (from AutoPVS1's
    ClinGen-sourced gene-disease table) — the same class of surface as
    clingen-link's ``get_gene_validity /assertions/*/disease_name`` — so it
    ships as ``untrusted_text``. ``gene``/``inheritance``/``clinical_validity``
    /``consideration``/``adjusted_strength`` are short controlled-vocabulary
    values (HGNC symbol; ClinGen validity/inheritance/PVS1-adjustment
    categories), not free prose.
    """

    gene: str
    gene_url: str | None = None
    disease: UntrustedText
    disease_url: str | None = None
    inheritance: str
    clinical_validity: str
    consideration: str
    adjusted_strength: str


class SearchResultMCP(MCPContractModel):
    """Typed AutoPVS1 search result row.

    Only ``variant_id`` and ``url`` are guaranteed to be present.
    ``response_mode='ids_only'`` drops the descriptive fields so callers
    that only need the identifier and a re-fetch URL pay no extra bytes.
    """

    variant_id: str
    url: str
    gene: str | None = None
    variant_type: str | None = None
    genome_build: str | None = None


class ToolSummaryMCP(BaseModel):
    """Compact MCP tool summary for first-turn discovery.

    ``default_response_mode`` is the response_mode the tool emits when
    the caller omits the parameter. Surfaced so LLM consumers can plan
    bandwidth without parsing the tool description; cheap tools that do
    not accept response_mode leave it absent.
    """

    purpose: str
    example: dict[str, ExampleValue] = Field(default_factory=dict)
    default_response_mode: str | None = None


class WorkflowStepMCP(BaseModel):
    """Compact ordered workflow guidance for first-turn discovery."""

    step: str
    when: str


class VariantMCPData(BaseModel):
    """MCP-presented variant data.

    ``pvs1_flowchart`` is required in summary/standard/full modes but
    omitted entirely when ``response_mode='ids_only'`` returns just the
    upstream identifier.
    """

    genome_build: str
    variant_info: VariantInfoMCP
    pvs1_flowchart: PVS1FlowchartMCP | None = None
    disease_mechanisms: list[DiseaseMechanismMCP] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"

    def __init__(
        self,
        *,
        genome_build: str,
        variant_info: VariantInfoMCP | dict[str, Any],
        pvs1_flowchart: PVS1FlowchartMCP | dict[str, Any] | None = None,
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
    """MCP-presented CNV data.

    ``pvs1_flowchart`` is required in summary/standard/full modes but
    omitted entirely when ``response_mode='ids_only'`` returns just the
    upstream identifier.
    """

    genome_build: str
    cnv_info: CNVInfoMCP
    pvs1_flowchart: PVS1FlowchartMCP | None = None
    disease_mechanisms: list[DiseaseMechanismMCP] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"

    def __init__(
        self,
        *,
        genome_build: str,
        cnv_info: CNVInfoMCP | dict[str, Any],
        pvs1_flowchart: PVS1FlowchartMCP | dict[str, Any] | None = None,
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


class SearchPaginationMCP(BaseModel):
    """Pagination block for ``search_variants``.

    Cursors are base64url-encoded ``{"offset": N}`` tokens. They are
    transparent by convention: a caller MAY decode one to read the row
    offset, but the encoding is not a stable contract and MAY change to an
    opaque form later, so prefer echoing ``next_cursor`` back verbatim.
    ``offset`` is echoed for operator visibility only.
    ``total_count_kind`` documents how to interpret ``total_count`` on the
    surrounding ``SearchMCPData``: ``upstream_page`` means the count is
    only what the upstream returned for this query (no guarantee of
    exhaustiveness); ``upstream_total`` means the upstream guarantees the
    full result set was returned.

    ``previous_cursor`` and ``next_cursor`` carry ``= None`` defaults so
    the published JSON schema marks them non-required. The wire payload
    strips null fields (``exclude_none=True``) and the MCP client
    validates structured content against that schema — without the
    defaults, page 1 (no previous) and the last page (no next) would
    fail validation.
    """

    previous_cursor: str | None = None
    next_cursor: str | None = None
    has_more: bool
    offset: int
    total_count_kind: Literal["upstream_total", "upstream_page"] = "upstream_page"


class SearchMCPData(BaseModel):
    """MCP-presented search page."""

    query: str
    genome_build: str
    total_count: int
    returned_count: int
    pagination: SearchPaginationMCP
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
        pagination: SearchPaginationMCP | dict[str, Any],
        ordering: Literal["upstream"] = "upstream",
        results: Sequence[SearchResultMCP | dict[str, Any]] | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "query": query,
            "genome_build": genome_build,
            "total_count": total_count,
            "returned_count": returned_count,
            "pagination": pagination,
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
    capabilities_version: str
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


class BulkVariantPVS1InputItem(BaseModel):
    """One item in a bulk variant PVS1 request."""

    genome_build: str = Field(
        ...,
        description="Genome build: hg19 or hg38. Invalid values yield a per-item error.",
    )
    variant_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="AutoPVS1 variant ID, for example X-82763936-A-T.",
    )


class BulkCNVPVS1InputItem(BaseModel):
    """One item in a bulk CNV PVS1 request."""

    genome_build: str = Field(
        ...,
        description="Genome build: hg19 or hg38. Invalid values yield a per-item error.",
    )
    cnv_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form.",
    )


class BulkPerItemMeta(BaseModel):
    """Per-item cost/cache observability for bulk PVS1 result items.

    Top-level ``meta.cache_status`` aggregates the batch ("mixed" when
    items had varying outcomes) — agents that need to forecast cost on a
    per-item basis read this block. Absent when the item short-circuited
    before any upstream call (e.g. invalid input).
    """

    cache_status: Literal["hit", "miss", "coalesced", "bypass"] | None = None
    elapsed_ms: float | None = None


class BulkVariantPVS1ResultItem(BaseModel):
    """Per-item result for a bulk variant PVS1 request."""

    ok: bool
    input: BulkVariantPVS1InputItem
    data: VariantMCPData | None = None
    error: MCPError | None = None
    meta: BulkPerItemMeta | None = None


class BulkCNVPVS1ResultItem(BaseModel):
    """Per-item result for a bulk CNV PVS1 request."""

    ok: bool
    input: BulkCNVPVS1InputItem
    data: CNVMCPData | None = None
    error: MCPError | None = None
    meta: BulkPerItemMeta | None = None


class BulkVariantsMCPData(BaseModel):
    """Aggregate payload for ``get_variants_pvs1_data_bulk``.

    ``total`` is always the requested item count. ``attempted`` is the count
    that ran (= ``len(items)``). ``skipped`` is the count that the server did
    not attempt because ``continue_on_error=False`` broke the loop early.
    Invariant: ``attempted == succeeded + failed`` and ``total == attempted + skipped``.
    """

    total: int
    attempted: int
    skipped: int
    succeeded: int
    failed: int
    items: list[BulkVariantPVS1ResultItem] = Field(default_factory=list)


class BulkCNVsMCPData(BaseModel):
    """Aggregate payload for ``get_cnvs_pvs1_data_bulk``.

    Same semantics as :class:`BulkVariantsMCPData`.
    """

    total: int
    attempted: int
    skipped: int
    succeeded: int
    failed: int
    items: list[BulkCNVPVS1ResultItem] = Field(default_factory=list)
