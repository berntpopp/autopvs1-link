"""Validation for MCP response and metadata detail modes."""

from __future__ import annotations

from typing import Any, Literal, cast

ResponseMode = Literal["ids_only", "summary", "standard", "full"]
MetaMode = Literal["full", "compact", "minimal"]

_RESPONSE_MODES = {"ids_only", "summary", "standard", "full"}
_META_MODES = {"full", "compact", "minimal"}


class InvalidMCPModeError(ValueError):
    """Unsupported MCP mode value supplied by a caller."""

    def __init__(
        self,
        *,
        code: str,
        parameter: str,
        value: Any,
        supported_values: str,
        suggestions: list[str],
    ) -> None:
        super().__init__(
            f"Unsupported {parameter} value {value!r}. "
            f"{parameter} must be one of {supported_values}."
        )
        self.code = code
        self.retryable = False
        self.suggestions = suggestions


def normalize_response_mode(response_mode: Any) -> ResponseMode:
    """Return a validated response detail mode."""
    if isinstance(response_mode, str):
        normalized = response_mode.lower()
        if normalized in _RESPONSE_MODES:
            return cast(ResponseMode, normalized)
    raise InvalidMCPModeError(
        code="invalid_response_mode",
        parameter="response_mode",
        value=response_mode,
        supported_values="ids_only, summary, standard, or full",
        suggestions=[
            "Use response_mode='standard' unless a smaller (ids_only/summary) "
            "or audit-trail (full) payload is needed."
        ],
    )


def normalize_meta_mode(meta_mode: Any) -> MetaMode:
    """Return a validated metadata detail mode."""
    if isinstance(meta_mode, str):
        normalized = meta_mode.lower()
        if normalized in _META_MODES:
            return cast(MetaMode, normalized)
    raise InvalidMCPModeError(
        code="invalid_meta_mode",
        parameter="meta_mode",
        value=meta_mode,
        supported_values="full, compact, or minimal",
        suggestions=["Use meta_mode='full' unless compact or minimal metadata is needed."],
    )
