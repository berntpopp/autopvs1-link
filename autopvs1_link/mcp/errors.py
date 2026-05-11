"""MCP error envelopes."""

from __future__ import annotations

from typing import Any


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
