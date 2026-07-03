"""Standard MCP response envelopes and metadata."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar
from uuid import uuid4

from asgi_correlation_id.context import correlation_id
from fastmcp.tools.base import ToolResult
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from autopvs1_link import __version__
from autopvs1_link.config import settings
from autopvs1_link.mcp.cost_tiers import SCRAPE_TIER, cold_latency_ms_for, cost_tier_for
from autopvs1_link.mcp.mode_validation import MetaMode, normalize_meta_mode
from autopvs1_link.mcp.next_commands import error_next_commands
from autopvs1_link.mcp.registries import capabilities_version, next_actions_for
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
    """Common metadata carried in the ``_meta`` block of every MCP tool envelope.

    Response-Envelope Standard v1 field canon: ``tool``, ``request_id``,
    tiered ``next_commands``, ``capabilities_version``, and provenance
    (``recommended_citation``, ``unsafe_for_clinical_use``). ``tool`` and
    ``capabilities_version`` are populated by :func:`ok_envelope` /
    :func:`error_envelope`; callers never set them directly.

    ``effective_chars`` is the byte length of the serialized ``data`` field
    (compact JSON). It lets LLM callers calibrate against the advertised
    per-mode ``char_budget`` after the first call instead of guessing.

    ``elapsed_ms`` and ``cache_status`` echo the LAST upstream call's
    wall-clock time and cache outcome (``hit`` | ``miss`` | ``coalesced``
    | ``bypass``). Populated by the cache wrapper via the telemetry
    ContextVar; both drop from the wire when the tool made no upstream
    call (e.g. ``get_server_health`` or ``get_server_capabilities``).

    ``cost_tier`` is a coarse latency hint sourced from
    :data:`autopvs1_link.mcp.cost_tiers.TOOL_COST_TIERS`. The same value
    appears in the detailed capabilities resource so the wire and the
    discovery doc stay in lockstep. LLM callers use it to plan call
    sequencing without re-fetching capabilities every turn.

    ``rate_limit_floor_ms`` is the configured AutoPVS1 upstream gap
    (default 1000 ms; tunable via
    ``AUTOPVS1_LINK_API_RATE_LIMIT_DELAY``). Surfaced only on
    scrape-tier envelopes since it is meaningless for cheap tools.

    ``next_call_earliest_at`` is an ISO-8601 UTC timestamp populated
    only when this call actually drove an upstream request
    (``cache_status in {"miss", "coalesced"}``) — those reset the
    rate-limit clock, so the next upstream call is gated until that
    instant. ``hit`` / ``bypass`` cannot determine the next earliest
    time (the clock may already have elapsed), so the field stays
    absent.

    ``retry_after_ms`` populates only on error envelopes for which the
    caller can sensibly retry after a delay; on success envelopes it
    drops from the wire.

    ``next_actions`` is a per-error-code list of recovery hints
    sourced from
    :data:`autopvs1_link.mcp.registries.ERROR_NEXT_ACTIONS`. Populates
    on every error envelope so a failing LLM dispatcher can pick the
    next move without paying a ToolSearch round-trip to re-discover
    the surface; absent on success envelopes.

    ``cached_count`` and ``uncached_count`` populate only on bulk
    success envelopes when items had mixed cache outcomes. In that
    case ``cache_status='mixed'`` and the counts split items by
    whether they returned warm (``hit`` + ``coalesced``) or cold
    (``miss`` + ``bypass``). Unanimous batches emit the single
    underlying status and drop both counts. Cheap and single-tool
    envelopes never carry these.
    """

    tool: str | None = None
    request_id: str = Field(default_factory=lambda: correlation_id.get() or str(uuid4()))
    server_version: str = __version__
    capabilities_version: str | None = None
    unsafe_for_clinical_use: bool = True
    recommended_citation: RecommendedCitation = Field(default_factory=RecommendedCitation)
    warnings: list[MCPWarning] = Field(default_factory=list)
    effective_chars: int | None = None
    elapsed_ms: float | None = None
    cache_status: str | None = None
    cost_tier: str | None = None
    rate_limit_floor_ms: int | None = None
    next_call_earliest_at: str | None = None
    expected_cold_latency_ms: int | None = None
    retry_after_ms: int | None = None
    next_actions: list[str] | None = None
    next_commands: list[dict[str, Any]] | None = None
    cached_count: int | None = None
    uncached_count: int | None = None


def _dump_warning(warning: MCPWarning) -> dict[str, Any]:
    return warning.model_dump(mode="json")


def _normalize_meta_mode(meta_mode: Any) -> MetaMode:
    return normalize_meta_mode(meta_mode)


def _split_defs(schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pop ``$defs`` off a pydantic JSON Schema so it can be re-hoisted to a new root.

    ``$ref`` pointers (``#/$defs/Foo``) resolve against the schema ROOT, so
    nesting a model's own schema as a property value only stays valid if
    its ``$defs`` are hoisted alongside it rather than left nested.
    """
    schema = dict(schema)
    defs = schema.pop("$defs", {})
    schema.pop("title", None)
    return schema, defs


