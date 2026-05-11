"""Cover the dict-path branch in MCP tool wrappers via service_adapters."""

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_get_variant_returns_service_dict(mocker) -> None:
    from autopvs1_link.mcp import service_adapters

    fake = AsyncMock()
    fake.get_variant_data = AsyncMock(return_value={"raw": True})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )
    out = await service_adapters.get_variant("hg38", "X-1-A-T")
    assert out == {"raw": True}


@pytest.mark.asyncio
async def test_search_returns_service_dict(mocker) -> None:
    from autopvs1_link.mcp import service_adapters

    fake = AsyncMock()
    fake.search_variants = AsyncMock(return_value={"results": []})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )
    out = await service_adapters.search_variants("MYH9", "hg38")
    assert out == {"results": []}


@pytest.mark.asyncio
async def test_get_cnv_returns_service_dict(mocker) -> None:
    from autopvs1_link.mcp import service_adapters

    fake = AsyncMock()
    fake.get_cnv_data = AsyncMock(return_value={"cnv": True})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )
    out = await service_adapters.get_cnv("hg19", "1-1-2-DEL")
    assert out == {"cnv": True}


@pytest.mark.asyncio
async def test_cache_statistics_returns_service_dict(mocker) -> None:
    from autopvs1_link.mcp import service_adapters

    fake = AsyncMock()
    fake.get_cache_statistics = AsyncMock(return_value={"hits": 0, "misses": 0})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )
    stats = await service_adapters.cache_statistics()
    assert stats["hits"] == 0
