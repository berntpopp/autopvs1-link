# MCP LLM Polish Design

- **Status:** Approved for direct execution by user request
- **Date:** 2026-05-26
- **Scope:** MCP contract polish, token-cost controls, structured schemas, prompts, and discovery hygiene

## Goal

Move AutoPVS1-Link's MCP surface from a strong 8.x implementation to a
9+/10 agent-facing interface by reducing successful-response token cost,
making output schemas more explicit, improving first-turn discovery, and
keeping destructive capabilities off the default surface.

## Research Basis

This pass follows current MCP and agent-tool guidance:

- MCP 2025-06-18 says tools may declare `outputSchema`; structured results
  must conform to it, and structured results should also be serialized in text
  content for backward compatibility.
  https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP defines prompts, resources, and tools as separate primitives:
  prompts are user-controlled, resources are application-controlled, and tools
  are model-controlled.
  https://modelcontextprotocol.io/specification/2025-06-18/server/index
- MCP prompts are the standard way for servers to expose reusable workflows.
  https://modelcontextprotocol.io/specification/2025-06-18/server/prompts
- Claude Code's MCP guidance emphasizes concise server instructions because
  descriptions and instructions are truncated at 2 KB, and tool search makes
  first-turn discovery quality important.
  https://code.claude.com/docs/en/mcp
- Anthropic's engineering guidance on MCP token efficiency recommends
  progressive disclosure, result filtering, and detail-level knobs so large
  tool results do not flow through the model context unnecessarily.
  https://www.anthropic.com/engineering/code-execution-with-mcp

## Design

Add three lightweight contract controls to read tools:

- `response_mode`: `summary`, `standard`, or `full`.
- `meta_mode`: `full`, `compact`, or `minimal`.
- `include_unmet`: optional disease-mechanism filter for scoring tools.

Defaults preserve today's behavior where possible: `standard` data and `full`
metadata. `summary` returns the verdict-oriented subset an agent needs for a
quick answer. `full` preserves all presenter fields. `minimal` metadata keeps
request ID, server version, research-use flag, and warnings while omitting the
full citation text; it never removes the research-use framing.

Replace `dict[str, Any]` output surfaces with typed Pydantic models for
variant info, CNV info, flowcharts, disease mechanisms, search rows, workflow
steps, and tool summaries. Keep parser and REST models unchanged. The MCP
presenters remain the boundary that converts upstream scrape output into the
LLM-facing contract.

Improve affordances without changing tool names:

- put examples into JSON Schema fields;
- return structured CNV correction details for auto-retry;
- compute CNV size and parsed `DEL`/`DUP` type in the presenter;
- warn when search defaults to `hg38`;
- use clean Pydantic input types for `search_variants`;
- convert routine final-strength inference from warning-only noise into a data
  field while keeping warning compatibility outside summary mode;
- expose compact MCP prompts for canonical workflows;
- register `clear_cache` only when destructive tools are explicitly enabled;
- add a read-only health tool that does not call upstream by default.

## Non-Goals

- No upstream rate-limit changes.
- No parser changes unless a presenter test exposes a factual parser bug.
- No clinical decision support framing.
- No destructive tool exposure unless `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS`
  is true.
- No bulk tool implementation in this pass. Bulk scoring is valuable, but it
  changes upstream-call behavior and deserves a separate rate-limit-aware plan.

## Testing

Use focused, test-first changes under `tests/unit/mcp/`. Keep fixtures unchanged
unless parser behavior changes. Regenerate `docs/mcp-tool-catalog.md` and run:

- focused MCP tests touched by this pass;
- `uv run pytest tests/unit/mcp/test_tool_catalog_docs.py -q`;
- `uv run python scripts/check_file_size.py`;
- `make ci-local`.
