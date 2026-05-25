"""Tests for compact and detailed MCP capabilities payloads."""

from autopvs1_link.mcp.presenters.capabilities import (
    detailed_capabilities_resource,
    present_compact_capabilities,
)


def test_compact_capabilities_are_first_turn_tool_selection_data() -> None:
    compact = present_compact_capabilities()

    assert compact.research_use_only is True
    assert compact.details_resource == "autopvs1-link://capabilities"
    assert compact.canonical_parameters["search_variants"] == [
        "query",
        "genome_build",
        "limit",
        "cursor",
    ]
    assert "genome_version" not in compact.canonical_parameters["search_variants"]
    assert "research-use" in compact.tool_summaries["get_variant_pvs1_data"]


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
