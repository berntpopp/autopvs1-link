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
        "purpose": (
            "Research-use PVS1 analysis for one AutoPVS1 SNV/indel ID. "
            "LLM-first: pass response_mode='summary' for the verdict."
        ),
        "example": {
            "genome_build": "hg19",
            "variant_id": "X-82763936-A-T",
            "response_mode": "summary",
        },
    }
    assert payload["tool_summaries"]["search_variants"] == {
        "purpose": (
            "Search AutoPVS1 by gene symbol, partial variant ID, or "
            "upstream-supported query. Use response_mode='ids_only' "
            "to resolve to a variant_id with minimum bytes."
        ),
        "example": {
            "query": "BRCA1",
            "genome_build": "hg38",
            "limit": 10,
            "response_mode": "ids_only",
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
        "response_mode": "summary",
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
    # Task 9.7 Item 1: ids_only is the lowest-bandwidth lookup tier and
    # must be discoverable on the same payload_modes table that documents
    # summary/standard/full so clients pick the right enum value without
    # reading source.
    assert "ids_only" in detailed["payload_modes"]
    assert detailed["payload_modes"]["ids_only"]["char_budget"] < 1500


def test_search_behavior_documents_cursor_opacity_posture() -> None:
    """The cursor is opaque-by-convention (base64url JSON), not signed.

    For a research-use server this is fine, but callers must NOT rely
    on cursor opacity for integrity — anyone can decode the offset.
    The capabilities resource must say so explicitly so clients don't
    treat the cursor as a secure handle.
    """
    detailed = detailed_capabilities_resource()
    opacity = detailed["search_behavior"]["cursor_opacity"]
    assert isinstance(opacity, str)
    # Must mention that opacity is syntactic only, not cryptographic.
    assert "syntactic" in opacity.lower()
    assert "integrity" in opacity.lower() or "secur" in opacity.lower()


def test_search_behavior_documents_pagination_block_fields() -> None:
    detailed = detailed_capabilities_resource()
    assert "pagination_block" in detailed["search_behavior"]
    pagination_blurb = detailed["search_behavior"]["pagination_block"]
    for field in (
        "previous_cursor",
        "next_cursor",
        "has_more",
        "offset",
        "total_count_kind",
    ):
        assert field in pagination_blurb, field


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


def test_capabilities_version_is_memoized_after_first_call() -> None:
    """Item 3: SERVER_VERSION + registries are module-level immutables so the
    hash computation must collapse to a single sha256 pass. functools.cache
    is the canonical memoization here; verify ``cache_info().hits`` grows
    on the second call.
    """
    capabilities_version.cache_clear()
    capabilities_version()
    capabilities_version()
    info = capabilities_version.cache_info()
    assert info.hits >= 1
    assert info.misses == 1


def test_capabilities_version_invalidates_on_known_error_codes_mutation(
    monkeypatch,
) -> None:
    """Item 7c: an accidental change to KNOWN_ERROR_CODES (e.g. someone
    renames invalid_variant_id to invalid_variant_identifier without
    auditing the wire contract) must yield a different
    capabilities_version. Otherwise the hash lies about registry state
    and cache-aware clients keyed on it never invalidate.

    Mutation is scoped via monkeypatch.setattr against a fresh copy of
    the dict so the registries module state is restored on test
    teardown — no leakage into downstream tests.
    """
    from autopvs1_link.mcp import registries as registries_module

    capabilities_version.cache_clear()
    before = capabilities_version()

    # Swap exactly one entry to verify the hash is sensitive to message
    # content too (not just key set). Use a copy so monkeypatch can
    # restore the original dict on teardown.
    mutated = dict(registries_module.KNOWN_ERROR_CODES)
    mutated["invalid_variant_id"] = "Mutated message for hash test."
    monkeypatch.setattr(registries_module, "KNOWN_ERROR_CODES", mutated)

    capabilities_version.cache_clear()
    after = capabilities_version()
    assert before != after

    # Cleanup — drop the cached mutated value so downstream tests recompute
    # against the restored (original) KNOWN_ERROR_CODES.
    capabilities_version.cache_clear()


def test_capabilities_version_blends_server_version_into_hash(monkeypatch) -> None:
    """Item 3 provenance: bumping SERVER_VERSION must yield a different
    capabilities_version so deployments are correlatable. Without the blend,
    two builds with identical registries but different SERVER_VERSION would
    advertise the same hash and clients couldn't invalidate caches keyed on
    the deployment.
    """
    from autopvs1_link.mcp import registries as registries_module

    capabilities_version.cache_clear()
    before = capabilities_version()
    monkeypatch.setattr(registries_module, "SERVER_VERSION", "999.99.99")
    capabilities_version.cache_clear()
    after = capabilities_version()
    assert before != after
    # And the stable shape (16 hex chars) is preserved.
    assert re.fullmatch(r"[0-9a-f]{16}", after), after
    # Restore caching invariants for downstream tests.
    capabilities_version.cache_clear()


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


def test_detailed_capabilities_documents_warning_aggregation_policy() -> None:
    """Item 4: callers consuming meta.warnings from a bulk call need to know
    exactly when count and affected_indices are populated so they can
    correctly interpret 'one warning' vs 'many items emitted this code'."""
    detailed = detailed_capabilities_resource()
    aggregation = detailed["bulk_behavior"]["warning_aggregation"]
    assert aggregation["scope"] == "top-level meta.warnings only; per-item warnings are not echoed"
    assert aggregation["gate"] == "code aggregated only when emitted by more than one distinct item"
    assert (
        aggregation["fields"] == "count and affected_indices populated; absent on single-item codes"
    )
    assert aggregation["ordering"] == "first-seen-code-first"
