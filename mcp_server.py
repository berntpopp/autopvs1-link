#!/usr/bin/env python
"""MCP server entry point for AutoPVS1-Link."""

import asyncio
import os
import sys


def main() -> None:
    """Start MCP server."""
    # Set transport mode and disable FastMCP banner/colors
    os.environ["TRANSPORT"] = "stdio"
    os.environ["FASTMCP_DISABLE_BANNER"] = "1"
    os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"  # Only errors
    os.environ["NO_COLOR"] = "1"  # Disable ANSI colors

    # Configure minimal logging to stderr only for MCP mode
    import logging

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,  # Use stderr instead of stdout
        level=logging.ERROR,  # Only log errors
    )

    # Suppress all third-party loggers
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    logging.getLogger("uvicorn").setLevel(logging.CRITICAL)
    logging.getLogger("fastapi").setLevel(logging.CRITICAL)
    logging.getLogger("fastmcp").setLevel(logging.CRITICAL)

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
