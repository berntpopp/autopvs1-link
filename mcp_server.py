#!/usr/bin/env python
"""Legacy MCP server entry point - redirects to unified server.

NOTE: This file is maintained for backward compatibility.
For the enhanced unified server with MCP support, use:
    autopvs1-link mcp
    or
    python -m autopvs1_link.unified_server:run_mcp_stdio()
"""

import asyncio
import warnings

# Issue deprecation warning
warnings.warn(
    "mcp_server.py is deprecated. Use 'autopvs1-link mcp' for enhanced features.",
    DeprecationWarning,
    stacklevel=2
)


async def main():
    """Legacy main function - redirects to unified MCP server."""
    print("⚠️  Redirecting to unified MCP server...")
    print("💡 For future use, run: autopvs1-link mcp")
    print("")
    
    from autopvs1_link.unified_server import run_mcp_stdio
    await run_mcp_stdio()


if __name__ == "__main__":
    asyncio.run(main())
