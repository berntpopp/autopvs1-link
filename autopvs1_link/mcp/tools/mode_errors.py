"""Helpers for returning structured mode validation errors from tools."""

from __future__ import annotations

from autopvs1_link.mcp.envelope import ErrorToolResult, error_envelope
from autopvs1_link.mcp.mode_validation import InvalidMCPModeError, MetaMode


def external_egress_disabled_error() -> dict[str, object]:
    """Return the stable deployment-policy error contract."""
    return {
        "code": "external_egress_disabled",
        "message": "External variant transfer is disabled by deployment policy.",
        "retryable": False,
        "suggestions": [
            "Use a deployment with an explicitly approved AutoPVS1 upstream.",
            "Do not submit patient-derived variants to a public research instance.",
        ],
    }


def external_egress_disabled_envelope(
    *,
    meta_mode: MetaMode = "full",
    tool_name: str | None = None,
) -> ErrorToolResult:
    """Return the deployment-policy error as an MCP envelope."""
    return error_envelope(
        code="external_egress_disabled",
        message="External variant transfer is disabled by deployment policy.",
        retryable=False,
        suggestions=[
            "Use a deployment with an explicitly approved AutoPVS1 upstream.",
            "Do not submit patient-derived variants to a public research instance.",
        ],
        meta_mode=meta_mode,
        tool_name=tool_name,
    )


def invalid_mode_envelope(
    exc: InvalidMCPModeError,
    *,
    meta_mode: MetaMode = "full",
    tool_name: str | None = None,
) -> ErrorToolResult:
    """Return an input-error envelope for unsupported response/meta modes.

    ``tool_name`` is threaded through so the error envelope picks up the
    correct ``meta.cost_tier`` / ``meta.rate_limit_floor_ms`` hints.
    """
    return error_envelope(
        code=exc.code,
        message=str(exc),
        retryable=exc.retryable,
        suggestions=exc.suggestions,
        meta_mode=meta_mode,
        tool_name=tool_name,
    )
