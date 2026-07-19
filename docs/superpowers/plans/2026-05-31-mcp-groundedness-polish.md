# MCP Groundedness & Token-Efficiency Polish Implementation Plan

> Historical record

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the AutoPVS1-Link MCP surface from ~8.4/10 to ~9.5/10 for LLM consumers by adding a deterministic decision-path gloss, machine-executable next-step commands, a leaner default metadata tier, an honest cursor contract, and a per-response cold-latency hint.

**Architecture:** Five additive, backward-compatible changes plus one versioned default flip. New cohesive helper modules (`pvs1_glossary.py`, `next_commands.py`) keep logic out of the near-cap `bulk_tools.py`. All metadata changes ride the existing `MCPMeta` + null-strip machinery; the cold-latency source lives in `cost_tiers.py` to avoid an `envelope → capabilities` import cycle.

**Tech Stack:** Python 3.12, Pydantic v2, FastMCP, pytest, Ruff, mypy, `uv`. Spec: `docs/superpowers/specs/2026-05-31-mcp-groundedness-polish-design.md`.

---

## File Structure

**New files:**
- `autopvs1_link/mcp/pvs1_glossary.py` — pure `synthesize_path_gloss(...)`; deterministic compression of the parsed decision-tree branch into a one-line rationale.
- `autopvs1_link/mcp/next_commands.py` — pure builders for machine-executable `{tool, arguments, reason}` next steps (widen, next-page, bulk-retry, error disambiguation).
- `tests/unit/mcp/test_pvs1_glossary.py` — unit tests for the glossary.
- `tests/unit/mcp/test_next_commands.py` — unit tests for the builders.

**Modified files:**
- `autopvs1_link/mcp/presenters/variant.py` — attach `path_gloss` in `_present_flowchart`.
- `autopvs1_link/mcp/contracts.py` — add `path_gloss` field; relabel cursor docstring.
- `autopvs1_link/mcp/envelope.py` — `MCPMeta.next_commands` + `expected_cold_latency_ms`; thread through `ok_envelope`/`error_envelope`; extend null-strip.
- `autopvs1_link/mcp/cost_tiers.py` — `COLD_CALL_LATENCY_MS` + `cold_latency_ms_for`.
- `autopvs1_link/mcp/resolution.py` — add `genome_build` to disambiguation candidate rows.
- `autopvs1_link/mcp/tools/{variant_tool,cnv_tool,search_tool,bulk_tools}.py` — flip `meta_mode` default to `compact`; attach `next_commands`.
- `autopvs1_link/mcp/mode_validation.py` — flip default wording in the `meta_mode` suggestion.
- `autopvs1_link/mcp/presenters/capabilities.py` — document `path_gloss`, `next_commands`, `expected_cold_latency_ms`; relabel cursor.
- `autopvs1_link/mcp/server_info.py` — sync the `meta_mode` default note in `SERVER_DESCRIPTION` (stay under the ~1900-byte test ceiling).
- `autopvs1_link/__init__.py`, `pyproject.toml` — version `1.1.0 → 1.2.0`.
- `CHANGELOG.md` — breaking-default note.
- `docs/api.md`, `docs/mcp-tool-catalog.md` — meta-default + new-field docs (if present; verify in Task 9).
- Existing tests: `test_variant_presenter.py`, `test_envelope.py`, `test_validation.py`, `test_capabilities_presenter.py`, `test_cost_tiers.py`, `test_tool_runtime.py`, `test_bulk_tools.py`, `test_server_info.py` — updated assertions.

**Branch:** `feat/mcp-groundedness-polish` (already created; spec committed at `d35176b`).

---

## Task 1: `pvs1_glossary` module (deterministic path gloss)

**Files:**
- Create: `autopvs1_link/mcp/pvs1_glossary.py`
- Test: `tests/unit/mcp/test_pvs1_glossary.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/mcp/test_pvs1_glossary.py`:

```python
"""Unit tests for deterministic PVS1 path-gloss synthesis."""

from __future__ import annotations

from autopvs1_link.mcp.pvs1_glossary import synthesize_path_gloss


def test_joins_branch_nodes_with_ascii_arrow_and_appends_strength() -> None:
    steps = [
        {"code": "Nonsense or Frameshift"},
        {"code": "Not predicted to undergo NMD"},
        {"code": "Removes >10% of protein"},
    ]
    gloss = synthesize_path_gloss(
        steps, final_strength="Strong", preliminary_decision_path="NF5"
    )
    assert gloss == (
        "Nonsense or Frameshift -> Not predicted to undergo NMD -> "
        "Removes >10% of protein -> Strong"
    )


def test_does_not_duplicate_trailing_strength_when_last_node_is_strength() -> None:
    steps = [{"code": "Nonsense or Frameshift"}, {"code": "Strong"}]
    gloss = synthesize_path_gloss(
        steps, final_strength="Strong", preliminary_decision_path="NF5"
    )
    assert gloss == "Nonsense or Frameshift -> Strong"


def test_collapses_consecutive_duplicate_nodes() -> None:
    steps = [{"code": "A"}, {"code": "A"}, {"code": "B"}]
    gloss = synthesize_path_gloss(steps, final_strength="Unmet", preliminary_decision_path="NF4")
    assert gloss == "A -> B -> Unmet"


def test_empty_tree_falls_back_to_identifiers_only() -> None:
    gloss = synthesize_path_gloss([], final_strength="Unmet", preliminary_decision_path="NF4")
    assert gloss == "Decision path NF4 -> Unmet"


def test_returns_none_when_no_signal_at_all() -> None:
    assert synthesize_path_gloss([], final_strength="", preliminary_decision_path="") is None


def test_ignores_blank_node_text() -> None:
    steps = [{"code": "  "}, {"code": "Real node"}, {"code": ""}]
    gloss = synthesize_path_gloss(
        steps, final_strength="VeryStrong", preliminary_decision_path="NF1"
    )
    assert gloss == "Real node -> VeryStrong"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_pvs1_glossary.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'autopvs1_link.mcp.pvs1_glossary'`

