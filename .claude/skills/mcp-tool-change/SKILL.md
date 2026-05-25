---
name: mcp-tool-change
description: Use when adding, renaming, or changing AutoPVS1-Link MCP tools, resources, prompts, or schemas.
---

# MCP Tool Change

Follow `AGENTS.md` first.

## Workflow

1. Inspect `autopvs1_link/mcp/` and reuse the existing facade, contracts, and
   service adapter patterns.
2. Keep hosted public tools research-use scoped; do not expose clinical
   decision support, destructive cache operations, or broad filesystem/network
   powers.
3. Keep `clear_cache` gated by `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`.
4. Prefer typed Pydantic inputs and stable structured error codes.
5. Update MCP tests under `tests/unit/mcp/` and docs if tool names, arguments,
   resources, or safety language change.
6. Run focused MCP tests, then `make ci-local`.
