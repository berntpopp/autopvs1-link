# MCP LLM Ergonomics Implementation Plan

> Historical record

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the AutoPVS1-Link MCP surface reliable for LLM agents by returning stable envelope-shaped structured content, cleaner validation errors, fixture-backed parser fixes, richer MCP-only presentation data, stable cache resources, and updated documentation.

**Architecture:** Keep REST routes, service methods, scraper URL construction, and MCP tool names stable. Fix incorrect parsed facts in the parser/model layer, then add focused MCP envelope, validation, and presenter modules that shape service results into LLM-oriented MCP responses without turning AutoPVS1 output into clinical decision support.

**Tech Stack:** Python 3.12, `uv`, Makefile targets, pytest, pytest-asyncio, Pydantic v2, FastMCP 3, MCP Python SDK, BeautifulSoup/lxml, httpx, Ruff, mypy.

---

## Current Repo Facts

- `autopvs1_link/api/autopvs1_client.py` fetches AutoPVS1 HTML and delegates parsing to `autopvs1_link/api/autopvs1_parsers.py`.
- `autopvs1_link/models/autopvs1_models.py` defines the shared REST/service Pydantic models. New fields here must be optional or excluded from serialization when they are internal parser metadata.
- `autopvs1_link/mcp/facade.py` builds the FastMCP server and registers metadata, tools, and resources.
- Current MCP tool wrappers live in `autopvs1_link/mcp/tools/variant_tool.py`, `cnv_tool.py`, `search_tool.py`, and `cache_tools.py`.
- Current MCP discovery and capabilities live in `autopvs1_link/mcp/metadata.py`.
- Current MCP resources live in `autopvs1_link/mcp/resources.py`.
- Current service adapters live in `autopvs1_link/mcp/service_adapters.py`; keep them thin.
- FastMCP `mcp.call_tool(...)` currently returns a `ToolResult` whose `structured_content` contains the dict returned by the tool, and whose text content contains the same dict serialized as JSON.
- The required final check before claiming completion is `make ci-local`.
- Do not shorten the upstream AutoPVS1 rate-limit delay. Fixture acquisition in Task 1 sleeps at least 1.0 second between upstream requests.
- Keep all new Python modules under 600 lines. Current modules are below the hard cap, and there is no `.loc-allowlist`.

## Parser vs MCP Presenter Boundary

Parser-level tasks must own facts extracted from upstream HTML and may affect REST and MCP outputs:

- `final_strength` extraction for `VeryStrong`, reduced-weight labels, and inferred terminal strengths.
- `final_strength_inferred` metadata on `PVS1Flowchart`.
- Decision-tree whitespace cleanup and `note_id` extraction.
- ClinVar `/variation/na` sentinel links removed from serialized REST `external_links`.

MCP presenter-only tasks must own agent-facing contract shape and enrichments:

- Envelope, metadata, request IDs, warnings, citation, and suggestions.
- Inline `note_text` on MCP decision-tree steps.
- MCP `external_links` values that may be `null` when a known invalid upstream link was observed.
- `pli_score_display`.
- Search pagination, no-result guidance, compact capabilities, and cache-resource shaping.

## File Structure

- Create `tests/unit/test_fixture_inventory.py` to enforce the two required real upstream `VeryStrong` HTML fixtures and capture metadata.
- Create `tests/fixtures/variant_hg19_BRCA1_17-41276045-ACT-A.html` from `https://autopvs1.bgi.com/variant/hg19/17-41276045-ACT-A`.
- Create `tests/fixtures/cnv_hg19_MYO15A_17-15000000-20000000-DEL.html` from `https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL`.
- Modify `autopvs1_link/models/autopvs1_models.py` for optional parser metadata fields.
- Modify `autopvs1_link/api/autopvs1_parsers.py` for parser-level fact fixes.
- Create `autopvs1_link/mcp/envelope.py` for envelope, metadata, citation, warning, and error response helpers.
- Modify `autopvs1_link/mcp/errors.py` for validation/runtime error objects that can be converted into envelopes.
- Modify `autopvs1_link/mcp/contracts.py` for envelope data models and cache-resource models; replace the stale flat `CacheStatistics` contract.
- Create `autopvs1_link/mcp/validation.py` for MCP-only input normalization and validation.
- Create `autopvs1_link/mcp/presenters/__init__.py`.
- Create `autopvs1_link/mcp/presenters/variant.py` for variant/CNV MCP data shaping.
- Create `autopvs1_link/mcp/presenters/search.py` for search pagination and guidance.
- Create `autopvs1_link/mcp/presenters/cache.py` for stable cache-stat resource shaping.
- Create `autopvs1_link/mcp/presenters/capabilities.py` for compact tool discovery and detailed capabilities resource data.
- Create `autopvs1_link/mcp/server_info.py` for shared MCP server name, version, and description constants.
- Modify `autopvs1_link/mcp/tools/variant_tool.py`, `cnv_tool.py`, `search_tool.py`, and `cache_tools.py` to return standard envelopes and advertise envelope output schemas.
- Modify `autopvs1_link/mcp/metadata.py` so `get_server_capabilities` returns an envelope and `autopvs1-link://capabilities` returns the detailed resource payload.
- Modify `autopvs1_link/mcp/resources.py` so `autopvs1-link://cache/statistics` returns stable method-keyed resource data.
- Modify `autopvs1_link/utils/cache_manager.py` only for counter semantics needed by the cache-stat tests.
- Modify `scripts/generate_mcp_tool_catalog.py` so generated docs show input schemas, output schemas, and resources.
- Modify `docs/mcp-tool-catalog.md` by running `uv run python scripts/generate_mcp_tool_catalog.py`.
- Modify `docs/api.md` and `README.md` MCP sections.
- Create `docs/mcp-evaluation-checklist.md`.
- Add focused tests under `tests/unit/` and `tests/unit/mcp/`; do not create another test root.

## Task 1: Acquire Required VeryStrong HTML Fixtures

**Files:**
- Create: `tests/unit/test_fixture_inventory.py`
- Create: `tests/fixtures/variant_hg19_BRCA1_17-41276045-ACT-A.html`
- Create: `tests/fixtures/cnv_hg19_MYO15A_17-15000000-20000000-DEL.html`

- [ ] **Step 1: Write the failing fixture inventory test**

Create `tests/unit/test_fixture_inventory.py`:

```python
"""Inventory checks for real upstream HTML fixtures required by parser tests."""

from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

REQUIRED_VERYSTRONG_FIXTURES = {
    "variant_hg19_BRCA1_17-41276045-ACT-A.html": {
        "url": "https://autopvs1.bgi.com/variant/hg19/17-41276045-ACT-A",
        "genome_build": "hg19",
        "kind": "variant",
        "id": "17-41276045-ACT-A",
    },
    "cnv_hg19_MYO15A_17-15000000-20000000-DEL.html": {
        "url": "https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
        "genome_build": "hg19",
        "kind": "cnv",
        "id": "17-15000000-20000000-DEL",
    },
}


def test_required_verystrong_fixtures_are_real_upstream_captures() -> None:
    for filename, metadata in REQUIRED_VERYSTRONG_FIXTURES.items():
        path = FIXTURE_DIR / filename
        assert path.exists(), f"Missing required fixture: {filename}"
        text = path.read_text(encoding="utf-8")
        assert f"Captured from {metadata['url']}" in text
        assert f"genome_build={metadata['genome_build']}" in text
        assert f"{metadata['kind']}_id={metadata['id']}" in text
        assert "<code>VeryStrong</code>" in text
```

- [ ] **Step 2: Run the fixture inventory test to verify it fails**

Run:

```bash
uv run pytest tests/unit/test_fixture_inventory.py -q
```

Expected: FAIL because both fixture files are missing.

- [ ] **Step 3: Acquire the real upstream fixtures with capture metadata**

Run this exact command from the repository root. It requests the BRCA1 fixture, waits 1.0 second, then requests the MYO15A CNV fixture.

```bash
uv run python - <<'PY'
from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

FIXTURE_DIR = Path("tests/fixtures")
CAPTURES = [
    {
        "url": "https://autopvs1.bgi.com/variant/hg19/17-41276045-ACT-A",
        "path": FIXTURE_DIR / "variant_hg19_BRCA1_17-41276045-ACT-A.html",
        "kind": "variant",
        "id": "17-41276045-ACT-A",
        "genome_build": "hg19",
    },
    {
        "url": "https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
        "path": FIXTURE_DIR / "cnv_hg19_MYO15A_17-15000000-20000000-DEL.html",
        "kind": "cnv",
        "id": "17-15000000-20000000-DEL",
        "genome_build": "hg19",
    },
]

captured_on = datetime.now(UTC).date().isoformat()
with httpx.Client(
    timeout=30.0,
    follow_redirects=True,
    headers={"User-Agent": "AutoPVS1-Link fixture capture"},
) as client:
    for index, capture in enumerate(CAPTURES):
        if index:
            time.sleep(1.0)
        response = client.get(capture["url"])
        response.raise_for_status()
        html = response.text
        if "<code>VeryStrong</code>" not in html:
            raise SystemExit(f"{capture['url']} did not contain a terminal VeryStrong code")
        metadata = (
            f"<!-- Captured from {capture['url']} on {captured_on}; "
            f"genome_build={capture['genome_build']}; "
            f"{capture['kind']}_id={capture['id']} -->\n"
        )
        capture["path"].write_text(metadata + html, encoding="utf-8")
        print(f"Wrote {capture['path']}")
PY
```

Expected:

```text
Wrote tests/fixtures/variant_hg19_BRCA1_17-41276045-ACT-A.html
Wrote tests/fixtures/cnv_hg19_MYO15A_17-15000000-20000000-DEL.html
```

- [ ] **Step 4: Run the fixture inventory test to verify it passes**

Run:

```bash
uv run pytest tests/unit/test_fixture_inventory.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_fixture_inventory.py tests/fixtures/variant_hg19_BRCA1_17-41276045-ACT-A.html tests/fixtures/cnv_hg19_MYO15A_17-15000000-20000000-DEL.html
git commit -m "test: add verystrong autopvs1 fixtures"
```

## Task 2: Fix Parser Final Strength Extraction and Inference Metadata

**Files:**
- Modify: `autopvs1_link/models/autopvs1_models.py`
- Modify: `autopvs1_link/api/autopvs1_parsers.py`
- Modify: `tests/unit/test_real_website_parsing.py`

- [ ] **Step 1: Write failing parser tests for `VeryStrong` and inference metadata**

In `tests/unit/test_real_website_parsing.py`, add these tests to `TestRealWebsiteParsing`:

```python
    @pytest.mark.asyncio
    async def test_parse_brca1_variant_with_verystrong_strength(self):
        """Parse BRCA1 upstream fixture with a terminal VeryStrong PVS1 node."""
        html_content = load_fixture("variant_hg19_BRCA1_17-41276045-ACT-A.html")
        mock_response = MagicMock()
        mock_response.text = html_content
        client = AutoPVS1Client()

        try:
            with patch("httpx.AsyncClient.get", return_value=mock_response):
                result = await client.get_variant_data("hg19", "17-41276045-ACT-A")
        finally:
            await client.close()

        assert result.genome_build == "hg19"
        assert result.variant_info.variant_id == "17-41276045-ACT-A"
        assert result.pvs1_flowchart.final_strength == "VeryStrong"
        assert result.pvs1_flowchart.final_strength_inferred is True
        assert "VeryStrong" in [step.code for step in result.pvs1_flowchart.decision_tree]

    @pytest.mark.asyncio
    async def test_parse_myo15a_cnv_with_verystrong_strength(self):
        """Parse MYO15A upstream CNV fixture with a terminal VeryStrong PVS1 node."""
        html_content = load_fixture("cnv_hg19_MYO15A_17-15000000-20000000-DEL.html")
        mock_response = MagicMock()
        mock_response.text = html_content
        client = AutoPVS1Client()

        try:
            with patch("httpx.AsyncClient.get", return_value=mock_response):
                result = await client.get_cnv_data("hg19", "17-15000000-20000000-DEL")
        finally:
            await client.close()

        assert result.genome_build == "hg19"
        assert result.cnv_info.cnv_id == "17-15000000-20000000-DEL"
        assert result.pvs1_flowchart.final_strength == "VeryStrong"
        assert result.pvs1_flowchart.final_strength_inferred is True
        assert "VeryStrong" in [step.code for step in result.pvs1_flowchart.decision_tree]
```

