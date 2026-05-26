"""Standard MCP response envelopes and metadata."""

from __future__ import annotations

from typing import Any, TypeVar
from uuid import uuid4

from asgi_correlation_id.context import correlation_id
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from autopvs1_link import __version__
from autopvs1_link.mcp.mode_validation import MetaMode, normalize_meta_mode

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
    """Structured non-fatal warning for LLM callers."""

    code: str
    message: str


class MCPError(BaseModel):
    """Structured MCP tool error."""

    code: str
    message: str
    retryable: bool
    suggestions: list[str] = Field(default_factory=list)
    details: SkipJsonSchema[dict[str, Any] | None] = None


class MCPMeta(BaseModel):
    """Common metadata on every MCP tool envelope."""

    request_id: str = Field(default_factory=lambda: correlation_id.get() or str(uuid4()))
    server_version: str = __version__
    research_use_only: bool = True
    recommended_citation: RecommendedCitation = Field(default_factory=RecommendedCitation)
    warnings: list[MCPWarning] = Field(default_factory=list)


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


def ok_envelope(
    data: BaseModel | dict[str, Any],
    warnings: list[MCPWarning] | None = None,
    *,
    meta_mode: Any = "full",
) -> dict[str, Any]:
    """Return a successful MCP envelope as a JSON-ready dict."""
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    envelope: MCPEnvelope[Any] = MCPEnvelope(
        ok=True,
        data=payload,
        error=None,
        meta=MCPMeta(warnings=warnings or []),
    )
    return _apply_meta_mode(envelope.model_dump(mode="json"), meta_mode)


def error_envelope(
    *,
    code: str,
    message: str,
    retryable: bool,
    suggestions: list[str] | None = None,
    details: dict[str, Any] | None = None,
    warnings: list[MCPWarning] | None = None,
    meta_mode: Any = "full",
) -> dict[str, Any]:
    """Return a failed MCP envelope as a JSON-ready dict."""
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
    return _apply_meta_mode(payload, meta_mode)
