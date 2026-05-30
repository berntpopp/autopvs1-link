"""MCP-specific input normalization and validation."""

from __future__ import annotations

import base64
import json
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
CNV_FORMAT_SUGGESTION = "Use AutoPVS1 CNV format such as 17-15000000-20000000-DEL."


def normalize_genome_build(value: object) -> str:
    if not isinstance(value, str):
        raise MCPInputError(
            code="invalid_genome_build",
            message="Genome build must be hg19 or hg38.",
            suggestions=["Use genome_build='hg38' unless the source variant coordinates are hg19."],
        )
    normalized = value.strip()
    if normalized not in VALID_GENOME_BUILDS:
        raise MCPInputError(
            code="invalid_genome_build",
            message="Genome build must be hg19 or hg38.",
            suggestions=["Use genome_build='hg38' unless the source variant coordinates are hg19."],
        )
    return normalized


def normalize_genome_builds(
    genome_build: object | None,
    genome_version: object | None,
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
    if canonical is None and deprecated is None:
        warnings.append(
            MCPWarning(
                code="default_genome_build",
                message="Search defaulted to genome_build='hg38'; confirm coordinates use hg38.",
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
    if int(start) >= int(end):
        raise _invalid_cnv_interval_error()
    return f"{chrom}-{start}-{end}-{cnv_type}"


def _invalid_cnv_interval_error() -> MCPInputError:
    return MCPInputError(
        code="invalid_cnv_id",
        message="CNV start must be less than end.",
        suggestions=[CNV_FORMAT_SUGGESTION],
    )


def normalize_cnv_id(cnv_id: str) -> str:
    value = cnv_id.strip().upper()
    match = CNV_ID_RE.fullmatch(value)
    if not match:
        correction = _cnv_correction(cnv_id)
        suggestions = [f"Use {correction}."] if correction else [CNV_FORMAT_SUGGESTION]
        raise MCPInputError(
            code="invalid_cnv_id",
            message="CNV IDs must use {chrom}-{start}-{end}-{TYPE}, with TYPE DEL or DUP.",
            suggestions=suggestions,
            details={"corrected_id": correction} if correction else None,
        )

    start = int(match.group("start"))
    end = int(match.group("end"))
    if start >= end:
        raise _invalid_cnv_interval_error()
    return value


def normalize_search_query(query: object) -> str:
    if not isinstance(query, str):
        raise MCPInputError(
            code="invalid_search_query",
            message="Search query must be text.",
            suggestions=[
                "Search by gene symbol, partial AutoPVS1 variant ID, or upstream-supported query."
            ],
        )
    value = query.strip()
    if not value:
        raise MCPInputError(
            code="invalid_search_query",
            message="Search query must not be empty.",
            suggestions=[
                "Search by gene symbol, partial AutoPVS1 variant ID, or upstream-supported query."
            ],
        )
    return value


def _invalid_search_pagination(message: str) -> MCPInputError:
    return MCPInputError(
        code="invalid_search_query",
        message=message,
        suggestions=[
            "Use limit as an integer from 1 to 50 and cursor as the returned next_cursor."
        ],
    )


def _invalid_search_cursor(message: str) -> MCPInputError:
    return MCPInputError(
        code="invalid_search_cursor",
        message=message,
        suggestions=[
            "Use the opaque next_cursor value returned by the previous search_variants call; "
            "omit cursor to reset to the first page.",
        ],
    )


def _encode_cursor(offset: int) -> str:
    """Encode an integer offset as a base64url JSON payload (no padding)."""
    payload = json.dumps({"offset": int(offset)}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(cursor: str) -> int:
    """Decode an opaque cursor to its integer offset, raising on malformed input."""
    if not isinstance(cursor, str) or not cursor:
        raise _invalid_search_cursor("Search cursor must be a non-empty opaque string.")
    if cursor.isdigit():
        # Reject the legacy integer-offset form so callers cannot construct cursors.
        raise _invalid_search_cursor(
            "Search cursor must be the opaque next_cursor returned by search_variants."
        )
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        decoded_bytes = base64.urlsafe_b64decode(padded.encode())
    except (ValueError, TypeError) as exc:
        raise _invalid_search_cursor("Search cursor is not valid base64url.") from exc
    try:
        payload = json.loads(decoded_bytes.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _invalid_search_cursor("Search cursor payload is not valid JSON.") from exc
    if not isinstance(payload, dict) or "offset" not in payload:
        raise _invalid_search_cursor("Search cursor payload must contain an integer offset.")
    raw_offset = payload["offset"]
    if not isinstance(raw_offset, int) or isinstance(raw_offset, bool):
        raise _invalid_search_cursor("Search cursor offset must be an integer.")
    if raw_offset < 0:
        raise _invalid_search_cursor("Search cursor offset must be zero or greater.")
    return raw_offset


def _normalize_limit(limit: object) -> int:
    if isinstance(limit, int) and not isinstance(limit, bool):
        return limit
    if isinstance(limit, str):
        value = limit.strip()
        if value:
            try:
                return int(value)
            except ValueError as exc:
                raise _invalid_search_pagination("Search limit must be an integer.") from exc
    raise _invalid_search_pagination("Search limit must be an integer.")


def normalize_limit_cursor(limit: object, cursor: object | None) -> tuple[int, int, int]:
    """Return ``(bounded_limit, offset, requested_limit)``.

    ``requested_limit`` is the caller's pre-clamp value so callers can emit a
    ``limit_clamped`` warning when ``bounded_limit != requested_limit``.
    ``cursor`` is now an opaque base64url-encoded token; callers must pass
    through the ``next_cursor`` returned by a previous search call.
    """
    requested_limit = _normalize_limit(limit)
    bounded_limit = max(1, min(requested_limit, 50))
    if cursor is None:
        return bounded_limit, 0, requested_limit
    if not isinstance(cursor, str):
        raise _invalid_search_cursor("Search cursor must be a non-empty opaque string.")
    offset = _decode_cursor(cursor)
    return bounded_limit, offset, requested_limit
