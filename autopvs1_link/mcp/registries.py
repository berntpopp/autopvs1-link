"""Source-of-truth registries for MCP error codes, warning codes, payload modes.

Capabilities presenters import from here so the wire-level enumerations stay
in lockstep with what tools actually raise. A drift test in
``tests/unit/mcp/test_registries.py`` scans every MCPInputError / MCPWarning
construction under ``autopvs1_link/mcp/`` and fails if a code is raised but
not declared here.
"""

from __future__ import annotations

import functools
import hashlib
import json
from typing import TypedDict

from autopvs1_link.mcp.server_info import SERVER_VERSION


class PayloadModeSpec(TypedDict):
    """Per-response-mode metadata exposed on capabilities."""

    char_budget: int
    note: str


KNOWN_ERROR_CODES: dict[str, str] = {
    "invalid_variant_id": "Variant ID malformed; expect CHROM-POS-REF-ALT.",
    "invalid_cnv_id": "CNV ID malformed; expect CHROM-START-END-DEL|DUP.",
    "invalid_genome_build": "Build must be hg19 or hg38.",
    "invalid_search_query": "Query empty or malformed (limit handled separately).",
    "invalid_search_cursor": "Cursor is malformed; reset by omitting cursor.",
    "invalid_bulk_input": "items list missing or malformed.",
    "invalid_response_mode": "response_mode not a documented enum value.",
    "invalid_meta_mode": "meta_mode not a documented enum value.",
    "not_found": "Upstream returned 404 for the requested ID.",
    "parse_error": "Upstream HTML did not match expected schema.",
    "upstream_timeout": "Upstream timed out; retry with backoff.",
    "upstream_unavailable": "Upstream unreachable or HTTP 5xx.",
    "destructive_disabled": ("clear_cache requires AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true."),
    "internal_error": "Unexpected server error; retry once with backoff.",
    "requires_disambiguation": (
        "Auto-resolution of an rsID/HGVS input returned multiple "
        "candidates; caller must pick one. details.candidates carries "
        "id + spdi + allele_key + resource_uri rows."
    ),
    "external_resolver_unavailable": (
        "Ensembl Variant Recoder was unreachable, rate-limited, or "
        "returned a 5xx while resolving an rsID/HGVS input. Retryable; "
        "callers can re-issue or supply a pre-resolved canonical "
        "CHROM-POS-REF-ALT variant_id."
    ),
}

KNOWN_WARNING_CODES: dict[str, str] = {
    "default_genome_build": "Search defaulted to genome_build='hg38'.",
    "deprecated_genome_version": "genome_version param is deprecated.",
    "invalid_external_link": "Upstream link replaced with null.",
    "limit_clamped": "Search limit clamped to allowed range.",
    "pvs1_not_applicable": "Upstream returned a non-scorable sentinel.",
    "search_results_truncated": "Page truncated; use next_cursor.",
    "unsupported_hgvs_like_search": "HGVS-like text returned zero results.",
    "auto_resolved": (
        "An rsID/HGVS variant_id was auto-resolved to canonical SPDI via "
        "the Ensembl Variant Recoder REST API. The warning carries the "
        "original input, the resolved id, the detected input form, and "
        "the resolver source so consumers can audit the resolution path."
    ),
}

PAYLOAD_MODES: dict[str, PayloadModeSpec] = {
    "ids_only": {
        "char_budget": 500,
        "note": (
            "Lowest-bandwidth lookup tier: emits only the upstream "
            "identifier, genome_build, and source_url so callers can "
            "round-trip IDs through batch screens without paying for the "
            "decision tree or disease-mechanism rows."
        ),
    },
    "summary": {
        "char_budget": 1500,
        "note": "IDs + final strength only.",
    },
    "standard": {
        "char_budget": 6000,
        "note": "Full presented payload (default).",
    },
    "full": {
        "char_budget": 12000,
        "note": "Adds *_raw audit-trail fields.",
    },
}


@functools.cache
def capabilities_version() -> str:
    """Return a stable 16-char sha256 prefix over the full published surface.

    Wired into ``CompactCapabilitiesData.capabilities_version`` and the
    detailed capabilities resource so clients can cache discovery output
    and invalidate when ANY published capability changes. The hash now
    blends the registries (error/warning codes, payload modes) AND the
    tool surface (tool_summaries, canonical_parameters, compact_workflow,
    performance block) so an LLM-facing edit to a purpose string or an
    example invocation invalidates downstream caches keyed on the hash.

    Regression: a prior implementation hashed only the registries; tool
    surface mutations (purpose strings, examples gaining response_mode)
    slipped past and cache-aware clients never saw the change.

    The capabilities presenters are lazy-imported to break the import
    cycle (capabilities.py imports this function for its
    ``capabilities_version`` field; this function in turn reads the
    surface constants defined alongside the presenters).

    Memoized with ``functools.cache``: the inputs are module-level
    immutables in production. Tests must call
    ``capabilities_version.cache_clear()`` after monkeypatching any
    contributing input.
    """
    from autopvs1_link.mcp.presenters.capabilities import (
        _CANONICAL_PARAMETERS,
        _COMPACT_WORKFLOW,
        _PERFORMANCE_BLOCK,
        _TOOL_SUMMARIES,
    )

    blob = json.dumps(
        [
            SERVER_VERSION,
            KNOWN_ERROR_CODES,
            KNOWN_WARNING_CODES,
            PAYLOAD_MODES,
            _TOOL_SUMMARIES,
            _CANONICAL_PARAMETERS,
            _COMPACT_WORKFLOW,
            _PERFORMANCE_BLOCK,
        ],
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
