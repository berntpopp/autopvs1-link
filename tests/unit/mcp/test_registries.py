"""Source-of-truth registries plus drift detection."""

from __future__ import annotations

import re
from pathlib import Path

from autopvs1_link.mcp.registries import (
    KNOWN_ERROR_CODES,
    KNOWN_WARNING_CODES,
    PAYLOAD_MODES,
)

_MCP_ROOT = Path(__file__).resolve().parents[3] / "autopvs1_link" / "mcp"


def test_known_error_codes_cover_every_mcp_input_error_raise_site() -> None:
    """Every site under autopvs1_link/mcp/ that emits an error code must
    declare that code in KNOWN_ERROR_CODES. Otherwise capabilities lies
    to callers and clients see an undocumented code on the wire.

    The scanner covers three emission paths:
    1. ``MCPInputError(code="...", ...)`` — direct user-input validation.
    2. ``error_envelope(code="...", ...)`` — tool-level error wrapping.
    3. ``InvalidMCPModeError(code="...", ...)`` — response/meta mode validation.
    """
    patterns = [
        re.compile(r"MCPInputError\(\s*\n?\s*[^)]*?code=\"([a-z_]+)\""),
        re.compile(r"error_envelope\(\s*\n?\s*[^)]*?code=\"([a-z_]+)\""),
        re.compile(r"InvalidMCPModeError\(\s*\n?\s*[^)]*?code=\"([a-z_]+)\""),
    ]
    found: set[str] = set()
    for path in _MCP_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            found.update(pattern.findall(text))
    missing = found - set(KNOWN_ERROR_CODES)
    assert not missing, f"error codes emitted but not registered: {sorted(missing)}"


def test_known_warning_codes_cover_every_mcp_warning_construction() -> None:
    """Every MCPWarning(code='X', ...) construction must declare X in
    KNOWN_WARNING_CODES, otherwise capabilities lies to callers."""
    pattern = re.compile(r"MCPWarning\(\s*\n?\s*code=\"([a-z_]+)\"")
    found: set[str] = set()
    for path in _MCP_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        found.update(pattern.findall(text))
    missing = found - set(KNOWN_WARNING_CODES)
    assert not missing, f"warning codes constructed but not registered: {sorted(missing)}"


def test_payload_modes_documents_every_response_mode() -> None:
    assert set(PAYLOAD_MODES) == {"ids_only", "summary", "standard", "full"}
    for _mode, meta in PAYLOAD_MODES.items():
        assert isinstance(meta["char_budget"], int)
        assert isinstance(meta["note"], str) and meta["note"]


def test_payload_modes_budgets_grow_monotonically_with_detail() -> None:
    """ids_only < summary < standard < full — the budget ordering encodes
    the bandwidth ladder clients pick from."""
    budgets = [PAYLOAD_MODES[m]["char_budget"] for m in ("ids_only", "summary", "standard", "full")]
    assert budgets == sorted(budgets), budgets
    assert len(set(budgets)) == len(budgets), "budgets must be distinct"


def test_known_error_codes_messages_are_one_line_strings() -> None:
    for code, message in KNOWN_ERROR_CODES.items():
        assert isinstance(message, str) and "\n" not in message, code


def _emitted_error_subcodes() -> set[str]:
    """Every code literally emitted under autopvs1_link/mcp/ (same scan as the
    KNOWN_ERROR_CODES drift guard), so the mapping test derives its subject set
    from the source, never a hardcoded list."""
    patterns = [
        re.compile(r'MCPInputError\(\s*\n?\s*[^)]*?code="([a-z_]+)"'),
        re.compile(r'error_envelope\(\s*\n?\s*[^)]*?code="([a-z_]+)"'),
        re.compile(r'InvalidMCPModeError\(\s*\n?\s*[^)]*?code="([a-z_]+)"'),
        re.compile(r'_err\(\s*\n?\s*"([a-z_]+)"'),
    ]
    found: set[str] = set()
    for path in _MCP_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            found.update(pattern.findall(text))
    return found


def test_every_emitted_subcode_has_an_explicit_canonical_mapping() -> None:
    """Response-Envelope Standard v1 closes ``error_code`` to six values; the wire
    canonicalises every granular subcode onto one of them. ``canonical_error_code``
    backstops an unknown code to ``internal``, so testing the FUNCTION alone would
    pass even after a mapping is deleted (the subcode would silently reclassify).
    This asserts an EXPLICIT entry in ``_CANONICAL_BY_SUBCODE`` for every code the
    source actually emits, and that every mapping target is one of the six.
    """
    from autopvs1_link.mcp.registries import (
        _CANONICAL_BY_SUBCODE,
        CANONICAL_ERROR_CODES,
    )

    assert {
        "invalid_input",
        "not_found",
        "ambiguous_query",
        "upstream_unavailable",
        "rate_limited",
        "internal",
    } == CANONICAL_ERROR_CODES
    # Every mapping target is inside the closed enum.
    assert set(_CANONICAL_BY_SUBCODE.values()) <= CANONICAL_ERROR_CODES
    # Every registered code AND every code the source emits is EXPLICITLY mapped.
    unmapped = (set(KNOWN_ERROR_CODES) | _emitted_error_subcodes()) - set(_CANONICAL_BY_SUBCODE)
    assert not unmapped, f"error codes with no explicit canonical mapping: {sorted(unmapped)}"


def test_canonical_error_code_backstops_an_unmapped_code_to_internal() -> None:
    """Prove the guard by breaking it: an unmapped/future subcode must still
    resolve to a canonical value (``internal``), never leak a non-enum code."""
    from autopvs1_link.mcp.registries import canonical_error_code

    assert canonical_error_code("some_future_unmapped_code") == "internal"


def test_known_warning_codes_messages_are_one_line_strings() -> None:
    for code, message in KNOWN_WARNING_CODES.items():
        assert isinstance(message, str) and "\n" not in message, code
