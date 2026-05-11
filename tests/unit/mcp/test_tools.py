"""Smoke tests for MCP tool registration."""

import pytest
from fastmcp import FastMCP

from autopvs1_link.mcp.facade import build_mcp_server


@pytest.mark.asyncio
async def test_build_mcp_server_registers_expected_tools() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert {
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
        "search_variants",
        "clear_cache",
    } <= tool_names
