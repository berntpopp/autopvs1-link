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

ERROR_NEXT_ACTIONS: dict[str, list[str]] = {
    "invalid_variant_id": [
        "Re-call with variant_id in CHROM-POS-REF-ALT form (X-82763936-A-T).",
        "Call search_variants to discover an AutoPVS1 variant_id for a gene or HGVS string.",
    ],
    "invalid_cnv_id": [
        "Re-call with cnv_id in CHROM-START-END-DEL|DUP form (17-15000000-20000000-DEL).",
    ],
    "invalid_genome_build": [
        "Re-call with genome_build='hg19' or genome_build='hg38'.",
    ],
    "invalid_search_query": [
        "Use a non-empty query; gene symbols (BRCA1) and partial variant IDs are supported.",
    ],
    "invalid_search_cursor": [
        "Drop the cursor (cursor=None) to start from page 1.",
        "Re-page using data.pagination.next_cursor from a prior call.",
    ],
    "invalid_bulk_input": [
        "Pass items as a JSON list of 1-10 objects matching the per-item schema.",
    ],
    "invalid_response_mode": [
        "Use one of: ids_only, summary, standard, full.",
        "Omit response_mode to accept the LLM-first default for this tool.",
    ],
    "invalid_meta_mode": [
        "Use one of: full, compact, minimal.",
    ],
    "not_found": [
        "Confirm the identifier exists upstream; search_variants resolves gene or text queries.",
        "Try the other genome_build if the source coordinate is ambiguous between hg19 and hg38.",
    ],
    "requires_disambiguation": [
        "Pick one of error.details.candidates[*].id (carries spdi + allele_key + resource_uri) and re-call.",
    ],
    "external_resolver_unavailable": [
        "Retry after meta.retry_after_ms; Ensembl Variant Recoder may be transiently unreachable.",
        "Bypass the resolver by passing a canonical CHROM-POS-REF-ALT variant_id.",
    ],
    "upstream_timeout": [
        "Retry after meta.retry_after_ms; AutoPVS1 cold calls can take ~3-4s.",
        "Call get_server_health(check_upstream=true) to confirm AutoPVS1 is reachable.",
    ],
    "upstream_unavailable": [
        "Retry after meta.retry_after_ms; AutoPVS1 may be temporarily down or rate-limiting.",
        "Call get_server_health(check_upstream=true) to confirm AutoPVS1 is reachable.",
    ],
    "parse_error": [
        "Confirm the identifier exists in AutoPVS1; the HTML schema may have changed for new edge cases.",
        "Report the failing input so the parser can be adjusted.",
    ],
    "destructive_disabled": [
        "Set AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true and restart the server (administrative environments only).",
    ],
    "internal_error": [
        "Retry once with backoff; report a reproducer if the error persists.",
    ],
}


def next_actions_for(code: str) -> list[str] | None:
    """Return canonical recovery hints for ``code``, or None if absent.

    Surfaced on ``meta.next_actions`` of every error envelope so a
    failing LLM dispatcher does not need to re-discover the tool surface
    via ToolSearch to recover. ``None`` keeps the meta field absent for
    unregistered codes (forward-compatible).
    """
    return ERROR_NEXT_ACTIONS.get(code)


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
    "upstream_format_unrecognized": (
        "AutoPVS1 returned a final PVS1 strength value that is not in the "
        "recognized set. The scraped upstream HTML format may have changed; "
        "treat this result as unverified pending a parser review."
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
            ERROR_NEXT_ACTIONS,
            _TOOL_SUMMARIES,
            _CANONICAL_PARAMETERS,
            _COMPACT_WORKFLOW,
            _PERFORMANCE_BLOCK,
        ],
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
