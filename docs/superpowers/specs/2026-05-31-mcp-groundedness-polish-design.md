# AutoPVS1-Link MCP Groundedness & Token-Efficiency Polish

Date: 2026-05-31
Status: Approved (design)
Target: lift the MCP surface from a measured ~8.4/10 to ~9.5/10 for LLM consumers
Supersedes/extends: `2026-05-26-mcp-llm-polish-design.md`, `2026-05-25-mcp-llm-ergonomics-design.md`

## 1. Context & Goal

An expert LLM consumer exercised all seven tools across 14 calls (happy-path,
error, auto-resolve, pagination, bulk aggregation, cache hit/miss/mixed) and
filed a detailed report scoring the server ~8.4/10. Discovery, schema clarity,
per-item bulk envelopes, cache observability, defensive scraping, and health
are already top-tier. The gap to 9.5 is concentrated in five findings. This
spec turns those findings into a backward-compatible (versioned) implementation
grounded in primary Anthropic and Google guidance.

Non-goal: this is not a re-architecture. The envelope already separates `data`
from a `meta` sub-object and exposes `response_mode`/`meta_mode` tiers — the
work is to fix defaults and close the groundedness gap, not to rebuild.

## 2. Findings → decisions

| # | Finding (reviewer) | Severity | Decision |
|---|---|---|---|
| P0 | Verdict returns bare codes (`NF5`, `DUP3`) with `decision_tree: []` in summary mode → forces the model to invent the rationale | Highest | Add `path_gloss`, **synthesized deterministically** from the parsed decision-tree branch text (no hand-authored code table) |
| P1a | Default meta block (`meta_mode=full`) outweighs the data payload | High | Flip global default to `meta_mode=compact`; minor version bump + CHANGELOG breaking-default note |
| P1b | Recovery / next-step hints are prose strings, not machine-executable | High | Add additive `meta.next_commands: [{tool, arguments, reason}]` on success and error |
| P2a | `next_cursor` documented "opaque" but base64-decodes to plaintext `{offset:N}` | Medium | Relabel honestly (doc/string only); no HMAC |
| P2b | Cold search (~5 s) sets no per-response latency expectation | Medium | Add additive `meta.expected_cold_latency_ms`, sourced from the existing performance block, cold-calls only |

## 3. Guideline grounding (primary sources, verbatim-verified)

- **Gloss the codes — endorsed by both.** Anthropic: resolving cryptic
  identifiers to "semantically meaningful and interpretable language…
  significantly improves Claude's precision… by reducing hallucinations"
  (`anthropic.com/engineering/writing-tools-for-agents`). Google ADK: "instead
  of returning a numeric error code, return a dictionary with… a human-readable
  explanation. Remember that the LLM, not a piece of code, needs to understand
  the result" (`adk.dev/tools-custom/function-tools/`).
  **Critical nuance:** keep the *code too* — Anthropic notes agents need the raw
  code "to trigger downstream tool calls." Return code **and** gloss.
- **Trim default meta — endorsed.** Anthropic: "return only high signal
  information… eschew low-level technical identifiers." Google: "trim ceremony,
  never trim grounding data." Caution (Anthropic + our own MEMORY note):
  changing a default can break schema-validating clients — relocate/keep schema
  stable and gate behind a version bump; validate output after compaction.
- **Machine-executable next steps — idiomatic, not a standard.** Neither vendor
  defines a wire-level `next_commands`. Anthropic favors enriching responses to
  cut model guesswork; Google ships named in-process actions (`escalate`,
  `transfer_to_agent`) and a `pending` status pointing to a structured next
  step. Our `next_commands` is a reasonable, additive realization (the sibling
  `gnomad-link` server already does this).
- **Error recovery — keep the prose.** The directly-cited requirement on both
  sides is *human-readable, example-bearing* error text. Machine-executable
  recovery is an addition, never a replacement. `error.suggestions[]` stays.
