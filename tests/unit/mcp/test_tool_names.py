"""Tool-name compliance with the GeneFoundry Tool-Naming Standard v1.1.

Every registered tool must be unprefixed, snake_case, <= 50 chars, and start with
a canonical verb (or be exempt via the ops/meta tag carve-out) so it composes
cleanly behind the ``genefoundry-router`` gateway, which mounts this server under
the ``autopvs1`` namespace (tools surface as ``autopvs1_<tool>``). Guards against
future drift. See issue berntpopp/autopvs1-link#24.

VERB CANON (ratified Standard v1.1, 2026-06-30)
------------------------------------------------
Tier-1 (universal read/query, all backends):
    get, search, list, resolve, find, compare, compute, map

Tier-2 (sanctioned domain action/compute verbs):
    predict, annotate, recode, liftover, analyze, score,
    submit, export, generate, download

Operational/meta carve-out (by tag, not verb, Standard v1.1 §Q3):
    Tools tagged ``ops`` or ``meta`` skip the verb rule but still must pass
    charset/length/no-self-prefix checks. Covers ``clear_cache`` (tags:
    meta, admin) via its ``meta`` tag, without needing a per-name exception.
    Per-name exceptions (`_VERB_EXCEPTIONS`) are removed; the tag carve-out
    is the fleet-ratified mechanism.
"""

from __future__ import annotations

import re
from typing import Any

from autopvs1_link.mcp.facade import build_mcp_server

_NAME_RE = re.compile(r"^[a-z0-9_]{1,50}$")

# Ratified Tier-1: universal read/query canon (Standard v1.1, Rule 2).
_CANONICAL_VERBS = frozenset(
    {"get", "search", "list", "resolve", "find", "compare", "compute", "map"}
)

# Ratified Tier-2: sanctioned domain action/compute verbs (Standard v1.1).
_TIER2_VERBS = frozenset(
    {
        "predict",
        "annotate",
        "recode",
        "liftover",
        "analyze",
        "score",
        "submit",
        "export",
        "generate",
        "download",
    }
)

# Combined allowed verb set for domain tools.
_ALL_VERBS = _CANONICAL_VERBS | _TIER2_VERBS

# Tags that grant an ops/meta carve-out (Standard v1.1, §Q3 ratification).
# Tools carrying any of these tags skip the verb rule (but still pass
# charset/length/no-self-prefix). Covers ``clear_cache`` (meta, admin) via
# its ``meta`` tag — the ratified carve-out set is exactly {ops, meta}.
_OPS_CARVEOUT_TAGS = frozenset({"ops", "meta"})

_NAMESPACE = "autopvs1"


async def test_tool_names_conform_to_standard_v1_1(monkeypatch: Any) -> None:
    # Enable destructive tools so the full registered surface (including the gated
    # ``clear_cache`` tool) is covered by the guard.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    mcp = build_mcp_server()
    tools = await mcp.list_tools()
    assert tools, "no tools registered on the server"
    for tool in tools:
        name = tool.name
        tags = set(getattr(tool, "tags", None) or ())
        assert _NAME_RE.match(name), f"{name!r} must match ^[a-z0-9_]{{1,50}}$"
        assert not name.startswith(f"{_NAMESPACE}_"), (
            f"{name!r} must not self-prefix the '{_NAMESPACE}' namespace "
            "token — the gateway adds it"
        )
        # Ops/meta tag carve-out: infrastructure/admin tools are exempt from the
        # verb rule. ``clear_cache`` carries (meta, admin) and is covered here.
        if tags & _OPS_CARVEOUT_TAGS:
            continue
        verb = name.split("_", 1)[0]
        assert verb in _ALL_VERBS, (
            f"{name!r} must start with a Tier-1 or Tier-2 verb; "
            f"Tier-1: {sorted(_CANONICAL_VERBS)}, Tier-2: {sorted(_TIER2_VERBS)}; "
            "or tag the tool ops/meta for the operational carve-out "
            "(Standard v1.1, genefoundry-router/docs/TOOL-NAMING-STANDARD-v1.md)"
        )


async def test_every_tool_carries_domain_tags(monkeypatch: Any) -> None:
    # Rule 6: domain tags let the gateway filter/curate the surfaced toolset.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    mcp = build_mcp_server()
    for tool in await mcp.list_tools():
        assert tool.tags, f"{tool.name!r} must declare at least one domain tag"
