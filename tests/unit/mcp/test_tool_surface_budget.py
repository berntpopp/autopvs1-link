"""Regression guard for the GeneFoundry Tool-Surface Budget Standard v1.

The tool surface — the ``tools/list`` payload — is re-sent to the model on every
request for the life of a session, before any work happens. This test measures
this server's OWN advertised surface (built offline from ``build_mcp_server``,
no network) and fails if it regresses past the standard's ceilings:

* ``B1`` — no single tool definition exceeds 1,200 tokens.
* ``B2`` — the whole server surface stays under 10,000 tokens.

Tokens are estimated as ``len(json.dumps(x)) / 4`` — the same comparative
heuristic the router's ``scripts/surface.py`` and ``mcp_survey.py`` use, so this
gate and the fleet survey measure the same number.

See ``docs/TOOL-SURFACE-BUDGET-STANDARD-v1.md``.
"""

from __future__ import annotations

import json

import pytest

from autopvs1_link.mcp.facade import build_mcp_server

MAX_TOOL_TOKENS = 1_200
MAX_SERVER_TOKENS = 10_000


def _tokens(obj: object) -> int:
    """Approximate token cost of a JSON-serialisable object (chars / 4)."""
    return len(json.dumps(obj, default=str)) // 4


def _wire_entry(tool: object) -> dict[str, object]:
    """The tool as a client sees it in ``tools/list`` (name/desc/schemas/annotations)."""
    entry: dict[str, object] = {
        "name": getattr(tool, "name", None),
        "title": getattr(tool, "title", None),
        "description": getattr(tool, "description", None),
        "inputSchema": getattr(tool, "parameters", None),
        "outputSchema": getattr(tool, "output_schema", None),
        "annotations": getattr(tool, "annotations", None),
    }
    return {k: v for k, v in entry.items() if v is not None}


async def _surface_entries() -> list[dict[str, object]]:
    mcp = build_mcp_server()
    tools = await mcp.list_tools()
    return [_wire_entry(tool) for tool in tools]


@pytest.mark.asyncio
async def test_no_tool_definition_exceeds_the_per_tool_budget() -> None:
    entries = await _surface_entries()
    assert entries, "the server advertised no tools"
    oversized = {
        str(entry.get("name")): _tokens(entry)
        for entry in entries
        if _tokens(entry) > MAX_TOOL_TOKENS
    }
    assert not oversized, (
        f"tool definitions exceed the {MAX_TOOL_TOKENS}-token B1 ceiling: {oversized}"
    )


@pytest.mark.asyncio
async def test_server_surface_stays_under_budget() -> None:
    entries = await _surface_entries()
    total = _tokens(entries)
    assert total < MAX_SERVER_TOKENS, (
        f"total tool surface {total} tokens exceeds the {MAX_SERVER_TOKENS}-token B2 ceiling"
    )


@pytest.mark.asyncio
async def test_output_schema_is_suppressed_on_every_tool() -> None:
    """Every tool publishes NO outputSchema (the runtime envelope is unchanged).

    ``outputSchema`` is optional in MCP and was 88% of this server's surface; it
    is suppressed with ``@mcp.tool(output_schema=None)``. ``structuredContent``
    is still emitted at runtime for the dict envelopes every tool returns.
    """
    mcp = build_mcp_server()
    tools = await mcp.list_tools()
    published = {t.name: t.output_schema for t in tools if t.output_schema is not None}
    assert not published, f"these tools still publish an outputSchema: {sorted(published)}"
