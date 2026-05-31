"""Tests for MCP-only input validation and normalization."""

import base64
import json

import pytest

from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.validation import (
    _decode_cursor,
    _encode_cursor,
    classify_variant_input,
    normalize_cnv_id,
    normalize_genome_builds,
    normalize_limit_cursor,
    normalize_search_query,
    normalize_variant_id,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        # Canonical SPDI with chrom variants and chr prefix.
        ("X-82763936-A-T", "canonical"),
        ("chr1-12345-A-T", "canonical"),
        ("MT-100-G-C", "canonical"),
        ("M-100-G-C", "canonical"),
        # Leading/trailing whitespace tolerated.
        ("  17-12345-AC-A  ", "canonical"),
        # rsID — lowercase required per dbSNP FAQ.
        ("rs80357906", "rsid"),
        ("RS80357906", "unknown"),
        ("rs0", "rsid"),
        ("rs", "unknown"),
        ("rs1234567890123", "unknown"),
        # HGVS coding: NM_/NR_/LRG_ with underscore; ENST without; gene parenthetical.
        ("NM_000059.3:c.5266dup", "hgvs_c"),
        ("NM_007294.4(BRCA1):c.5266dup", "hgvs_c"),
        ("ENST00000357654:c.5266dup", "hgvs_c"),
        ("NR_002196.2:n.123A>G", "hgvs_c"),
        # HGVS protein.
        ("NP_000050.2:p.Glu1756fs", "hgvs_p"),
        ("ENSP00000350283:p.Glu1756fs", "hgvs_p"),
        # HGVS genomic with and without GRCh build wrapper.
        ("NC_000017.10:g.41197709C>A", "hgvs_g"),
        ("GRCh38(NC_000017.11):g.43091983C>A", "hgvs_g"),
        # Whitespace inside is rejected (HGVS forbids).
        ("rs 12345", "unknown"),
        ("NM_000059.3:c.5266 dup", "unknown"),
        # Empty / non-string / junk.
        ("", "unknown"),
        ("   ", "unknown"),
        ("not a variant", "unknown"),
        ("BRCA1", "unknown"),
    ],
)
def test_classify_variant_input_covers_canonical_rsid_hgvs_and_junk(
    text: str, expected: str
) -> None:
    assert classify_variant_input(text) == expected


def test_classify_variant_input_rejects_non_string() -> None:
    assert classify_variant_input(None) == "unknown"
    assert classify_variant_input(12345) == "unknown"


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
    assert normalize_limit_cursor(10, None) == (10, 0, 10)
    assert normalize_limit_cursor(99, _encode_cursor(5)) == (50, 5, 99)
    assert normalize_limit_cursor(0, None) == (1, 0, 0)


def test_normalize_limit_cursor_returns_requested_limit_for_clamp_warning() -> None:
    # Caller relies on requested != bounded to emit limit_clamped.
    bounded, offset, requested = normalize_limit_cursor(200, None)
    assert (bounded, offset, requested) == (50, 0, 200)


def test_normalize_limit_cursor_rejects_non_integer_cursor() -> None:
    with pytest.raises(MCPInputError) as exc_info:
        normalize_limit_cursor(10, "abc")

    assert exc_info.value.code == "invalid_search_cursor"
    assert "cursor" in str(exc_info.value)


def test_normalize_limit_cursor_rejects_negative_cursor() -> None:
    bad = base64.urlsafe_b64encode(json.dumps({"offset": -1}).encode()).decode().rstrip("=")
    with pytest.raises(MCPInputError) as exc_info:
        normalize_limit_cursor(10, bad)

    assert exc_info.value.code == "invalid_search_cursor"
    assert "zero or greater" in str(exc_info.value)


def test_cursor_round_trip_through_encode_decode() -> None:
    encoded = _encode_cursor(42)
    assert isinstance(encoded, str)
    # base64url with no padding
    assert "=" not in encoded
    assert _decode_cursor(encoded) == 42


def test_decode_cursor_rejects_raw_integer_offset_string() -> None:
    """Integer-offset cursors are no longer accepted; they are not opaque."""
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor("10")
    assert exc.value.code == "invalid_search_cursor"


def test_decode_cursor_rejects_malformed_base64() -> None:
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor("not-base64!")
    assert exc.value.code == "invalid_search_cursor"


def test_cursor_roundtrips_and_is_transparent_offset() -> None:
    """The cursor is honestly a transparent base64url JSON offset token."""
    from autopvs1_link.mcp.validation import _decode_cursor, _encode_cursor

    cur = _encode_cursor(40)
    assert _decode_cursor(cur) == 40
    # Transparency contract: it really is base64url JSON of {"offset": 40}.
    import base64
    import json

    padded = cur + "=" * (-len(cur) % 4)
    assert json.loads(base64.urlsafe_b64decode(padded.encode()).decode()) == {"offset": 40}


def test_decode_cursor_rejects_base64_without_offset_key() -> None:
    bad = base64.urlsafe_b64encode(json.dumps({"page": 1}).encode()).decode().rstrip("=")
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor(bad)
    assert exc.value.code == "invalid_search_cursor"


def test_decode_cursor_rejects_negative_offset() -> None:
    bad = base64.urlsafe_b64encode(json.dumps({"offset": -1}).encode()).decode().rstrip("=")
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor(bad)
    assert exc.value.code == "invalid_search_cursor"


def test_decode_cursor_rejects_empty_string() -> None:
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor("")
    assert exc.value.code == "invalid_search_cursor"


def test_decode_cursor_rejects_base64_decoding_to_non_json() -> None:
    """Valid base64url that decodes to bytes that aren't JSON must error."""
    bad = base64.urlsafe_b64encode(b"not json bytes").decode().rstrip("=")
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor(bad)
    assert exc.value.code == "invalid_search_cursor"


@pytest.mark.parametrize(
    "bad_offset_value",
    [
        True,  # bool is an int subclass - must be rejected to keep semantics tight.
        False,
        "5",  # string offset.
        1.5,  # float offset.
        None,  # null offset.
    ],
)
def test_decode_cursor_rejects_non_integer_offset(bad_offset_value: object) -> None:
    bad = (
        base64.urlsafe_b64encode(json.dumps({"offset": bad_offset_value}).encode())
        .decode()
        .rstrip("=")
    )
    with pytest.raises(MCPInputError) as exc:
        _decode_cursor(bad)
    assert exc.value.code == "invalid_search_cursor"


def test_normalize_limit_cursor_accepts_opaque_cursor() -> None:
    bounded, offset, requested = normalize_limit_cursor(10, _encode_cursor(20))
    assert (bounded, offset, requested) == (10, 20, 10)
