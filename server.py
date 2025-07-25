#!/usr/bin/env python
"""Legacy server entry point - redirects to unified server.

NOTE: This file is maintained for backward compatibility.
For the enhanced unified server with MCP support, use:
    autopvs1-link server
    or
    python -m autopvs1_link.unified_server
"""

import warnings

from autopvs1_link.unified_server import main as unified_main

# Issue deprecation warning
warnings.warn(
    "server.py is deprecated. Use 'autopvs1-link server' or autopvs1_link.unified_server for enhanced features.",
    DeprecationWarning,
    stacklevel=2
)


def main():
    """Legacy main function - redirects to unified server."""
    print("⚠️  Redirecting to unified server...")
    print("💡 For future use, run: autopvs1-link server")
    print("")
    unified_main()


if __name__ == "__main__":
    main()
