"""MCP tool: get_server_health."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP
from pydantic import BaseModel

from autopvs1_link.mcp.annotations import READ_ONLY_CLOSED_WORLD
from autopvs1_link.mcp.envelope import MCPEnvelope, ok_envelope
from autopvs1_link.mcp.server_info import SERVER_NAME, SERVER_VERSION
from autopvs1_link.mcp.tools.cache_tools import destructive_tools_enabled


class HealthData(BaseModel):
    """Local MCP server health status."""

    status: Literal["ok"] = "ok"
    server: str = SERVER_NAME
    version: str = SERVER_VERSION
    upstream_checked: bool = False
    upstream_status: Literal["not_checked"] = "not_checked"
    destructive_tools_enabled: bool = False


class HealthMCPEnvelope(MCPEnvelope[HealthData]):
    """Envelope schema for ``get_server_health``."""


def register(mcp: FastMCP) -> None:
    """Register the local read-only health tool."""

    @mcp.tool(
        name="get_server_health",
        title="Get AutoPVS1-Link Health",
        output_schema=HealthMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_CLOSED_WORLD,
    )
    async def get_server_health() -> dict[str, Any]:
        """Return local MCP server health without contacting AutoPVS1 upstream."""
        return ok_envelope(HealthData(destructive_tools_enabled=destructive_tools_enabled()))
