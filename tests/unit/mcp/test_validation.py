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
    assert exc_info.value.details == {"corrected_id": "17-15000000-20000000-DEL"}


def test_normalize_cnv_id_rejects_colon_format_invalid_interval_without_correction() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_cnv_id("17:200-100:DEL")

    assert exc_info.value.code == "invalid_cnv_id"
    assert "start must be less than end" in str(exc_info.value)
    assert "Use 17-200-100-DEL." not in exc_info.value.suggestions


def test_normalize_cnv_id_rejects_invalid_interval() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_cnv_id("17-20000000-15000000-DEL")

    assert exc_info.value.code == "invalid_cnv_id"
    assert "start must be less than end" in str(exc_info.value)


def test_normalize_genome_builds_defaults_to_hg38() -> None:
    build, warnings = normalize_genome_builds(None, None)
    assert build == "hg38"
    assert warnings[0].code == "default_genome_build"
    assert "hg38" in warnings[0].message


def test_normalize_genome_builds_accepts_deprecated_alias_with_warning() -> None:
    build, warnings = normalize_genome_builds(None, "hg19")
    assert build == "hg19"
    assert warnings[0].code == "deprecated_genome_version"


def test_normalize_genome_builds_accepts_matching_deprecated_alias_with_warning() -> None:
    build, warnings = normalize_genome_builds("hg19", "hg19")
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


def test_normalize_limit_cursor_rejects_negative_cursor() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_limit_cursor(10, "-1")

    assert exc_info.value.code == "invalid_search_query"
    assert "zero or greater" in str(exc_info.value)