- [ ] **Step 3: Write minimal implementation**

Create `autopvs1_link/mcp/pvs1_glossary.py`:

```python
"""Deterministic one-line gloss for a PVS1 decision path.

The gloss is a faithful compression of the decision-tree branch the
variant actually traversed (already parsed from the AutoPVS1 HTML) plus
the terminal strength. It introduces NO hand-authored clinical mappings:
every word comes from upstream scraped text, so the gloss is grounded and
fixture-testable. It exists to fill the summary-mode gap where the full
``decision_tree`` is stripped, so a caller can explain *why* a verdict
landed without paying a round-trip to widen to ``standard``.

ASCII ``->`` is used as the separator per the repo ASCII rule.
"""

from __future__ import annotations

from typing import Any

_ARROW = " -> "


def synthesize_path_gloss(
    steps: list[dict[str, Any]],
    *,
    final_strength: str,
    preliminary_decision_path: str,
) -> str | None:
    """Return a one-line rationale for the decision path, or ``None``.

    ``steps`` are the presented decision-tree steps (each a dict with a
    ``code`` field holding the upstream branch-node text). Consecutive
    duplicate node texts are collapsed. The terminal ``final_strength`` is
    appended unless the last node already is that strength. When there are
    no usable steps, falls back to ``"Decision path {code} -> {strength}"``
    using only the bare identifiers (no invented meaning). Returns ``None``
    only when there is no signal at all so callers drop the field instead
    of shipping an empty string.
    """
    texts: list[str] = []
    for step in steps:
        text = str(step.get("code") or "").strip()
        if text and (not texts or texts[-1] != text):
            texts.append(text)
    strength = (final_strength or "").strip()
    path = (preliminary_decision_path or "").strip()

    if not texts:
        if not path and not strength:
            return None
        return f"Decision path {path or 'unknown'}{_ARROW}{strength or 'unknown'}"

    gloss = _ARROW.join(texts)
    if strength and texts[-1].lower() != strength.lower():
        gloss = f"{gloss}{_ARROW}{strength}"
    return gloss
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/mcp/test_pvs1_glossary.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/pvs1_glossary.py tests/unit/mcp/test_pvs1_glossary.py
git commit -m "feat(mcp): deterministic PVS1 path-gloss synthesis helper"
```

---

## Task 2: Wire `path_gloss` into the presenter + contract

**Files:**
- Modify: `autopvs1_link/mcp/contracts.py:118` (add field), `:112-119` (docstring)
- Modify: `autopvs1_link/mcp/presenters/variant.py:88-160` (`_present_flowchart`)
- Test: `tests/unit/mcp/test_variant_presenter.py` (extend + update)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/mcp/test_variant_presenter.py` (uses the real models; self-contained — do not depend on private helpers):

```python
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1Data,
    FlowchartStep,
    PVS1Flowchart,
    VariantInfo,
)
from autopvs1_link.mcp.presenters.variant import present_variant


def _variant_with_path(strength: str, steps: list[FlowchartStep]) -> AutoPVS1Data:
    return AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T", variant_type="SNV", gene_symbol="POU3F4"
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength=strength,
            decision_tree=steps,
        ),
    )


def test_path_gloss_present_in_summary_for_strong_verdict() -> None:
    parsed = _variant_with_path(
        "Strong",
        [
            FlowchartStep(code="Nonsense or Frameshift"),
            FlowchartStep(code="Not predicted to undergo NMD"),
            FlowchartStep(code="Strong"),
        ],
    )
    data, _ = present_variant(parsed, source_url=None, response_mode="summary")
    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["pvs1_flowchart"]["path_gloss"] == (
        "Nonsense or Frameshift -> Not predicted to undergo NMD -> Strong"
    )


def test_path_gloss_present_in_standard_mode() -> None:
    parsed = _variant_with_path("Unmet", [FlowchartStep(code="Nonsense or Frameshift")])
    data, _ = present_variant(parsed, source_url=None, response_mode="standard")
    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["pvs1_flowchart"]["path_gloss"] == "Nonsense or Frameshift -> Unmet"


def test_path_gloss_absent_in_ids_only_mode() -> None:
    parsed = _variant_with_path("Strong", [FlowchartStep(code="Nonsense or Frameshift")])
    data, _ = present_variant(parsed, source_url=None, response_mode="ids_only")
    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload.get("pvs1_flowchart") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_variant_presenter.py -q -k path_gloss`
Expected: FAIL — `KeyError: 'path_gloss'` (field not yet emitted).

- [ ] **Step 3a: Add the contract field**

In `autopvs1_link/mcp/contracts.py`, inside `PVS1FlowchartMCP`, add the field after `terminal_note` (line 118):

```python
    terminal_note: str | None = None
    path_gloss: str | None = None
