# MCP LLM Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve AutoPVS1-Link MCP agent ergonomics with typed schemas, verbosity controls, better discovery, structured corrections, prompts, and safer destructive-tool exposure.

**Architecture:** Keep parser and REST behavior stable. Add MCP-only typed contracts and response shaping in `autopvs1_link/mcp/`, with tools passing optional control parameters into presenters. Regenerate generated docs after implementation.

**Tech Stack:** Python 3.12, FastMCP, Pydantic 2, pytest, Ruff, mypy, uv/make.

---

## File Structure

- Modify `autopvs1_link/mcp/contracts.py` for typed data models and mode enums.
- Modify `autopvs1_link/mcp/envelope.py` for `meta_mode` and structured error details.
- Modify `autopvs1_link/mcp/presenters/variant.py` and `search.py` for response modes.
- Modify `autopvs1_link/mcp/presenters/capabilities.py` for structured workflow and examples.
- Modify `autopvs1_link/mcp/validation.py` and `errors.py` for structured CNV corrections and mode validation.
- Modify `autopvs1_link/mcp/tools/*.py`, `metadata.py`, and `facade.py` for typed inputs, examples, optional controls, hidden destructive registration, prompts, and health.
- Add `autopvs1_link/mcp/prompts.py` and `autopvs1_link/mcp/tools/health_tool.py`.
- Update tests under `tests/unit/mcp/`.
- Regenerate `docs/mcp-tool-catalog.md`.

## Task 1: Typed Contracts and Capabilities Discovery

**Files:**
- Modify: `autopvs1_link/mcp/contracts.py`
- Modify: `autopvs1_link/mcp/presenters/capabilities.py`
- Test: `tests/unit/mcp/test_capabilities_presenter.py`
- Test: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting `tool_summaries` entries are objects with `purpose` and
`example`, `compact_workflow` entries are ordered objects with `step` and
`when`, and output schemas expose typed `variant_info`, `cnv_info`,
`pvs1_flowchart`, and search result rows instead of opaque object lists.

- [ ] **Step 2: Verify failure**

Run:

```bash
uv run pytest tests/unit/mcp/test_capabilities_presenter.py tests/unit/mcp/test_tools.py -q
```

Expected: fails because the current contracts still use `dict[str, Any]` and
flat strings.

- [ ] **Step 3: Implement**

Add Pydantic models for `VariantInfoMCP`, `CNVInfoMCP`, `PVS1FlowchartMCP`,
`FlowchartStepMCP`, `DiseaseMechanismMCP`, `SearchResultMCP`,
`ToolSummaryMCP`, and `WorkflowStepMCP`. Update capabilities presenter to emit
structured summaries and workflow steps with examples.

- [ ] **Step 4: Verify pass**

Run the same focused test command.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/contracts.py autopvs1_link/mcp/presenters/capabilities.py tests/unit/mcp/test_capabilities_presenter.py tests/unit/mcp/test_tools.py
git commit -m "feat: type mcp discovery contracts"
```

## Task 2: Response and Metadata Modes

**Files:**
- Modify: `autopvs1_link/mcp/envelope.py`
- Modify: `autopvs1_link/mcp/presenters/variant.py`
- Modify: `autopvs1_link/mcp/presenters/search.py`
- Modify: `autopvs1_link/mcp/tools/variant_tool.py`
- Modify: `autopvs1_link/mcp/tools/cnv_tool.py`
- Modify: `autopvs1_link/mcp/tools/search_tool.py`
- Test: `tests/unit/mcp/test_variant_presenter.py`
- Test: `tests/unit/mcp/test_search_presenter.py`
- Test: `tests/unit/mcp/test_tool_runtime.py`

- [ ] **Step 1: Write failing tests**

Add tests for `response_mode="summary"` on variant, CNV, and search calls;
`response_mode="full"` preserving existing rich fields; `meta_mode="compact"`
returning citation DOI/PMID without text/URL; and `meta_mode="minimal"`
preserving research-use metadata while omitting citation.

- [ ] **Step 2: Verify failure**

Run:

```bash
uv run pytest tests/unit/mcp/test_variant_presenter.py tests/unit/mcp/test_search_presenter.py tests/unit/mcp/test_tool_runtime.py -q
```

Expected: fails because tools do not accept these controls.

- [ ] **Step 3: Implement**

Thread `response_mode`, `meta_mode`, and `include_unmet` through the relevant
tools and presenters. Keep defaults backward compatible. Move
`final_strength_inferred` into flowchart data as `final_strength_source`, and
emit the warning only for non-summary responses.

- [ ] **Step 4: Verify pass**

Run the same focused test command.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/envelope.py autopvs1_link/mcp/presenters/variant.py autopvs1_link/mcp/presenters/search.py autopvs1_link/mcp/tools/variant_tool.py autopvs1_link/mcp/tools/cnv_tool.py autopvs1_link/mcp/tools/search_tool.py tests/unit/mcp/test_variant_presenter.py tests/unit/mcp/test_search_presenter.py tests/unit/mcp/test_tool_runtime.py
git commit -m "feat: add mcp verbosity controls"
```

