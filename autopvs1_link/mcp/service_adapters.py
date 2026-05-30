"""Async adapters bridging MCP tool handlers to the service layer."""

from __future__ import annotations

import os
from typing import Any

from autopvs1_link.api.variant_recoder import RecoderCandidate, get_recoder_client
from autopvs1_link.mcp.errors import DestructiveOperationDisabledError
from autopvs1_link.services.service_manager import get_service_manager
from autopvs1_link.utils.cache_manager import cache_manager


async def _service() -> Any:
    """Resolve the live AutoPVS1Service.

    Indirected through this helper so tests can monkeypatch it without
    touching the singleton.
    """
    manager = await get_service_manager()
    return await manager.get_service()


async def get_variant(genome_build: str, variant_id: str) -> Any:
    service = await _service()
    return await service.get_variant_data(genome_build, variant_id)


async def search_variants(query: str, genome_version: str) -> Any:
    service = await _service()
    return await service.search_variants(query, genome_version)


async def get_cnv(genome_build: str, cnv_id: str) -> Any:
    service = await _service()
    return await service.get_cnv_data(genome_build, cnv_id)


@cache_manager.enhanced_cache(
    maxsize=512,
    key_func=lambda input_id, genome_build: f"recoder:{genome_build}:{input_id}",
)
async def recode_variant(input_id: str, genome_build: str) -> list[RecoderCandidate]:
    """Resolve an rsID / HGVS input to canonical SPDI candidates.

    Wrapped in ``enhanced_cache`` so repeat resolutions are free and
    so the wire-side ``cache_status``/``elapsed_ms`` telemetry covers
    recoder calls just like AutoPVS1 calls. Build is part of the cache
    key because the SAME rsID returns different coordinates between
    GRCh37 and GRCh38 hosts.
    """
    client = get_recoder_client()
    return await client.recode(input_id, genome_build)


async def cache_statistics() -> Any:
    service = await _service()
    return await service.get_cache_statistics()


async def clear_cache() -> dict[str, bool]:
    if os.environ.get("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false").lower() != "true":
        raise DestructiveOperationDisabledError("clear_cache")
    service = await _service()
    await service.clear_cache()
    return {"cleared": True}