```

And extend the class docstring (after the `terminal_note` paragraph, before the closing `"""`):

```python
    ``path_gloss`` is a one-line, deterministic compression of the
    decision-tree branch the variant traversed plus the terminal
    strength (ASCII ``->`` separated). Unlike ``terminal_note`` it is
    emitted for EVERY path in summary/standard/full modes (not just
    ambiguous verdicts), so a summary-mode caller can always state why a
    verdict landed without widening to standard. Built only from upstream
    scraped node text — no hand-authored clinical mappings.
```

- [ ] **Step 3b: Wire synthesis into the presenter**

In `autopvs1_link/mcp/presenters/variant.py`, add the import near the top (after line 12):

```python
from autopvs1_link.mcp.pvs1_glossary import synthesize_path_gloss
```

In `_present_flowchart`, after `raw["decision_tree"] = presented_steps` (line 132) and before `if response_mode == "summary":`, compute the gloss once:

```python
    raw["decision_tree"] = presented_steps
    path_gloss = synthesize_path_gloss(
        presented_steps,
        final_strength=final_strength,
        preliminary_decision_path=str(raw.get("preliminary_decision_path") or ""),
    )
    if response_mode == "summary":
        summary: dict[str, Any] = {
            "preliminary_decision_path": raw["preliminary_decision_path"],
            "final_strength": raw["final_strength"],
            "final_strength_source": raw["final_strength_source"],
        }
```

Then attach it in both branches. In the summary branch, after the existing `terminal_note` block (after line 152) and before `raw = summary`:

```python
            if note is not None:
                summary["terminal_note"] = note
        if path_gloss is not None:
            summary["path_gloss"] = path_gloss
        raw = summary
    elif response_mode == "full":
        raw["decision_tree_raw"] = raw_decision_tree
        if path_gloss is not None:
            raw["path_gloss"] = path_gloss
    else:
        # standard: notes legend is duplicative because decision_tree
        # steps already carry note_text; drop it from the wire payload.
        raw.pop("notes", None)
        if path_gloss is not None:
            raw["path_gloss"] = path_gloss
    return raw, warnings
```

- [ ] **Step 4: Run new tests to verify they pass**

Run: `uv run pytest tests/unit/mcp/test_variant_presenter.py -q -k path_gloss`
Expected: PASS (3 passed)

- [ ] **Step 5: Fix any pre-existing summary-mode key-equality assertions**

Run: `uv run pytest tests/unit/mcp/test_variant_presenter.py -q`
Some existing tests assert the exact summary `pvs1_flowchart` dict (they now gain a `path_gloss` key). For each failure, read the asserted expected dict and add the matching `path_gloss` value, OR change exact-equality (`==`) on the flowchart sub-dict to assert the previously-checked keys individually. Do NOT delete the new key — update the expectation to include it. Re-run until green.

- [ ] **Step 6: Document the field in capabilities + update its snapshot test**

In `autopvs1_link/mcp/presenters/capabilities.py`, inside `tier_specific_fields` (after the `pvs1_flowchart.terminal_note` entry, ~line 347), add:

```python
            "pvs1_flowchart.path_gloss": (
                "One-line deterministic rationale: the decision-tree "
                "branch the variant traversed plus the terminal strength "
                "(ASCII '->' separated). Present for EVERY path in "
                "summary, standard, and full tiers (absent in ids_only). "
                "Built only from upstream scraped node text; lets a "
                "summary-mode caller explain the verdict without widening."
            ),
```

Run: `uv run pytest tests/unit/mcp/test_capabilities_presenter.py -q`
If a snapshot test asserts the exact `tier_specific_fields` dict, add the new key to the expected snapshot. Re-run until green.

- [ ] **Step 7: Commit**

```bash
git add autopvs1_link/mcp/contracts.py autopvs1_link/mcp/presenters/variant.py \
        autopvs1_link/mcp/presenters/capabilities.py tests/unit/mcp/test_variant_presenter.py \
        tests/unit/mcp/test_capabilities_presenter.py
git commit -m "feat(mcp): emit deterministic path_gloss on every PVS1 verdict"
```

---

## Task 3: `next_commands` builder module

**Files:**
- Create: `autopvs1_link/mcp/next_commands.py`
- Test: `tests/unit/mcp/test_next_commands.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/mcp/test_next_commands.py`:

```python
"""Unit tests for machine-executable next_commands builders."""

from __future__ import annotations

from autopvs1_link.mcp.next_commands import (
    bulk_retry_failed,
    error_next_commands,
    search_next_page,
    widen_response_mode,
)


class _Input:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


class _Item:
    def __init__(self, ok: bool, **kw: object) -> None:
        self.ok = ok
        self.input = _Input(**kw)


def test_widen_from_summary_targets_standard() -> None:
    cmds = widen_response_mode(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
        "summary",
    )
    assert cmds == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {
                "genome_build": "hg19",
                "variant_id": "X-82763936-A-T",
                "response_mode": "standard",
            },
            "reason": "Widen to response_mode='standard' for the full decision tree.",
        }
    ]


def test_widen_from_full_returns_none() -> None:
    assert widen_response_mode("get_variant_pvs1_data", {"x": 1}, "full") is None


def test_search_next_page_only_when_cursor_present() -> None:
    args = {"query": "BRCA1", "genome_build": "hg38", "limit": 10}
    assert search_next_page(args, None) is None
    cmds = search_next_page(args, "Y2Vu")
    assert cmds == [
        {
            "tool": "search_variants",
            "arguments": {"query": "BRCA1", "genome_build": "hg38", "limit": 10, "cursor": "Y2Vu"},
            "reason": "Fetch the next page of results.",
        }
    ]


def test_bulk_retry_failed_lists_only_failed_items() -> None:
    results = [
        _Item(True, genome_build="hg19", variant_id="X-82763936-A-T"),
        _Item(False, genome_build="hg19", variant_id="BADID"),
    ]
    cmds = bulk_retry_failed("get_variant_pvs1_data", results, "variant_id")
    assert cmds == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"genome_build": "hg19", "variant_id": "BADID"},
            "reason": "Retry this failed item individually.",
        }
    ]


def test_bulk_retry_failed_none_when_all_ok() -> None:
    results = [_Item(True, genome_build="hg19", variant_id="X-82763936-A-T")]
    assert bulk_retry_failed("get_variant_pvs1_data", results, "variant_id") is None


def test_error_next_commands_builds_one_command_per_candidate() -> None:
    details = {
        "candidates": [
            {"id": "17-43045712-A-G", "genome_build": "hg38", "spdi": "..."},
            {"id": "17-43045713-A-G", "genome_build": "hg38"},
        ]
    }
    cmds = error_next_commands("requires_disambiguation", details)
    assert cmds == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"variant_id": "17-43045712-A-G", "genome_build": "hg38"},
            "reason": "Re-score with this disambiguated candidate id.",
        },
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"variant_id": "17-43045713-A-G", "genome_build": "hg38"},
            "reason": "Re-score with this disambiguated candidate id.",
        },
    ]


def test_error_next_commands_none_for_other_codes() -> None:
    assert error_next_commands("invalid_variant_id", {"candidates": []}) is None
    assert error_next_commands("requires_disambiguation", None) is None
    assert error_next_commands("requires_disambiguation", {"candidates": []}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_next_commands.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'autopvs1_link.mcp.next_commands'`

- [ ] **Step 3: Write minimal implementation**

Create `autopvs1_link/mcp/next_commands.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/mcp/test_next_commands.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/next_commands.py tests/unit/mcp/test_next_commands.py
git commit -m "feat(mcp): next_commands builders for machine-executable chaining"
```

---

## Task 4: Thread `next_commands` through the envelope + enrich disambiguation candidates

**Files:**
- Modify: `autopvs1_link/mcp/envelope.py` (MCPMeta:104-170; ok_envelope:299-364; error_envelope:367-441; `_strip_none_telemetry_fields`:223-248)
- Modify: `autopvs1_link/mcp/resolution.py:19-50,102-114` (candidate `genome_build`)
- Test: `tests/unit/mcp/test_envelope.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/mcp/test_envelope.py`:

```python
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope


def test_ok_envelope_carries_next_commands_when_supplied() -> None:
    out = ok_envelope(
        {"x": 1},
        meta_mode="full",
        tool_name="get_variant_pvs1_data",
        next_commands=[{"tool": "get_variant_pvs1_data", "arguments": {"y": 2}, "reason": "r"}],
    )
    assert out["meta"]["next_commands"] == [
        {"tool": "get_variant_pvs1_data", "arguments": {"y": 2}, "reason": "r"}
    ]


def test_ok_envelope_drops_next_commands_when_absent() -> None:
    out = ok_envelope({"x": 1}, meta_mode="full", tool_name="get_variant_pvs1_data")
    assert "next_commands" not in out["meta"]


def test_error_envelope_derives_disambiguation_next_commands() -> None:
    result = error_envelope(
        code="requires_disambiguation",
        message="pick one",
        retryable=False,
        details={"candidates": [{"id": "17-1-A-G", "genome_build": "hg38"}]},
        tool_name="get_variant_pvs1_data",
    )
    meta = result.structured_content["meta"]
    assert meta["next_commands"] == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"variant_id": "17-1-A-G", "genome_build": "hg38"},
            "reason": "Re-score with this disambiguated candidate id.",
        }
    ]


def test_error_envelope_without_candidates_drops_next_commands() -> None:
    result = error_envelope(
        code="invalid_variant_id",
        message="bad",
        retryable=False,
        tool_name="get_variant_pvs1_data",
    )
    assert "next_commands" not in result.structured_content["meta"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_envelope.py -q -k next_commands`
Expected: FAIL — `TypeError: ok_envelope() got an unexpected keyword argument 'next_commands'`

- [ ] **Step 3a: Add the MCPMeta field**

In `autopvs1_link/mcp/envelope.py`, add to `MCPMeta` after `next_actions` (line 168):

```python
    next_actions: list[str] | None = None
    next_commands: list[dict[str, Any]] | None = None
```

- [ ] **Step 3b: Extend the null-strip list**

In `_strip_none_telemetry_fields` (line 235-245 tuple), add the two new keys (the second is added in Task 6 — add both now to avoid re-touching):

```python
        for key in (
            "elapsed_ms",
            "cache_status",
            "cost_tier",
            "rate_limit_floor_ms",
            "next_call_earliest_at",
            "retry_after_ms",
            "next_actions",
            "next_commands",
            "expected_cold_latency_ms",
            "cached_count",
            "uncached_count",
        ):
```

- [ ] **Step 3c: Thread through `ok_envelope`**

Add the parameter to `ok_envelope` (after `uncached_count: int | None = None,` at line 308):

```python
    cached_count: int | None = None,
    uncached_count: int | None = None,
    next_commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
```

And pass it into the `MCPMeta(...)` constructor (after `uncached_count=uncached_count,` at line 356):

```python
            cached_count=cached_count,
            uncached_count=uncached_count,
            next_commands=next_commands,
        ),
```

- [ ] **Step 3d: Derive in `error_envelope`**

Add the import near the top of `envelope.py` (after line 20):

```python
from autopvs1_link.mcp.next_commands import error_next_commands
```

In `error_envelope`, set `next_commands` on the meta (after `next_actions=next_actions_for(code),` at line 429):

```python
            next_actions=next_actions_for(code),
            next_commands=error_next_commands(code, details),
        ),
```

- [ ] **Step 3e: Enrich disambiguation candidates with `genome_build`**

In `autopvs1_link/mcp/resolution.py`, change `_candidate_rows` to accept the build (line 19):

```python
def _candidate_rows(results: list[VariantRecoderResult], build: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in results:
        row = {
            "id": item.variant_id,
            "spdi": item.spdi,
            "allele_key": item.allele_key,
            "genome_build": build,
        }
        if item.resource_uri:
            row["resource_uri"] = item.resource_uri
        rows.append(row)
    return rows
```

Update both call sites to pass the build: in `_disambiguation_error` use `_candidate_rows(results, build)`, and in the inline `requires_disambiguation` raise (the `details={"candidates": _candidate_rows(results)}` call) use `_candidate_rows(results, genome_build)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/mcp/test_envelope.py -q -k next_commands`
Expected: PASS (4 passed)

- [ ] **Step 5: Fix fallout in envelope/resolution tests**

Run: `uv run pytest tests/unit/mcp/test_envelope.py tests/unit/mcp/test_resolution.py tests/unit/mcp/test_tool_runtime.py -q`
If a resolution test asserts the exact candidate-row dict, add `"genome_build"` to the expected row. If an envelope absence test enumerates meta keys, add `next_commands` to the strip expectations. Update and re-run until green.

- [ ] **Step 6: Commit**

```bash
git add autopvs1_link/mcp/envelope.py autopvs1_link/mcp/resolution.py tests/unit/mcp/
git commit -m "feat(mcp): wire next_commands through envelope + disambiguation candidates"
```

---

## Task 5: Attach `next_commands` at tool call sites

**Files:**
- Modify: `autopvs1_link/mcp/tools/variant_tool.py:139-144`
- Modify: `autopvs1_link/mcp/tools/cnv_tool.py:117-122`
- Modify: `autopvs1_link/mcp/tools/search_tool.py:141-146`
- Modify: `autopvs1_link/mcp/tools/bulk_tools.py:381-387,544-550`
- Test: `tests/unit/mcp/test_tool_runtime.py`, `tests/unit/mcp/test_bulk_tools.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/mcp/test_tool_runtime.py` (follow the existing mocker/`build_mcp_server`/`call_tool` pattern already used in that file — construct the parsed `AutoPVS1Data` the same way the existing variant runtime tests do):

```python
import pytest

from autopvs1_link.mcp.facade import build_mcp_server


@pytest.mark.asyncio
async def test_variant_success_offers_widen_next_command(mocker) -> None:
    from autopvs1_link.models.autopvs1_models import (
        AutoPVS1Data,
        FlowchartStep,
        PVS1Flowchart,
        VariantInfo,
    )

    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T", variant_type="SNV", gene_symbol="POU3F4"
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[FlowchartStep(code="Nonsense or Frameshift"), FlowchartStep(code="Strong")],
        ),
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=mocker.AsyncMock(return_value=parsed),
    )
    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T", "response_mode": "summary"},
    )
    cmds = result.structured_content["meta"]["next_commands"]
    assert cmds[0]["tool"] == "get_variant_pvs1_data"
    assert cmds[0]["arguments"]["response_mode"] == "standard"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_tool_runtime.py -q -k widen_next_command`
Expected: FAIL — `KeyError: 'next_commands'`

- [ ] **Step 3a: variant_tool**

In `autopvs1_link/mcp/tools/variant_tool.py`, add the import (after line 24):

```python
from autopvs1_link.mcp.next_commands import widen_response_mode
```

Change the success `ok_envelope` call (lines 139-144) to attach the widen command:

```python
            return ok_envelope(
                data,
                warnings=resolution_warnings + warnings,
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
                next_commands=widen_response_mode(
                    _TOOL_NAME,
                    {"genome_build": normalized_build, "variant_id": normalized_variant_id},
                    normalized_response_mode,
                ),
            )
```

- [ ] **Step 3b: cnv_tool**

In `autopvs1_link/mcp/tools/cnv_tool.py`, add the import (after line 25):

```python
from autopvs1_link.mcp.next_commands import widen_response_mode
```

Change the success `ok_envelope` call (lines 117-122):

```python
            return ok_envelope(
                data,
                warnings=warnings,
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
                next_commands=widen_response_mode(
                    _TOOL_NAME,
                    {"genome_build": normalized_build, "cnv_id": normalized_cnv_id},
                    normalized_response_mode,
                ),
            )
```

- [ ] **Step 3c: search_tool**

In `autopvs1_link/mcp/tools/search_tool.py`, add the import (after line 22):

```python
from autopvs1_link.mcp.next_commands import search_next_page
```

Change the success `ok_envelope` call (lines 141-146):

```python
            return ok_envelope(
                data,
                warnings=warnings,
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
                next_commands=search_next_page(
                    {
                        "query": normalized_query,
                        "genome_build": normalized_build,
                        "limit": normalized_limit,
                    },
                    data.pagination.next_cursor,
                ),
            )
```

- [ ] **Step 3d: bulk_tools (both surfaces)**

In `autopvs1_link/mcp/tools/bulk_tools.py`, add the import (after line 31):

```python
from autopvs1_link.mcp.next_commands import bulk_retry_failed
```

Change the variants success `ok_envelope` call (lines 381-387):

```python
        return ok_envelope(
            payload,
            warnings=_dedupe_warnings(aggregated_warnings),
            meta_mode=normalized_meta_mode,
            tool_name=_VARIANTS_BULK_TOOL,
            next_commands=bulk_retry_failed("get_variant_pvs1_data", results, "variant_id"),
            **aggregate_kwargs,
        )
```

Change the CNVs success `ok_envelope` call (lines 544-550):

```python
        return ok_envelope(
            payload,
            warnings=_dedupe_warnings(aggregated_warnings),
            meta_mode=normalized_meta_mode,
            tool_name=_CNVS_BULK_TOOL,
            next_commands=bulk_retry_failed("get_cnv_pvs1_data", results, "cnv_id"),
            **aggregate_kwargs,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_bulk_tools.py -q`
Expected: PASS (the new test passes; existing tests still green — `next_commands` is additive and absent unless set).

- [ ] **Step 5: Verify LOC budget on bulk_tools.py**

Run: `uv run python scripts/check_file_size.py` (or `make lint-loc`)
Expected: PASS — `bulk_tools.py` gained ~3 lines (≈553/600), still under cap.

- [ ] **Step 6: Commit**

```bash
git add autopvs1_link/mcp/tools/ tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_bulk_tools.py
git commit -m "feat(mcp): attach next_commands on variant/cnv/search/bulk success envelopes"
```

---

## Task 6: Cold-latency hint

**Files:**
- Modify: `autopvs1_link/mcp/cost_tiers.py` (add `COLD_CALL_LATENCY_MS` + `cold_latency_ms_for`)
- Modify: `autopvs1_link/mcp/envelope.py` (MCPMeta field already added in Task 4 strip-list; add field + emit in `ok_envelope`)
- Test: `tests/unit/mcp/test_cost_tiers.py`, `tests/unit/mcp/test_envelope.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/mcp/test_cost_tiers.py`:

```python
from autopvs1_link.mcp.cost_tiers import COLD_CALL_LATENCY_MS, cold_latency_ms_for


def test_cold_latency_lockstep_with_performance_block() -> None:
    from autopvs1_link.mcp.presenters.capabilities import _PERFORMANCE_BLOCK

    for tool, ms in COLD_CALL_LATENCY_MS.items():
        expected = int(_PERFORMANCE_BLOCK[tool]["cold_call_seconds"] * 1000)
        assert ms == expected, f"{tool}: {ms} != {expected}"


def test_cold_latency_ms_for_unknown_is_none() -> None:
    assert cold_latency_ms_for("get_server_health") is None
    assert cold_latency_ms_for(None) is None
```

Append to `tests/unit/mcp/test_envelope.py`:

```python
def test_ok_envelope_emits_cold_latency_only_on_cold_call() -> None:
    cold = ok_envelope(
        {"x": 1},
        meta_mode="full",
        tool_name="search_variants",
        cache_status_override="miss",
    )
    assert cold["meta"]["expected_cold_latency_ms"] == 3000
    warm = ok_envelope(
        {"x": 1},
        meta_mode="full",
        tool_name="search_variants",
        cache_status_override="hit",
    )
    assert "expected_cold_latency_ms" not in warm["meta"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_cost_tiers.py tests/unit/mcp/test_envelope.py -q -k cold_latency`
Expected: FAIL — `ImportError: cannot import name 'COLD_CALL_LATENCY_MS'`

- [ ] **Step 3a: Add the cold-latency source to cost_tiers.py**

In `autopvs1_link/mcp/cost_tiers.py`, after `TOOL_COST_TIERS` (line 23), add:

```python
# Coarse cold-call latency per scrape-tier tool, in milliseconds. Kept in
# lockstep with capabilities `_PERFORMANCE_BLOCK[tool]["cold_call_seconds"]`
# by ``tests/unit/mcp/test_cost_tiers.py``. Surfaced on cold envelopes as
# ``meta.expected_cold_latency_ms`` so a caller sees the first-call cost.
COLD_CALL_LATENCY_MS: dict[str, int] = {
    "get_variant_pvs1_data": 3500,
    "get_cnv_pvs1_data": 3500,
    "search_variants": 3000,
    "get_variants_pvs1_data_bulk": 10000,
    "get_cnvs_pvs1_data_bulk": 10000,
}


def cold_latency_ms_for(tool_name: str | None) -> int | None:
    """Return the cold-call latency hint for a tool, or None if unknown."""
    if tool_name is None:
        return None
    return COLD_CALL_LATENCY_MS.get(tool_name)
```

- [ ] **Step 3b: Add the MCPMeta field**

In `autopvs1_link/mcp/envelope.py`, add to `MCPMeta` after `next_call_earliest_at` (line 166):

```python
    next_call_earliest_at: str | None = None
    expected_cold_latency_ms: int | None = None
```

(The strip-list entry was already added in Task 4 Step 3b.)

- [ ] **Step 3c: Emit it in `ok_envelope`**

In `envelope.py`, extend the import from cost_tiers (line 18):

```python
from autopvs1_link.mcp.cost_tiers import SCRAPE_TIER, cold_latency_ms_for, cost_tier_for
```

In `ok_envelope`, after the `cost_tier, rate_limit_floor_ms, next_call_earliest_at = _cost_hints_for(...)` line (342), compute and pass the hint:

```python
        cost_tier, rate_limit_floor_ms, next_call_earliest_at = _cost_hints_for(tool_name, cache_status)
        expected_cold_latency_ms = (
            cold_latency_ms_for(tool_name)
            if cache_status in ("miss", "coalesced")
            else None
        )
```

And in the `MCPMeta(...)` constructor add (after `next_call_earliest_at=next_call_earliest_at,` line 354):

```python
            next_call_earliest_at=next_call_earliest_at,
            expected_cold_latency_ms=expected_cold_latency_ms,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/mcp/test_cost_tiers.py tests/unit/mcp/test_envelope.py -q -k "cold_latency"`
Expected: PASS

- [ ] **Step 5: Document in capabilities + update snapshot**

In `autopvs1_link/mcp/presenters/capabilities.py`, inside the existing `performance` consumer or `tier_specific_fields`, add a note for the new field. Add to `tier_specific_fields`:

```python
            "meta.expected_cold_latency_ms": (
                "Present only on cold scrape-tier responses (cache_status "
                "miss/coalesced); the coarse first-call latency in ms, in "
                "lockstep with the performance block's cold_call_seconds. "
                "Absent on warm calls so callers do not over-budget."
            ),
```

Run: `uv run pytest tests/unit/mcp/test_capabilities_presenter.py -q` and update the snapshot if it pins `tier_specific_fields`.

- [ ] **Step 6: Commit**

```bash
git add autopvs1_link/mcp/cost_tiers.py autopvs1_link/mcp/envelope.py \
        autopvs1_link/mcp/presenters/capabilities.py tests/unit/mcp/test_cost_tiers.py \
        tests/unit/mcp/test_envelope.py tests/unit/mcp/test_capabilities_presenter.py
git commit -m "feat(mcp): per-response cold-latency hint on cold scrape envelopes"
```

---

## Task 7: Honest cursor contract (doc/string only)

**Files:**
- Modify: `autopvs1_link/mcp/contracts.py:244-261` (`SearchPaginationMCP` docstring)
- Modify: `autopvs1_link/mcp/tools/search_tool.py:82,116-118`
- Modify: `autopvs1_link/mcp/validation.py:227-235` (`_invalid_search_cursor` suggestion)
- Modify: `autopvs1_link/mcp/presenters/capabilities.py:276-279` (search_behavior cursor line)
- Test: `tests/unit/mcp/test_validation.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/mcp/test_validation.py`:

```python
import base64
import json

from autopvs1_link.mcp.validation import _decode_cursor, _encode_cursor


def test_cursor_roundtrips_and_is_transparent_offset() -> None:
    # Honesty contract: the cursor is an encoded offset, not an opaque token.
    cursor = _encode_cursor(30)
    assert _decode_cursor(cursor) == 30
    padded = cursor + "=" * (-len(cursor) % 4)
    assert json.loads(base64.urlsafe_b64decode(padded.encode())) == {"offset": 30}
```

- [ ] **Step 2: Run test to verify it passes already (behavior unchanged)**

Run: `uv run pytest tests/unit/mcp/test_validation.py -q -k transparent_offset`
Expected: PASS — this test documents existing behavior; the task's substance is removing the false "opaque" claims from docs. (If a separate test pins the old "opaque" suggestion string, it will fail in Step 4 and must be updated.)

- [ ] **Step 3: Replace the false "opaque" language**

In `autopvs1_link/mcp/contracts.py`, replace the first sentence of the `SearchPaginationMCP` docstring (lines 246-248):

```python
    """Pagination block for ``search_variants``.

    ``next_cursor`` / ``previous_cursor`` are base64url-encoded JSON
    ``{"offset": N}`` tokens. They round-trip transparently and are NOT
    authenticated — treat them as opaque for forward-compatibility, but
    do not rely on opacity as an integrity or security boundary. Pass the
    returned ``next_cursor`` back unchanged to page. ``offset`` is echoed
    for operator visibility only.