Extend `test_final_strength_extraction_comprehensive` in the same file so `test_cases` is:

```python
        test_cases = [
            ("VeryStrong", "VeryStrong"),
            ("Strong", "Strong"),
            ("Moderate", "Moderate"),
            ("Supporting", "Supporting"),
            ("Not applicable", "Not applicable"),
            ("Unmet", "Unmet"),
            ("Strong_RWS", "Strong_RWS"),
            ("Moderate_RWS", "Moderate_RWS"),
            ("Supporting_RWS", "Supporting_RWS"),
        ]
```

Add this assertion after `flowchart.final_strength == expected` inside the loop:

```python
                assert flowchart.final_strength_inferred is True
```

- [ ] **Step 2: Run the parser tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/test_real_website_parsing.py::TestRealWebsiteParsing::test_parse_brca1_variant_with_verystrong_strength tests/unit/test_real_website_parsing.py::TestRealWebsiteParsing::test_parse_myo15a_cnv_with_verystrong_strength tests/unit/test_real_website_parsing.py::TestRealWebsiteParsing::test_final_strength_extraction_comprehensive -q
```

Expected: FAIL because `PVS1Flowchart` has no `final_strength_inferred` field and `VeryStrong`/reduced-weight labels are not recognized by the parser.

- [ ] **Step 3: Add parser support for the complete strength vocabulary and inference metadata**

In `autopvs1_link/models/autopvs1_models.py`, change `PVS1Flowchart` to:

```python
class PVS1Flowchart(BaseModel):
    """PVS1 flowchart decision path and outcome."""

    preliminary_decision_path: str
    final_strength: str
    final_strength_inferred: bool = False
    decision_tree: list[FlowchartStep] = Field(default_factory=list)
    notes: dict[str, str] = Field(default_factory=dict)
```

In `autopvs1_link/api/autopvs1_parsers.py`, add this module-level vocabulary near `logger`:

```python
PVS1_STRENGTH_LABELS = {
    "VeryStrong",
    "Strong",
    "Moderate",
    "Supporting",
    "Not applicable",
    "Unmet",
    "Strong_RWS",
    "Moderate_RWS",
    "Supporting_RWS",
}
```

Replace the final-strength extraction block in `parse_pvs1_flowchart` with:

```python
    final_strength = ""
    final_strength_inferred = False
    flowchart_codes = flowchart_col.select("ul.tree code")

    explicit_strength = _extract_explicit_final_strength(flowchart_col)
    if explicit_strength:
        final_strength = explicit_strength
    else:
        final_strength = _infer_terminal_strength(flowchart_codes)
        final_strength_inferred = bool(final_strength)
```

Add these helper functions below `_href`:

```python
def _collapse_html_text(tag: Tag) -> str:
    """Return visible text with HTML layout whitespace collapsed."""
    return re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()


def _extract_explicit_final_strength(flowchart_col: Tag) -> str:
    """Extract an explicit final-strength label if the HTML exposes one."""
    final_strength_pattern = re.compile(r"Final\s+Strength\s*:\s*(.+)", re.IGNORECASE)
    for text_node in flowchart_col.find_all(string=final_strength_pattern):
        match = final_strength_pattern.search(str(text_node))
        if match:
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if candidate in PVS1_STRENGTH_LABELS:
                return candidate
    return ""


def _infer_terminal_strength(flowchart_codes: list[Tag]) -> str:
    """Infer final strength from the last recognized terminal decision-tree code."""
    for code in reversed(flowchart_codes):
        text = _collapse_html_text(code)
        if text in PVS1_STRENGTH_LABELS:
            logger.debug("Found final strength", strength=text, method="terminal_code")
            return text
    return ""
```

When returning `PVS1Flowchart`, include the new field:

```python
    return PVS1Flowchart(
        preliminary_decision_path=preliminary_path,
        final_strength=final_strength,
        final_strength_inferred=final_strength_inferred,
        decision_tree=decision_tree,
        notes=notes,
    )
```

- [ ] **Step 4: Run the parser tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/test_real_website_parsing.py::TestRealWebsiteParsing::test_parse_brca1_variant_with_verystrong_strength tests/unit/test_real_website_parsing.py::TestRealWebsiteParsing::test_parse_myo15a_cnv_with_verystrong_strength tests/unit/test_real_website_parsing.py::TestRealWebsiteParsing::test_final_strength_extraction_comprehensive -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/models/autopvs1_models.py autopvs1_link/api/autopvs1_parsers.py tests/unit/test_real_website_parsing.py
git commit -m "fix: parse verystrong pvs1 strengths"
```

## Task 3: Fix Parser Decision-Tree Cleanup and ClinVar Sentinel Handling

**Files:**
- Modify: `autopvs1_link/models/autopvs1_models.py`
- Modify: `autopvs1_link/api/autopvs1_parsers.py`
- Modify: `tests/unit/test_scraper_parsers.py`

- [ ] **Step 1: Write failing parser tests for clean decision steps and invalid ClinVar links**

In `tests/unit/test_scraper_parsers.py`, change `test_parse_variant_info_external_links` to:

```python
    def test_parse_variant_info_external_links(self, client, variant_soup):
        """Test parsing external links without serializing invalid ClinVar sentinels."""
        variant_info = client._parse_variant_info(variant_soup, "X-83508928-A-T")

        assert "OMIM" in variant_info.external_links
        assert "ClinVar" not in variant_info.external_links
        assert "gnomAD" in variant_info.external_links
        assert variant_info.invalid_external_links == {
            "ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na"
        }
        assert "invalid_external_links" not in variant_info.model_dump(mode="json")
        assert (
            variant_info.external_links["gnomAD"]
            == "https://gnomad.broadinstitute.org/variant/X-83508928-A-T"
        )
```

Add this test to `TestPVS1FlowchartParsing`:

```python
    def test_parse_pvs1_flowchart_cleans_steps_and_extracts_note_ids(self, client, variant_soup):
        """Decision-tree codes should be compact, ordered, and carry note IDs separately."""
        flowchart = client._parse_pvs1_flowchart(variant_soup)

        role_step = next(
            step for step in flowchart.decision_tree if step.code.startswith("Role of region")
        )
        lof_step = next(
            step for step in flowchart.decision_tree if step.code.startswith("LoF variants")
        )

        assert role_step.code == "Role of region in protein function is unknown"
        assert role_step.note_id == "#1"
        assert lof_step.code == (
            "LoF variants in this exon are not frequent in the general population "
            "and exon is present in biologically-relevant transcripts"
        )
        assert lof_step.note_id == "#2"
        assert "<br>" not in role_step.code
        assert "\n" not in lof_step.code
        assert "#1" not in role_step.code
        assert "#2" not in lof_step.code
```

- [ ] **Step 2: Run the focused parser tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/test_scraper_parsers.py::TestVariantInfoParsing::test_parse_variant_info_external_links tests/unit/test_scraper_parsers.py::TestPVS1FlowchartParsing::test_parse_pvs1_flowchart_cleans_steps_and_extracts_note_ids -q
```

Expected: FAIL because `invalid_external_links` does not exist, ClinVar `/variation/na` is still serialized, and decision-tree note markers remain embedded in `code`.

- [ ] **Step 3: Implement parser cleanup and internal invalid-link metadata**

In `autopvs1_link/models/autopvs1_models.py`, add the excluded internal field to `VariantInfo`:

```python
    invalid_external_links: dict[str, str] = Field(default_factory=dict, exclude=True)
```

In `autopvs1_link/api/autopvs1_parsers.py`, add these helpers below `_infer_terminal_strength`:

```python
def _is_invalid_clinvar_sentinel(label: str, url: str) -> bool:
    """Return true for AutoPVS1 ClinVar sentinel URLs that are not citations."""
    return label == "ClinVar" and url.rstrip("/").endswith("/variation/na")


def _extract_note_id(code: Tag) -> str | None:
    """Extract the first red note marker from a decision-tree code element."""
    note_tag = code.find("b", style=re.compile(r"color:#CD5C5C"))
    if not isinstance(note_tag, Tag):
        return None
    note_text = note_tag.get_text(" ", strip=True)
    return note_text if re.fullmatch(r"#\d+", note_text) else None


def _flowchart_step_from_code(code: Tag) -> FlowchartStep | None:
    """Build a clean decision-tree step from one upstream code element."""
    code_copy = BeautifulSoup(str(code), "lxml").find("code")
    if not isinstance(code_copy, Tag):
        return None
    note_id = _extract_note_id(code_copy)
    for note_tag in code_copy.find_all("b", style=re.compile(r"color:#CD5C5C")):
        note_tag.decompose()
    code_text = _collapse_html_text(code_copy)
    if not code_text:
        return None
    return FlowchartStep(code=code_text, note_id=note_id)
```

In `parse_variant_info`, change external link parsing to collect invalid links separately:

```python
    external_links: dict[str, str] = {}
    invalid_external_links: dict[str, str] = {}
    for link in info_col.find_all("a", class_="btn"):
        link_text = link.text.strip()
        link_url = _href(link if isinstance(link, Tag) else None)
        if not link_text or not link_url:
            continue
        if _is_invalid_clinvar_sentinel(link_text, link_url):
            invalid_external_links[link_text] = link_url
            continue
        external_links[link_text] = link_url
```

In the `VariantInfo(...)` return call, add:

```python
        invalid_external_links=invalid_external_links,
```

In `parse_pvs1_flowchart`, replace the decision-tree loop with:

```python
    decision_tree = []
    for code in flowchart_codes:
        step = _flowchart_step_from_code(code)
        if step is not None:
            decision_tree.append(step)
```

- [ ] **Step 4: Run parser tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/test_scraper_parsers.py::TestVariantInfoParsing::test_parse_variant_info_external_links tests/unit/test_scraper_parsers.py::TestPVS1FlowchartParsing::test_parse_pvs1_flowchart_cleans_steps_and_extracts_note_ids tests/unit/test_real_website_parsing.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/models/autopvs1_models.py autopvs1_link/api/autopvs1_parsers.py tests/unit/test_scraper_parsers.py
git commit -m "fix: clean parser flowchart output"
```

## Task 4: Add MCP Envelope Contracts and Error Helpers

**Files:**
- Create: `autopvs1_link/mcp/envelope.py`
- Modify: `autopvs1_link/mcp/errors.py`
- Modify: `autopvs1_link/mcp/contracts.py`
- Create: `tests/unit/mcp/test_envelope.py`

- [ ] **Step 1: Write failing envelope contract tests**

Create `tests/unit/mcp/test_envelope.py`:

```python
"""Tests for MCP envelope metadata, warnings, and errors."""

from uuid import UUID

from autopvs1_link.mcp.contracts import ClearCacheData, ClearCacheMCPEnvelope
from autopvs1_link.mcp.envelope import MCPWarning, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError


def test_ok_envelope_contains_required_metadata() -> None:
    envelope = ok_envelope(ClearCacheData(cleared=True, message="cleared"))

    assert envelope["ok"] is True
    assert envelope["data"] == {"cleared": True, "message": "cleared"}
    assert envelope["error"] is None
    assert envelope["meta"]["server_version"] == "1.0.0"
    assert envelope["meta"]["research_use_only"] is True
    assert envelope["meta"]["recommended_citation"]["doi"] == "10.1002/humu.24051"
    UUID(envelope["meta"]["request_id"])


def test_error_envelope_contains_machine_readable_error() -> None:
    envelope = error_envelope(
        code="invalid_variant_id",
        message="Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
        retryable=False,
        suggestions=["Use search_variants with a gene symbol."],
    )

    assert envelope["ok"] is False
    assert envelope["data"] is None
    assert envelope["error"] == {
        "code": "invalid_variant_id",
        "message": "Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
        "retryable": False,
        "suggestions": ["Use search_variants with a gene symbol."],
    }
    assert envelope["meta"]["research_use_only"] is True


def test_warning_objects_are_serialized_in_meta() -> None:
    envelope = ok_envelope(
        ClearCacheData(cleared=True, message="cleared"),
        warnings=[MCPWarning(code="deprecated_genome_version", message="Use genome_build.")],
    )

    assert envelope["meta"]["warnings"] == [
        {"code": "deprecated_genome_version", "message": "Use genome_build."}
    ]


def test_mcp_input_error_converts_to_error_envelope() -> None:
    exc = MCPInputError(
        code="invalid_cnv_id",
        message="CNV IDs must use {chrom}-{start}-{end}-{TYPE}.",
        suggestions=["Use 17-15000000-20000000-DEL."],
    )

    envelope = exc.to_envelope()

    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "invalid_cnv_id"
    assert envelope["error"]["retryable"] is False
    assert envelope["error"]["suggestions"] == ["Use 17-15000000-20000000-DEL."]


def test_concrete_envelope_schema_uses_standard_fields() -> None:
    schema = ClearCacheMCPEnvelope.model_json_schema()

    assert set(schema["properties"]) == {"ok", "data", "error", "meta"}
    assert set(schema["required"]) == {"ok", "data", "error", "meta"}
```

