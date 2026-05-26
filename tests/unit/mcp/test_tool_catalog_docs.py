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