```

In `autopvs1_link/mcp/tools/search_tool.py`, change the `cursor` param description (line 82):

```python
                description=(
                    "Pagination token from a prior call's next_cursor "
                    "(base64url-encoded offset; not authenticated). Pass "
                    "it back unchanged to page."
                ),
```

And the docstring sentence (lines 116-118):

```python
        ``get_variant_pvs1_data``. ``next_cursor`` is a base64url-encoded
        offset (not authenticated); pass it back unchanged to page.
        AutoPVS1 outputs are research-use only, not clinical decision
        support.
```

In `autopvs1_link/mcp/validation.py`, update the `_invalid_search_cursor` suggestion (lines 231-234):

```python
        suggestions=[
            "Pass back the next_cursor value returned by the previous "
            "search_variants call unchanged; omit cursor to reset to the "
            "first page.",
        ],
```

In `autopvs1_link/mcp/presenters/capabilities.py`, update the `search_behavior.cursor` line (lines 276-279) to drop "Opaque":

```python
            "cursor": (
                "Pagination token returned as next_cursor "
                "(base64url-encoded offset; not authenticated); pass it "
                "back unchanged."
            ),
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/mcp/test_validation.py tests/unit/mcp/test_search_presenter.py tests/unit/mcp/test_capabilities_presenter.py -q`
Expected: PASS. If any test asserts the old "opaque, do not construct" wording, update it to the new honest wording.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/contracts.py autopvs1_link/mcp/tools/search_tool.py \
        autopvs1_link/mcp/validation.py autopvs1_link/mcp/presenters/capabilities.py \
        tests/unit/mcp/test_validation.py
git commit -m "docs(mcp): honest cursor contract — base64url offset, not opaque/authenticated"
```

