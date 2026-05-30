"""MCP workflow prompts."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP

_PAYLOAD_SIZING_GUIDANCE = (
    "Payload sizing: pass response_mode='summary' first; widen to "
    "'standard' only if the user asks for the decision tree, and use "
    "'full' only when an auditor needs the *_raw upstream fields. Use "
    "meta_mode='compact' unless citations need to be reproduced verbatim."
)


_ERROR_HANDLING_GUIDANCE = (
    "Error handling:\n"
    "- error.code in {invalid_variant_id, invalid_cnv_id, "
    "invalid_genome_build}: ask the user to confirm inputs.\n"
    "- error.code == 'not_found' OR warning.code == "
    "'pvs1_not_applicable': do NOT present a classification. Call "
    "search_variants and ask the user to confirm the resolved ID. "
    "PVS1_Not_Applicable means the variant fell outside an annotated "
    "PVS1 region, not that scoring succeeded.\n"
    "- error.code in {upstream_timeout, upstream_unavailable}: retry "
    "once with backoff.\n"
    "- CallToolResult.isError=true ALWAYS means failure regardless of "
    "envelope shape."
)


def _classify_variant_body(genome_build: str, variant_id: str) -> str:
    return (
        "Use AutoPVS1-Link for research-use PVS1 interpretation only. "
        f"Call get_variant_pvs1_data with genome_build={genome_build!r} "
        f"and variant_id={variant_id!r}. "
        "If the user supplied a gene, HGVS-like text, or partial "
        "identifier instead of an AutoPVS1 variant ID, call "
        "search_variants first and ask the user to confirm the resolved "
        "genome build and identifier.\n\n"
        f"{_PAYLOAD_SIZING_GUIDANCE}\n\n"
        f"{_ERROR_HANDLING_GUIDANCE}\n\n"
        "Summarize the final PVS1 strength, decision path, "
        "disease-mechanism rows, source URL, warnings, and citation. "
        "State that the result is not clinical decision support."
    )


def _classify_cnv_body(genome_build: str, cnv_id: str) -> str:
    return (
        "Use AutoPVS1-Link for research-use PVS1 interpretation only. "
        f"Call get_cnv_pvs1_data with genome_build={genome_build!r} and "
        f"cnv_id={cnv_id!r}. The CNV ID should use "
        "{chrom}-{start}-{end}-{TYPE}; if the user provided another "
        "coordinate format (or the upstream returns invalid_cnv_id), "
        "normalize or ask for confirmation before scoring. If the user "
        "supplied a gene or partial identifier instead of an AutoPVS1 "
        "CNV ID, call search_variants first and ask the user to confirm "
        "the resolved genome build and identifier.\n\n"
        f"{_PAYLOAD_SIZING_GUIDANCE}\n\n"
        f"{_ERROR_HANDLING_GUIDANCE}\n\n"
        "Summarize the final PVS1 strength, decision path, "
        "disease-mechanism rows, source URL, warnings, and citation. "
        "State that the result is not clinical decision support."
    )


_WORKFLOW_HELP_BODIES: dict[str, str] = {
    "clinical_review": (
        "Use AutoPVS1-Link for research-use PVS1 review only - not for "
        "clinical decision support.\n\n"
        "Chain for a single variant under review:\n"
        "1. get_server_capabilities to confirm tool surface and "
        "capabilities_version (cache it client-side).\n"
        "2. If only a gene symbol or HGVS string is in hand, call "
        "search_variants(query=..., genome_build='hg38') and let the user "
        "confirm the resolved AutoPVS1 ID before scoring.\n"
        "3. get_variant_pvs1_data(genome_build, variant_id, "
        "response_mode='standard', meta_mode='compact') for the typical "
        "review payload. Upgrade to response_mode='full' only if the "
        "reviewer needs the *_raw decision tree or external_links_raw.\n"
        "4. Present final_strength, decision_path, disease_mechanisms, "
        "source_url, all warnings, recommended_citation. Treat "
        "pvs1_not_applicable as a non-call."
    ),
    "batch_screen": (
        "Use AutoPVS1-Link for research-use PVS1 batch screening only.\n\n"
        "Chain for 1-10 variants in one call:\n"
        "1. Confirm all variants share a genome build; otherwise split "
        "into per-build batches.\n"
        "2. get_variants_pvs1_data_bulk(items=[...], "
        "response_mode='summary', meta_mode='compact', "
        "continue_on_error=True). 'summary' keeps each item compact; the "
        "top-level meta carries aggregated warnings with count and "
        "affected_indices when codes repeat across items.\n"
        "3. For per-item failures, inspect data.items[i].error.code and "
        "decide per error-handling guidance (retry, ask user, surface "
        "as non-call).\n"
        "4. For CNVs use get_cnvs_pvs1_data_bulk with the same shape."
    ),
    "search_first": (
        "Use AutoPVS1-Link for research-use lookup; never bypass "
        "search_variants if the user has only a gene or partial "
        "identifier.\n\n"
        "Chain to resolve an AutoPVS1 ID:\n"
        "1. search_variants(query=..., genome_build=..., limit=10, "
        "cursor=None). The cursor is an opaque pagination token; do "
        "NOT construct cursors yourself.\n"
        "2. If warnings include search_results_truncated, follow "
        "data.pagination.next_cursor for the next page; "
        "data.pagination.has_more tells you whether to keep paging.\n"
        "3. If warnings include unsupported_hgvs_like_search, fall back "
        "to suggestions (e.g., gene-only re-search).\n"
        "4. Confirm the resolved variant_id with the user, then call "
        "get_variant_pvs1_data."
    ),
}


def register(mcp: FastMCP) -> None:
    """Register reusable workflow prompts."""

    @mcp.prompt(
        name="classify_variant",
        title="Classify SNV/Indel with AutoPVS1",
        description="Guide a research-use AutoPVS1 SNV/indel PVS1 workflow.",
    )
    def classify_variant(
        genome_build: Annotated[str, "Genome build, usually hg19 or hg38."],
        variant_id: Annotated[str, "AutoPVS1 variant ID such as X-82763936-A-T."],
    ) -> str:
        """Guide SNV/indel PVS1 classification with existing tools."""
        return _classify_variant_body(genome_build, variant_id)

    @mcp.prompt(
        name="classify_cnv",
        title="Classify CNV with AutoPVS1",
        description="Guide a research-use AutoPVS1 CNV PVS1 workflow.",
    )
    def classify_cnv(
        genome_build: Annotated[str, "Genome build, usually hg19 or hg38."],
        cnv_id: Annotated[str, "AutoPVS1 CNV ID such as 17-15000000-20000000-DEL."],
    ) -> str:
        """Guide CNV PVS1 classification with existing tools."""
        return _classify_cnv_body(genome_build, cnv_id)

    @mcp.prompt(
        name="pvs1_workflow_help",
        title="AutoPVS1 Workflow Guidance",
        description=(
            "Return concrete tool-chain guidance for one of three tasks: "
            "clinical_review, batch_screen, or search_first."
        ),
    )
    def pvs1_workflow_help(
        task: Annotated[
            str,
            "One of clinical_review, batch_screen, or search_first.",
        ],
    ) -> str:
        """Return tool-chain guidance keyed by task."""
        body = _WORKFLOW_HELP_BODIES.get(task)
        if body is None:
            valid = ", ".join(_WORKFLOW_HELP_BODIES)
            return f"Unknown task. Choose one of: {valid}."
        return body
