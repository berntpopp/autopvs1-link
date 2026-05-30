"""Tests for the per-tool cost tier registry."""

from __future__ import annotations

from autopvs1_link.mcp.cost_tiers import (
    CHEAP_TIER,
    SCRAPE_TIER,
    TOOL_COST_TIERS,
    UNKNOWN_TIER,
    cost_tier_for,
)


def test_cost_tier_for_returns_none_when_tool_name_unknown_caller() -> None:
    """``None`` caller (tool_name not supplied) returns ``None`` so the wire stays clean."""
    assert cost_tier_for(None) is None


def test_cost_tier_for_returns_unknown_for_unregistered_tool_names() -> None:
    """A tool name not in the registry returns the explicit UNKNOWN_TIER sentinel."""
    assert cost_tier_for("does_not_exist") == UNKNOWN_TIER


def test_every_registered_tool_uses_a_known_tier() -> None:
    """No accidental ad-hoc tier strings in TOOL_COST_TIERS."""
    allowed = {SCRAPE_TIER, CHEAP_TIER}
    bad = {name: tier for name, tier in TOOL_COST_TIERS.items() if tier not in allowed}
    assert not bad, f"Unknown tier strings: {bad}"


def test_scrape_tier_covers_every_pvs1_scoring_path() -> None:
    """The five scoring/search tools must be scrape-tier (LLMs read this hint)."""
    scrape = {name for name, tier in TOOL_COST_TIERS.items() if tier == SCRAPE_TIER}
    expected = {
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
        "search_variants",
        "get_variants_pvs1_data_bulk",
        "get_cnvs_pvs1_data_bulk",
    }
    assert expected.issubset(scrape), (
        f"Missing from scrape-tier: {expected - scrape}. LLM clients use "
        "cost_tier to plan cold-call batching; the scoring tools must "
        "be tagged."
    )


def test_cheap_tier_covers_no_upstream_tools() -> None:
    """Discovery/health tools must be cheap (sub-ms, no upstream)."""
    cheap = {name for name, tier in TOOL_COST_TIERS.items() if tier == CHEAP_TIER}
    assert {"get_server_health", "get_server_capabilities"}.issubset(cheap)


def test_cost_tiers_stay_in_lockstep_with_performance_block() -> None:
    """The detailed capabilities resource and the wire meta must agree.

    Both source the same constants; a future drift would be a real bug
    because LLM clients caching the capabilities tier would see a
    different ``cost_tier`` from the one echoed on the wire.
    """
    from autopvs1_link.mcp.presenters.capabilities import _PERFORMANCE_BLOCK

    for name, tier in TOOL_COST_TIERS.items():
        block_entry = _PERFORMANCE_BLOCK.get(name)
        if not isinstance(block_entry, dict):
            continue
        block_tier = block_entry.get("cost_tier")
        assert block_tier == tier, (
            f"Tool {name!r} disagrees: registry={tier!r}, _PERFORMANCE_BLOCK={block_tier!r}"
        )