- **Cursor honesty.** Engineering judgment: the cursor encodes a public-search
  offset; forging it only changes which public page is returned — no security
  boundary exists, so HMAC is unjustified complexity. Relabel honestly.

## 4. Design

Data spine (every PVS1 verdict):

```
HTML
 -> api/autopvs1_parsers.py        parse_pvs1_flowchart -> PVS1Flowchart
 -> models/autopvs1_models.py      PVS1Flowchart / FlowchartStep (raw)
 -> mcp/presenters/variant.py      _present_flowchart (mode-shaping, terminal_note)
 -> mcp/contracts.py               PVS1FlowchartMCP (typed wire contract)
 -> mcp/envelope.py                ok_envelope / error_envelope -> MCPMeta
 -> mcp/tools/*.py                 call sites
```

LOC discipline: `.loc-allowlist` is **empty** → every module is held to the
plain 600-line cap. `bulk_tools.py` is at **550/600** (50 left), so shared
logic goes in new helper modules, never inline in bulk. `capabilities.py`
(491) and `contracts.py` (473) have headroom but must be edited tersely.

### P0 — `path_gloss` (deterministic synthesis)

**Why deterministic, not a curated table.** There is no upstream `autopvs1`
Python dependency (pure HTML scraper). The scraped HTML exposes the path only
as a bare code in the `<figcaption>` plus the *traversed branch* as node text
(`Nonsense or Frameshift -> Not predict to undergo NMD -> ... -> Strong`). The
`NF/SS/IC/DEL/DUP` numberings cannot be verified from anything in the repo, so
a hand-authored code→meaning table would ship guessed clinical claims. The
branch text, by contrast, is already parsed, variant-accurate, and
fixture-grounded. `path_gloss` is therefore a one-line **compression of data we
already have**, matching the reviewer's own example format.

- New module `autopvs1_link/mcp/pvs1_glossary.py`:
  - `synthesize_path_gloss(steps, final_strength) -> str | None` — joins the
    meaningful decision-tree step descriptions (deduped, trimmed to the
    salient nodes) and appends `-> {strength}`. Returns `None` only when no
    code and no steps exist.
  - Empty-tree fallback: `"Decision path {preliminary_decision_path} -> {strength}"`
    (restates identifiers only — no invented meaning).
  - Pure function, no I/O; standalone so its content can feed
    `capabilities_version()` if advertised.
- Contract: add `path_gloss: str | None = None` to `PVS1FlowchartMCP`
  (`contracts.py` ~line 118, beside `terminal_note`). Optional → schema marks
  it non-required → safe under the null-strip pass.
- Presenter: in `_present_flowchart` (`presenters/variant.py` ~88–160),
  synthesis runs **once** and `path_gloss` is attached to the presented
  flowchart object in **all flowchart-bearing modes** (summary, standard,
  full); omitted in ids_only. It is the *sole* rationale in summary mode (where
  the tree is stripped at ~133–153) and a convenience one-liner in
  standard/full (where the full tree is also present). It is attached for
  **every** path, unconditionally — this resolves the `terminal_note`
  inconsistency: `terminal_note` is deliberately gated to
  `_AMBIGUOUS_VERDICT_STRENGTHS` (lines 52–60, 145–152), so Strong/Very-Strong
  paths come back bare today; `path_gloss` has no such gate. `terminal_note`
  semantics are left unchanged.
- **No parser change → no new HTML fixture required** (AGENTS.md). Tests build
  Pydantic models in-test, the dominant existing pattern.
- Backward-compat: additive optional field. Existing summary-mode key-equality
  tests (`test_variant_presenter.py` ~794–893) will see a new key → update
  those assertions (expected under TDD).

### P1a — global default `meta_mode=compact`

- Flip the `"full"` default at every site: `envelope.py:303` (`ok_envelope`),
  `envelope.py:375` (`error_envelope`); tool params `variant_tool.py:94`,
  `cnv_tool.py` (META_MODE param), `search_tool.py:110`, `bulk_tools.py:243` &
  `:430`; tool-local fallbacks `variant_tool.py:120`, `search_tool.py:120`,
  `bulk_tools.py:303` & `:470`; and the suggestion string in
  `mode_validation.py:66`.
