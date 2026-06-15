"""Tool-name compliance with the GeneFoundry Tool-Naming Standard v1.

Every registered tool must be unprefixed, snake_case, <= 50 chars, and start with
a canonical verb so it composes cleanly behind the ``genefoundry-router`` gateway,
which mounts this server under the ``autopvs1`` namespace (tools surface as
``autopvs1_<tool>``). Guards against future drift. See issue
berntpopp/autopvs1-link#24.
"""

from __future__ import annotations

import re
from typing import Any

from autopvs1_link.mcp.facade import build_mcp_server

_NAME_RE = re.compile(r"^[a-z0-9_]{1,50}$")
_CANONICAL_VERBS = frozenset({"get", "search", "list", "resolve", "find", "compare", "compute"})
_NAMESPACE = "autopvs1"
# Approved exceptions: gated, off-by-default destructive tools whose action has no
# natural canonical-verb mapping. Documented in issue #24 and the README.
_VERB_EXCEPTIONS = frozenset({"clear_cache"})


async def test_tool_names_conform_to_standard_v1(monkeypatch: Any) -> None:
    # Enable destructive tools so the full registered surface (including the gated
    # ``clear_cache`` tool) is covered by the guard.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    mcp = build_mcp_server()
    names = sorted(tool.name for tool in await mcp.list_tools())
    assert names, "no tools registered on the server"
    for name in names:
        assert _NAME_RE.match(name), f"{name!r} must match ^[a-z0-9_]{{1,50}}$"
        if name not in _VERB_EXCEPTIONS:
            assert name.split("_", 1)[0] in _CANONICAL_VERBS, (
                f"{name!r} must start with a canonical verb {sorted(_CANONICAL_VERBS)}"
            )
        assert not name.startswith(f"{_NAMESPACE}_"), (
            f"{name!r} must not self-prefix the '{_NAMESPACE}' namespace "
            "token — the gateway adds it"
        )


async def test_every_tool_carries_domain_tags(monkeypatch: Any) -> None:
    # Rule 6: domain tags let the gateway filter/curate the surfaced toolset.
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    mcp = build_mcp_server()
    for tool in await mcp.list_tools():
        assert tool.tags, f"{tool.name!r} must declare at least one domain tag"
