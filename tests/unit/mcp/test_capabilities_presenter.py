"""Tests for compact and detailed MCP capabilities payloads."""

from autopvs1_link.mcp.presenters.capabilities import (
    detailed_capabilities_resource,
    present_compact_capabilities,
)


def test_compact_capabilities_are_first_turn_tool_selection_data() -> None:
    compact = present_compact_capabilities()
    payload = compact.model_dump(mode="json")

    assert compact.research_use_only is True
    assert compact.details_resource == "autopvs1-link://capabilities"
    assert compact.canonical_parameters["search_variants"] == [
        "query",
        "genome_build",
        "limit",
        "cursor",
    ]
    assert "genome_version" not in compact.canonical_parameters["search_variants"]
    assert payload["tool_summaries"]["get_variant_pvs1_data"] == {
        "purpose": "research-use PVS1 analysis for one AutoPVS1 SNV/indel ID.",
        "example": {
            "genome_build": "hg19",
            "variant_id": "X-82763936-A-T",
        },
    }
    assert payload["tool_summaries"]["search_variants"] == {
        "purpose": "Search AutoPVS1 by gene symbol, partial variant ID, or upstream-supported query.",
        "example": {
            "query": "BRCA1",
            "genome_build": "hg38",
            "limit": 10,
            "cursor": None,
        },
    }
    assert payload["compact_workflow"] == [
        {
            "step": "Confirm genome build",
            "when": "The source coordinate build is unknown or absent.",
        },
        {
            "step": "Search for an AutoPVS1 ID",
            "when": "The caller has a gene symbol, partial variant ID, or upstream-supported query.",
        },
        {
            "step": "Score one variant or CNV",
            "when": "The caller has a normalized AutoPVS1 variant_id or cnv_id.",
        },
        {
            "step": "Report research-use output",
            "when": "Summarizing any AutoPVS1 result for a user.",
        },
    ]


def test_detailed_capabilities_resource_has_examples_and_is_not_duplicate() -> None:
    compact = present_compact_capabilities().model_dump(mode="json")
    detailed = detailed_capabilities_resource()

    assert detailed["accepted_formats"]["cnv_id"] == "{chrom}-{start}-{end}-{TYPE}"
    assert "17-15000000-20000000-DEL" in detailed["examples"]["get_cnv_pvs1_data"]["cnv_id"]
    assert detailed["error_envelope"]["required_fields"] == [
        "ok",
        "data",
        "error",
        "meta",
    ]
    assert detailed != compact
