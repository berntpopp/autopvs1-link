"""FastMCP server facade.

Builds the FastMCP instance and registers tools/resources.
"""

from __future__ import annotations

from fastmcp import FastMCP
from mcp.server.lowlevel.server import NotificationOptions

from autopvs1_link.mcp.metadata import (
    SERVER_DESCRIPTION,
    SERVER_NAME,
    SERVER_VERSION,
    register_metadata,
)


def build_mcp_server() -> FastMCP:
    """Construct and return a configured FastMCP server."""
    mcp = FastMCP(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=SERVER_DESCRIPTION,
        # Do NOT inline every $defs/$ref at each use site (Tool-Surface Budget
        # Standard v1, Rule 4). The constructor defaults this to True and appends
        # DereferenceRefsMiddleware, which amplifies schema size ~1.35x. Turning it
        # off is free and safe: 0/7 of this server's INPUT schemas contain a $ref,
        # so no input-schema client can be affected.
        dereference_schemas=False,
        # Mask UNHANDLED tool/resource exceptions: every expected failure is
        # already returned as a fixed/sanitized error envelope, but an
        # unexpected exception type (e.g. a RuntimeError from a presenter) would
        # otherwise bypass the envelope and surface str(exc) — potentially raw
        # upstream text with control/zero-width/bidi/NUL code points — in the
        # TextContent mirror. Masking replaces it with a fixed "Error calling
        # tool" message; classified ToolError/ResourceError messages (which we
        # author) are still surfaced.
        mask_error_details=True,
    )
    # Spec compliance (MCP 2025-06-18 / basic/lifecycle §Capability Negotiation):
    # advertise listChanged=False because this server never emits
    # notifications/{tools,resources,prompts}/list_changed. Clients can then
    # trust the negotiated capability shape.
    mcp._mcp_server.notification_options = NotificationOptions(
        prompts_changed=False,
        resources_changed=False,
        tools_changed=False,
    )

    # Guard the FastMCP-core not-found reflection surface: core echoes the
    # caller's OWN requested tool name / resource URI / prompt name (with any
    # control/zero-width/bidi/NUL code points) to the caller and to logs BEFORE
    # backend middleware runs. NotFoundGuard preflights the tool NAME (unknown ->
    # fixed name-free envelope) and fixes the on_read_resource boundary; it is
    # added FIRST so it is the OUTERMOST middleware. See notfound_guard.py.
    from autopvs1_link.mcp.notfound_guard import (
        NotFoundGuard,
        install_protocol_error_handler,
        install_validation_log_filter,
    )

    mcp.add_middleware(NotFoundGuard())

    # Fence the arg-validation boundary: FastMCP raises ValidationError (echoing
    # a hostile top-level argument name + control code points) BEFORE its masked
    # generic path. This middleware returns our fixed invalid_input envelope.
    from autopvs1_link.mcp.error_guard import ArgumentValidationGuard

    mcp.add_middleware(ArgumentValidationGuard())

    # Layer 5: scrub FastMCP-core / MCP-SDK validation logs that would echo the
    # caller-supplied name/URI (idempotent; process-global).
    install_validation_log_filter()

    from autopvs1_link.mcp import prompts, resources
    from autopvs1_link.mcp.tools import (
        bulk_tools,
        cache_tools,
        cnv_tool,
        health_tool,
        search_tool,
        variant_tool,
    )

    register_metadata(mcp)
    health_tool.register(mcp)
    variant_tool.register(mcp)
    cnv_tool.register(mcp)
    bulk_tools.register(mcp)
    search_tool.register(mcp)
    cache_tools.register(mcp)
    prompts.register(mcp)
    resources.register(mcp)

    # Layer 3: install the protocol-handler backstop AFTER every tool/resource/
    # prompt is registered (so the request handlers exist). Outermost wrapper on
    # the raw CallTool/ReadResource/GetPrompt handlers — catches the unknown-tool
    # *return* path and any resource/prompt dispatch error that would echo the
    # requested name/URI (the only layer covering the unknown-prompt surface).
    install_protocol_error_handler(mcp)
    return mcp
