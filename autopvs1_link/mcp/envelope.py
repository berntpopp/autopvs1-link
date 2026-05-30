"""Standard MCP response envelopes and metadata."""

from __future__ import annotations

import json
from typing import Any, TypeVar
from uuid import uuid4

from asgi_correlation_id.context import correlation_id
from fastmcp.tools.base import ToolResult
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from autopvs1_link import __version__
from autopvs1_link.mcp.mode_validation import MetaMode, normalize_meta_mode
from autopvs1_link.mcp.telemetry import get_call_telemetry


class ErrorToolResult(ToolResult):
    """ToolResult subclass that flips ``CallToolResult.isError=True`` on the wire.

    The structured envelope is unchanged — clients that parse ``ok/data/error``
    keep working — but MCP-spec-compliant clients can now distinguish failed
    calls via ``CallToolResult.isError`` without parsing the envelope.

    Dict-like accessors delegate to ``structured_content`` so existing call
    sites and tests that index the envelope continue to work.
    """

    def __getitem__(self, key: str) -> Any:
        if self.structured_content is None:
            raise KeyError(key)
        return self.structured_content[key]

    def __contains__(self, key: object) -> bool:
        return self.structured_content is not None and key in self.structured_content

    def get(self, key: str, default: Any = None) -> Any:
        if self.structured_content is None:
            return default
        return self.structured_content.get(key, default)

    def to_mcp_result(self) -> CallToolResult:
        return CallToolResult(
            content=self.content,
            structuredContent=self.structured_content,
            isError=True,
            _meta=self.meta,
        )


# Tool handlers return either a plain dict envelope (success path) or an
# ErrorToolResult (error path that flips ``CallToolResult.isError=true`` on the
# wire). FastMCP handles both forms; expose a single alias so tool signatures
# stay readable.
type ToolResponse = dict[str, Any] | ErrorToolResult

DataT = TypeVar("DataT")


class RecommendedCitation(BaseModel):
    """Recommended citation for AutoPVS1 research-use outputs."""

    text: str = (
        "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic "
        "classification tool for PVS1 interpretation of null variants. "
        "Human Mutation. 2020;41(9):1488-1498."
    )
    doi: str = "10.1002/humu.24051"
    pmid: str = "32442321"
    url: str = "https://pubmed.ncbi.nlm.nih.gov/32442321/"


class MCPWarning(BaseModel):
    """Structured non-fatal warning for LLM callers.

    ``count`` and ``affected_indices`` are populated only when this warning
    aggregates per-item occurrences in a bulk call. Single-tool warnings
    leave them ``None`` and they drop out of the wire payload via
    ``exclude_none`` on the per-item meta serialization path.
    """

    code: str
    message: str
    count: int | None = None
    affected_indices: list[int] | None = None


class MCPError(BaseModel):
    """Structured MCP tool error."""

    code: str
    message: str
    retryable: bool
    suggestions: list[str] = Field(default_factory=list)
    details: SkipJsonSchema[dict[str, Any] | None] = None


class MCPMeta(BaseModel):
    """Common metadata on every MCP tool envelope.

    ``effective_chars`` is the byte length of the serialized ``data`` field
    (compact JSON). It lets LLM callers calibrate against the advertised
    per-mode ``char_budget`` after the first call instead of guessing.

    ``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's
    wall-clock time and cache outcome (``hit`` | ``miss`` | ``bypass``).
    Populated by the cache wrapper via the telemetry ContextVar; both
    drop from the wire when the tool made no upstream call (e.g.
    ``get_server_health`` or ``get_server_capabilities``).
    """

    request_id: str = Field(default_factory=lambda: correlation_id.get() or str(uuid4()))
    server_version: str = __version__
    research_use_only: bool = True
    recommended_citation: RecommendedCitation = Field(default_factory=RecommendedCitation)
    warnings: list[MCPWarning] = Field(default_factory=list)
    effective_chars: int | None = None
    elapsed_ms: float | None = None
    cache_status: str | None = None


class MCPEnvelope[DataT](BaseModel):
    """Standard MCP tool response envelope."""

    ok: bool
    data: DataT | None
    error: MCPError | None
    meta: MCPMeta


def _dump_warning(warning: MCPWarning) -> dict[str, Any]:
    return warning.model_dump(mode="json")


def _normalize_meta_mode(meta_mode: Any) -> MetaMode:
    return normalize_meta_mode(meta_mode)


def _apply_meta_mode(payload: dict[str, Any], meta_mode: Any) -> dict[str, Any]:
    mode = _normalize_meta_mode(meta_mode)
    meta = payload["meta"]
    if mode == "compact":
        citation = RecommendedCitation()
        meta["recommended_citation"] = {
            "doi": citation.doi,
            "pmid": citation.pmid,
        }
    elif mode == "minimal":
        meta.pop("recommended_citation", None)
    return payload


