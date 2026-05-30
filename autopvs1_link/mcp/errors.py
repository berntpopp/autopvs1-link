"""MCP error envelopes."""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.envelope import ErrorToolResult, error_envelope


class MCPToolError(Exception):
    """Raised by MCP tools to surface a structured error to the client."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "tool_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class UpstreamUnavailableError(MCPToolError):
    """The AutoPVS1 upstream returned an unexpected response or was unreachable."""

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message, code="upstream_unavailable", details=details)


class DestructiveOperationDisabledError(MCPToolError):
    """The caller attempted a destructive operation while gating is off."""

    def __init__(self, op_name: str) -> None:
        super().__init__(
            f"Destructive operation '{op_name}' is disabled. Set "
            "AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true to enable.",
            code="destructive_disabled",
            details={"op": op_name},
        )


class MCPInputError(MCPToolError):
    """Validation error that should be returned as a structured MCP envelope."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        suggestions: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code=code, details=details)
        self.suggestions = suggestions or []
        self.retryable = False

    def to_envelope(self) -> ErrorToolResult:
        return error_envelope(
            code=self.code,
            message=str(self),
            retryable=self.retryable,
            suggestions=self.suggestions,
            details=self.details or None,
        )
