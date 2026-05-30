"""Tests for MCP envelope metadata, warnings, and errors."""

import json
from uuid import UUID

from autopvs1_link.mcp.contracts import ClearCacheData, ClearCacheMCPEnvelope
from autopvs1_link.mcp.envelope import MCPWarning, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError


def test_ok_envelope_contains_required_metadata() -> None:
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))

    assert envelope["ok"] is True
    assert envelope["data"] == {"cleared": True, "message": "cleared"}
    assert envelope["error"] is None
    assert envelope["meta"]["server_version"] == "1.1.0"
    assert envelope["meta"]["research_use_only"] is True
    assert envelope["meta"]["recommended_citation"]["doi"] == "10.1002/humu.24051"
    UUID(envelope["meta"]["request_id"])


def test_error_envelope_contains_machine_readable_error() -> None:
    envelope = error_envelope(
        code="invalid_variant_id",
        message="Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
        retryable=False,
        suggestions=["Use search_variants with a gene symbol."],
    )

    assert envelope["ok"] is False
    assert envelope["data"] is None
    assert envelope["error"] == {
        "code": "invalid_variant_id",
        "message": "Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
        "retryable": False,
        "suggestions": ["Use search_variants with a gene symbol."],
    }
    assert envelope["meta"]["research_use_only"] is True


def test_warning_objects_are_serialized_in_meta() -> None:
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        warnings=[MCPWarning(code="deprecated_genome_version", message="Use genome_build.")],
    )

    assert envelope["meta"]["warnings"] == [
        {"code": "deprecated_genome_version", "message": "Use genome_build."}
    ]


def test_mcp_input_error_converts_to_error_envelope() -> None:
    exc = MCPInputError(
        code="invalid_cnv_id",
        message="CNV IDs must use {chrom}-{start}-{end}-{TYPE}.",
        suggestions=["Use 17-15000000-20000000-DEL."],
    )

    envelope = exc.to_envelope()

    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "invalid_cnv_id"
    assert envelope["error"]["retryable"] is False
    assert envelope["error"]["suggestions"] == ["Use 17-15000000-20000000-DEL."]


def test_concrete_envelope_schema_uses_standard_fields() -> None:
    schema = ClearCacheMCPEnvelope.model_json_schema()

    assert set(schema["properties"]) == {"ok", "data", "error", "meta"}
    assert set(schema["required"]) == {"ok", "data", "error", "meta"}


def test_mcp_warning_serializes_without_aggregate_fields_when_unset() -> None:
    warning = MCPWarning(code="invalid_external_link", message="X link nulled.")
    payload = warning.model_dump(mode="json", exclude_none=True)
    assert payload == {"code": "invalid_external_link", "message": "X link nulled."}


def test_ok_envelope_meta_echoes_telemetry_when_upstream_call_happened() -> None:
    """If a service adapter ran, meta echoes its elapsed_ms + cache_status.

    The cache wrapper records into a ContextVar; ok_envelope reads it.
    Without an upstream call (e.g. health/capabilities), the CV stays at
    its default ``None`` and the fields drop off the wire via
    ``exclude_none`` on MCPMeta serialization.
    """
    from autopvs1_link.mcp.telemetry import record_upstream_call, reset_call_telemetry

    reset_call_telemetry()
    record_upstream_call(elapsed_ms=42.5, cache_status="hit")
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))
    assert envelope["meta"]["elapsed_ms"] == 42.5
    assert envelope["meta"]["cache_status"] == "hit"


def test_ok_envelope_meta_drops_telemetry_for_no_upstream_call_tools() -> None:
    """Cheap tools (no service-adapter call) must NOT echo elapsed_ms.

    A ``None`` ContextVar default + ``exclude_none`` keeps the wire clean
    so callers don't see misleading 0ms readings for tools that never
    touched the upstream.
    """
    from autopvs1_link.mcp.telemetry import reset_call_telemetry

    reset_call_telemetry()
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))
    assert "elapsed_ms" not in envelope["meta"]
    assert "cache_status" not in envelope["meta"]


