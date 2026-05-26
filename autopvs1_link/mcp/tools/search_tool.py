"""MCP tool: search_variants."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import SearchMCPEnvelope
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.presenters.search import present_search
from autopvs1_link.mcp.validation import (
    normalize_genome_builds,
    normalize_limit_cursor,
    normalize_search_query,
)

GENOME_BUILD_SCHEMA = {
    "anyOf": [
        {"type": "string", "enum": ["hg19", "hg38"]},
        {"type": "null"},
    ]
}
NULLABLE_STRING_SCHEMA = {"anyOf": [{"type": "string"}, {"type": "null"}]}


def register(mcp: FastMCP) -> None:
    """Register the search_variants tool."""

    @mcp.tool(
        name="search_variants",
        title="Search AutoPVS1 Variants",
        output_schema=SearchMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def search_variants(
        query: Annotated[
            Any,
            Field(
                description="Gene symbol, HGVS text, or partial variant string.",
                json_schema_extra={"type": "string"},
            ),
        ],
        genome_build: Annotated[
            Any,
            Field(
                description="Canonical genome build for MCP search: hg19 or hg38.",
                json_schema_extra=GENOME_BUILD_SCHEMA,
            ),
        ] = None,
        limit: Annotated[
            Any,
            Field(
                description=(
                    "Maximum results to return; default 10. Values below 1 are treated "
                    "as 1 and values above 50 are treated as 50."
                ),
                json_schema_extra={"type": "integer"},
            ),
        ] = 10,
        cursor: Annotated[
            Any,
            Field(
                description="Opaque integer-offset cursor returned as next_cursor.",
                json_schema_extra=NULLABLE_STRING_SCHEMA,
            ),
        ] = None,
        genome_version: Annotated[
            Any,
            Field(
                description="Deprecated alias for genome_build; accepted for one release.",
                json_schema_extra=GENOME_BUILD_SCHEMA,
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Use this to search AutoPVS1 by gene symbol or variant text."""
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
                retryable=exc.response.status_code in {408, 429} or exc.response.status_code >= 500,
                suggestions=["Retry later or simplify the search query."],
            )
        except httpx.RequestError:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream was unreachable while searching variants.",
                retryable=True,
                suggestions=["Retry later or search by gene symbol only."],
            )
