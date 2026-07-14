"""The README's ``## Tools`` table must match the registered tool surface.

GeneFoundry README Standard v1, Rule 6: the table is machine-verified, not
hand-maintained. Adding, renaming, or removing a tool without updating the
README fails CI here.

The live tool list is obtained exactly as ``tests/unit/mcp/test_tool_names.py``
obtains it — ``build_mcp_server()`` plus ``await mcp.list_tools()`` — so the
two guards can never disagree about what "registered" means.

Scope: the **default** surface. ``clear_cache`` is gated off by
``AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`` and is documented in prose rather
than in the table, so the flag is pinned to ``false`` here (an operator's
ambient environment must not change the contract under test).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from autopvs1_link.mcp.facade import build_mcp_server

README = Path(__file__).resolve().parents[2] / "README.md"

# A tool row: the first cell is the tool name in backticks. The header and the
# `|---|---|` separator do not match, so no filtering is needed afterwards.
_TOOL_ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|")


def _readme_tool_table() -> list[str]:
    """Tool names listed in the README's ``## Tools`` section, in order."""
    lines = README.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## Tools")
    except ValueError:  # pragma: no cover - the README linter also catches this
        raise AssertionError("README.md has no '## Tools' section") from None

    names: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):  # next H2 ends the section
            break
        match = _TOOL_ROW.match(line)
        if match:
            names.append(match.group(1))
    return names


async def test_readme_tool_table_matches_registered_tools(monkeypatch: Any) -> None:
    # Pin the default surface: clear_cache stays unregistered and out of the table.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false")
    mcp = build_mcp_server()
    registered = {tool.name for tool in await mcp.list_tools()}
    assert registered, "no tools registered on the server"

    documented = _readme_tool_table()
    assert documented, "README '## Tools' table lists no tools"

    missing = registered - set(documented)
    assert not missing, (
        f"registered but undocumented in the README '## Tools' table: {sorted(missing)}. "
        "Add a row (| `tool` | Purpose |) in the same commit that adds the tool."
    )

    extra = set(documented) - registered
    assert not extra, (
        f"documented in the README '## Tools' table but not registered: {sorted(extra)}. "
        "Remove the row, or fix the tool name."
    )


async def test_readme_tool_table_has_no_duplicate_rows(monkeypatch: Any) -> None:
    # Sets hide duplicates; one row per tool is the rule.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false")
    documented = _readme_tool_table()
    assert len(documented) == len(set(documented)), (
        f"duplicate rows in the README '## Tools' table: {sorted(documented)}"
    )


async def test_readme_does_not_table_the_gated_destructive_tool(monkeypatch: Any) -> None:
    # clear_cache is off the default surface by design; the table describes that surface.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "false")
    assert "clear_cache" not in _readme_tool_table()

    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    mcp = build_mcp_server()
    registered = {tool.name for tool in await mcp.list_tools()}
    assert "clear_cache" in registered, (
        "clear_cache must register when AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true; "
        "if this contract changed, the README prose must change with it"
    )