def success_output_schema(
    data_model: type[BaseModel],
    *,
    collection_field: str | None = None,
) -> dict[str, Any]:
    """Build the MCP ``outputSchema`` for the flat Response-Envelope v1 banner.

    Single-item tools (``collection_field=None``) get ``data_model``'s own
    schema embedded as the ``result`` object. Collection tools pass the
    ``data_model`` field name whose array becomes the canonical top-level
    ``results`` key (Response-Envelope Standard v1 §1); every other field
    on ``data_model`` becomes a sibling top-level key (e.g. ``pagination``,
    ``total_count``) rather than a nested alias.

    The frame declares both the success shape (``result``/``results``) and
    the flat error shape (``error_code``/``message``/``retryable``/
    ``recovery_action``) as optional properties on one schema, matching the
    envelope's existing non-discriminated-union pattern: a given response is
    one or the other, never both.
    """
    inner, inner_defs = _split_defs(data_model.model_json_schema())
    meta_schema, meta_defs = _split_defs(MCPMeta.model_json_schema())
    properties: dict[str, Any] = {
        "success": {"type": "boolean"},
        "error_code": {"type": "string"},
        "message": {"type": "string"},
        "retryable": {"type": "boolean"},
        "recovery_action": {"type": "string"},
        "_meta": meta_schema,
    }
    if collection_field is None:
        properties["result"] = inner
    else:
        inner_properties = dict(inner.get("properties", {}))
        results_schema = inner_properties.pop(collection_field, {"type": "array"})
        properties["results"] = results_schema
        properties.update(inner_properties)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": ["success", "_meta"],
    }
    defs = {**inner_defs, **meta_defs}
    if defs:
        schema["$defs"] = defs
    return schema


def _apply_meta_mode(payload: dict[str, Any], meta_mode: Any) -> dict[str, Any]:
    mode = _normalize_meta_mode(meta_mode)
    meta = payload["_meta"]
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
    """Drop telemetry / cost-hint meta keys whose value is None.

    Cheap tools (``get_server_health``, ``get_server_capabilities``) never
    touch the upstream; the telemetry ContextVar stays at its default
    ``None`` and the fields would otherwise ship as ``null`` and mislead
    callers reading them as ``0ms`` or as advertised latency hints that
    do not apply. ``retry_after_ms`` is also stripped on success
    envelopes. ``tool`` drops when a low-level caller built an envelope
    without threading ``tool_name`` through (every registered MCP tool
    passes it; this only affects internal/unit-test call sites).
    """
    meta = payload.get("_meta")
    if isinstance(meta, dict):
        for key in (
            "tool",
            "effective_chars",
            "elapsed_ms",
            "cache_status",
            "cost_tier",
            "rate_limit_floor_ms",
            "next_call_earliest_at",
            "retry_after_ms",
            "next_actions",
            "next_commands",
            "expected_cold_latency_ms",
            "cached_count",
            "uncached_count",
        ):
            if meta.get(key) is None:
                meta.pop(key, None)
    return payload


def _rate_limit_floor_ms() -> int:
    """Return the configured AutoPVS1 upstream rate-limit floor in ms."""
    return int(settings.api.rate_limit_delay * 1000)


