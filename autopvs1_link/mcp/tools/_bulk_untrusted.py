"""Response-wide untrusted-text helpers for the bulk PVS1 tools.

Each per-item presenter already enforces its own item's Response-Envelope
v1.1 ceilings, but a bulk call aggregates up to ``BULK_MAX_ITEMS`` results —
10 items each near the 128-object / 8 MiB limit would otherwise exceed the
response-wide ceiling with no typed error. These helpers collect every fenced
object across the whole bulk payload for one aggregate enforcement call and
map a breach to the typed ``untrusted_text_limit_exceeded`` error envelope.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.envelope import ToolResponse, error_envelope
from autopvs1_link.mcp.mode_validation import MetaMode
from autopvs1_link.mcp.untrusted_content import UntrustedText


def collect_untrusted_texts(node: Any) -> list[UntrustedText]:
    """Recursively gather every fenced ``UntrustedText`` in a payload subtree."""
    if isinstance(node, UntrustedText):
        return [node]
    found: list[UntrustedText] = []
    if isinstance(node, BaseModel):
        for field_name in type(node).model_fields:
            found.extend(collect_untrusted_texts(getattr(node, field_name)))
    elif isinstance(node, dict):
        for value in node.values():
            found.extend(collect_untrusted_texts(value))
    elif isinstance(node, (list, tuple)):
        for value in node:
            found.extend(collect_untrusted_texts(value))
    return found


def bulk_untrusted_limit_envelope(*, meta_mode: MetaMode, tool_name: str) -> ToolResponse:
    """Typed error when the whole bulk response exceeds a v1.1 untrusted ceiling."""
    return error_envelope(
        code="untrusted_text_limit_exceeded",
        message=(
            "Aggregate AutoPVS1 scraped content across the bulk response exceeded the "
            "Response-Envelope v1.1 untrusted-text ceiling."
        ),
        retryable=False,
        suggestions=[
            "Request fewer items per call.",
            "Use response_mode='summary' or 'ids_only' to shrink per-item payloads.",
        ],
        meta_mode=meta_mode,
        tool_name=tool_name,
    )