def test_ok_envelope_meta_echoes_effective_chars_count() -> None:
    """Meta echoes effective_chars so callers learn the actual wire cost.

    The advertised char_budget on each payload_mode tier is theoretical;
    the echoed count is what the LLM actually paid. Letting clients
    calibrate after the first call is a peer-server pattern from HNF1B.
    """
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))
    chars = envelope["meta"]["effective_chars"]
    assert isinstance(chars, int)
    expected = len(json.dumps(envelope["data"], separators=(",", ":")))
    assert chars == expected, f"effective_chars {chars} != actual data bytes {expected}"


def test_mcp_warning_with_aggregate_fields_serializes_count_and_indices() -> None:
    warning = MCPWarning(
        code="invalid_external_link",
        message="gnomAD link nulled.",
        count=3,
        affected_indices=[0, 1, 2],
    )
    payload = warning.model_dump(mode="json")
    assert payload["count"] == 3
    assert payload["affected_indices"] == [0, 1, 2]


# ---------------------------------------------------------------------------
# Cost-tier / rate-limit-floor / next-call-earliest-at hints (Improvement 2)
# ---------------------------------------------------------------------------


def test_ok_envelope_meta_emits_cost_tier_for_scrape_tools() -> None:
    """Scrape-tier tools must surface meta.cost_tier and meta.rate_limit_floor_ms.

    LLM consumers use these to plan call sequencing — they tell the
    model whether the next call will pay a cold-scrape cost and what
    the upstream floor is.
    """
    from autopvs1_link.mcp.telemetry import record_upstream_call, reset_call_telemetry

    reset_call_telemetry()
    record_upstream_call(elapsed_ms=50.0, cache_status="hit")
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        tool_name="get_variant_pvs1_data",
    )
    assert envelope["meta"]["cost_tier"] == "expensive_cold_cheap_warm"
    assert envelope["meta"]["rate_limit_floor_ms"] == 1000
    # cache_status='hit' means the rate-limit clock did NOT reset; we
    # cannot compute next_call_earliest_at honestly.
    assert "next_call_earliest_at" not in envelope["meta"]


def test_ok_envelope_meta_emits_next_call_earliest_at_only_on_real_upstream() -> None:
    """next_call_earliest_at must populate on miss/coalesced (clock reset only)."""
    from autopvs1_link.mcp.telemetry import record_upstream_call, reset_call_telemetry

    reset_call_telemetry()
    record_upstream_call(elapsed_ms=1500.0, cache_status="miss")
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        tool_name="get_variant_pvs1_data",
    )
    assert envelope["meta"]["cache_status"] == "miss"
    # ISO-8601 string in the future
    next_at = envelope["meta"]["next_call_earliest_at"]
    assert isinstance(next_at, str)
    assert next_at.endswith("+00:00"), f"Expected UTC offset, got {next_at!r}"

    # Coalesced waiters also reset the clock from their perspective (they
    # paid wall-clock time too).
    reset_call_telemetry()
    record_upstream_call(elapsed_ms=1500.0, cache_status="coalesced")
    envelope2 = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        tool_name="get_variant_pvs1_data",
    )
    assert isinstance(envelope2["meta"]["next_call_earliest_at"], str)


def test_ok_envelope_meta_emits_cheap_tier_without_rate_limit_floor() -> None:
    """Cheap tools (health, capabilities) surface cost_tier but no floor."""
    from autopvs1_link.mcp.telemetry import reset_call_telemetry

    reset_call_telemetry()
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        tool_name="get_server_health",
    )
    assert envelope["meta"]["cost_tier"] == "cheap"
    assert "rate_limit_floor_ms" not in envelope["meta"]
    assert "next_call_earliest_at" not in envelope["meta"]


def test_ok_envelope_meta_drops_cost_tier_when_tool_name_unknown() -> None:
    """Calls without tool_name keep meta absent of cost hints (backwards-compat)."""
    from autopvs1_link.mcp.telemetry import reset_call_telemetry

    reset_call_telemetry()
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))
    assert "cost_tier" not in envelope["meta"]
    assert "rate_limit_floor_ms" not in envelope["meta"]
    assert "next_call_earliest_at" not in envelope["meta"]