---

## Task 8: Flip default `meta_mode` to `compact`

**Files:**
- Modify: `autopvs1_link/mcp/envelope.py:303,375` (`ok_envelope`/`error_envelope` defaults)
- Modify: `autopvs1_link/mcp/tools/variant_tool.py:94,120`; `cnv_tool.py:84,100`; `search_tool.py:110,120`; `bulk_tools.py:243,303,430,470`
- Modify: `autopvs1_link/mcp/mode_validation.py:66`
- Modify: `autopvs1_link/mcp/server_info.py:32-34`
- Test: `tests/unit/mcp/test_tool_runtime.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/mcp/test_tool_runtime.py`:

```python
@pytest.mark.asyncio
async def test_default_meta_mode_is_compact_and_validates_against_contract(mocker) -> None:
    from autopvs1_link.mcp.contracts import VariantMCPEnvelope
    from autopvs1_link.models.autopvs1_models import (
        AutoPVS1Data,
        FlowchartStep,
        PVS1Flowchart,
        VariantInfo,
    )

    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T", variant_type="SNV", gene_symbol="POU3F4"
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[FlowchartStep(code="Nonsense or Frameshift"), FlowchartStep(code="Strong")],
        ),
    )
    mocker.patch(
        "autopvs1_link.mcp.service_adapters.get_variant",
        new=mocker.AsyncMock(return_value=parsed),
    )
    mcp = build_mcp_server()
    # No meta_mode passed -> must default to compact (citation trimmed to doi+pmid).
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
    )
    citation = result.structured_content["meta"]["recommended_citation"]
    assert set(citation.keys()) == {"doi", "pmid"}

    # Honor the MEMORY null-strip lesson: the default (compact) output still
    # validates against the published envelope contract after null-stripping.
    VariantMCPEnvelope.model_validate(result.structured_content)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/mcp/test_tool_runtime.py -q -k default_meta_mode_is_compact`
