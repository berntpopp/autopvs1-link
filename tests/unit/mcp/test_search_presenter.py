"""Tests for search MCP pagination and guidance."""

import base64
import json

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
    assert data.pagination.next_cursor is not None
    assert data.pagination.has_more is True
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
    assert data.pagination.next_cursor is None
    assert data.pagination.has_more is False
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


def test_present_search_adds_guidance_for_gene_colon_hgvs_like_query() -> None:
    parsed = AutoPVS1SearchResults(query="BRCA1:c.5266dupC", genome_version="hg38", results=[])

    data, warnings = present_search(
        parsed,
        query="BRCA1:c.5266dupC",
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


def test_present_search_adds_guidance_for_gene_colon_space_hgvs_like_query() -> None:
    query = "BRCA1: c.5266dupC"
    parsed = AutoPVS1SearchResults(query=query, genome_version="hg38", results=[])

    data, warnings = present_search(
        parsed,
        query=query,
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


def test_present_search_adds_guidance_for_gene_space_colon_space_hgvs_like_query() -> None:
    query = "BRCA1 : c.5266dupC"
    parsed = AutoPVS1SearchResults(query=query, genome_version="hg38", results=[])

    data, warnings = present_search(
        parsed,
        query=query,
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


def test_present_search_adds_guidance_for_transcript_gene_hgvs_like_query() -> None:
    query = "NM_000059.4(BRCA2):c.5946delT"
    parsed = AutoPVS1SearchResults(query=query, genome_version="hg38", results=[])

    data, warnings = present_search(
        parsed,
        query=query,
        genome_build="hg38",
        limit=10,
        offset=0,
        inherited_warnings=[],
    )

    assert data.total_count == 0
    assert data.results == []
    assert data.suggestions == [
        "Search for BRCA2 only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]
    assert warnings[0].code == "unsupported_hgvs_like_search"


def test_present_search_uses_generic_guidance_for_transcript_only_hgvs_like_query() -> None:
    query = "NM_000059.4:c.5946delT"
    parsed = AutoPVS1SearchResults(query=query, genome_version="hg38", results=[])

    data, warnings = present_search(
        parsed,
        query=query,
        genome_build="hg38",
        limit=10,
        offset=0,
        inherited_warnings=[],
    )

    assert data.total_count == 0
    assert data.results == []
    assert data.suggestions == [
        "Search for the gene symbol only.",
        "Use a resolved AutoPVS1 variant ID when known.",
        "Confirm genome build before scoring.",
    ]
    assert warnings[0].code == "unsupported_hgvs_like_search"


def test_present_search_summary_keeps_counts_and_omits_result_rows() -> None:
    parsed = AutoPVS1SearchResults(
        query="BRCA1",
        genome_version="hg38",
        results=[_result(index) for index in range(3)],
    )

    data, warnings = present_search(
        parsed,
        query="BRCA1",
        genome_build="hg38",
        limit=2,
        offset=0,
        inherited_warnings=[],
        response_mode="summary",
    )

    payload = data.model_dump(mode="json")
    assert payload["query"] == "BRCA1"
    assert payload["genome_build"] == "hg38"
    assert payload["total_count"] == 3
    assert payload["returned_count"] == 2
    assert payload["pagination"]["next_cursor"] is not None
    assert payload["pagination"]["has_more"] is True
    assert payload["ordering"] == "upstream"
    assert payload["results"] == []
    assert warnings[0].code == "search_results_truncated"


def test_present_search_full_preserves_result_rows() -> None:
    parsed = AutoPVS1SearchResults(
        query="BRCA1",
        genome_version="hg38",
        results=[_result(index) for index in range(3)],
    )

    data, warnings = present_search(
        parsed,
        query="BRCA1",
        genome_build="hg38",
        limit=2,
        offset=0,
        inherited_warnings=[],
        response_mode="full",
    )

    assert [row["variant_id"] for row in data.results] == ["17-0-A-T", "17-1-A-T"]
    assert warnings[0].code == "search_results_truncated"


def _make_results(n: int) -> dict[str, object]:
    return {
        "query": "POU3F4",
        "genome_version": "hg38",
        "results": [
            {
                "variant_id": f"X-{i}-A-T",
                "gene": "POU3F4",
                "variant_type": "Nonsense",
                "genome_build": "hg38",
                "url": f"https://autopvs1.bgi.com/variant/hg38/X-{i}-A-T",
            }
            for i in range(n)
        ],
    }


def test_search_pagination_block_carries_opaque_cursors_and_offset_echo() -> None:
    parsed = _make_results(25)
    data, _ = present_search(
        parsed,
        query="POU3F4",
        genome_build="hg38",
        limit=10,
        offset=0,
        inherited_warnings=[],
    )
    payload = data.model_dump(mode="json")
    pagination = payload["pagination"]
    assert pagination["offset"] == 0
    assert pagination["has_more"] is True
    assert pagination["total_count_kind"] == "upstream_page"
    next_cursor = pagination["next_cursor"]
    assert next_cursor is not None
    # opaque: not a bare integer string
    assert not next_cursor.isdigit()
    decoded = json.loads(
        base64.urlsafe_b64decode(next_cursor + "=" * (-len(next_cursor) % 4)).decode()
    )
    assert decoded == {"offset": 10}


def test_search_pagination_has_previous_cursor_on_subsequent_pages() -> None:
    parsed = _make_results(25)
    data, _ = present_search(
        parsed,
        query="POU3F4",
        genome_build="hg38",
        limit=10,
        offset=10,
        inherited_warnings=[],
    )
    pagination = data.model_dump(mode="json")["pagination"]
    assert pagination["offset"] == 10
    previous = pagination["previous_cursor"]
    assert previous is not None
    decoded = json.loads(base64.urlsafe_b64decode(previous + "=" * (-len(previous) % 4)).decode())
    assert decoded == {"offset": 0}


def test_search_pagination_has_no_next_cursor_on_last_page() -> None:
    parsed = _make_results(5)
    data, _ = present_search(
        parsed,
        query="POU3F4",
        genome_build="hg38",
        limit=10,
        offset=0,
        inherited_warnings=[],
    )
    pagination = data.model_dump(mode="json")["pagination"]
    assert pagination["next_cursor"] is None
    assert pagination["has_more"] is False
    assert pagination["previous_cursor"] is None
