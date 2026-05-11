"""FastMCP server facade.

Builds the FastMCP instance and registers tools/resources.
"""

from __future__ import annotations

from fastmcp import FastMCP

from autopvs1_link.mcp.metadata import (
    SERVER_DESCRIPTION,
    SERVER_NAME,
    SERVER_VERSION,
)


def build_mcp_server() -> FastMCP:
    """Construct and return a configured FastMCP server."""
    mcp = FastMCP(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=SERVER_DESCRIPTION,
    )

    from autopvs1_link.mcp import resources
    from autopvs1_link.mcp.tools import (
        cache_tools,
        cnv_tool,
        search_tool,
        variant_tool,
    )

    variant_tool.register(mcp)
    cnv_tool.register(mcp)
    search_tool.register(mcp)
    cache_tools.register(mcp)
    resources.register(mcp)
    return mcp