Expected: FAIL — citation keys are `{"text","doi","pmid","url"}` (current default `full`).

- [ ] **Step 3a: Flip the envelope defaults**

In `autopvs1_link/mcp/envelope.py`, change `ok_envelope` (line 303) and `error_envelope` (line 375) parameter defaults:

```python
    meta_mode: Any = "compact",
```

(both functions).

- [ ] **Step 3b: Flip every tool param default + local fallback**

Change `meta_mode: Annotated[..., Field(...)] = "full"` to `= "compact"` and the description to name the new default in each tool:
- `variant_tool.py:94`, `cnv_tool.py:84`, `search_tool.py:110`, `bulk_tools.py:243`, `bulk_tools.py:430`.

Change every tool-local fallback `normalized_meta_mode: MetaMode = "full"` to `= "compact"`:
- `variant_tool.py:120`, `cnv_tool.py:100`, `search_tool.py:120`, `bulk_tools.py:303`, `bulk_tools.py:470`.

Update each `meta_mode` `Field(description=...)` to: `"Metadata detail level: compact (default — doi+pmid), full (adds verbatim citation text+url), or minimal (no citation)."`

- [ ] **Step 3c: Flip the validator suggestion**

In `autopvs1_link/mcp/mode_validation.py`, change the suggestion (line 66):

