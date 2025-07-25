#!/usr/bin/env python
"""MCP server entry point for AutoPVS1-Link."""

import asyncio
import os
import sys

from autopvs1_link.logging_config import configure_logging


def main() -> None:
    """Start MCP server."""
    # Set transport mode and disable FastMCP banner/colors
    os.environ["TRANSPORT"] = "stdio"
    os.environ["FASTMCP_DISABLE_BANNER"] = "1"
    os.environ["FASTMCP_LOG_LEVEL"] = "WARNING"
    os.environ["NO_COLOR"] = "1"  # Disable ANSI colors

    # Configure logging (will automatically use stderr for stdio mode)
    configure_logging()

    try:
        from autopvs1_link.unified_server import run_mcp_stdio

        asyncio.run(run_mcp_stdio())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Log errors to stderr (won't interfere with STDIO protocol)
        print(f"MCP server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
