"""Tests for MCP server metadata: byte budget and tool-name coverage.

Claude Code truncates the ``instructions`` field at 2 KB; anything past
the cliff is silently dropped, hurting cold-start tool selection.
Anthropic Tool Search docs report a 27-40% first-turn cost when LLM
clients have to ToolSearch the deferred tool catalogue, so naming the
entry-point tools verbatim in ``SERVER_DESCRIPTION`` matters.

These tests guard both invariants so a future edit cannot quietly
exceed the cliff or forget to advertise a new tool.
"""

from __future__ import annotations

from autopvs1_link.mcp.server_info import (
    SERVER_DESCRIPTION,
    SERVER_NAME,
    SERVER_VERSION,
)

CLAUDE_CODE_INSTRUCTIONS_TRUNCATION_BYTES = 2048
SAFE_INSTRUCTIONS_CEILING_BYTES = 1900

NON_DESTRUCTIVE_TOOL_NAMES = (
    "get_variant_pvs1_data",
    "get_cnv_pvs1_data",
    "search_variants",
    "get_variants_pvs1_data_bulk",
    "get_cnvs_pvs1_data_bulk",
    "get_server_capabilities",
    "get_server_health",
)


def test_server_description_stays_under_claude_code_truncation_cliff() -> None:
    """SERVER_DESCRIPTION must stay below the 2 KB Claude Code truncation cliff."""
    byte_length = len(SERVER_DESCRIPTION.encode("utf-8"))
    assert byte_length <= SAFE_INSTRUCTIONS_CEILING_BYTES, (
        f"SERVER_DESCRIPTION is {byte_length} bytes; ceiling is "
        f"{SAFE_INSTRUCTIONS_CEILING_BYTES} bytes (Claude Code truncates at "
        f"{CLAUDE_CODE_INSTRUCTIONS_TRUNCATION_BYTES})."
    )


def test_server_description_lists_every_visible_tool_verbatim() -> None:
    """Each non-destructive tool name must appear verbatim in SERVER_DESCRIPTION.

    Anthropic Tool Search guidance recommends naming the most-likely-used
    tools in the server instructions so cold-start clients can skip a
    ToolSearch round-trip. This test fails closed when a new tool lands
    and someone forgets to mention it.
    """
    missing = [name for name in NON_DESTRUCTIVE_TOOL_NAMES if name not in SERVER_DESCRIPTION]
    assert not missing, (
        f"SERVER_DESCRIPTION is missing tool names: {missing}. Add them so "
        "cold-start clients skip the ToolSearch round-trip."
    )


def test_server_description_does_not_advertise_destructive_tools() -> None:
    """``clear_cache`` is env-gated; it must not appear in the public instructions.

    Mentioning it would advertise a destructive operation that is disabled
    by default and signal an attack surface to LLM consumers.
    """
    assert "clear_cache" not in SERVER_DESCRIPTION


def test_server_description_names_workflow_helper_prompt() -> None:
    """``pvs1_workflow_help`` exists; cold-start clients must learn about it.

    Otherwise the prompt is invisible until a discovery call lands.
    """
    assert "pvs1_workflow_help" in SERVER_DESCRIPTION


def test_server_metadata_constants_are_well_formed() -> None:
    """SERVER_NAME / SERVER_VERSION shapes must stay legible to clients."""
    assert SERVER_NAME == "AutoPVS1 Link"
    assert SERVER_VERSION.count(".") == 2
    assert all(part.isdigit() for part in SERVER_VERSION.split("."))
