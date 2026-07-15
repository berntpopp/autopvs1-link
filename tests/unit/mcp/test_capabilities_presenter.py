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
            "Default response_mode is 'summary' (verdict + final "
            "strength); widen to 'standard' for the decision tree."
        ),
        "example": {
            "genome_build": "hg19",
            "variant_id": "X-82763936-A-T",
        },
        "default_response_mode": "summary",
    }
    assert payload["tool_summaries"]["search_variants"] == {
        "purpose": (
            "Search AutoPVS1 by gene symbol, partial variant ID, or "
            "upstream-supported query. Default response_mode is "
            "'ids_only' (variant_id + url per row, ~40% smaller) so "
            "callers can hand the resolved id to get_variant_pvs1_data. "
            "For rsID/HGVS, skip search and call get_variant_pvs1_data "
            "directly — its built-in Ensembl Variant Recoder resolver "
            "is authoritative."
        ),
        "example": {
            "query": "BRCA1",
            "genome_build": "hg38",
            "limit": 10,
        },
        "default_response_mode": "ids_only",
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
    assert (
        payload["tool_summaries"]["get_variants_pvs1_data_bulk"]["default_response_mode"]
        == "summary"
    )
    assert "get_variants_pvs1_data_bulk" in compact.canonical_parameters
    assert "get_cnvs_pvs1_data_bulk" in compact.canonical_parameters


def test_detailed_capabilities_resource_has_examples_and_is_not_duplicate() -> None:
    compact = present_compact_capabilities().model_dump(mode="json")
    detailed = detailed_capabilities_resource()

    assert detailed["accepted_formats"]["cnv_id"] == "{chrom}-{start}-{end}-{TYPE}"
    assert "17-15000000-20000000-DEL" in detailed["examples"]["get_cnv_pvs1_data"]["cnv_id"]
    assert detailed["response_envelope"]["success_fields"] == [
        "success",
        "result | results",
        "_meta",
    ]
    assert detailed["response_envelope"]["error_fields"] == [
        "success",
        "error_code",
        "error_subcode",
        "message",
        "retryable",
        "recovery_action",
        "_meta",
    ]
    assert detailed["response_envelope"]["canonical_error_codes"] == [
        "ambiguous_query",
        "internal",
        "invalid_input",
        "not_found",
        "rate_limited",
        "upstream_unavailable",
    ]
    assert detailed != compact
    assert set(detailed["response_envelope"]["stable_error_codes"]) >= {
        "invalid_variant_id",
        "invalid_cnv_id",
        "invalid_genome_build",
        "invalid_search_cursor",
        "destructive_disabled",
    }
    assert set(detailed["response_envelope"]["stable_warning_codes"]) >= {
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
    per_item = bulk["per_item_envelope"]
    assert per_item["ok"] == "bool"
    assert per_item["input"] == "object"
    assert per_item["data"] == "object|null"
    assert per_item["error"] == "object|null"
    # Per-item meta carries cache_status + elapsed_ms so LLM dispatchers
    # can forecast cost per item, not just across the batch.
    assert "cache_status" in per_item["meta"]
    assert "elapsed_ms" in per_item["meta"]
    assert bulk["applies_response_mode_per_item"] is True
    assert bulk["applies_meta_mode_top_level_only"] is True
    assert bulk["accounting_invariant"] == "total == attempted + skipped"
    # Bulk auto-resolves rsID/HGVS per item so the surface stays symmetric
    # with the single tool.
    assert bulk["auto_resolves_per_item"] is True
    assert "Ensembl Variant Recoder" in bulk["auto_resolution_note"]
    # Aggregate cache observability is documented for "mixed" batches.
    assert "mixed" in bulk["cache_status_aggregation"]
    assert "cached_count" in bulk["cache_status_aggregation"]
    assert "uncached_count" in bulk["cache_status_aggregation"]


def test_capabilities_version_invalidates_on_tool_summary_mutation(monkeypatch) -> None:
    """Tool surface mutations must change the version hash.

    Regression: between two passes the ``tool_summaries`` purpose strings and
    examples changed (added ``LLM-first`` framing, ``response_mode`` keys)
    but ``capabilities_version`` stayed ``7372b825144a8d55``. Cache-aware
    clients keyed on the hash never saw the change. The hash must cover the
    full published surface, not just the registries.
    """
    from autopvs1_link.mcp.presenters import capabilities as caps_mod
    from autopvs1_link.mcp.registries import capabilities_version

    capabilities_version.cache_clear()
    before = capabilities_version()

    # Mutate the published surface in a way a client could observe.
    mutated_summaries = {
        name: {**data, "purpose": "Mutated purpose for hash test."}
        if name == "get_variant_pvs1_data"
        else data
        for name, data in caps_mod._TOOL_SUMMARIES.items()
    }
    monkeypatch.setattr(caps_mod, "_TOOL_SUMMARIES", mutated_summaries)

    capabilities_version.cache_clear()
    after = capabilities_version()
    capabilities_version.cache_clear()

    assert before != after, (
        "capabilities_version must change when tool_summaries content changes; "
        "otherwise clients caching on the hash never see surface updates."
    )


def test_capabilities_version_invalidates_on_performance_block_mutation(monkeypatch) -> None:
    """Performance block mutations must change the version hash too.

    The performance block was added in the same pass that broke search;
    a future tweak to ``warm_call_seconds`` or ``cost_tier`` must invalidate
    cached discovery output so LLM clients adjust their latency planning.
    """
    from autopvs1_link.mcp.presenters import capabilities as caps_mod
    from autopvs1_link.mcp.registries import capabilities_version

    capabilities_version.cache_clear()
    before = capabilities_version()
    mutated_perf = {
        **caps_mod._PERFORMANCE_BLOCK,
        "get_variant_pvs1_data": {
            **caps_mod._PERFORMANCE_BLOCK["get_variant_pvs1_data"],
            "warm_call_seconds": 0.123,
        },
    }
    monkeypatch.setattr(caps_mod, "_PERFORMANCE_BLOCK", mutated_perf)
    capabilities_version.cache_clear()
    after = capabilities_version()
    capabilities_version.cache_clear()
    assert before != after


def test_detailed_capabilities_documents_per_tool_performance_block() -> None:
    """Each tool advertises a cost_tier + cold/warm latency hint.

    The LLM-consumer feedback flagged that AutoPVS1's HTML-scrape upstream
    makes the first call structurally slow (~few seconds) but subsequent
    calls hit the in-process cache and complete in milliseconds. Surfacing
    this distinction in capabilities lets agents plan: batch when uncached,
    re-call freely when warm. ``get_server_health`` is the cheap-only path.
    """
    detailed = detailed_capabilities_resource()
    perf = detailed["performance"]
    expected_tools = {
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
        "search_variants",
        "get_variants_pvs1_data_bulk",
        "get_cnvs_pvs1_data_bulk",
        "get_server_health",
        "get_server_capabilities",
    }
    assert expected_tools.issubset(set(perf)), (
        f"missing tools in performance: {expected_tools - set(perf)}"
    )
    # Scrape-then-cache tools advertise the warm/cold differential.
    scrape_tools = ["get_variant_pvs1_data", "get_cnv_pvs1_data", "search_variants"]
    for tool in scrape_tools:
        block = perf[tool]
        assert block["cost_tier"] == "expensive_cold_cheap_warm", tool
        assert block["cold_call_seconds"] > block["warm_call_seconds"], tool
        assert block["cache_ttl_seconds"] > 0, tool
    # Local-only tools are cheap.
    assert perf["get_server_health"]["cost_tier"] == "cheap"
    assert perf["get_server_capabilities"]["cost_tier"] == "cheap"


def test_detailed_capabilities_documents_warning_aggregation_policy() -> None:
    """Item 4: callers consuming meta.warnings from a bulk call need to know
    exactly when count and affected_indices are populated so they can
    correctly interpret 'one warning' vs 'many items emitted this code'."""
    detailed = detailed_capabilities_resource()
    aggregation = detailed["bulk_behavior"]["warning_aggregation"]
    assert aggregation["scope"] == "top-level _meta.warnings only; per-item warnings are not echoed"
    assert aggregation["gate"] == "code aggregated only when emitted by more than one distinct item"
    assert (
        aggregation["fields"] == "count and affected_indices populated; absent on single-item codes"
    )
    assert aggregation["ordering"] == "first-seen-code-first"
