"""Smoke tests for MCP resources."""

import json

import pytest

from autopvs1_link.mcp.facade import build_mcp_server


@pytest.mark.asyncio
async def test_build_mcp_server_registers_cache_resource() -> None:
    mcp = build_mcp_server()
    resources = await mcp.list_resources()
    resource_uris = {str(r.uri) for r in resources}
    assert any("autopvs1-link://cache/statistics" in u for u in resource_uris)
    assert any("autopvs1-link://capabilities" in u for u in resource_uris)


@pytest.mark.asyncio
async def test_capabilities_tool_and_resource_are_not_duplicates() -> None:
    mcp = build_mcp_server()

    tool_result = await mcp.call_tool("get_server_capabilities", {})
    resource_result = await mcp.read_resource("autopvs1-link://capabilities")

    assert tool_result.structured_content["ok"] is True
    assert (
        tool_result.structured_content["data"]["details_resource"] == "autopvs1-link://capabilities"
    )
    assert resource_result is not None
    assert resource_result.contents
    detailed_resource = json.loads(resource_result.contents[0].content)
    assert "accepted_formats" in detailed_resource
    assert detailed_resource != tool_result.structured_content["data"]
