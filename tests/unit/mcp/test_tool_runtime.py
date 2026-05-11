"""Exercise MCP tool wrappers through FastMCP's call_tool runtime."""

from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from autopvs1_link.mcp.facade import build_mcp_server


class _FakeResult(BaseModel):
    """Minimal Pydantic model so tools take the model_dump branch."""

    ok: bool = True
    method: str = ""


@pytest.mark.asyncio
async def test_get_variant_pvs1_data_tool_runtime(mocker) -> None:
    fake = AsyncMock(return_value=_FakeResult(method="variant"))
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"payload": {"genome_build": "hg38", "variant_id": "X-1-A-T"}},
    )
    fake.assert_awaited_once_with("hg38", "X-1-A-T")
    assert result is not None


@pytest.mark.asyncio
async def test_get_cnv_pvs1_data_tool_runtime(mocker) -> None:
    fake = AsyncMock(return_value=_FakeResult(method="cnv"))
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"payload": {"genome_build": "hg19", "cnv_id": "1-1-2-DEL"}},
    )
    fake.assert_awaited_once_with("hg19", "1-1-2-DEL")
    assert result is not None


@pytest.mark.asyncio
async def test_search_variants_tool_runtime(mocker) -> None:
    fake = AsyncMock(return_value=_FakeResult(method="search"))
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"payload": {"query": "MYH9", "genome_version": "hg38"}},
    )
    fake.assert_awaited_once_with("MYH9", "hg38")
    assert result is not None


@pytest.mark.asyncio
async def test_clear_cache_tool_runtime_when_enabled(monkeypatch, mocker) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    fake = AsyncMock()
    fake.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool("clear_cache", {})
    assert result is not None
    fake.clear_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_resource_runtime(mocker) -> None:
    fake = AsyncMock()
    fake.get_cache_statistics = AsyncMock(return_value={"hits": 5, "misses": 2})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.read_resource("autopvs1-link://cache/statistics")
    assert result is not None
