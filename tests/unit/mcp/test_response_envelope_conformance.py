"""Conformance tests for the GeneFoundry Response-Envelope Standard v1 banner.

Locks in the flat frame: success responses carry ``success``/``result`` (or
``results`` for collection tools) plus ``_meta``; failures carry a flat
``error_code``/``message``/``retryable``/``recovery_action`` plus ``_meta``
and set MCP ``isError=true``. See
``docs/RESPONSE-ENVELOPE-STANDARD-v1.md`` (genefoundry-router-standards).
"""

from __future__ import annotations

from autopvs1_link.mcp.contracts import ClearCacheData
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope, success_output_schema


def test_ok_envelope_single_item_uses_flat_success_banner() -> None:
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        tool_name="clear_cache",
    )

    assert envelope["success"] is True
    assert envelope["result"] == {"cleared": True, "message": "cleared"}
    assert "results" not in envelope
    assert "ok" not in envelope
    assert "data" not in envelope
    assert "meta" not in envelope
    assert "_meta" in envelope
    assert envelope["_meta"]["tool"] == "clear_cache"


def test_ok_envelope_meta_carries_response_envelope_standard_fields() -> None:
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        tool_name="clear_cache",
    )
    meta = envelope["_meta"]

    assert meta["unsafe_for_clinical_use"] is True
    assert "request_id" in meta
    assert "capabilities_version" in meta
    assert meta["tool"] == "clear_cache"


def test_ok_envelope_collection_hoists_field_to_top_level_results() -> None:
    envelope = ok_envelope(
        {"query": "BRCA1", "total_count": 2, "results": [{"id": "a"}, {"id": "b"}]},
        tool_name="search_variants",
        collection_field="results",
    )

    assert envelope["success"] is True
    assert envelope["results"] == [{"id": "a"}, {"id": "b"}]
    # Sibling domain keys sit beside `results`, not nested under it.
    assert envelope["query"] == "BRCA1"
    assert envelope["total_count"] == 2
    assert "result" not in envelope


def test_ok_envelope_collection_renames_domain_alias_to_results() -> None:
    """A collection field named e.g. ``items`` still surfaces as top-level ``results``.

    Response-Envelope Standard v1 §1: the primary payload key is always
    ``results``/``result`` -- never a domain-specific alias.
    """
    envelope = ok_envelope(
        {"total": 1, "items": [{"variant_id": "X-1-A-T"}]},
        tool_name="get_variants_pvs1_data_bulk",
        collection_field="items",
    )

    assert envelope["results"] == [{"variant_id": "X-1-A-T"}]
    assert envelope["total"] == 1
    assert "items" not in envelope


def test_error_envelope_uses_flat_error_banner() -> None:
    result = error_envelope(
        code="invalid_variant_id",
        message="Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
        retryable=False,
        suggestions=["Use search_variants with a gene symbol."],
        tool_name="get_variant_pvs1_data",
    )
    payload = result.structured_content

    assert payload["success"] is False
    assert payload["error_code"] == "invalid_variant_id"
    assert payload["message"] == ("Variant IDs must use AutoPVS1 format such as X-82763936-A-T.")
    assert payload["retryable"] is False
    assert payload["recovery_action"] == "Use search_variants with a gene symbol."
    assert "error" not in payload
    assert "ok" not in payload
    assert "_meta" in payload


def test_error_envelope_sets_mcp_is_error_true_on_the_wire() -> None:
    result = error_envelope(
        code="invalid_genome_build",
        message="bad build",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )

    mcp_result = result.to_mcp_result()

    assert mcp_result.isError is True
    assert result.structured_content["success"] is False


def test_error_envelope_sets_is_error_on_the_instance() -> None:
    """Defensive-correctness regression: FastMCP's caching middleware reads
    ``ToolResult.is_error`` directly (not via ``to_mcp_result()``), so a
    cached error result must carry ``is_error=True`` on the instance itself
    or a cache replay would unwrap it as ``is_error=False``.
    """
    result = error_envelope(
        code="invalid_genome_build",
        message="bad build",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )

    assert result.is_error is True


def test_error_envelope_recovery_action_falls_back_to_registered_next_action() -> None:
    """Without call-specific suggestions, recovery_action uses the registry hint."""
    result = error_envelope(
        code="not_found",
        message="not found",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    payload = result.structured_content

    assert payload["recovery_action"]
    assert isinstance(payload["recovery_action"], str)


def test_error_envelope_omits_recovery_action_when_no_hint_available() -> None:
    result = error_envelope(
        code="future_unknown_code",
        message="x",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "recovery_action" not in result.structured_content


def test_success_output_schema_single_item_declares_result_key() -> None:
    schema = success_output_schema(ClearCacheData)

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"success", "_meta"}
    assert "result" in schema["properties"]
    assert "results" not in schema["properties"]
    for key in ("error_code", "message", "retryable", "recovery_action"):
        assert key in schema["properties"]


def test_success_output_schema_collection_hoists_field_and_siblings() -> None:
    from autopvs1_link.mcp.contracts import SearchMCPData

    schema = success_output_schema(SearchMCPData, collection_field="results")

    assert "results" in schema["properties"]
    assert "result" not in schema["properties"]
    # Sibling domain keys from SearchMCPData surface at the top level.
    assert "pagination" in schema["properties"]
    assert "total_count" in schema["properties"]
