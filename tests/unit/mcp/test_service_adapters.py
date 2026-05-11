"""Tests for MCP service adapters."""

from unittest.mock import AsyncMock

import pytest

from autopvs1_link.mcp import service_adapters


@pytest.mark.asyncio
async def test_get_variant_calls_service(mocker) -> None:
    fake_service = AsyncMock()
    fake_service.get_variant_data = AsyncMock(return_value={"ok": True})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake_service),
    )

    result = await service_adapters.get_variant("hg38", "1-12345-A-G")

    fake_service.get_variant_data.assert_awaited_once_with("hg38", "1-12345-A-G")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_search_variants_calls_service(mocker) -> None:
    fake_service = AsyncMock()
    fake_service.search_variants = AsyncMock(return_value={"results": []})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake_service),
    )

    result = await service_adapters.search_variants("MYH9", "hg38")
    fake_service.search_variants.assert_awaited_once_with("MYH9", "hg38")
    assert result == {"results": []}


@pytest.mark.asyncio
async def test_clear_cache_gated(monkeypatch, mocker) -> None:
    from autopvs1_link.mcp.errors import DestructiveOperationDisabledError

    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false")
    fake_service = AsyncMock()
    fake_service.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake_service),
    )

    with pytest.raises(DestructiveOperationDisabledError):
        await service_adapters.clear_cache()
    fake_service.clear_cache.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_cache_when_enabled(monkeypatch, mocker) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    fake_service = AsyncMock()
    fake_service.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake_service),
    )

    result = await service_adapters.clear_cache()
    fake_service.clear_cache.assert_awaited_once()
    assert result["cleared"] is True