def test_error_envelope_meta_emits_retry_after_ms_for_transient_codes() -> None:
    """Transient upstream errors default retry_after_ms to the rate-limit floor.

    An LLM client retrying immediately on upstream_timeout would just
    block on the floor; surfacing the floor as retry_after_ms lets the
    client schedule the retry intelligently.
    """
    envelope = error_envelope(
        code="upstream_timeout",
        message="AutoPVS1 upstream timed out.",
        retryable=True,
        tool_name="get_variant_pvs1_data",
    )
    assert envelope["meta"]["retry_after_ms"] == 1000
    assert envelope["meta"]["cost_tier"] == "expensive_cold_cheap_warm"


def test_error_envelope_meta_no_retry_after_for_input_errors() -> None:
    """Permanent input errors are not retryable; retry_after_ms stays absent."""
    envelope = error_envelope(
        code="invalid_variant_id",
        message="bad",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "retry_after_ms" not in envelope["meta"]


def test_error_envelope_retry_after_ms_can_be_overridden_by_caller() -> None:
    """A 429 / Retry-After upstream header should propagate verbatim."""
    envelope = error_envelope(
        code="upstream_unavailable",
        message="rate limited",
        retryable=True,
        tool_name="get_variant_pvs1_data",
        retry_after_ms=5_000,
    )
    assert envelope["meta"]["retry_after_ms"] == 5_000


# ---------------------------------------------------------------------------
# Recovery hints (Improvement 4)
# ---------------------------------------------------------------------------


def test_error_envelope_meta_emits_next_actions_for_known_codes() -> None:
    """Every documented error code must carry recovery hints on the wire.

    LLM consumers reading next_actions can recover in a single follow-up
    call without re-discovering the surface via ToolSearch.
    """
    envelope = error_envelope(
        code="invalid_variant_id",
        message="bad id",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    actions = envelope["meta"]["next_actions"]
    assert isinstance(actions, list) and actions
    assert any("CHROM-POS-REF-ALT" in step for step in actions)


def test_error_envelope_meta_drops_next_actions_for_unknown_codes() -> None:
    """An unregistered code keeps next_actions absent (forward-compat)."""
    envelope = error_envelope(
        code="future_unknown_code",
        message="x",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "next_actions" not in envelope["meta"]


def test_success_envelope_meta_drops_next_actions() -> None:
    """next_actions belongs only on errors; success envelopes drop it."""
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))
    assert "next_actions" not in envelope["meta"]


def test_every_known_error_code_has_next_actions_registered() -> None:
    """Drift guard: every code in KNOWN_ERROR_CODES needs a recovery list.

    When a new error code lands, its recovery hints must land in the
    same commit so LLM consumers never see an error without a
    next-step plan.
    """
    from autopvs1_link.mcp.registries import ERROR_NEXT_ACTIONS, KNOWN_ERROR_CODES

    missing = sorted(set(KNOWN_ERROR_CODES) - set(ERROR_NEXT_ACTIONS))
    assert not missing, (
        f"KNOWN_ERROR_CODES has codes without ERROR_NEXT_ACTIONS hints: "
        f"{missing}. Add recovery hints in registries.py so the wire's "
        "meta.next_actions[] stays populated."
    )


def test_every_next_action_code_is_a_known_error_code() -> None:
    """Reverse drift guard: no orphaned hints for deleted codes."""
    from autopvs1_link.mcp.registries import ERROR_NEXT_ACTIONS, KNOWN_ERROR_CODES

    orphans = sorted(set(ERROR_NEXT_ACTIONS) - set(KNOWN_ERROR_CODES))
    assert not orphans, f"ERROR_NEXT_ACTIONS has codes not in KNOWN_ERROR_CODES: {orphans}"


def test_every_recovery_hint_is_non_empty_and_actionable() -> None:
    """Every hint must be a non-empty string; LLMs read these verbatim."""
    from autopvs1_link.mcp.registries import ERROR_NEXT_ACTIONS

    for code, actions in ERROR_NEXT_ACTIONS.items():
        assert actions, f"{code}: empty next_actions list"
        for index, step in enumerate(actions):
            assert isinstance(step, str) and step.strip(), (
                f"{code}[{index}]: empty / non-string step {step!r}"
            )


# ---------------------------------------------------------------------------
# Error-envelope cost-hint honesty (v1.2)
# ---------------------------------------------------------------------------


def test_error_envelope_drops_cost_tier_for_input_errors() -> None:
    """Permanent input errors short-circuit before upstream — drop the cost hint.

    Pre-fix: invalid_genome_build echoed cost_tier='expensive_cold_cheap_warm'
    and rate_limit_floor_ms=1000 even though no upstream call happened.
    That misled cost-aware LLM dispatchers into budgeting a cost the
    call never paid. The transient error codes (which DO hit upstream
    and whose retry will too) keep the hints.
    """
    envelope = error_envelope(
        code="invalid_genome_build",
        message="bad build",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "cost_tier" not in envelope["meta"]
    assert "rate_limit_floor_ms" not in envelope["meta"]


def test_error_envelope_drops_cost_tier_for_invalid_variant_id() -> None:
    envelope = error_envelope(
        code="invalid_variant_id",
        message="bad",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "cost_tier" not in envelope["meta"]
    assert "rate_limit_floor_ms" not in envelope["meta"]


def test_error_envelope_drops_cost_tier_for_requires_disambiguation() -> None:
    """Multi-candidate resolver outcome doesn't retry — drop cost hints."""
    envelope = error_envelope(
        code="requires_disambiguation",
        message="multi",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "cost_tier" not in envelope["meta"]
    assert "rate_limit_floor_ms" not in envelope["meta"]


def test_error_envelope_keeps_cost_tier_for_upstream_unavailable() -> None:
    """Transient upstream errors keep cost hints for retry budgeting."""
    envelope = error_envelope(
        code="upstream_unavailable",
        message="down",
        retryable=True,
        tool_name="get_variant_pvs1_data",
    )
    assert envelope["meta"]["cost_tier"] == "expensive_cold_cheap_warm"
    assert envelope["meta"]["rate_limit_floor_ms"] == 1000
    assert envelope["meta"]["retry_after_ms"] == 1000


def test_error_envelope_keeps_cost_tier_for_external_resolver_unavailable() -> None:
    envelope = error_envelope(
        code="external_resolver_unavailable",
        message="recoder down",
        retryable=True,
        tool_name="get_variant_pvs1_data",
    )
    assert envelope["meta"]["cost_tier"] == "expensive_cold_cheap_warm"
    assert envelope["meta"]["rate_limit_floor_ms"] == 1000


def test_ok_envelope_bulk_mixed_aggregate_overrides_telemetry() -> None:
    """ok_envelope must let bulk supply an aggregate, ignoring the ContextVar."""
    from autopvs1_link.mcp.telemetry import record_upstream_call, reset_call_telemetry
    from autopvs1_link.models.autopvs1_models import CNVInfo

    # Seed the ContextVar to a per-item value the bulk tool wants to override.
    record_upstream_call(elapsed_ms=99.0, cache_status="hit")
    try:
        envelope = ok_envelope(
            CNVInfo(
                cnv_id="11-2797090-2869333-DEL",
                cnv_type="Deletion",
                gene_symbol="GENE",
                coordinates="11-2797090-2869333-DEL",
            ),
            tool_name="get_variants_pvs1_data_bulk",
            cache_status_override="mixed",
            elapsed_ms_override=1505.0,
            cached_count=1,
            uncached_count=1,
        )
        assert envelope["meta"]["cache_status"] == "mixed"
        assert envelope["meta"]["elapsed_ms"] == 1505.0
        assert envelope["meta"]["cached_count"] == 1
        assert envelope["meta"]["uncached_count"] == 1
    finally:
        reset_call_telemetry()
