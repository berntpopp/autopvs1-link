"""Transport composer: stdio MCP or HTTP (FastAPI + MCP mount)."""

from __future__ import annotations

import asyncio

import uvicorn

from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.server_manager import create_app


def main(host: str = "127.0.0.1", port: int = 8000, transport: str = "unified") -> None:
    """Start the appropriate transport for the unified server."""
    if transport == "stdio":
        asyncio.run(run_mcp_stdio())
        return
    app = create_app()
    uvicorn.run(app, host=host, port=port)


async def run_mcp_stdio() -> None:
    """Run the MCP server over stdio."""
    mcp = build_mcp_server()
    await mcp.run_stdio_async()


if __name__ == "__main__":
    main()