```python
        suggestions=[
            "Omit meta_mode to accept the compact default (doi+pmid). "
            "Pass meta_mode='full' for the verbatim citation text+url, "
            "or 'minimal' to drop the citation."
        ],
```

- [ ] **Step 3d: Sync the server instructions**

In `autopvs1_link/mcp/server_info.py`, change the final `SERVER_DESCRIPTION` paragraph (lines 32-34):

```python
    "response_mode in {ids_only, summary, standard, full}; meta_mode in "
    "{compact (default), full, minimal}. Start with summary for verdicts "
    "and widen on demand; request meta_mode=full for the verbatim "
    "recommended_citation text."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/mcp/test_tool_runtime.py -q -k default_meta_mode_is_compact`
Expected: PASS

Run: `uv run pytest tests/unit/mcp/test_server_info.py -q`
Expected: PASS — confirm `SERVER_DESCRIPTION` stays under the ~1900-byte ceiling. If the test fails on length, trim wording (e.g. drop "and widen on demand").

- [ ] **Step 5: Fix fallout across the suite**

Run: `uv run pytest tests/unit/mcp -q`
Tests that called tools without `meta_mode` and asserted the full 4-field citation now see `{doi, pmid}`. For each: either pass `meta_mode="full"` explicitly (when the test's intent is the full citation) or update the expectation to the compact 2-field shape (when the test exercises the default). Do not weaken assertions beyond what the new default requires. Re-run until green.

- [ ] **Step 6: Commit**

```bash
git add autopvs1_link/mcp/ tests/unit/mcp/
git commit -m "feat(mcp)!: default meta_mode=compact (BREAKING: full citation now opt-in)"
```

---

## Task 9: Version bump, CHANGELOG, docs, and full `ci-local`

**Files:**
- Modify: `autopvs1_link/__init__.py:3`, `pyproject.toml:3`
- Modify: `CHANGELOG.md`
- Modify: `docs/api.md`, `docs/mcp-tool-catalog.md` (if they document meta_mode default / response fields)
- Test: `tests/unit/mcp/test_capabilities_presenter.py` and any version-pinned test

- [ ] **Step 1: Bump the version**

In `autopvs1_link/__init__.py` line 3:

```python
__version__ = "1.2.0"
```

In `pyproject.toml` line 3:

```toml
version = "1.2.0"
```

- [ ] **Step 2: Update CHANGELOG**

Prepend a new section to `CHANGELOG.md` (match the file's existing heading style):

```markdown
## 1.2.0

### Changed (BREAKING)
- Default `meta_mode` is now `compact` (was `full`) on every MCP tool.
  Responses that omit `meta_mode` now carry `recommended_citation` as
  `{doi, pmid}` only. Request `meta_mode=full` for the verbatim citation
  `text` + `url`. Rationale: the full metadata block out-weighed the data
  payload by default; trimming follows Anthropic ("return only high-signal
  information") and Google ("trim ceremony, never trim grounding data").

### Added
- `pvs1_flowchart.path_gloss`: a deterministic one-line rationale (the
  traversed decision-tree branch + terminal strength) on every PVS1
  verdict in summary/standard/full modes — closes the bare-code
  groundedness gap without widening to standard.
- `meta.next_commands`: machine-executable `{tool, arguments, reason}`
  next steps on variant/cnv/search/bulk success envelopes and on
  `requires_disambiguation` errors.
- `meta.expected_cold_latency_ms`: per-response cold-call latency hint on
  cold scrape-tier envelopes.

### Documentation
- Cursor contract corrected: `next_cursor` is a base64url-encoded offset
  (not opaque, not authenticated), documented honestly.
```

- [ ] **Step 3: Update human docs (if present)**

Check and update meta-default + new-field mentions:

Run: `grep -rn "meta_mode" docs/ 2>/dev/null; grep -rn "recommended_citation" docs/ 2>/dev/null`
Update any doc stating the default is `full`, and add `path_gloss` / `next_commands` / `expected_cold_latency_ms` to the tool-catalog field lists. If `docs/` has no such mention, skip.

- [ ] **Step 4: Fix the capabilities version + any version-pinned tests**

Run: `uv run pytest tests/unit/mcp/test_capabilities_presenter.py -q`
The `capabilities_version()` hash moves because `SERVER_VERSION` changed. If a test pins the literal hash, recompute and update it:

```bash
uv run python -c "from autopvs1_link.mcp.registries import capabilities_version; print(capabilities_version())"
```

Update the expected `version` (`1.2.0`) and the expected `capabilities_version` value in the snapshot. Run any other test that pins `server_version`/`version` and update to `1.2.0`. Re-run until green.

- [ ] **Step 5: Full local CI**

Run: `make ci-local`
Expected: PASS — `format-check`, `lint-ci`, `lint-loc` (all modules < 600), `typecheck-fast`, `test-fast` (coverage ≥ 80).
Fix any failures (formatting via `make format`; lint via `make lint-fix`; types per mypy output). Re-run until fully green.

- [ ] **Step 6: Commit**

```bash
git add autopvs1_link/__init__.py pyproject.toml CHANGELOG.md docs/ tests/
git commit -m "chore(release): bump to 1.2.0 — groundedness & token-efficiency polish"
```

---

## Self-Review (completed during plan authoring)

**Spec coverage:** P0 path_gloss → Tasks 1–2. P1a compact default → Task 8 (+ version Task 9). P1b next_commands → Tasks 3–5. P2a cursor → Task 7. P2b cold-latency → Task 6. Cross-cutting (capabilities docs, null-strip, version hash, citation contract sync, CHANGELOG) → folded into the relevant tasks + Task 9. All five spec success criteria map to tasks.

**Placeholder scan:** No "TBD/TODO/handle edge cases". Two intentional executor-judgement steps remain — updating *pre-existing* snapshot/key-equality assertions (Task 2 Step 5, Task 4 Step 5, Task 8 Step 5, Task 9 Step 4) — because those assert against current files the executor must read; each step states exactly what value to change and forbids weakening assertions.

**Type consistency:** `synthesize_path_gloss(steps, *, final_strength, preliminary_decision_path)` keyword-only signature matches its call in Task 2. `widen_response_mode`/`search_next_page`/`bulk_retry_failed`/`error_next_commands` signatures match their Task 4/5 call sites. `ok_envelope(..., next_commands=...)` and `MCPMeta.next_commands`/`expected_cold_latency_ms` are consistent across Tasks 4 and 6. `_candidate_rows(results, build)` updated at both call sites. `cold_latency_ms_for` used in `ok_envelope` after its cost_tiers import is extended.

**Ordering safety:** Additive tasks (1–7) land before the breaking default flip (8) and version bump (9), so each task's suite stays green on its own. The null-strip list gains both new keys in Task 4 so Task 6 needs no envelope re-touch.