- `compact` keeps `{doi, pmid}` (sufficient to cite). The verbatim citation
  `text` + `url` become opt-in via `meta_mode=full`. `minimal` (drops citation
  entirely) is **never** the default — it would violate the research-use
  citation contract.
- Versioning: bump `1.1.0 -> 1.2.0` in `pyproject.toml`; add a CHANGELOG entry
  with a prominent breaking-default note. The data `output_schema` is
  unchanged; only `meta` content shrinks, and `compact` already validates
  against `MCPMeta` (all fields optional), so this is a content change, not a
  schema break → minor bump is correct.
- Contract sync: update the citation-contract wording in `server_info.py`
  instructions and `docs/` to state the default is `compact` (doi+pmid) and
  that `meta_mode=full` yields the verbatim `recommended_citation`. Keep
  `server_info.py` `SERVER_DESCRIPTION` under its ~1900-byte test ceiling.
- Defensive test (honoring the MEMORY null-strip lesson): assert that a
  **default-mode** tool response validates against the published
  `output_schema`.

### P1b — machine-executable `next_commands`

- `MCPMeta` (`envelope.py` ~104–170): add
  `next_commands: list[dict[str, Any]] | None = None` beside `next_actions`.
- Thread an optional `next_commands` param through `ok_envelope`
  (`envelope.py` 299–364; meta built 347–357) and `error_envelope`
  (367–441; meta 424–430). Register `"next_commands"` in
  `_strip_none_telemetry_fields` (223–248) so it is absent-by-default.
- New helper module `autopvs1_link/mcp/next_commands.py` (keeps `bulk_tools.py`
  under cap) building `{tool, arguments, reason}` entries.
