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
