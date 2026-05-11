"""Smoke tests for MCP resources."""

import pytest

from autopvs1_link.mcp.facade import build_mcp_server


@pytest.mark.asyncio
async def test_build_mcp_server_registers_cache_resource() -> None:
    mcp = build_mcp_server()
    resources = await mcp.list_resources()
    resource_uris = {str(r.uri) for r in resources}
    assert any("autopvs1-link://cache/statistics" in u for u in resource_uris)