- Per-surface attach (success + error, mirroring `gnomad-link`):
  - variant (`variant_tool.py` ~139–144): widen-to-`standard` re-call.
  - cnv (`cnv_tool.py` ok_envelope): widen-to-`standard` re-call.
  - search (`search_tool.py` ~141–146): next-page `{cursor}` when
    `data.pagination.next_cursor` exists.
  - bulk (`bulk_tools.py` ~381–387 variants, ~544–550 cnvs): retry-failed-items
    derived from `results[*].input` + `results[*].error.code`.
  - `requires_disambiguation` error: include the disambiguation re-call
    (Google's "pending → structured next step").
- Shape (documented): `{"tool": str, "arguments": object, "reason": str}`.
- Backward-compat: additive optional meta field; null-strip keeps unset
  payloads byte-identical. The published `MCPMeta` JSON schema gains an optional
  field (safe). `test_envelope.py` absence-assertions get the new key added to
  their strip expectations.

### P2a — honest cursor (doc/string only)

- No logic change to `_encode_cursor`/`_decode_cursor` (`validation.py`
  238–269). Replace the "opaque; callers must not parse or construct" language
  with "base64url-encoded `{offset:N}`; treat as opaque — it is **not
  authenticated**" in: `contracts.py:244–261` (`SearchPaginationMCP`),
  `search_tool.py:82` & `:116`, and the cursor mention in `capabilities.py`.
- Backward-compat: existing cursors keep working; only doc strings change.

### P2b — cold-latency hint

- `MCPMeta`: add `expected_cold_latency_ms: int | None = None`.
- Source it inside `_cost_hints_for(tool_name, cache_status)` (`envelope.py`
  256–274) from the per-tool `_PERFORMANCE_BLOCK` `cold_call_seconds`
  (`capabilities.py` ~176–181), emitted only when `cache_status` is cold
  (`miss`/`coalesced`). Consistent-by-construction with the perf block →
  preserves the `test_cost_tiers.py:54` lockstep. Register in the null-strip
  list. Applies to all scrape-tier tools (warm calls omit it).

## 5. Cross-cutting

- **Capabilities + version hash.** Document the four new surface elements
  (`path_gloss`, `next_commands`, compact default, `expected_cold_latency_ms`)
  in `capabilities.py` so `capabilities_version()` (`registries.py` 167–214)
  moves and clients re-read. Update the exact-snapshot tests in
  `test_capabilities_presenter.py` that this breaks.
- **Null-strip registration** is mandatory for every new optional meta field
  (`envelope.py` `_strip_none_telemetry_fields`) — forgetting it ships `null`
  on the wire and breaks the "absence = no signal" contract.
- **Drift test** (`test_registries.py`): no new error/warning codes are
  introduced, so it stays green; verify.

## 6. Test plan (TDD, three layers)

1. `tests/unit/mcp/test_pvs1_glossary.py` (new): known branch → exact gloss;
   empty tree → identifier-only fallback; no steps & no code → `None`. Drift
   guard: every label in `PVS1_STRENGTH_LABELS` + the two sentinels produces a
   non-empty trailing strength.
2. `test_variant_presenter.py`: `path_gloss` present for summary/standard,
   absent for ids_only; Strong path (previously bare) now carries it; update
   existing key-equality assertions.
3. `test_tool_runtime.py`: `structured_content["data"]["pvs1_flowchart"]["path_gloss"]`
   present; default response validates against `output_schema`; `next_commands`
   present and well-formed on a success call.
4. `test_envelope.py` / `test_cost_tiers.py`: default `meta_mode=compact`
   content; `next_commands` + `expected_cold_latency_ms` absence-by-default and
   cold-only presence; perf-block lockstep.
5. `test_bulk_tools.py`: per-item retry `next_commands` on a mixed
   success/error batch.
6. `test_capabilities_presenter.py`: updated snapshots + version-hash movement.
7. `make ci-local` (ruff, mypy py3.12, `lint-loc` 600-cap, tests, coverage
   `fail_under=80`).

## 7. Out of scope / deferred (documented, not done)

- **Protocol-level `_meta` relocation** of ceremony fields (Anthropic's
  strongest recommendation). Deferred: the compact default already fixes the
  token complaint and our `meta` is already a separate sub-object. A full
  relocation touches every tool's output schema and is more breaking — it earns
  its own spec and version.
- **HMAC-signed cursor.** Rejected for this surface: no security boundary on a
  public read-only offset; adds key management, breaks in-flight cursors, makes
  them host-specific, for no benefit.
- **Hand-authored code→meaning table** for `NF/SS/IC/DEL/DUP`. Rejected:
  numberings unverifiable; deterministic branch synthesis is strictly safer for
  clinical-adjacent data.

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Default-meta flip breaks a client parsing full citation by default | Version bump + CHANGELOG; `compact` keeps doi+pmid; full text via `meta_mode=full`; output-schema validation test |
| New optional field ships `null` (MEMORY null-strip class bug) | Register every new field in the null-strip helpers; add absence-by-default tests |
| Snapshot tests (`capabilities`, `variant_presenter`, `envelope`) break | Expected under TDD; update assertions deliberately, not by loosening them |
| `bulk_tools.py` breaches 600-cap | All shared logic in `pvs1_glossary.py` / `next_commands.py`; no inline growth |
| Gloss reads as clinical guidance | Deterministic compression of scraped branch text only; research-use framing preserved; no invented mappings |

## 9. Success criteria

- Every PVS1 verdict (including Strong/Very-Strong) carries a one-line
  `path_gloss` in summary mode, derived only from parsed branch text.
- Default responses are compact-meta; verbatim citation available on demand;
  default output validates against `output_schema`.
- `next_commands` present (success + error) on variant, cnv, search, bulk, and
  `requires_disambiguation`, each a ready-to-call `{tool, arguments, reason}`.
- Cursor docs are honest; cold scrape responses carry a latency expectation.
- Version `1.2.0`, CHANGELOG updated, `make ci-local` green, coverage ≥ 80.
