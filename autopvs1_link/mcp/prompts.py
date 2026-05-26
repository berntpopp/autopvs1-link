"""Workflow prompts for AutoPVS1-Link MCP clients."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP


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
        return (
            "Use AutoPVS1-Link for research-use PVS1 interpretation only. "
            "Call get_variant_pvs1_data with genome_build="
            f"{genome_build!r} and variant_id={variant_id!r}. "
            "If the user supplied a gene, HGVS-like text, or partial identifier "
            "instead of an AutoPVS1 variant ID, call search_variants first and ask "
            "the user to confirm the resolved genome build and identifier. "
            "Summarize the final PVS1 strength, decision path, disease-mechanism "
            "rows, source URL, warnings, and citation. State that the result is "
            "not clinical decision support."
        )

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
        return (
            "Use AutoPVS1-Link for research-use PVS1 interpretation only. "
            "Call get_cnv_pvs1_data with genome_build="
            f"{genome_build!r} and cnv_id={cnv_id!r}. "
            "The CNV ID should use {chrom}-{start}-{end}-{TYPE}; if the user "
            "provided another coordinate format, normalize or ask for confirmation "
            "before scoring. If the user supplied a gene or partial identifier "
            "instead of an AutoPVS1 CNV ID, call search_variants first and ask "
            "the user to confirm the resolved genome build and identifier. "
            "Summarize the final PVS1 strength, decision path, disease-mechanism "
            "rows, source URL, warnings, and citation. State that the result is "
            "not clinical decision support."
        )
