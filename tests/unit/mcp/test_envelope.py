"""Tests for MCP envelope metadata, warnings, and errors."""

from uuid import UUID

from autopvs1_link.mcp.contracts import ClearCacheData, ClearCacheMCPEnvelope
from autopvs1_link.mcp.envelope import MCPWarning, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError


def test_ok_envelope_contains_required_metadata() -> None:
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))

    assert envelope["ok"] is True
    assert envelope["data"] == {"cleared": True, "message": "cleared"}
    assert envelope["error"] is None
    assert envelope["meta"]["server_version"] == "1.0.0"
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
