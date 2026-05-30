"""MCP presenter for search results."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.contracts import SearchMCPData, SearchPaginationMCP
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.mcp.mode_validation import ResponseMode, normalize_response_mode
from autopvs1_link.mcp.validation import _encode_cursor

HGVS_LIKE_RE = re.compile(
    r"((?:^|\s)[A-Z][A-Z0-9-]*(?:\s+|\s*:\s*)c\.)"
    r"|(\bN[MR]_\d+(?:\.\d+)?(?:\([A-Z0-9-]+\))?:[cn]\.)",
    re.IGNORECASE,
)
TRANSCRIPT_GENE_HGVS_RE = re.compile(
    r"\bN[MR]_\d+(?:\.\d+)?\(([A-Z0-9-]+)\):[cn]\.",
    re.IGNORECASE,
)
GENE_HGVS_RE = re.compile(
    r"(?:^|\s)([A-Z][A-Z0-9-]*)(?:\s+|\s*:\s*)c\.",
    re.IGNORECASE,
)


def _dump_result(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)


def _normalize_response_mode(response_mode: Any) -> ResponseMode:
    return normalize_response_mode(response_mode)


def _empty_search_suggestions(query: str) -> list[str]:
    transcript_gene_match = TRANSCRIPT_GENE_HGVS_RE.search(query)
    gene_match = GENE_HGVS_RE.search(query)
    if transcript_gene_match:
        gene = transcript_gene_match.group(1)
    elif gene_match:
        gene = gene_match.group(1)
    else:
        gene = "the gene symbol"
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
    response_mode: Any = "standard",
) -> tuple[SearchMCPData, list[MCPWarning]]:
    """Shape search results into a bounded MCP page."""
    mode = _normalize_response_mode(response_mode)
    raw = parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else dict(parsed)
    all_results = [_dump_result(result) for result in raw.get("results", [])]
    total_count = len(all_results)
    page = all_results[offset : offset + limit]
    next_offset = offset + limit
    has_more = next_offset < total_count
    next_cursor = _encode_cursor(next_offset) if has_more else None
    previous_cursor = _encode_cursor(max(0, offset - limit)) if offset > 0 else None
    warnings = list(inherited_warnings)
    suggestions: list[str] = []

    if has_more:
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

    pagination = SearchPaginationMCP(
        previous_cursor=previous_cursor,
        next_cursor=next_cursor,
        has_more=has_more,
        offset=offset,
        total_count_kind="upstream_page",
    )

    if mode == "summary":
        emitted_results: list[dict[str, Any]] = []
        emitted_suggestions = suggestions
    elif mode == "ids_only":
        emitted_results = [{"variant_id": row["variant_id"], "url": row["url"]} for row in page]
        emitted_suggestions = []
    else:
        emitted_results = page
        emitted_suggestions = suggestions

    return (
        SearchMCPData(
            query=query,
            genome_build=genome_build,
            total_count=total_count,
            returned_count=len(page),
            pagination=pagination,
            results=emitted_results,
            suggestions=emitted_suggestions,
        ),
        warnings,
    )
