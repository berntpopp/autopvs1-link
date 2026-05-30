"""Per-tool cost tier registry.

Shared by the envelope helper (``autopvs1_link.mcp.envelope``) so every
ok/error envelope can echo ``meta.cost_tier`` and the capabilities
presenter (``autopvs1_link.mcp.presenters.capabilities._PERFORMANCE_BLOCK``)
so the detailed capabilities resource advertises the same value. Single
source of truth means the wire and the discovery doc cannot drift.

Two real tiers today:

* ``cheap`` — in-process compute only (e.g. ``get_server_health``,
  ``get_server_capabilities``); no upstream call, no rate-limit gating.
* ``expensive_cold_cheap_warm`` — scrapes the AutoPVS1 HTML upstream
  behind a ~1 req/s floor; cold calls take ~1-3s; subsequent calls hit
  the TTL cache and return in milliseconds. LLM clients should batch
  first-contact and re-call freely once warm.
"""

from __future__ import annotations

SCRAPE_TIER = "expensive_cold_cheap_warm"
"""Upstream HTML scrape with TTL cache: cold ~1-3s, warm ~ms."""

CHEAP_TIER = "cheap"
"""In-process compute only; sub-millisecond and free."""

UNKNOWN_TIER = "unknown"
"""Tool name not registered. Tools should not hit this in production."""


TOOL_COST_TIERS: dict[str, str] = {
    "get_variant_pvs1_data": SCRAPE_TIER,
    "get_cnv_pvs1_data": SCRAPE_TIER,
    "search_variants": SCRAPE_TIER,
    "get_variants_pvs1_data_bulk": SCRAPE_TIER,
    "get_cnvs_pvs1_data_bulk": SCRAPE_TIER,
    "get_server_health": CHEAP_TIER,
    "get_server_capabilities": CHEAP_TIER,
    "clear_cache": CHEAP_TIER,
}


def cost_tier_for(tool_name: str | None) -> str | None:
    """Return the registered cost tier for ``tool_name``.

    ``None`` when ``tool_name`` is itself ``None`` (the caller did not
    declare which tool produced this envelope), which keeps the wire
    field absent rather than ``"unknown"`` — absence is correctly
    interpreted by consumers as "no signal" rather than a sentinel.
    """
    if tool_name is None:
        return None
    return TOOL_COST_TIERS.get(tool_name, UNKNOWN_TIER)
