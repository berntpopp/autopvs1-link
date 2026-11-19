"""FastMCP middleware that fences the argument-validation error boundary.

FastMCP validates a tool call's arguments (pydantic) BEFORE the tool body runs.
On failure it raises ``fastmcp.exceptions.ValidationError`` whose message echoes
the raw argument name/value — including a hostile *top-level argument name*
carrying injection prose and control/zero-width/bidi/NUL code points. That path
is NOT covered by ``mask_error_details`` (the framework surfaces the message as a
caller-facing ToolError). This middleware intercepts it and returns the same
fixed ``invalid_input`` envelope the tools use, with the offending argument name
never echoed and only the exception TYPE logged.
"""

from __future__ import annotations

from typing import Any, cast

import structlog
from fastmcp.exceptions import ValidationError as FastMCPValidationError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.base import ToolResult

from autopvs1_link.mcp.envelope import error_envelope
from autopvs1_link.mcp.untrusted_content import sanitize_message

logger = structlog.get_logger()


def _offending_fields(exc: BaseException) -> list[str]:
    """Top-level argument names from the pydantic error behind ``exc`` (walks ``__cause__``)."""
    err: BaseException | None = exc
    while err is not None:
        errors_fn = getattr(err, "errors", None)
        if callable(errors_fn):
            try:
                return list(dict.fromkeys(str(e["loc"][0]) for e in errors_fn() if e.get("loc")))
            except Exception:
                return []
        err = err.__cause__
    return []


class ArgumentValidationGuard(Middleware):
    """Convert FastMCP arg-validation failures into a fixed invalid_input envelope."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: Any,
    ) -> ToolResult:
        try:
            return cast(ToolResult, await call_next(context))
        except FastMCPValidationError as exc:
            # The tool name is a registered identifier (safe), but sanitize it
            # defensively; the offending ARGUMENT name is never surfaced.
            raw_name = getattr(getattr(context, "message", None), "name", None)
            tool_name = sanitize_message(raw_name) if isinstance(raw_name, str) else None
            # Name the VALID parameters (safe, author-declared identifiers) so the
            # model can self-correct — MCP 2025-11-25 SEP-1303 requires a tool
            # execution error to carry actionable feedback. An offending name is
            # echoed/logged ONLY when it is a declared parameter: an unknown key
            # is caller-controlled and could carry injection prose / code points.
            allowed = await self._valid_argument_names(context, raw_name)
            fields = [f for f in _offending_fields(exc) if f in allowed]
            logger.warning(
                "tool argument validation failed",
                tool=tool_name,
                error_type=type(exc).__name__,
                fields=fields,
            )
            if allowed:
                problem = f" Check: {', '.join(fields)}." if fields else ""
                message = (
                    f"One or more tool arguments are missing or invalid.{problem} Valid "
                    f"argument names: {', '.join(allowed)}."
                )
                allowed_values = allowed
            else:
                message = "This tool accepts no arguments; call it with an empty arguments object."
                allowed_values = ["(this tool accepts no arguments)"]
            return error_envelope(
                code="invalid_input",
                message=message,
                retryable=False,
                suggestions=["Call the tool with the documented argument names and types."],
                tool_name=tool_name,
                allowed_values=allowed_values,
            )

    @staticmethod
    async def _valid_argument_names(
        context: MiddlewareContext[Any],
        raw_name: object,
    ) -> list[str]:
        """The tool's declared parameter names, sorted; ``[]`` if not resolvable.

        Read from the registered tool's own inputSchema via the FastMCP context —
        the same resolution NotFoundGuard uses — so the names are author-declared
        identifiers, never caller input.
        """
        fctx = getattr(context, "fastmcp_context", None)
        if fctx is None or not isinstance(raw_name, str):
            return []
        try:
            tool = await fctx.fastmcp.get_tool(raw_name)
            schema = getattr(tool, "parameters", None) or {}
            props = schema.get("properties") or {}
        except Exception:
            return []
        return sorted(str(name) for name in props)