- [ ] **Step 2: Run envelope tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_envelope.py -q
```

Expected: FAIL because `autopvs1_link.mcp.envelope`, `MCPInputError`, and concrete envelope contracts do not exist.

- [ ] **Step 3: Implement envelope models and concrete MCP contracts**

Create `autopvs1_link/mcp/envelope.py`:

```python
"""Standard MCP response envelopes and metadata."""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import uuid4

from asgi_correlation_id.context import correlation_id
from pydantic import BaseModel, Field

from autopvs1_link import __version__

DataT = TypeVar("DataT")


class RecommendedCitation(BaseModel):
    """Recommended citation for AutoPVS1 research-use outputs."""

    text: str = (
        "Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic "
        "classification tool for PVS1 interpretation of null variants. "
        "Human Mutation. 2020;41(9):1488-1498."
    )
    doi: str = "10.1002/humu.24051"
    pmid: str = "32442321"
    url: str = "https://pubmed.ncbi.nlm.nih.gov/32442321/"


class MCPWarning(BaseModel):
    """Structured non-fatal warning for LLM callers."""

    code: str
    message: str


class MCPError(BaseModel):
    """Structured MCP tool error."""

    code: str
    message: str
    retryable: bool
    suggestions: list[str] = Field(default_factory=list)


class MCPMeta(BaseModel):
    """Common metadata on every MCP tool envelope."""

    request_id: str = Field(default_factory=lambda: correlation_id.get() or str(uuid4()))
    server_version: str = __version__
    research_use_only: bool = True
    recommended_citation: RecommendedCitation = Field(default_factory=RecommendedCitation)
    warnings: list[MCPWarning] = Field(default_factory=list)


class MCPEnvelope(BaseModel, Generic[DataT]):
    """Standard MCP tool response envelope."""

    ok: bool
    data: DataT | None
    error: MCPError | None
    meta: MCPMeta


def _dump_warning(warning: MCPWarning) -> dict[str, Any]:
    return warning.model_dump(mode="json")


def ok_envelope(data: BaseModel | dict[str, Any], warnings: list[MCPWarning] | None = None) -> dict[str, Any]:
    """Return a successful MCP envelope as a JSON-ready dict."""
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    envelope: MCPEnvelope[Any] = MCPEnvelope(
        ok=True,
        data=payload,
        error=None,
        meta=MCPMeta(warnings=warnings or []),
    )
    return envelope.model_dump(mode="json")


def error_envelope(
    *,
    code: str,
    message: str,
    retryable: bool,
    suggestions: list[str] | None = None,
    warnings: list[MCPWarning] | None = None,
) -> dict[str, Any]:
    """Return a failed MCP envelope as a JSON-ready dict."""
    envelope: MCPEnvelope[Any] = MCPEnvelope(
        ok=False,
        data=None,
        error=MCPError(
            code=code,
            message=message,
            retryable=retryable,
            suggestions=suggestions or [],
        ),
        meta=MCPMeta(warnings=warnings or []),
    )
    return envelope.model_dump(mode="json")
```

Modify `autopvs1_link/mcp/errors.py` by adding:

```python
from autopvs1_link.mcp.envelope import error_envelope


class MCPInputError(MCPToolError):
    """Validation error that should be returned as a structured MCP envelope."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        suggestions: list[str] | None = None,
    ) -> None:
        super().__init__(message, code=code, details={"suggestions": suggestions or []})
        self.suggestions = suggestions or []
        self.retryable = False

    def to_envelope(self) -> dict[str, Any]:
        return error_envelope(
            code=self.code,
            message=str(self),
            retryable=self.retryable,
            suggestions=self.suggestions,
        )
```

Replace `autopvs1_link/mcp/contracts.py` with these contracts while keeping `GenomeBuild`:

```python
"""Pydantic input/output contracts for MCP tools and resources."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from autopvs1_link.mcp.envelope import MCPEnvelope

GenomeBuild = Literal["hg19", "hg38"]


class VariantPVS1Input(BaseModel):
    """Input for ``get_variant_pvs1_data``."""

    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    variant_id: str = Field(
        ..., min_length=1, description="AutoPVS1 variant ID, for example X-82763936-A-T."
    )


class CNVPVS1Input(BaseModel):
    """Input for ``get_cnv_pvs1_data``."""

    genome_build: GenomeBuild = Field(..., description="Genome build: hg19 or hg38.")
    cnv_id: str = Field(
        ...,
        min_length=1,
        description="AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form.",
    )


class ClearCacheInput(BaseModel):
    """Empty input accepted by ``clear_cache``."""


class VariantMCPData(BaseModel):
    """MCP-presented variant data."""

    genome_build: str
    variant_info: dict[str, Any]
    pvs1_flowchart: dict[str, Any]
    disease_mechanisms: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"


class CNVMCPData(BaseModel):
    """MCP-presented CNV data."""

    genome_build: str
    cnv_info: dict[str, Any]
    pvs1_flowchart: dict[str, Any]
    disease_mechanisms: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str | None = None
    upstream_service: str = "AutoPVS1"


class SearchMCPData(BaseModel):
    """MCP-presented search page."""

    query: str
    genome_build: str
    total_count: int
    returned_count: int
    next_cursor: str | None
    ordering: Literal["upstream"] = "upstream"
    results: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CompactCapabilitiesData(BaseModel):
    """Compact first-turn MCP capabilities payload."""

    server: str
    version: str
    transport: str
    endpoint: str
    research_use_only: bool
    tool_summaries: dict[str, str]
    canonical_parameters: dict[str, list[str]]
    compact_workflow: list[str]
    details_resource: str


class ClearCacheData(BaseModel):
    """Clear-cache result data."""

    cleared: bool
    message: str


class CacheStatBlock(BaseModel):
    """One cache-stat method block."""

    hits: int = 0
    misses: int = 0
    errors: int = 0
    evictions: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    average_time_ms: float = 0.0
    last_hit: float | None = None
    last_miss: float | None = None
    uptime_seconds: float = 0.0
    cache_key_shape: str
    description: str


class CacheStatisticsResource(BaseModel):
    """Read-only method-keyed cache statistics resource."""

    statistics: dict[str, CacheStatBlock]


class VariantMCPEnvelope(MCPEnvelope[VariantMCPData]):
    """Envelope schema for ``get_variant_pvs1_data``."""


class CNVMCPEnvelope(MCPEnvelope[CNVMCPData]):
    """Envelope schema for ``get_cnv_pvs1_data``."""


class SearchMCPEnvelope(MCPEnvelope[SearchMCPData]):
    """Envelope schema for ``search_variants``."""


class CompactCapabilitiesMCPEnvelope(MCPEnvelope[CompactCapabilitiesData]):
    """Envelope schema for ``get_server_capabilities``."""


class ClearCacheMCPEnvelope(MCPEnvelope[ClearCacheData]):
    """Envelope schema for ``clear_cache``."""
```

- [ ] **Step 4: Run envelope tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_envelope.py tests/unit/test_mcp_errors.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/envelope.py autopvs1_link/mcp/errors.py autopvs1_link/mcp/contracts.py tests/unit/mcp/test_envelope.py
git commit -m "feat: add mcp response envelopes"
```

## Task 5: Add MCP Input Validation and Normalization Helpers

**Files:**
- Create: `autopvs1_link/mcp/validation.py`
- Create: `tests/unit/mcp/test_validation.py`

- [ ] **Step 1: Write failing validation tests**

Create `tests/unit/mcp/test_validation.py`:

```python
"""Tests for MCP-only input validation and normalization."""

import pytest

from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.validation import (
    normalize_cnv_id,
    normalize_genome_builds,
    normalize_limit_cursor,
    normalize_search_query,
    normalize_variant_id,
)


def test_normalize_variant_id_accepts_autopvs1_examples() -> None:
    assert normalize_variant_id(" X-82763936-A-T ") == "X-82763936-A-T"
    assert normalize_variant_id("17-41276045-ACT-A") == "17-41276045-ACT-A"
    assert normalize_variant_id("2-48033984-G-GGATT") == "2-48033984-G-GGATT"


def test_normalize_variant_id_rejects_obviously_invalid_value() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_variant_id("NOT-A-VARIANT")

    assert exc_info.value.code == "invalid_variant_id"
    assert "X-82763936-A-T" in str(exc_info.value)
    assert "Use search_variants" in exc_info.value.suggestions[0]


def test_normalize_cnv_id_accepts_hyphenated_autopvs1_format() -> None:
    assert normalize_cnv_id(" 17-15000000-20000000-DEL ") == "17-15000000-20000000-DEL"
    assert normalize_cnv_id("X-50000000-60000000-DUP") == "X-50000000-60000000-DUP"


def test_normalize_cnv_id_rejects_colon_format_with_correction() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_cnv_id("chr17:15000000-20000000:DEL")

    assert exc_info.value.code == "invalid_cnv_id"
    assert exc_info.value.suggestions == ["Use 17-15000000-20000000-DEL."]


def test_normalize_cnv_id_rejects_invalid_interval() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_cnv_id("17-20000000-15000000-DEL")

    assert exc_info.value.code == "invalid_cnv_id"
    assert "start must be less than end" in str(exc_info.value)


def test_normalize_genome_builds_defaults_to_hg38() -> None:
    build, warnings = normalize_genome_builds(None, None)
    assert build == "hg38"
    assert warnings == []


def test_normalize_genome_builds_accepts_deprecated_alias_with_warning() -> None:
    build, warnings = normalize_genome_builds(None, "hg19")
    assert build == "hg19"
    assert warnings[0].code == "deprecated_genome_version"


def test_normalize_genome_builds_rejects_conflict() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_genome_builds("hg19", "hg38")

    assert exc_info.value.code == "invalid_genome_build"
    assert "genome_build" in str(exc_info.value)
    assert "genome_version" in str(exc_info.value)


def test_normalize_search_query_trims_and_rejects_whitespace() -> None:
    assert normalize_search_query(" BRCA1 ") == "BRCA1"
    with pytest.raises(MCPInputError) as exc_info:
        normalize_search_query("   ")

    assert exc_info.value.code == "invalid_search_query"


def test_normalize_limit_cursor_bounds_values() -> None:
    assert normalize_limit_cursor(10, None) == (10, 0)
    assert normalize_limit_cursor(99, "5") == (50, 5)
    assert normalize_limit_cursor(0, None) == (1, 0)


def test_normalize_limit_cursor_rejects_non_integer_cursor() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_limit_cursor(10, "abc")

    assert exc_info.value.code == "invalid_search_query"
    assert "cursor" in str(exc_info.value)
```

- [ ] **Step 2: Run validation tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_validation.py -q
```

Expected: FAIL because `autopvs1_link.mcp.validation` does not exist.

- [ ] **Step 3: Implement MCP validation helpers**

Create `autopvs1_link/mcp/validation.py`:

```python
"""MCP-specific input normalization and validation."""

from __future__ import annotations

import re

from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.mcp.errors import MCPInputError

