"""Machine-executable next-step builders for MCP tool envelopes.

Each builder returns a list of ready-to-call ``{tool, arguments, reason}``
objects (or ``None`` when no next step applies) for ``meta.next_commands``.
This is an idiomatic application of the envelope's own ``meta`` channel
(not an MCP protocol primitive); it mirrors the sibling gnomad-link
server's chaining hints so an LLM dispatcher can advance without guessing
the next tool. ``None`` is dropped from the wire by the envelope's
null-strip pass.
"""

from __future__ import annotations

from typing import Any

_WIDER_MODE: dict[str, str] = {
    "ids_only": "standard",
    "summary": "standard",
    "standard": "full",
}
_WIDEN_REASON: dict[str, str] = {
    "standard": "Widen to response_mode='standard' for the full decision tree.",
    "full": "Widen to response_mode='full' for audit-trail *_raw fields.",
}


def widen_response_mode(
    tool_name: str,
    arguments: dict[str, Any],
    current_mode: str,
) -> list[dict[str, Any]] | None:
    """Suggest re-calling ``tool_name`` at the next-wider response_mode."""
    wider = _WIDER_MODE.get(current_mode)
    if wider is None:
        return None
    args = dict(arguments)
    args["response_mode"] = wider
    return [{"tool": tool_name, "arguments": args, "reason": _WIDEN_REASON[wider]}]


def search_next_page(
    arguments: dict[str, Any],
    next_cursor: str | None,
) -> list[dict[str, Any]] | None:
    """Suggest the next search page when a ``next_cursor`` exists."""
    if not next_cursor:
        return None
    args = dict(arguments)
    args["cursor"] = next_cursor
    return [
        {"tool": "search_variants", "arguments": args, "reason": "Fetch the next page of results."}
    ]


def bulk_retry_failed(
    single_tool: str,
    results: list[Any],
    id_field: str,
) -> list[dict[str, Any]] | None:
    """Suggest re-calling the single-item tool for each failed bulk item."""
    commands: list[dict[str, Any]] = []
    for item in results:
        if getattr(item, "ok", True):
            continue
        item_input = getattr(item, "input", None)
        if item_input is None:
            continue
        commands.append(
            {
                "tool": single_tool,
                "arguments": {
                    "genome_build": getattr(item_input, "genome_build", None),
                    id_field: getattr(item_input, id_field, None),
                },
                "reason": "Retry this failed item individually.",
            }
        )
    return commands or None


def error_next_commands(
    code: str,
    details: dict[str, Any] | None,
) -> list[dict[str, Any]] | None:
    """Derive next_commands for error codes that carry actionable context.

    Currently handles ``requires_disambiguation``: one re-score command
    per resolver candidate. Other codes keep the prose ``next_actions``
    recovery hints (the vendor-cited requirement) and return ``None``
    here.
    """
    if code != "requires_disambiguation" or not isinstance(details, dict):
        return None
    candidates = details.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    commands: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        variant_id = candidate.get("id")
        if not variant_id:
            continue
        arguments: dict[str, Any] = {"variant_id": variant_id}
        build = candidate.get("genome_build")
        if build:
            arguments["genome_build"] = build
        commands.append(
            {
                "tool": "get_variant_pvs1_data",
                "arguments": arguments,
                "reason": "Re-score with this disambiguated candidate id.",
            }
        )
    return commands or None
