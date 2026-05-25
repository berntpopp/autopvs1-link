"""Cache management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from autopvs1_link.services.service_manager import get_service_manager

router = APIRouter(prefix="/api/cache", tags=["Cache"])


@router.get("/stats")
async def cache_stats() -> dict[str, Any]:
    """Return cache statistics across managed services."""
    manager = await get_service_manager()
    stats: dict[str, Any] = await manager.get_cache_statistics()
    return stats


@router.post("/clear")
async def cache_clear() -> dict[str, Any]:
    """Clear all managed service caches."""
    manager = await get_service_manager()
    result: dict[str, Any] = await manager.clear_all_caches()
    return result
