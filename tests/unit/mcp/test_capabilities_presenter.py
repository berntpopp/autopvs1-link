"""Tests for compact and detailed MCP capabilities payloads."""

import re

from autopvs1_link.mcp.presenters.capabilities import (
    detailed_capabilities_resource,
    present_compact_capabilities,
)
from autopvs1_link.mcp.registries import capabilities_version


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
    assert "get_server_health" in compact.tool_summaries
    assert "get_server_health" in compact.canonical_parameters
    assert "clear_cache" not in compact.tool_summaries
    assert "clear_cache" not in compact.canonical_parameters
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
            "when": "The caller has a single normalized AutoPVS1 variant_id or cnv_id.",
        },
        {
            "step": "Score multiple variants or CNVs in one call",
            "when": (
                "The caller has 2 to 10 IDs of the same kind; use "
                "get_variants_pvs1_data_bulk or get_cnvs_pvs1_data_bulk."
            ),
        },
        {
            "step": "Report research-use output",
            "when": "Summarizing any AutoPVS1 result for a user.",
        },
    ]
    assert payload["tool_summaries"]["get_variants_pvs1_data_bulk"]["example"] == {
        "items": [{"genome_build": "hg19", "variant_id": "X-82763936-A-T"}],
    }
    assert "get_variants_pvs1_data_bulk" in compact.canonical_parameters
    assert "get_cnvs_pvs1_data_bulk" in compact.canonical_parameters


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
    assert set(detailed["error_envelope"]["stable_error_codes"]) >= {
        "invalid_variant_id",
        "invalid_cnv_id",
        "invalid_genome_build",
        "invalid_search_cursor",
        "destructive_disabled",
    }
    assert set(detailed["error_envelope"]["stable_warning_codes"]) >= {
        "invalid_external_link",
        "pvs1_not_applicable",
        "limit_clamped",
        "search_results_truncated",
    }
    assert detailed["payload_modes"]["summary"]["char_budget"] == 1500
    assert detailed["payload_modes"]["full"]["char_budget"] == 12000


def test_compact_capabilities_includes_capabilities_version_hash() -> None:
    payload = present_compact_capabilities().model_dump(mode="json")
    version = payload["capabilities_version"]
    assert isinstance(version, str)
    assert re.fullmatch(r"[0-9a-f]{16}", version), version
    assert version == capabilities_version()


def test_capabilities_version_is_stable_across_calls() -> None:
    a = present_compact_capabilities().capabilities_version
    b = present_compact_capabilities().capabilities_version
    assert a == b


def test_detailed_capabilities_mirrors_capabilities_version() -> None:
    detailed = detailed_capabilities_resource()
    compact = present_compact_capabilities().model_dump(mode="json")
    assert detailed["capabilities_version"] == compact["capabilities_version"]


def test_detailed_capabilities_documents_bulk_behavior_contract() -> None:
    detailed = detailed_capabilities_resource()
    bulk = detailed["bulk_behavior"]
    assert bulk["max_items"] == 10
    assert bulk["execution"] == "sequential"
    assert bulk["respects_upstream_rate_limit"] is True
    assert bulk["upstream_rate_limit_seconds"] == 1.0
    assert bulk["worst_case_latency_seconds"] == 10
    assert bulk["continue_on_error_default"] is True
    assert bulk["ordering"] == "preserves input order"
    assert bulk["per_item_envelope"] == {
        "ok": "bool",
        "input": "object",
        "data": "object|null",
        "error": "object|null",
    }
    assert bulk["applies_response_mode_per_item"] is True
    assert bulk["applies_meta_mode_top_level_only"] is True
    assert bulk["accounting_invariant"] == "total == attempted + skipped"
