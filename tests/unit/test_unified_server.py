"""Smoke test the unified_server module imports + transport routing."""

from autopvs1_link import unified_server


def test_unified_server_exports() -> None:
    assert callable(unified_server.main)
    assert callable(unified_server.run_mcp_stdio)
