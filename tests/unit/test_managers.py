"""Tests for ClientManager and ServiceManager singletons."""

import pytest

from autopvs1_link.api.client_manager import ClientManager, get_client_manager
from autopvs1_link.services.service_manager import ServiceManager


@pytest.mark.asyncio
async def test_client_manager_singleton() -> None:
    a = ClientManager()
    b = ClientManager()
    assert a is b


@pytest.mark.asyncio
async def test_get_client_manager_returns_initialized_singleton() -> None:
    manager = await get_client_manager()
    assert isinstance(manager, ClientManager)


@pytest.mark.asyncio
async def test_client_manager_get_client_creates_one() -> None:
    manager = ClientManager()
    client = await manager.get_client()
    assert client is not None
    again = await manager.get_client()
    assert again is client


@pytest.mark.asyncio
async def test_client_manager_health_check() -> None:
    manager = ClientManager()
    health = await manager.health_check()
    assert "status" in health


@pytest.mark.asyncio
async def test_service_manager_singleton() -> None:
    a = ServiceManager()
    b = ServiceManager()
    assert a is b


@pytest.mark.asyncio
async def test_service_manager_health_check() -> None:
    manager = ServiceManager()
    health = await manager.health_check()
    assert "status" in health


@pytest.mark.asyncio
async def test_service_manager_get_cache_statistics() -> None:
    manager = ServiceManager()
    stats = await manager.get_cache_statistics()
    assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_service_manager_clear_all_caches() -> None:
    manager = ServiceManager()
    result = await manager.clear_all_caches()
    assert "status" in result