VALID_GENOME_BUILDS = {"hg19", "hg38"}
VARIANT_ID_RE = re.compile(r"^(?:[1-9]|1[0-9]|2[0-2]|X|Y|MT)-[1-9][0-9]*-[ACGTN]+-[ACGTN]+$")
CNV_ID_RE = re.compile(
    r"^(?P<chrom>[1-9]|1[0-9]|2[0-2]|X|Y|MT)-(?P<start>[1-9][0-9]*)-"
    r"(?P<end>[1-9][0-9]*)-(?P<type>DEL|DUP)$"
)
COLON_CNV_RE = re.compile(
    r"^(?:chr)?(?P<chrom>[1-9]|1[0-9]|2[0-2]|X|Y|MT):"
    r"(?P<start>[1-9][0-9]*)-(?P<end>[1-9][0-9]*):(?P<type>DEL|DUP)$",
    re.IGNORECASE,
)


def normalize_genome_build(value: str) -> str:
    normalized = value.strip()
    if normalized not in VALID_GENOME_BUILDS:
        raise MCPInputError(
            code="invalid_genome_build",
            message="Genome build must be hg19 or hg38.",
            suggestions=["Use genome_build='hg38' unless the source variant coordinates are hg19."],
        )
    return normalized


def normalize_genome_builds(
    genome_build: str | None,
    genome_version: str | None,
) -> tuple[str, list[MCPWarning]]:
    warnings: list[MCPWarning] = []
    canonical = normalize_genome_build(genome_build) if genome_build is not None else None
    deprecated = normalize_genome_build(genome_version) if genome_version is not None else None

    if canonical and deprecated and canonical != deprecated:
        raise MCPInputError(
            code="invalid_genome_build",
            message="genome_build and deprecated genome_version must match when both are supplied.",
            suggestions=["Use only genome_build in new MCP calls."],
        )
    if deprecated is not None:
        warnings.append(
            MCPWarning(
                code="deprecated_genome_version",
                message="genome_version is deprecated for MCP search; use genome_build.",
            )
        )
    return canonical or deprecated or "hg38", warnings


def normalize_variant_id(variant_id: str) -> str:
    value = variant_id.strip().upper()
    if not value or not VARIANT_ID_RE.fullmatch(value):
        raise MCPInputError(
            code="invalid_variant_id",
            message="Variant IDs must use AutoPVS1 format such as X-82763936-A-T.",
            suggestions=[
                "Use search_variants with a gene symbol if you do not know the AutoPVS1 variant ID."
            ],
        )
    return value


def _cnv_correction(value: str) -> str | None:
    match = COLON_CNV_RE.fullmatch(value.strip())
    if not match:
        return None
    chrom = match.group("chrom").upper()
    start = match.group("start")
    end = match.group("end")
    cnv_type = match.group("type").upper()
    return f"{chrom}-{start}-{end}-{cnv_type}"


def normalize_cnv_id(cnv_id: str) -> str:
    value = cnv_id.strip().upper()
    match = CNV_ID_RE.fullmatch(value)
    if not match:
        correction = _cnv_correction(cnv_id)
        suggestions = [f"Use {correction}."] if correction else [
            "Use AutoPVS1 CNV format such as 17-15000000-20000000-DEL."
        ]
        raise MCPInputError(
            code="invalid_cnv_id",
            message="CNV IDs must use {chrom}-{start}-{end}-{TYPE}, with TYPE DEL or DUP.",
            suggestions=suggestions,
        )

    start = int(match.group("start"))
    end = int(match.group("end"))
    if start >= end:
        raise MCPInputError(
            code="invalid_cnv_id",
            message="CNV start must be less than end.",
            suggestions=["Use AutoPVS1 CNV format such as 17-15000000-20000000-DEL."],
        )
    return value


def normalize_search_query(query: str) -> str:
    value = query.strip()
    if not value:
        raise MCPInputError(
            code="invalid_search_query",
            message="Search query must not be empty.",
            suggestions=["Search by gene symbol, partial AutoPVS1 variant ID, or upstream-supported query."],
        )
    return value


def normalize_limit_cursor(limit: int, cursor: str | None) -> tuple[int, int]:
    bounded_limit = max(1, min(limit, 50))
    if cursor is None:
        return bounded_limit, 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise MCPInputError(
            code="invalid_search_query",
            message="Search cursor must be an integer-offset string.",
            suggestions=["Use the next_cursor value returned by the previous search_variants call."],
        ) from exc
    if offset < 0:
        raise MCPInputError(
            code="invalid_search_query",
            message="Search cursor must be zero or greater.",
            suggestions=["Use the next_cursor value returned by the previous search_variants call."],
        )
    return bounded_limit, offset
```

- [ ] **Step 4: Run validation tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_validation.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/validation.py tests/unit/mcp/test_validation.py
git commit -m "feat: validate mcp tool inputs"
```

## Task 6: Add Variant and CNV MCP Presenters

**Files:**
- Create: `autopvs1_link/mcp/presenters/__init__.py`
- Create: `autopvs1_link/mcp/presenters/variant.py`
- Create: `tests/unit/mcp/test_variant_presenter.py`

- [ ] **Step 1: Write failing presenter tests**

Create `tests/unit/mcp/test_variant_presenter.py`:

```python
"""Tests for variant and CNV MCP presenters."""

from autopvs1_link.mcp.presenters.variant import format_pli_score, present_cnv, present_variant
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    CNVInfo,
    FlowchartStep,
    PVS1Flowchart,
    VariantInfo,
)


def test_format_pli_score_for_llm_display() -> None:
    assert format_pli_score(None) is None
    assert format_pli_score(0.0) == "0"
    assert format_pli_score(3.29e-20) == "3.29e-20"
    assert format_pli_score(0.72) == "0.72"
    assert format_pli_score(0.123456) == "0.1235"


def test_present_variant_adds_note_text_invalid_link_warning_and_inference_warning() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T",
            variant_type="Nonsense",
            gene_symbol="POU3F4",
            pli_score=3.29e-20,
            external_links={"gnomAD": "https://gnomad.broadinstitute.org/variant/X-82763936-A-T"},
            invalid_external_links={
                "ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na"
            },
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            final_strength_inferred=True,
            decision_tree=[
                FlowchartStep(
                    code="Role of region in protein function is unknown",
                    note_id="#1",
                )
            ],
            notes={"#1": "Resolved note text."},
        ),
        disease_mechanisms=[],
    )

    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
    )

    assert data.upstream_service == "AutoPVS1"
    assert data.source_url == "https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T"
    assert data.variant_info["pli_score"] == 3.29e-20
    assert data.variant_info["pli_score_display"] == "3.29e-20"
    assert data.variant_info["external_links"]["ClinVar"] is None
    assert data.pvs1_flowchart["decision_tree"][0]["note_text"] == "Resolved note text."
    assert {warning.code for warning in warnings} == {
        "invalid_external_link",
        "final_strength_inferred",
    }


def test_present_cnv_shapes_cnv_payload() -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="17-15000000-20000000-DEL",
            cnv_type="Deletion",
            gene_symbol="MYO15A",
            coordinates="17-15000000-20000000-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="VeryStrong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )

    data, warnings = present_cnv(
        parsed,
        source_url="https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
    )

    assert data.genome_build == "hg19"
    assert data.cnv_info["gene_symbol"] == "MYO15A"
    assert data.pvs1_flowchart["final_strength"] == "VeryStrong"
    assert data.upstream_service == "AutoPVS1"
    assert warnings == []
```

- [ ] **Step 2: Run presenter tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_variant_presenter.py -q
```

Expected: FAIL because `autopvs1_link.mcp.presenters.variant` does not exist.

- [ ] **Step 3: Implement variant and CNV presenters**

Create `autopvs1_link/mcp/presenters/__init__.py`:

```python
"""MCP presentation helpers."""
```

Create `autopvs1_link/mcp/presenters/variant.py`:

```python
"""MCP presenters for variant and CNV service results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.contracts import CNVMCPData, VariantMCPData
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData, AutoPVS1Data


def _dump(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)


def format_pli_score(value: float | None) -> str | None:
    """Format pLI for stable LLM display without changing the numeric value."""
    if value is None:
        return None
    if value == 0:
        return "0"
    if 0 < abs(value) < 1e-3:
        return f"{value:.3g}"
    return f"{value:.4g}"


def _present_flowchart(flowchart: BaseModel | dict[str, Any]) -> tuple[dict[str, Any], list[MCPWarning]]:
    raw = _dump(flowchart)
    warnings: list[MCPWarning] = []
    notes = raw.get("notes") or {}
    presented_steps: list[dict[str, Any]] = []

    for step in raw.get("decision_tree", []):
        step_data = _dump(step) if isinstance(step, BaseModel) else dict(step)
        note_id = step_data.get("note_id")
        if note_id and note_id in notes:
            step_data["note_text"] = notes[note_id]
        presented_steps.append(step_data)

    raw["decision_tree"] = presented_steps
    if raw.get("final_strength_inferred"):
        warnings.append(
            MCPWarning(
                code="final_strength_inferred",
                message="final_strength was inferred from the terminal decision_tree node.",
            )
        )
    return raw, warnings


def _present_external_links(raw_info: dict[str, Any]) -> tuple[dict[str, str | None], list[MCPWarning]]:
    warnings: list[MCPWarning] = []
    links: dict[str, str | None] = dict(raw_info.get("external_links") or {})
    invalid_links: dict[str, str] = dict(raw_info.get("invalid_external_links") or {})

    for label, url in list(links.items()):
        if not url or url.rstrip("/").endswith("/variation/na"):
            invalid_links[label] = url or ""

    for label, url in invalid_links.items():
        links[label] = None
        warnings.append(
            MCPWarning(
                code="invalid_external_link",
                message=f"{label} link from upstream AutoPVS1 was invalid and was nulled.",
            )
        )
        raw_info.setdefault("_invalid_external_link_urls", {})[label] = url

    return links, warnings


def _invalid_links_from_variant(parsed: AutoPVS1Data | dict[str, Any]) -> dict[str, str]:
    """Read parser-internal invalid links before excluded fields are dumped."""
    if isinstance(parsed, AutoPVS1Data):
        return dict(parsed.variant_info.invalid_external_links)
    variant_info = dict(parsed.get("variant_info") or {})
    return dict(variant_info.get("invalid_external_links") or {})


def present_variant(
    parsed: AutoPVS1Data | dict[str, Any],
    *,
    source_url: str | None,
) -> tuple[VariantMCPData, list[MCPWarning]]:
    """Shape parsed variant data for MCP callers."""
    raw = _dump(parsed)
    warnings: list[MCPWarning] = []

    variant_info = dict(raw["variant_info"])
    invalid_external_links = _invalid_links_from_variant(parsed)
    if invalid_external_links:
        variant_info["invalid_external_links"] = invalid_external_links
    variant_info["pli_score_display"] = format_pli_score(variant_info.get("pli_score"))
    external_links, link_warnings = _present_external_links(variant_info)
    variant_info["external_links"] = external_links
    variant_info.pop("invalid_external_links", None)
    variant_info.pop("_invalid_external_link_urls", None)
    warnings.extend(link_warnings)

    flowchart, flowchart_warnings = _present_flowchart(raw["pvs1_flowchart"])
    warnings.extend(flowchart_warnings)

    data = VariantMCPData(
        genome_build=raw["genome_build"],
        variant_info=variant_info,
        pvs1_flowchart=flowchart,
        disease_mechanisms=list(raw.get("disease_mechanisms") or []),
        source_url=source_url,
    )
    return data, warnings


def present_cnv(
    parsed: AutoPVS1CNVData | dict[str, Any],
    *,
    source_url: str | None,
) -> tuple[CNVMCPData, list[MCPWarning]]:
    """Shape parsed CNV data for MCP callers."""
    raw = _dump(parsed)
    flowchart, warnings = _present_flowchart(raw["pvs1_flowchart"])
    data = CNVMCPData(
        genome_build=raw["genome_build"],
        cnv_info=dict(raw["cnv_info"]),
        pvs1_flowchart=flowchart,
        disease_mechanisms=list(raw.get("disease_mechanisms") or []),
        source_url=source_url,
    )
    return data, warnings
```

- [ ] **Step 4: Run presenter tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_variant_presenter.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/presenters/__init__.py autopvs1_link/mcp/presenters/variant.py tests/unit/mcp/test_variant_presenter.py
git commit -m "feat: present variant mcp data"
```

## Task 7: Add Search MCP Presenter

**Files:**
- Create: `autopvs1_link/mcp/presenters/search.py`
- Create: `tests/unit/mcp/test_search_presenter.py`

- [ ] **Step 1: Write failing search presenter tests**

Create `tests/unit/mcp/test_search_presenter.py`:

```python
"""Tests for search MCP pagination and guidance."""

from autopvs1_link.mcp.presenters.search import present_search
from autopvs1_link.models.autopvs1_models import AutoPVS1SearchResults, SearchResult


def _result(index: int) -> SearchResult:
    return SearchResult(
        variant_id=f"17-{index}-A-T",
        gene="BRCA1",
        variant_type="Nonsense",
        genome_build="hg38",
        url=f"https://autopvs1.bgi.com/variant/hg38/17-{index}-A-T",
    )


def test_present_search_paginates_in_upstream_order() -> None:
    parsed = AutoPVS1SearchResults(
        query="BRCA1",
        genome_version="hg38",
        results=[_result(index) for index in range(12)],
    )

    data, warnings = present_search(
        parsed,
        query="BRCA1",
        genome_build="hg38",
        limit=10,
        offset=0,
        inherited_warnings=[],
    )

    assert data.query == "BRCA1"
    assert data.genome_build == "hg38"
    assert data.total_count == 12
    assert data.returned_count == 10
    assert data.next_cursor == "10"
    assert data.ordering == "upstream"
    assert data.results[0]["variant_id"] == "17-0-A-T"
    assert warnings[0].code == "search_results_truncated"


def test_present_search_uses_cursor_offset() -> None:
    parsed = AutoPVS1SearchResults(
        query="BRCA1",
        genome_version="hg38",
        results=[_result(index) for index in range(12)],
    )

    data, warnings = present_search(
        parsed,
        query="BRCA1",
        genome_build="hg38",
        limit=10,
        offset=10,
        inherited_warnings=[],
    )

    assert data.returned_count == 2
    assert data.next_cursor is None
    assert [row["variant_id"] for row in data.results] == ["17-10-A-T", "17-11-A-T"]
    assert warnings == []


def test_present_search_adds_guidance_for_empty_hgvs_like_query() -> None:
    parsed = AutoPVS1SearchResults(query="BRCA1 c.5266dupC", genome_version="hg38", results=[])

    data, warnings = present_search(
        parsed,
        query="BRCA1 c.5266dupC",
        genome_build="hg38",
        limit=10,
        offset=0,
        inherited_warnings=[],
    )

    assert data.total_count == 0
    assert data.results == []
    assert data.suggestions == [
        "Search for BRCA1 only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]
    assert warnings[0].code == "unsupported_hgvs_like_search"
```

- [ ] **Step 2: Run search presenter tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_search_presenter.py -q
```

Expected: FAIL because `autopvs1_link.mcp.presenters.search` does not exist.

- [ ] **Step 3: Implement search presenter**

Create `autopvs1_link/mcp/presenters/search.py`:

```python
"""MCP presenter for search results."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.contracts import SearchMCPData
from autopvs1_link.mcp.envelope import MCPWarning