## Task 3: CNV and Search Affordances

**Files:**
- Modify: `autopvs1_link/mcp/errors.py`
- Modify: `autopvs1_link/mcp/validation.py`
- Modify: `autopvs1_link/mcp/presenters/variant.py`
- Modify: `autopvs1_link/mcp/tools/search_tool.py`
- Test: `tests/unit/mcp/test_validation.py`
- Test: `tests/unit/mcp/test_variant_presenter.py`
- Test: `tests/unit/mcp/test_tool_runtime.py`

- [ ] **Step 1: Write failing tests**

Add tests for structured `error.details.corrected_id`, computed CNV `size`,
parsed `cnv_type` as `DEL`/`DUP`, a warning when search defaults to `hg38`, and
clean non-`Any` JSON Schema for `search_variants` parameters.

- [ ] **Step 2: Verify failure**

Run:

```bash
uv run pytest tests/unit/mcp/test_validation.py tests/unit/mcp/test_variant_presenter.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py -q
```

Expected: fails on missing structured details, missing size/type derivation,
default-build warning, or schema typing.

- [ ] **Step 3: Implement**

Add optional `details` to `MCPError` and populate `corrected_id` for colon-form
CNV input. Derive CNV size and type from the normalized CNV ID in the MCP
presenter. Change search tool annotations from `Any` to clean `str | None` and
`int` types while retaining runtime validation.

- [ ] **Step 4: Verify pass**

Run the same focused test command.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/errors.py autopvs1_link/mcp/validation.py autopvs1_link/mcp/presenters/variant.py autopvs1_link/mcp/tools/search_tool.py tests/unit/mcp/test_validation.py tests/unit/mcp/test_variant_presenter.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py
git commit -m "feat: improve mcp input affordances"
```

## Task 4: Prompts, Health, and Destructive Surface

**Files:**
- Add: `autopvs1_link/mcp/prompts.py`
- Add: `autopvs1_link/mcp/tools/health_tool.py`
- Modify: `autopvs1_link/mcp/facade.py`
- Modify: `autopvs1_link/mcp/tools/cache_tools.py`
- Modify: `scripts/generate_mcp_tool_catalog.py`
- Test: `tests/unit/mcp/test_tool_runtime.py`
- Test: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting `clear_cache` is not registered by default, is registered
when `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`, `get_server_health` is
read-only and returns local health without upstream calls by default, MCP
prompts `classify_variant` and `classify_cnv` are listed, and the generated
catalog includes prompts.

- [ ] **Step 2: Verify failure**

Run:

```bash
uv run pytest tests/unit/mcp/test_tools.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tool_catalog_docs.py -q
```

Expected: fails because prompts and health are absent, `clear_cache` remains
registered by default, and the catalog does not render prompts.

- [ ] **Step 3: Implement**

Add prompt registration, a local health tool, conditional clear-cache
registration, and prompt rendering in the catalog generator.

- [ ] **Step 4: Verify pass**

Run the same focused test command.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/prompts.py autopvs1_link/mcp/tools/health_tool.py autopvs1_link/mcp/facade.py autopvs1_link/mcp/tools/cache_tools.py scripts/generate_mcp_tool_catalog.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tool_catalog_docs.py
git commit -m "feat: add mcp workflow prompts and health"
```

## Task 5: Documentation and Final Verification

**Files:**
- Modify: `docs/mcp-tool-catalog.md`
- Modify: `README.md`
- Modify: `docs/api.md`
- Modify: `docs/mcp-evaluation-checklist.md`

- [ ] **Step 1: Regenerate tool catalog**

Run:

```bash
uv run python scripts/generate_mcp_tool_catalog.py
```

- [ ] **Step 2: Update docs**

Document `response_mode`, `meta_mode`, summary/full behavior, structured CNV
corrections, default search build warning, prompts, health, and opt-in
destructive tools.

- [ ] **Step 3: Run final checks**

Run:

```bash
uv run pytest tests/unit/mcp/test_variant_presenter.py tests/unit/mcp/test_search_presenter.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py -q
uv run pytest tests/unit/mcp/test_tool_catalog_docs.py -q
uv run python scripts/check_file_size.py
make ci-local
```

- [ ] **Step 4: Commit**

```bash
git add docs/mcp-tool-catalog.md README.md docs/api.md docs/mcp-evaluation-checklist.md
git commit -m "docs: document mcp polish controls"
```