def _cost_hints_for(
    tool_name: str | None,
    cache_status: str | None,
) -> tuple[str | None, int | None, str | None]:
    """Compute ``(cost_tier, rate_limit_floor_ms, next_call_earliest_at)``.

    ``next_call_earliest_at`` populates only when the call drove a real
    upstream request — ``cache_status`` of ``miss`` or ``coalesced``
    means the rate-limit clock reset and the next upstream call is
    gated until ``floor_ms`` past now.
    """
    tier = cost_tier_for(tool_name)
    if tier != SCRAPE_TIER:
        return tier, None, None
    floor_ms = _rate_limit_floor_ms()
    next_at: str | None = None
    if cache_status in ("miss", "coalesced"):
        next_at = (datetime.now(UTC) + timedelta(milliseconds=floor_ms)).isoformat()
    return tier, floor_ms, next_at


def _strip_none_warning_aggregate_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Drop ``count``/``affected_indices`` from any warning where they are None.

    Pydantic emits them as ``null`` by default; we want them absent for
    single-tool callers and present (non-null) for aggregated bulk warnings.
    """
    meta = payload.get("_meta")
    if isinstance(meta, dict):
        warnings = meta.get("warnings") or []
        for warning in warnings:
            if isinstance(warning, dict):
                for key in ("count", "affected_indices"):
                    if warning.get(key) is None:
                        warning.pop(key, None)
    return payload


_RETRYABLE_TRANSIENT_CODES = frozenset(
    {"upstream_timeout", "upstream_unavailable", "external_resolver_unavailable"}
)


def _recovery_action_for(
    suggestions: list[str] | None,
    next_actions: list[str] | None,
) -> str | None:
    """Pick one imperative hint for the flat banner's ``recovery_action``.

    Prefers the call-specific ``suggestions`` (more precise for this exact
    failure) over the generic per-code ``next_actions`` registry entry, so
    the model gets the single most actionable instruction. ``None`` when
    neither is available (kept absent from the wire, not null).
    """
    if suggestions:
        return suggestions[0]
    if next_actions:
        return next_actions[0]
    return None


def ok_envelope(
    data: BaseModel | dict[str, Any],
    warnings: list[MCPWarning] | None = None,
    *,
    meta_mode: Any = "compact",
    tool_name: str | None = None,
    cache_status_override: str | None = None,
    elapsed_ms_override: float | None = None,
    cached_count: int | None = None,
    uncached_count: int | None = None,
    next_commands: list[dict[str, Any]] | None = None,
    collection_field: str | None = None,
) -> dict[str, Any]:
    """Return a successful MCP envelope as a JSON-ready dict (Response-Envelope Standard v1).

    Null leaves are always stripped from the inner data dump so the wire
    payload reflects the response_mode-shaped contract rather than the
    Pydantic schema's optional-with-default-None scaffolding. The outer
    frame is the flat banner: ``{"success": true, "result"|"results": ...,
    "_meta": {...}}`` — never a nested wrapper.

    ``collection_field`` names the field on ``data`` (once dumped) whose
    list value is hoisted to the canonical top-level ``results`` key; every
    other field on ``data`` becomes a sibling top-level key (e.g. a search
    page's ``pagination``, ``total_count``). ``None`` (default) keeps the
    whole dump as the single top-level ``result`` object.

    ``tool_name`` enables cost-tier and rate-limit-floor hints in
    ``_meta``, and is echoed verbatim as ``_meta.tool``; pass the declared
    MCP tool name (e.g. ``"get_variant_pvs1_data"``) so the envelope can
    look up the tier registered in :mod:`autopvs1_link.mcp.cost_tiers`
    without each caller hard-coding the value.

    ``cache_status_override`` and ``elapsed_ms_override`` let bulk tools
    supply an aggregate across per-item upstream calls instead of the
    ContextVar telemetry's last-call-only signal. Pass
    ``cache_status='mixed'`` plus the matching ``cached_count`` /
    ``uncached_count`` to document a batch with heterogeneous cache
    outcomes. When unset, single-tool callers get the existing
    ContextVar-driven behavior.
    """
    if isinstance(data, BaseModel):
        payload = data.model_dump(mode="json", exclude_none=True)
    else:
        payload = dict(data)
    effective_chars = len(json.dumps(payload, separators=(",", ":")))
    telemetry_elapsed_ms, telemetry_cache_status = get_call_telemetry()
    cache_status = (
        cache_status_override if cache_status_override is not None else telemetry_cache_status
    )
    elapsed_ms = elapsed_ms_override if elapsed_ms_override is not None else telemetry_elapsed_ms
    cost_tier, rate_limit_floor_ms, next_call_earliest_at = _cost_hints_for(tool_name, cache_status)
    expected_cold_latency_ms = (
        cold_latency_ms_for(tool_name) if cache_status in ("miss", "coalesced") else None
    )
    meta = MCPMeta(
        tool=tool_name,
        capabilities_version=capabilities_version(),
        warnings=warnings or [],
        effective_chars=effective_chars,
        elapsed_ms=round(elapsed_ms, 2) if elapsed_ms is not None else None,
        cache_status=cache_status,
        cost_tier=cost_tier,
        rate_limit_floor_ms=rate_limit_floor_ms,
        next_call_earliest_at=next_call_earliest_at,
        expected_cold_latency_ms=expected_cold_latency_ms,
        cached_count=cached_count,
        uncached_count=uncached_count,
        next_commands=next_commands,
    )
    banner: dict[str, Any] = {"success": True}
    if collection_field is None:
        banner["result"] = payload
    else:
        banner["results"] = payload.pop(collection_field, [])
        banner.update(payload)
    banner["_meta"] = meta.model_dump(mode="json")
    out = _apply_meta_mode(banner, meta_mode)
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
    meta_mode: Any = "compact",
    tool_name: str | None = None,
    retry_after_ms: int | None = None,
) -> ErrorToolResult:
    """Return a failed MCP result that flips ``CallToolResult.isError=true``.

    The structured payload is the Response-Envelope Standard v1 flat error
    frame: ``{"success": false, "error_code", "message", "retryable",
    "recovery_action", "_meta"}`` — no nested ``error`` object. The
    wire-level ``isError`` flag is set so MCP-spec clients can distinguish
    failed calls from successful ones without parsing the envelope.

    For transient upstream errors (``upstream_timeout``,
    ``upstream_unavailable``, ``external_resolver_unavailable``) we
    default ``retry_after_ms`` to the rate-limit floor when the caller
    did not supply one, so an LLM client retrying immediately does not
    just block on the floor.

    For permanent input errors (``invalid_variant_id``,
    ``invalid_genome_build``, ``requires_disambiguation``, …) the call
    short-circuited before any upstream contact: ``cost_tier`` and
    ``rate_limit_floor_ms`` are dropped because they would otherwise
    advertise a cost the caller never paid and a clock that never reset.
    The transient error codes — which DID hit upstream and whose retry
    will hit upstream again — keep the cost hints so an LLM scheduling a
    retry sees the real cost.
    """
    tier = cost_tier_for(tool_name)
    upstream_was_contacted = code in _RETRYABLE_TRANSIENT_CODES
    rate_limit_floor_ms = (
        _rate_limit_floor_ms() if tier == SCRAPE_TIER and upstream_was_contacted else None
    )
    cost_tier = tier if upstream_was_contacted else None
    if (
        retry_after_ms is None
        and retryable
        and rate_limit_floor_ms is not None
        and code in _RETRYABLE_TRANSIENT_CODES
    ):
        retry_after_ms = rate_limit_floor_ms
    next_actions = next_actions_for(code)
    meta = MCPMeta(
        tool=tool_name,
        capabilities_version=capabilities_version(),
        warnings=warnings or [],
        cost_tier=cost_tier,
        rate_limit_floor_ms=rate_limit_floor_ms,
        retry_after_ms=retry_after_ms,
        next_actions=next_actions,
        next_commands=error_next_commands(code, details),
    )
    payload: dict[str, Any] = {
        "success": False,
        "error_code": code,
        "message": message,
        "retryable": retryable,
        "recovery_action": _recovery_action_for(suggestions, next_actions),
        "_meta": meta.model_dump(mode="json"),
    }
    if payload["recovery_action"] is None:
        payload.pop("recovery_action")
    if suggestions:
        payload["suggestions"] = suggestions
    if details:
        payload["details"] = details
    payload = _apply_meta_mode(payload, meta_mode)
    payload = _strip_none_warning_aggregate_fields(payload)
    payload = _strip_none_telemetry_fields(payload)
    return ErrorToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, separators=(",", ":")))],
        structured_content=payload,
    )