HGVS_LIKE_RE = re.compile(r"(\b[A-Z0-9-]+\s+c\.)|(\bN[MR]_\d+\.\d+:[cn]\.)", re.IGNORECASE)


def _dump_result(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)


def _empty_search_suggestions(query: str) -> list[str]:
    gene = query.split()[0] if query.split() else "the gene symbol"
    return [
        f"Search for {gene} only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]


def present_search(
    parsed: BaseModel | dict[str, Any],
    *,
    query: str,
    genome_build: str,
    limit: int,
    offset: int,
    inherited_warnings: list[MCPWarning],
) -> tuple[SearchMCPData, list[MCPWarning]]:
    """Shape search results into a bounded MCP page."""
    raw = parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else dict(parsed)
    all_results = [_dump_result(result) for result in raw.get("results", [])]
    total_count = len(all_results)
    page = all_results[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = str(next_offset) if next_offset < total_count else None
    warnings = list(inherited_warnings)
    suggestions: list[str] = []

    if next_cursor is not None:
        warnings.append(
            MCPWarning(
                code="search_results_truncated",
                message="Search results were truncated by limit; use next_cursor for the next page.",
            )
        )

    if total_count == 0 and HGVS_LIKE_RE.search(query):
        suggestions = _empty_search_suggestions(query)
        warnings.append(
            MCPWarning(
                code="unsupported_hgvs_like_search",
                message="AutoPVS1 search returned no results for an HGVS-like free-text query.",
            )
        )

    return (
        SearchMCPData(
            query=query,
            genome_build=genome_build,
            total_count=total_count,
            returned_count=len(page),
            next_cursor=next_cursor,
            results=page,
            suggestions=suggestions,
        ),
        warnings,
    )
```

- [ ] **Step 4: Run search presenter tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_search_presenter.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/presenters/search.py tests/unit/mcp/test_search_presenter.py
git commit -m "feat: paginate mcp search output"
```

## Task 8: Stabilize Cache Statistics Resource Shape and Counter Semantics

**Files:**
- Create: `autopvs1_link/mcp/presenters/cache.py`
- Modify: `autopvs1_link/utils/cache_manager.py`
- Modify: `tests/unit/test_cache_manager.py`
- Create: `tests/unit/mcp/test_cache_presenter.py`

- [ ] **Step 1: Write failing cache presenter and counter tests**

Create `tests/unit/mcp/test_cache_presenter.py`:

```python
"""Tests for stable MCP cache statistics resource presentation."""

from autopvs1_link.mcp.presenters.cache import CACHE_STAT_METHODS, present_cache_statistics


def test_present_cache_statistics_includes_all_configured_keys_when_empty() -> None:
    resource = present_cache_statistics({})

    assert set(resource.statistics) == set(CACHE_STAT_METHODS)
    for method_name, block in resource.statistics.items():
        assert block.hits == 0
        assert block.misses == 0
        assert block.errors == 0
        assert block.total_requests == 0
        assert block.cache_key_shape == CACHE_STAT_METHODS[method_name]["cache_key_shape"]
        assert block.description == CACHE_STAT_METHODS[method_name]["description"]


def test_present_cache_statistics_merges_raw_counters() -> None:
    resource = present_cache_statistics(
        {
            "get_variant_data": {
                "hits": 3,
                "misses": 2,
                "errors": 1,
                "evictions": 0,
                "total_requests": 5,
                "hit_rate": 0.6,
                "average_time_ms": 12.5,
                "last_hit": 100.0,
                "last_miss": 90.0,
                "uptime_seconds": 30.0,
            }
        }
    )

    block = resource.statistics["get_variant_data"]
    assert block.hits == 3
    assert block.misses == 2
    assert block.errors == 1
    assert block.hit_rate == 0.6
    assert block.cache_key_shape == "variant:{genome_build}:{variant_id}"
```

Add this async test to `tests/unit/test_cache_manager.py`:

```python
import pytest
```

```python
@pytest.mark.asyncio
async def test_cache_error_increments_errors_without_miss() -> None:
    manager = AdvancedCacheManager()

    @manager.enhanced_cache(key_func=lambda value: f"flaky:{value}")
    async def flaky(value: str) -> str:
        raise RuntimeError(f"boom {value}")

    with pytest.raises(RuntimeError, match="boom x"):
        await flaky("x")

    stats = manager.get_statistics("flaky")["flaky"]
    assert stats["errors"] == 1
    assert stats["misses"] == 0
    assert stats["hits"] == 0
```

- [ ] **Step 2: Run cache tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_cache_presenter.py tests/unit/test_cache_manager.py::test_cache_error_increments_errors_without_miss -q
```

Expected: FAIL because the cache presenter does not exist. If the error-counter test already passes, keep it as regression coverage.

- [ ] **Step 3: Implement stable cache presenter and confirm counter behavior**

Create `autopvs1_link/mcp/presenters/cache.py`:

```python
"""MCP cache statistics resource presenter."""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.contracts import CacheStatBlock, CacheStatisticsResource

CACHE_STAT_METHODS: dict[str, dict[str, str]] = {
    "get_variant_data": {
        "cache_key_shape": "variant:{genome_build}:{variant_id}",
        "description": "Direct variant scoring by genome_build and variant_id.",
    },
    "get_cnv_data": {
        "cache_key_shape": "cnv:{genome_build}:{cnv_id}",
        "description": "Direct CNV scoring by genome_build and cnv_id.",
    },
    "search_variants": {
        "cache_key_shape": "search:{query}:{genome_build}",
        "description": "Search by normalized query and genome_build.",
    },
    "search_with_redirect_detection": {
        "cache_key_shape": "enhanced_search:{query}:{genome_build}",
        "description": "Enhanced search and HGVS redirect path used by REST or future MCP tools.",
    },
    "resolve_hgvs_notation": {
        "cache_key_shape": "hgvs:{hgvs}:{genome_build}",
        "description": "HGVS resolution path used by REST or future MCP tools.",
    },
}


def _block(method_name: str, raw: dict[str, Any] | None) -> CacheStatBlock:
    metadata = CACHE_STAT_METHODS[method_name]
    raw = raw or {}
    return CacheStatBlock(
        hits=int(raw.get("hits", 0)),
        misses=int(raw.get("misses", 0)),
        errors=int(raw.get("errors", 0)),
        evictions=int(raw.get("evictions", 0)),
        total_requests=int(raw.get("total_requests", 0)),
        hit_rate=float(raw.get("hit_rate", 0.0)),
        average_time_ms=float(raw.get("average_time_ms", 0.0)),
        last_hit=raw.get("last_hit"),
        last_miss=raw.get("last_miss"),
        uptime_seconds=float(raw.get("uptime_seconds", 0.0)),
        cache_key_shape=metadata["cache_key_shape"],
        description=metadata["description"],
    )


def present_cache_statistics(raw_statistics: dict[str, Any]) -> CacheStatisticsResource:
    """Return stable method-keyed cache statistics for the MCP resource."""
    return CacheStatisticsResource(
        statistics={
            method_name: _block(method_name, raw_statistics.get(method_name))
            for method_name in CACHE_STAT_METHODS
        }
    )
```

In `autopvs1_link/utils/cache_manager.py`, leave `_record_miss` after the cached function returns successfully. If the failing counter test shows that a miss is recorded on exception, move `_record_miss(method_name, cache_key, execution_time)` so it executes only after `result = await cached_func(*args, **kwargs)` returns and before `return result`. Preserve `_record_error(method_name, cache_key, str(e))` in the `except` block.

- [ ] **Step 4: Run cache tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_cache_presenter.py tests/unit/test_cache_manager.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/presenters/cache.py autopvs1_link/utils/cache_manager.py tests/unit/mcp/test_cache_presenter.py tests/unit/test_cache_manager.py
git commit -m "feat: stabilize mcp cache statistics"
```

## Task 9: Split Compact Capabilities Tool from Detailed Capabilities Resource

**Files:**
- Create: `autopvs1_link/mcp/presenters/capabilities.py`
- Create: `autopvs1_link/mcp/server_info.py`
- Modify: `autopvs1_link/mcp/metadata.py`
- Modify: `tests/unit/mcp/test_resources.py`
- Create: `tests/unit/mcp/test_capabilities_presenter.py`

- [ ] **Step 1: Write failing capabilities tests**

Create `tests/unit/mcp/test_capabilities_presenter.py`:

```python
"""Tests for compact and detailed MCP capabilities payloads."""

from autopvs1_link.mcp.presenters.capabilities import (
    detailed_capabilities_resource,
    present_compact_capabilities,
)


def test_compact_capabilities_are_first_turn_tool_selection_data() -> None:
    compact = present_compact_capabilities()

    assert compact.research_use_only is True
    assert compact.details_resource == "autopvs1-link://capabilities"
    assert compact.canonical_parameters["search_variants"] == ["query", "genome_build", "limit", "cursor"]
    assert "genome_version" not in compact.canonical_parameters["search_variants"]
    assert "research-use" in compact.tool_summaries["get_variant_pvs1_data"]


def test_detailed_capabilities_resource_has_examples_and_is_not_duplicate() -> None:
    compact = present_compact_capabilities().model_dump(mode="json")
    detailed = detailed_capabilities_resource()

    assert detailed["accepted_formats"]["cnv_id"] == "{chrom}-{start}-{end}-{TYPE}"
    assert "17-15000000-20000000-DEL" in detailed["examples"]["get_cnv_pvs1_data"]["cnv_id"]
    assert detailed["error_envelope"]["required_fields"] == ["ok", "data", "error", "meta"]
    assert detailed != compact
```

Extend `tests/unit/mcp/test_resources.py`:

```python

@pytest.mark.asyncio
async def test_capabilities_tool_and_resource_are_not_duplicates() -> None:
    mcp = build_mcp_server()

    tool_result = await mcp.call_tool("get_server_capabilities", {})
    resource_result = await mcp.read_resource("autopvs1-link://capabilities")

    assert tool_result.structured_content["ok"] is True
    assert tool_result.structured_content["data"]["details_resource"] == "autopvs1-link://capabilities"
    assert resource_result is not None
    assert tool_result.structured_content != resource_result
```

- [ ] **Step 2: Run capabilities tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_capabilities_presenter.py tests/unit/mcp/test_resources.py::test_capabilities_tool_and_resource_are_not_duplicates -q
```

Expected: FAIL because the presenter does not exist and the capabilities tool/resource currently use the same payload.

- [ ] **Step 3: Implement capabilities presenter and wire metadata**

Create `autopvs1_link/mcp/server_info.py`:

```python
"""Shared MCP server metadata constants."""

from __future__ import annotations

SERVER_NAME = "AutoPVS1 Link"
SERVER_VERSION = "1.0.0"
SERVER_DESCRIPTION = (
    "AutoPVS1-Link exposes research-use PVS1 variant classification tools. "
    "Use get_variant_pvs1_data for SNV/indel IDs like X-82763936-A-T after "
    "choosing genome_build hg19 or hg38. Use search_variants for gene or "
    "partial variant lookup, get_cnv_pvs1_data for CNVs, and "
    "get_server_capabilities when discovering the MCP surface. Results are "
    "research-use data, not clinical decision support."
)
```

Create `autopvs1_link/mcp/presenters/capabilities.py`:

```python
"""MCP capabilities presenters."""

from __future__ import annotations

from typing import Any

from autopvs1_link.mcp.contracts import CompactCapabilitiesData
from autopvs1_link.mcp.server_info import SERVER_NAME, SERVER_VERSION


def present_compact_capabilities() -> CompactCapabilitiesData:
    """Return compact capabilities optimized for first-turn tool selection."""
    return CompactCapabilitiesData(
        server=SERVER_NAME,
        version=SERVER_VERSION,
        transport="streamable-http",
        endpoint="/mcp/",
        research_use_only=True,
        tool_summaries={
            "get_variant_pvs1_data": "Research-use PVS1 analysis for one AutoPVS1 SNV/indel ID.",
            "get_cnv_pvs1_data": "Research-use PVS1 analysis for one AutoPVS1 CNV ID.",
            "search_variants": "Search AutoPVS1 by gene symbol, partial variant ID, or upstream-supported query.",
            "clear_cache": "Opt-in destructive cache clear; disabled unless explicitly enabled.",
        },
        canonical_parameters={
            "get_variant_pvs1_data": ["genome_build", "variant_id"],
            "get_cnv_pvs1_data": ["genome_build", "cnv_id"],
            "search_variants": ["query", "genome_build", "limit", "cursor"],
            "clear_cache": [],
        },
        compact_workflow=[
            "Ask for hg19 or hg38 if the source coordinate build is unknown.",
            "Use search_variants only when the AutoPVS1 variant or CNV ID is unknown.",
            "Use get_variant_pvs1_data or get_cnv_pvs1_data for scoring.",
            "Report outputs as research-use AutoPVS1 data, not clinical decision support.",
        ],
        details_resource="autopvs1-link://capabilities",
    )


def detailed_capabilities_resource() -> dict[str, Any]:
    """Return the full application-controlled capabilities reference resource."""
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "research_use_only": True,
        "accepted_formats": {
            "variant_id": "{chrom}-{position}-{reference}-{alternate}",
            "cnv_id": "{chrom}-{start}-{end}-{TYPE}",
            "genome_build": ["hg19", "hg38"],
        },
        "examples": {
            "get_variant_pvs1_data": {
                "genome_build": "hg19",
                "variant_id": "X-82763936-A-T",
            },
            "get_cnv_pvs1_data": {
                "genome_build": "hg19",
                "cnv_id": "17-15000000-20000000-DEL",
            },
            "search_variants": {
                "query": "BRCA1",
                "genome_build": "hg38",
                "limit": 10,
                "cursor": None,
            },
        },
        "search_behavior": {
            "ordering": "upstream",
            "limit_default": 10,
            "limit_min": 1,
            "limit_max": 50,
            "cursor": "Opaque integer-offset string returned as next_cursor.",
            "deprecated_alias": "genome_version is accepted for one release; use genome_build.",
        },
        "error_envelope": {
            "required_fields": ["ok", "data", "error", "meta"],
            "stable_error_codes": [
                "invalid_genome_build",
                "invalid_variant_id",
                "invalid_cnv_id",
                "invalid_search_query",
                "not_found",
                "upstream_unavailable",
                "upstream_timeout",
                "parse_error",
                "destructive_disabled",
                "internal_error",
            ],
        },
        "cache_statistics": {
            "resource": "autopvs1-link://cache/statistics",
            "semantics": "Method-keyed counters with stable keys and cache key shapes.",
        },
        "destructive_tools": {
            "clear_cache": "Disabled by default; enable only with AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true.",
        },
        "citation": {
            "doi": "10.1002/humu.24051",
            "pmid": "32442321",
            "url": "https://pubmed.ncbi.nlm.nih.gov/32442321/",
        },
        "known_upstream_limitations": [
            "AutoPVS1 returns HTML pages rather than a stable public JSON API.",
            "Unsupported HGVS-like free-text search may return no results.",
            "Outputs are research-use data and require domain review.",
        ],
    }
```

Modify `autopvs1_link/mcp/metadata.py`:

```python
from autopvs1_link.mcp.server_info import SERVER_DESCRIPTION, SERVER_NAME, SERVER_VERSION
from autopvs1_link.mcp.contracts import CompactCapabilitiesMCPEnvelope
from autopvs1_link.mcp.envelope import ok_envelope
from autopvs1_link.mcp.presenters.capabilities import (
    detailed_capabilities_resource,
    present_compact_capabilities,
)
```

Delete the existing `SERVER_NAME`, `SERVER_VERSION`, and `SERVER_DESCRIPTION` assignments from `metadata.py`; the imported constants from `server_info.py` replace them.

Change `get_capabilities()` to:

```python
def get_capabilities() -> dict[str, Any]:
    """Return compact MCP capabilities data as a JSON-ready dict."""
    return present_compact_capabilities().model_dump(mode="json")
```

Change the tool registration:

```python
    @mcp.tool(
        name="get_server_capabilities",
        title="Get AutoPVS1-Link Capabilities",
        output_schema=CompactCapabilitiesMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_CLOSED_WORLD,
    )
    async def get_server_capabilities() -> dict[str, Any]:
        """Use this to discover AutoPVS1-Link MCP tools, inputs, limitations, and workflow."""
        return ok_envelope(present_compact_capabilities())
```

Change the resource registration:

```python
    @mcp.resource("autopvs1-link://capabilities")
    def capabilities() -> dict[str, Any]:
        return detailed_capabilities_resource()
```

- [ ] **Step 4: Run capabilities tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_capabilities_presenter.py tests/unit/mcp/test_resources.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/server_info.py autopvs1_link/mcp/presenters/capabilities.py autopvs1_link/mcp/metadata.py tests/unit/mcp/test_capabilities_presenter.py tests/unit/mcp/test_resources.py
git commit -m "feat: split mcp capabilities payloads"
```

## Task 10: Wire Variant and CNV Tools to Envelopes, Validation, and Presenters

**Files:**
- Modify: `autopvs1_link/mcp/tools/variant_tool.py`
- Modify: `autopvs1_link/mcp/tools/cnv_tool.py`
- Modify: `tests/unit/mcp/test_tool_runtime.py`
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing runtime and schema tests for variant/CNV tools**

In `tests/unit/mcp/test_tool_runtime.py`, add imports:

```python
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    CNVInfo,
    PVS1Flowchart,
    VariantInfo,
)
```

Add these tests:

```python

@pytest.mark.asyncio
async def test_get_variant_invalid_id_returns_envelope_without_calling_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.get_variant", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_variant_pvs1_data",
        {"genome_build": "hg38", "variant_id": "NOT-A-VARIANT"},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_variant_id"
    assert "MDN" not in result.content[0].text
    assert "<html" not in result.content[0].text.lower()
    assert "traceback" not in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_get_cnv_colon_format_returns_guidance_without_calling_upstream(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": "chr17:15000000-20000000:DEL"},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_cnv_id"
    assert result.structured_content["error"]["suggestions"] == [
        "Use 17-15000000-20000000-DEL."
    ]


@pytest.mark.asyncio
async def test_get_cnv_hyphenated_format_forwards_upstream(mocker) -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="17-15000000-20000000-DEL",
            cnv_type="Deletion",
            gene_symbol="MYO15A",
            coordinates="17-15000000-20000000-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="VeryStrong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.get_cnv", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "get_cnv_pvs1_data",
        {"genome_build": "hg19", "cnv_id": "17-15000000-20000000-DEL"},
    )

    fake.assert_awaited_once_with("hg19", "17-15000000-20000000-DEL")
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["cnv_info"]["gene_symbol"] == "MYO15A"
```

Update existing variant/CNV runtime smoke assertions in the same file so they assert:

```python
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["upstream_service"] == "AutoPVS1"
```

For those existing tests, replace `_FakeResult` returns with real `AutoPVS1Data` or `AutoPVS1CNVData` instances so presenters receive the expected service shape:

```python
def _variant_result() -> AutoPVS1Data:
    return AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )


def _cnv_result() -> AutoPVS1CNVData:
    return AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="1-1-2-DEL",
            cnv_type="Deletion",
            gene_symbol="GENE",
            coordinates="1-1-2-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
```

In `tests/unit/mcp/test_tools.py`, extend `test_data_tools_have_titles_annotations_and_output_schemas`:

```python
        assert set(tool.output_schema["properties"]) == {"ok", "data", "error", "meta"}
```

- [ ] **Step 2: Run variant/CNV MCP tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_tool_runtime.py::test_get_variant_invalid_id_returns_envelope_without_calling_upstream tests/unit/mcp/test_tool_runtime.py::test_get_cnv_colon_format_returns_guidance_without_calling_upstream tests/unit/mcp/test_tool_runtime.py::test_get_cnv_hyphenated_format_forwards_upstream tests/unit/mcp/test_tools.py::test_data_tools_have_titles_annotations_and_output_schemas -q
```

Expected: FAIL because variant/CNV tools still advertise flat schemas and do not validate or envelope responses.

- [ ] **Step 3: Wire variant/CNV tools to validation, presenters, and envelope schemas**

In `autopvs1_link/mcp/tools/variant_tool.py`, update imports:

```python
import httpx

from autopvs1_link.api.autopvs1_urls import variant_url
from autopvs1_link.config import settings
from autopvs1_link.mcp.contracts import VariantMCPEnvelope
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.presenters.variant import present_variant
from autopvs1_link.mcp.validation import normalize_genome_build, normalize_variant_id
```

Change `output_schema`:

```python
        output_schema=VariantMCPEnvelope.model_json_schema(),
```

Change the `genome_build` argument annotation in `get_variant_pvs1_data` to accept a string and let the tool return structured validation errors:

```python
        genome_build: Annotated[
            str,
            Field(
                description="Genome build: hg19 or hg38.",
                json_schema_extra={"enum": ["hg19", "hg38"]},
            ),
        ],
```

Replace the function body with:

```python
        try:
            normalized_build = normalize_genome_build(genome_build)
            normalized_variant_id = normalize_variant_id(variant_id)
            result = await service_adapters.get_variant(normalized_build, normalized_variant_id)
            data, warnings = present_variant(
                result,
                source_url=variant_url(settings.api.base_url, normalized_build, normalized_variant_id),
            )
            return ok_envelope(data, warnings=warnings)
        except MCPInputError as exc:
            return exc.to_envelope()
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while fetching variant data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
            )
        except httpx.HTTPStatusError as exc:
            code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
            return error_envelope(
                code=code,
                message="AutoPVS1 upstream could not return variant data for this request.",
                retryable=exc.response.status_code >= 500,
                suggestions=["Confirm the genome_build and AutoPVS1 variant ID."],
            )
        except ValueError:
            return error_envelope(
                code="parse_error",
                message="AutoPVS1 variant HTML could not be parsed into the expected fields.",
                retryable=False,
                suggestions=["Retry after confirming the variant exists in AutoPVS1."],
            )
