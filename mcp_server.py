#!/usr/bin/env python
"""Entry point for `python mcp_server.py`; runs stdio MCP."""

import asyncio
import os
import sys


def main() -> None:
    """Start the MCP server over stdio."""
    os.environ.setdefault("FASTMCP_DISABLE_BANNER", "1")
    os.environ.setdefault("FASTMCP_LOG_LEVEL", "ERROR")
    os.environ.setdefault("NO_COLOR", "1")
    try:
        from autopvs1_link.unified_server import run_mcp_stdio

        asyncio.run(run_mcp_stdio())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        print(f"MCP server error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