def _strip_none_error_details(node: Any) -> Any:
    """Recursively drop ``error.details`` keys whose value is ``None``.

    Single-tool errors pop the key in ``error_envelope``; bulk per-item
    errors are nested in ``data.items[*].error`` and would otherwise leak
    ``"details": null``. This walker keeps the contract symmetric.
    """
    if isinstance(node, dict):
        err = node.get("error")
        if isinstance(err, dict) and err.get("details") is None and "details" in err:
            err.pop("details", None)
        for value in node.values():
            _strip_none_error_details(value)
    elif isinstance(node, list):
        for value in node:
            _strip_none_error_details(value)
    return node


def _strip_none_telemetry_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop ``elapsed_ms``/``cache_status`` from meta when no upstream call ran.

    Cheap tools (``get_server_health``, ``get_server_capabilities``) never
    touch the upstream; the telemetry ContextVar stays at its default
    ``None`` and the fields would otherwise ship as ``null`` and mislead
    callers reading them as ``0ms``.
    """
    meta = payload.get("meta")
    if isinstance(meta, dict):
        for key in ("elapsed_ms", "cache_status"):
            if meta.get(key) is None:
                meta.pop(key, None)
    return payload


def _strip_none_warning_aggregate_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop ``count``/``affected_indices`` from any warning where they are None.

    Pydantic emits them as ``null`` by default; we want them absent for
    single-tool callers and present (non-null) for aggregated bulk warnings.
    """
    meta = payload.get("meta")
    if isinstance(meta, dict):
        warnings = meta.get("warnings") or []
        for warning in warnings:
            if isinstance(warning, dict):
                for key in ("count", "affected_indices"):
                    if warning.get(key) is None:
                        warning.pop(key, None)
    return payload


def ok_envelope(
    data: BaseModel | dict[str, Any],
    warnings: list[MCPWarning] | None = None,
    *,
    meta_mode: Any = "full",
) -> dict[str, Any]:
    """Return a successful MCP envelope as a JSON-ready dict.

    Null leaves are always stripped from the inner data dump so the wire
    payload reflects the response_mode-shaped contract rather than the
    Pydantic schema's optional-with-default-None scaffolding. The outer
    envelope ``ok``/``data``/``error``/``meta`` shape is preserved so the
    documented ``required_fields`` contract still holds.
    """
    if isinstance(data, BaseModel):
        payload = data.model_dump(mode="json", exclude_none=True)
    else:
        payload = data
    effective_chars = len(json.dumps(payload, separators=(",", ":")))
    elapsed_ms, cache_status = get_call_telemetry()
    envelope: MCPEnvelope[Any] = MCPEnvelope(
        ok=True,
        data=payload,
        error=None,
        meta=MCPMeta(
            warnings=warnings or [],
            effective_chars=effective_chars,
            elapsed_ms=round(elapsed_ms, 2) if elapsed_ms is not None else None,
            cache_status=cache_status,
        ),
    )
    out = _apply_meta_mode(envelope.model_dump(mode="json"), meta_mode)
    cleaned = _strip_none_error_details(out)
    assert isinstance(cleaned, dict)
    cleaned = _strip_none_warning_aggregate_fields(cleaned)
    cleaned = _strip_none_telemetry_fields(cleaned)
    return cleaned


def error_envelope(
    *,
    code: str,
    message: str,
    retryable: bool,
    suggestions: list[str] | None = None,
    details: dict[str, Any] | None = None,
    warnings: list[MCPWarning] | None = None,
    meta_mode: Any = "full",
) -> ErrorToolResult:
    """Return a failed MCP result that flips ``CallToolResult.isError=true``.

    The structured payload retains the canonical ``ok/data/error/meta`` shape,
    so dict-style callers (and existing tests) keep working. The wire-level
    ``isError`` flag is set so MCP-spec clients can distinguish failed calls
    from successful ones without parsing the envelope.
    """
    envelope: MCPEnvelope[Any] = MCPEnvelope(
        ok=False,
        data=None,
        error=MCPError(
            code=code,
            message=message,
            retryable=retryable,
            suggestions=suggestions or [],
            details=details,
        ),
        meta=MCPMeta(warnings=warnings or []),
    )
    payload = envelope.model_dump(mode="json")
    if payload["error"]["details"] is None:
        payload["error"].pop("details")
    payload = _apply_meta_mode(payload, meta_mode)
    payload = _strip_none_warning_aggregate_fields(payload)
    return ErrorToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, separators=(",", ":")))],
        structured_content=payload,
    )