```

In `autopvs1_link/mcp/tools/cnv_tool.py`, update imports:

```python
import httpx

from autopvs1_link.api.autopvs1_urls import cnv_url
from autopvs1_link.config import settings
from autopvs1_link.mcp.contracts import CNVMCPEnvelope
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.presenters.variant import present_cnv
from autopvs1_link.mcp.validation import normalize_cnv_id, normalize_genome_build
```

Change `cnv_id` field description:

```python
            Field(
                min_length=1,
                description=(
                    "AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form, "
                    "for example 17-15000000-20000000-DEL. TYPE is DEL or DUP."
                ),
            )
```

Change `output_schema`:

```python
        output_schema=CNVMCPEnvelope.model_json_schema(),
```

Change the `genome_build` argument annotation in `get_cnv_pvs1_data` to accept a string and let the tool return structured validation errors:

```python
        genome_build: Annotated[
            str,
            Field(
                description="Genome build: hg19 or hg38.",
                json_schema_extra={"enum": ["hg19", "hg38"]},
            ),
        ],
```

Replace the function body with:

```python
        try:
            normalized_build = normalize_genome_build(genome_build)
            normalized_cnv_id = normalize_cnv_id(cnv_id)
            result = await service_adapters.get_cnv(normalized_build, normalized_cnv_id)
            data, warnings = present_cnv(
                result,
                source_url=cnv_url(settings.api.base_url, normalized_build, normalized_cnv_id),
            )
            return ok_envelope(data, warnings=warnings)
        except MCPInputError as exc:
            return exc.to_envelope()
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while fetching CNV data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
            )
        except httpx.HTTPStatusError as exc:
            code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
            return error_envelope(
                code=code,
                message="AutoPVS1 upstream could not return CNV data for this request.",
                retryable=exc.response.status_code >= 500,
                suggestions=["Use CNV format such as 17-15000000-20000000-DEL."],
            )
        except ValueError:
            return error_envelope(
                code="parse_error",
                message="AutoPVS1 CNV HTML could not be parsed into the expected fields.",
                retryable=False,
                suggestions=["Retry after confirming the CNV exists in AutoPVS1."],
            )
