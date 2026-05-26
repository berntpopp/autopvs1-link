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
        "get_server_capabilities",
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
        "search_variants",
        "clear_cache",
    } <= tool_names


@pytest.mark.asyncio
async def test_data_tools_use_direct_arguments_for_llm_discovery() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    variant_schema = tools["get_variant_pvs1_data"].parameters
    assert set(variant_schema["properties"]) == {"genome_build", "variant_id"}
    assert variant_schema["required"] == ["genome_build", "variant_id"]

    search_schema = tools["search_variants"].parameters
    assert set(search_schema["properties"]) == {"query", "genome_version"}
    assert search_schema["required"] == ["query"]


@pytest.mark.asyncio
async def test_data_tools_have_titles_annotations_and_output_schemas() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    for name in ("get_server_capabilities", "get_variant_pvs1_data", "get_cnv_pvs1_data"):
        tool = tools[name]
        assert tool.title
        assert tool.output_schema is not None
        assert set(tool.output_schema["properties"]) == {"ok", "data", "error", "meta"}
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
