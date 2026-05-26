"""Tests that generated MCP tool catalog docs are current."""

from pathlib import Path

import pytest

from scripts.generate_mcp_tool_catalog import render


@pytest.mark.asyncio
async def test_mcp_tool_catalog_is_generated_from_current_server() -> None:
    expected = await render()
    actual = Path("docs/mcp-tool-catalog.md").read_text(encoding="utf-8")

    assert actual == expected


@pytest.mark.asyncio
async def test_mcp_tool_catalog_render_has_no_trailing_whitespace() -> None:
    rendered = await render()

    for line in rendered.splitlines():
        assert line.rstrip() == line


@pytest.mark.asyncio
async def test_mcp_tool_catalog_render_includes_prompts() -> None:
    rendered = await render()

    assert "## Prompts" in rendered
    assert "### `classify_variant`" in rendered
    assert "### `classify_cnv`" in rendered


@pytest.mark.asyncio
async def test_mcp_tool_catalog_render_uses_default_public_surface(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")

    rendered = await render()

    assert "### `get_server_health`" in rendered
    assert "### `clear_cache`" not in rendered