```

- [ ] **Step 4: Run variant/CNV MCP tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py -q
```

Expected: PASS for variant/CNV-related tests. Existing search and clear-cache tests may still fail until later tasks; if so, run the specific tests listed in Step 2 and proceed to the next task.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/tools/variant_tool.py autopvs1_link/mcp/tools/cnv_tool.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py
git commit -m "feat: envelope variant and cnv tools"
```

## Task 11: Wire Search Tool to Canonical Arguments, Pagination, Alias Warnings, and Envelope Schema

**Files:**
- Modify: `autopvs1_link/mcp/tools/search_tool.py`
- Modify: `tests/unit/mcp/test_tool_runtime.py`
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing search runtime and schema tests**

In `tests/unit/mcp/test_tool_runtime.py`, add import:

```python
from autopvs1_link.models.autopvs1_models import AutoPVS1SearchResults
```

Add these tests:

```python

@pytest.mark.asyncio
async def test_search_whitespace_returns_invalid_search_query(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool("search_variants", {"query": "   "})

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_search_query"


@pytest.mark.asyncio
async def test_search_no_result_hgvs_like_query_returns_guidance(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="BRCA1 c.5266dupC", genome_version="hg38", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": " BRCA1 c.5266dupC ", "genome_build": "hg38"},
    )

    fake.assert_awaited_once_with("BRCA1 c.5266dupC", "hg38")
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"]["total_count"] == 0
    assert result.structured_content["data"]["suggestions"] == [
        "Search for BRCA1 only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]
    assert result.structured_content["meta"]["warnings"][0]["code"] == "unsupported_hgvs_like_search"


@pytest.mark.asyncio
async def test_search_deprecated_genome_version_alias_still_works(mocker) -> None:
    parsed = AutoPVS1SearchResults(query="MYH9", genome_version="hg19", results=[])
    fake = AsyncMock(return_value=parsed)
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": "MYH9", "genome_version": "hg19"},
    )

    fake.assert_awaited_once_with("MYH9", "hg19")
    assert result.structured_content["ok"] is True
    assert result.structured_content["meta"]["warnings"][0]["code"] == "deprecated_genome_version"


@pytest.mark.asyncio
async def test_search_conflicting_genome_build_alias_returns_error(mocker) -> None:
    fake = AsyncMock()
    mocker.patch("autopvs1_link.mcp.service_adapters.search_variants", new=fake)

    mcp = build_mcp_server()
    result = await mcp.call_tool(
        "search_variants",
        {"query": "MYH9", "genome_build": "hg19", "genome_version": "hg38"},
    )

    fake.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "invalid_genome_build"
```

In `tests/unit/mcp/test_tools.py`, update `test_data_tools_use_direct_arguments_for_llm_discovery` search assertions:

```python
    search_schema = tools["search_variants"].parameters
    assert set(search_schema["properties"]) == {
        "query",
        "genome_build",
        "limit",
        "cursor",
        "genome_version",
    }
    assert search_schema["required"] == ["query"]
    assert "deprecated" in search_schema["properties"]["genome_version"]["description"].lower()
```

- [ ] **Step 2: Run search MCP tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_tool_runtime.py::test_search_whitespace_returns_invalid_search_query tests/unit/mcp/test_tool_runtime.py::test_search_no_result_hgvs_like_query_returns_guidance tests/unit/mcp/test_tool_runtime.py::test_search_deprecated_genome_version_alias_still_works tests/unit/mcp/test_tool_runtime.py::test_search_conflicting_genome_build_alias_returns_error tests/unit/mcp/test_tools.py::test_data_tools_use_direct_arguments_for_llm_discovery -q
```

Expected: FAIL because `search_variants` still uses only `genome_version`, has no pagination, and returns a flat payload.

- [ ] **Step 3: Implement search tool migration shape and envelope output**

In `autopvs1_link/mcp/tools/search_tool.py`, update imports:

```python
import httpx

from autopvs1_link.mcp.contracts import SearchMCPEnvelope
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.presenters.search import present_search
from autopvs1_link.mcp.validation import (
    normalize_genome_builds,
    normalize_limit_cursor,
    normalize_search_query,
)
```

Change `output_schema`:

```python
        output_schema=SearchMCPEnvelope.model_json_schema(),
```

Replace the function signature with:

```python
    async def search_variants(
        query: Annotated[
            str,
            Field(min_length=1, description="Gene symbol, HGVS text, or partial variant string."),
        ],
        genome_build: Annotated[
            str | None,
            Field(
                description="Canonical genome build for MCP search: hg19 or hg38.",
                json_schema_extra={"enum": ["hg19", "hg38"]},
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(
                description=(
                    "Maximum results to return; default 10. Values below 1 are treated "
                    "as 1 and values above 50 are treated as 50."
                ),
            ),
        ] = 10,
        cursor: Annotated[
            str | None,
            Field(description="Opaque integer-offset cursor returned as next_cursor."),
        ] = None,
        genome_version: Annotated[
            str | None,
            Field(
                description="Deprecated alias for genome_build; accepted for one release.",
                json_schema_extra={"enum": ["hg19", "hg38"]},
            ),
        ] = None,
    ) -> dict[str, Any]:
```

Replace the function body with:

```python
        try:
            normalized_query = normalize_search_query(query)
            normalized_build, build_warnings = normalize_genome_builds(genome_build, genome_version)
            normalized_limit, offset = normalize_limit_cursor(limit, cursor)
            result = await service_adapters.search_variants(normalized_query, normalized_build)
            data, warnings = present_search(
                result,
                query=normalized_query,
                genome_build=normalized_build,
                limit=normalized_limit,
                offset=offset,
                inherited_warnings=build_warnings,
            )
            return ok_envelope(data, warnings=warnings)
        except MCPInputError as exc:
            return exc.to_envelope()
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while searching variants.",
                retryable=True,
                suggestions=["Retry later or search by gene symbol only."],
            )
        except httpx.HTTPStatusError as exc:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream could not complete the search request.",
                retryable=exc.response.status_code >= 500,
                suggestions=["Retry later or simplify the search query."],
            )
```

- [ ] **Step 4: Run search MCP tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py -q
```

Expected: PASS for search-related tests. Clear-cache tests may still fail until Task 12.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/tools/search_tool.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py
git commit -m "feat: migrate mcp search contract"
```

## Task 12: Wire Clear Cache and Cache Resource to New Contracts

**Files:**
- Modify: `autopvs1_link/mcp/tools/cache_tools.py`
- Modify: `autopvs1_link/mcp/resources.py`
- Modify: `tests/unit/mcp/test_tool_runtime.py`
- Modify: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write failing clear-cache and cache-resource runtime tests**

In `tests/unit/mcp/test_tool_runtime.py`, add:

```python

@pytest.mark.asyncio
async def test_clear_cache_disabled_returns_standard_envelope(monkeypatch, mocker) -> None:
    monkeypatch.delenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", raising=False)
    fake = AsyncMock()
    fake.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.call_tool("clear_cache", {})

    fake.clear_cache.assert_not_awaited()
    assert result.structured_content["ok"] is False
    assert result.structured_content["error"]["code"] == "destructive_disabled"
    assert result.structured_content["error"]["retryable"] is False


@pytest.mark.asyncio
async def test_clear_cache_enabled_accepts_empty_input(monkeypatch, mocker) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")
    fake = AsyncMock()
    fake.clear_cache = AsyncMock()
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.call_tool("clear_cache", {})

    fake.clear_cache.assert_awaited_once()
    assert result.structured_content["ok"] is True
    assert result.structured_content["data"] == {
        "cleared": True,
        "message": "All service caches and cache statistics cleared.",
    }


@pytest.mark.asyncio
async def test_cache_resource_returns_stable_method_keys(mocker) -> None:
    fake = AsyncMock()
    fake.get_cache_statistics = AsyncMock(return_value={})
    mocker.patch(
        "autopvs1_link.mcp.service_adapters._service",
        new=AsyncMock(return_value=fake),
    )

    mcp = build_mcp_server()
    result = await mcp.read_resource("autopvs1-link://cache/statistics")

    assert result is not None
    text = result[0].text if isinstance(result, list) else str(result)
    assert "get_variant_data" in text
    assert "get_cnv_data" in text
    assert "search_variants" in text
    assert "search_with_redirect_detection" in text
    assert "resolve_hgvs_notation" in text
```

In `tests/unit/mcp/test_tools.py`, add:

```python

@pytest.mark.asyncio
async def test_clear_cache_schema_accepts_empty_object_without_dummy_field() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    schema = tools["clear_cache"].parameters
    assert schema.get("properties", {}) == {}
    assert "_" not in schema.get("properties", {})
    assert set(tools["clear_cache"].output_schema["properties"]) == {"ok", "data", "error", "meta"}
```

- [ ] **Step 2: Run clear-cache/cache-resource tests to verify they fail**

Run:

```bash
uv run pytest tests/unit/mcp/test_tool_runtime.py::test_clear_cache_disabled_returns_standard_envelope tests/unit/mcp/test_tool_runtime.py::test_clear_cache_enabled_accepts_empty_input tests/unit/mcp/test_tool_runtime.py::test_cache_resource_returns_stable_method_keys tests/unit/mcp/test_tools.py::test_clear_cache_schema_accepts_empty_object_without_dummy_field -q
```

Expected: FAIL because `clear_cache` raises a tool error instead of returning an envelope, still exposes a dummy input field, and the cache resource does not shape stable method keys.

- [ ] **Step 3: Implement clear-cache envelope and stable cache resource**

In `autopvs1_link/mcp/tools/cache_tools.py`, update imports:

```python
from autopvs1_link.mcp.contracts import ClearCacheData, ClearCacheMCPEnvelope
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import DestructiveOperationDisabledError
```

Change the tool registration:

```python
    @mcp.tool(
        name="clear_cache",
        title="Clear AutoPVS1-Link Cache",
        output_schema=ClearCacheMCPEnvelope.model_json_schema(),
        annotations=DESTRUCTIVE_CLOSED_WORLD,
    )
    async def clear_cache() -> dict[str, Any]:
```

Replace the body with:

```python
        try:
            await service_adapters.clear_cache()
        except DestructiveOperationDisabledError as exc:
            return error_envelope(
                code="destructive_disabled",
                message=str(exc),
                retryable=False,
                suggestions=[
                    "Set AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true only in trusted administrative environments."
                ],
            )
        return ok_envelope(
            ClearCacheData(
                cleared=True,
                message="All service caches and cache statistics cleared.",
            )
        )
```

In `autopvs1_link/mcp/resources.py`, update imports:

```python
from autopvs1_link.mcp.presenters.cache import present_cache_statistics
```

Change `cache_statistics()`:

```python
    @mcp.resource("autopvs1-link://cache/statistics")
    async def cache_statistics() -> dict[str, Any]:
        """Read-only snapshot of in-memory cache statistics."""
        stats = await service_adapters.cache_statistics()
        raw = cast(dict[str, Any], stats.model_dump(mode="json")) if hasattr(stats, "model_dump") else dict(stats)
        return present_cache_statistics(raw).model_dump(mode="json")
```

- [ ] **Step 4: Run clear-cache/cache-resource tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py tests/unit/mcp/test_resources.py tests/unit/mcp/test_cache_presenter.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add autopvs1_link/mcp/tools/cache_tools.py autopvs1_link/mcp/resources.py tests/unit/mcp/test_tool_runtime.py tests/unit/mcp/test_tools.py
git commit -m "feat: envelope cache mcp surface"
```

## Task 13: Update Documentation, Evaluation Checklist, and Generated Tool Catalog

**Files:**
- Modify: `scripts/generate_mcp_tool_catalog.py`
- Modify: `docs/mcp-tool-catalog.md`
- Modify: `docs/api.md`
- Modify: `README.md`
- Create: `docs/mcp-evaluation-checklist.md`
- Create: `tests/unit/mcp/test_tool_catalog_docs.py`

- [ ] **Step 1: Write failing generated-catalog drift test**

Create `tests/unit/mcp/test_tool_catalog_docs.py`:

```python
"""Tests that generated MCP tool catalog docs are current."""

from pathlib import Path

import pytest

from scripts.generate_mcp_tool_catalog import render


@pytest.mark.asyncio
async def test_mcp_tool_catalog_is_generated_from_current_server() -> None:
    expected = await render()
    actual = Path("docs/mcp-tool-catalog.md").read_text(encoding="utf-8")

    assert actual == expected
```

- [ ] **Step 2: Run the catalog drift test to verify it fails**

Run:

```bash
uv run pytest tests/unit/mcp/test_tool_catalog_docs.py -q
```

Expected: FAIL because the generated catalog has not been regenerated after schema changes, or because the generator does not yet include output schemas.

- [ ] **Step 3: Update the catalog generator to include output schemas**

Modify `scripts/generate_mcp_tool_catalog.py` so each tool section writes both input and output schemas:

```python
        schema = tool.parameters
        if schema:
            lines.append("#### Input Schema")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(schema, indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")
        output_schema = tool.output_schema
        if output_schema:
            lines.append("#### Output Schema")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(output_schema, indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")
```

Keep the header text:

```python
    lines.append(
        "Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`. "
        "Regenerate with `uv run python scripts/generate_mcp_tool_catalog.py`."
    )
```

- [ ] **Step 4: Update human-written MCP docs and evaluation checklist**

Modify `docs/api.md` MCP section to include these exact tool signatures:

```markdown
- `get_variant_pvs1_data(genome_build, variant_id)` - Research-use PVS1 analysis for an AutoPVS1 SNV/indel ID such as `X-82763936-A-T`.
- `get_cnv_pvs1_data(genome_build, cnv_id)` - Research-use PVS1 analysis for an AutoPVS1 CNV ID such as `17-15000000-20000000-DEL`.
- `search_variants(query, genome_build=None, limit=10, cursor=None, genome_version=None)` - Search AutoPVS1. Use `genome_build`; `genome_version` is a deprecated alias for one release.
- `get_server_capabilities()` - Compact MCP discovery payload with a pointer to `autopvs1-link://capabilities`.
- `clear_cache()` - Cache management. **Gated** by `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`; default disabled.
```

Add this envelope note to `docs/api.md`:

```markdown
All MCP tools return structured content with the standard envelope:
`ok`, `data`, `error`, and `meta`. `meta.research_use_only` is always `true`,
and `meta.recommended_citation` cites AutoPVS1. Expected validation and
upstream failures use `ok: false` with stable `error.code` values rather than
raw HTML, tracebacks, or JSON-RPC protocol failures.
```

Modify the README MCP tools list so it uses canonical `genome_build`:

```markdown
- `get_variant_pvs1_data(genome_build, variant_id)`
- `get_cnv_pvs1_data(genome_build, cnv_id)`
- `search_variants(query, genome_build, limit=10, cursor=None)`
- `get_server_capabilities()`
- `clear_cache()` - **gated** behind `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`
```

Create `docs/mcp-evaluation-checklist.md`:

```markdown
# MCP Evaluation Checklist

Use this checklist after MCP contract changes. Outputs are research-use
AutoPVS1 data, not clinical decision support.

- `get_variant_pvs1_data` with `{"genome_build":"hg19","variant_id":"X-82763936-A-T"}` returns `ok: true`, `data.pvs1_flowchart.final_strength: "Strong"`, `meta.research_use_only: true`, and cache metadata remains available through `autopvs1-link://cache/statistics`.
- `get_variant_pvs1_data` with `{"genome_build":"hg19","variant_id":"17-41276045-ACT-A"}` returns `ok: true`, `data.pvs1_flowchart.final_strength: "VeryStrong"`, and `data.variant_info.pli_score_display` is present when `pli_score` is present.
- `get_variant_pvs1_data` with `{"genome_build":"hg38","variant_id":"NOT-A-VARIANT"}` returns `ok: false`, `error.code: "invalid_variant_id"`, and no raw HTML, MDN URL, or traceback.
- `get_cnv_pvs1_data` with `{"genome_build":"hg19","cnv_id":"17:15000000-20000000:DEL"}` returns `ok: false`, `error.code: "invalid_cnv_id"`, and a suggestion to use `17-15000000-20000000-DEL`.
- `get_cnv_pvs1_data` with `{"genome_build":"hg19","cnv_id":"17-15000000-20000000-DEL"}` returns `ok: true` when the service adapter returns CNV data.
- `search_variants` with `{"query":"BRCA1 c.5266dupC","genome_build":"hg38"}` returns `ok: true`, `data.results: []`, and guidance in warnings or suggestions when upstream returns no results.
- `search_variants` with `{"query":"   "}` returns `ok: false` and `error.code: "invalid_search_query"`.
- `clear_cache` with `{}` returns `ok: false` and `error.code: "destructive_disabled"` unless `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true` is set.
```

- [ ] **Step 5: Regenerate the MCP tool catalog**

Run:

```bash
uv run python scripts/generate_mcp_tool_catalog.py
```

Expected:

```text
Wrote /home/bernt-popp/development/autopvs1-link/docs/mcp-tool-catalog.md
```

- [ ] **Step 6: Run documentation and catalog tests to verify they pass**

Run:

```bash
make format
uv run pytest tests/unit/mcp/test_tool_catalog_docs.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/generate_mcp_tool_catalog.py docs/mcp-tool-catalog.md docs/api.md README.md docs/mcp-evaluation-checklist.md tests/unit/mcp/test_tool_catalog_docs.py
git commit -m "docs: update mcp ergonomics contract"
```

## Task 14: Final Verification and Spec Acceptance Self-Review

**Files:**
- Modify only if final verification exposes issues in files touched by Tasks 1-13.

- [ ] **Step 1: Run the complete local CI check**

Run:

```bash
make ci-local
```

Expected: PASS for formatting, linting, line-count budget, mypy, and tests.

- [ ] **Step 2: Verify all Python modules remain under the repository line cap**

Run:

```bash
uv run python scripts/check_file_size.py
```

Expected: PASS with no module over 600 lines.

- [ ] **Step 3: Verify generated docs are current**

Run:

```bash
uv run pytest tests/unit/mcp/test_tool_catalog_docs.py -q
```

Expected: PASS.

- [ ] **Step 4: Inspect current diff for scoped changes**

Run:

```bash
git diff --stat HEAD
git diff --check HEAD
```

Expected: diff contains only MCP ergonomics, parser fixtures/tests, docs, and catalog changes. `git diff --check HEAD` reports no whitespace errors.

- [ ] **Step 5: Commit final verification fixes if any were required**

If Step 1, Step 2, Step 3, or Step 4 required a fix, commit only those focused fixes:

```bash
git add autopvs1_link tests docs scripts README.md
git commit -m "fix: complete mcp ergonomics verification"
```

Expected: no commit is needed when all checks passed without follow-up edits.

## Plan Self-Review Against Spec Acceptance Criteria

- No tested invalid input path leaks a bare HTTP 500, MDN URL, raw HTML, or traceback through MCP: covered by Task 10 variant invalid ID runtime test and Task 11 whitespace/conflict search runtime tests; Task 14 runs full CI.
- CNV format is discoverable from the tool description and capabilities resource: covered by Task 10 CNV tool description and Task 9 detailed capabilities `accepted_formats` and examples.
- `final_strength` is populated for POU3F4 `Strong`, BRCA1 `VeryStrong`, and tested MYO15A CNV `VeryStrong`: existing POU3F4 tests remain, Task 1 adds BRCA1/MYO15A fixtures, Task 2 adds BRCA1/MYO15A parser tests.
- Search trims input and rejects whitespace-only queries: covered by Task 5 validation tests and Task 11 runtime test.
- Empty search results include useful warnings or suggestions when the query appears malformed or unsupported: covered by Task 7 presenter test and Task 11 runtime test for `BRCA1 c.5266dupC`.
- All five configured method keys appear in the cache statistics resource even when counters are zero, and the key set does not change between reads in one process lifetime: covered by Task 8 presenter test and Task 12 cache resource runtime test.
- `search_variants` uses canonical `genome_build` in documentation and MCP schema, with alias handling documented: covered by Task 11 schema and runtime alias tests, plus Task 13 docs/catalog updates.
- `external_links.ClinVar` never points to `/variation/na` in MCP output: covered by Task 3 parser test and Task 6 presenter test that returns `ClinVar: null` plus an `invalid_external_link` warning.
- `clear_cache` remains disabled by default and accepts `{}`: covered by Task 12 disabled and enabled runtime tests.
- `make ci-local` passes: covered by Task 14.

Self-review scan result:

- Spec coverage: every acceptance criterion above maps to one or more tasks.
- Open-marker scan: no deferral markers or vague implementation phrases are intentionally present in this plan.
- Type consistency: `MCPWarning`, `MCPInputError`, `VariantMCPData`, `CNVMCPData`, `SearchMCPData`, `CompactCapabilitiesData`, `ClearCacheData`, `CacheStatisticsResource`, and concrete envelope class names are introduced before later tasks use them.
