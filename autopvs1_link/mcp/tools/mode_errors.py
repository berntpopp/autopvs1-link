"""Helpers for returning structured mode validation errors from tools."""

from __future__ import annotations

from autopvs1_link.mcp.envelope import ErrorToolResult, error_envelope
from autopvs1_link.mcp.mode_validation import InvalidMCPModeError, MetaMode


def invalid_mode_envelope(
    exc: InvalidMCPModeError, *, meta_mode: MetaMode = "full"
) -> ErrorToolResult:
    """Return an input-error envelope for unsupported response/meta modes."""
    return error_envelope(
        code=exc.code,
        message=str(exc),
        retryable=exc.retryable,
        suggestions=exc.suggestions,
        meta_mode=meta_mode,
    )
