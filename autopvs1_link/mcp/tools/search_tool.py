"""MCP tool: search_variants."""

from __future__ import annotations

from typing import Annotated, Literal

import httpx
from fastmcp import FastMCP
from pydantic import Field, SkipValidation

from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import SearchMCPEnvelope
from autopvs1_link.mcp.envelope import MCPWarning, ToolResponse, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.presenters.search import present_search
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope
from autopvs1_link.mcp.validation import (
    normalize_genome_builds,
    normalize_limit_cursor,
    normalize_search_query,
)


def _make_limit_clamped_warning(requested: int, bounded: int) -> MCPWarning:
    return MCPWarning(
        code="limit_clamped",
        message=(f"Requested limit={requested} was clamped to {bounded} (allowed range 1-50)."),
    )


GenomeBuildParam = SkipValidation[Literal["hg19", "hg38"] | None]
IntParam = SkipValidation[int]
SearchTextParam = SkipValidation[str]
NullableStringParam = SkipValidation[str | None]
ResponseModeParam = SkipValidation[Literal["ids_only", "summary", "standard", "full"]]
MetaModeParam = SkipValidation[Literal["full", "compact", "minimal"]]


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
            SearchTextParam,
            Field(
                description="Gene symbol, HGVS text, or partial variant string.",
            ),
        ],
        genome_build: Annotated[
            GenomeBuildParam,
            Field(
                description="Canonical genome build for MCP search: hg19 or hg38.",
            ),
        ] = None,
        limit: Annotated[
            IntParam,
            Field(
                description=(
                    "Maximum results to return; default 10. Values below 1 are treated "
                    "as 1 and values above 50 are treated as 50."
                ),
            ),
        ] = 10,
        cursor: Annotated[
            NullableStringParam,
            Field(
                description="Opaque pagination token returned as next_cursor; do not construct.",
            ),
        ] = None,
        genome_version: Annotated[
            GenomeBuildParam,
            Field(
                description="Deprecated alias for genome_build; accepted for one release.",
            ),
        ] = None,
        response_mode: Annotated[
            ResponseModeParam,
            Field(
                description="Response detail level: ids_only, summary, standard, or full.",
            ),
        ] = "standard",
        meta_mode: Annotated[
            MetaModeParam,
            Field(
                description="Metadata detail level: full, compact, or minimal.",
            ),
        ] = "full",
    ) -> ToolResponse:
        """Use this to search AutoPVS1 by gene symbol or variant text."""
        normalized_meta_mode: MetaMode = "full"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            normalized_query = normalize_search_query(query)
            normalized_build, build_warnings = normalize_genome_builds(genome_build, genome_version)
            normalized_limit, offset, requested_limit = normalize_limit_cursor(limit, cursor)
            if requested_limit != normalized_limit:
                build_warnings.append(
                    _make_limit_clamped_warning(requested_limit, normalized_limit)
                )
            result = await service_adapters.search_variants(normalized_query, normalized_build)
            data, warnings = present_search(
                result,
                query=normalized_query,
                genome_build=normalized_build,
                limit=normalized_limit,
                offset=offset,
                inherited_warnings=build_warnings,
                response_mode=normalized_response_mode,
            )
            return ok_envelope(
                data,
                warnings=warnings,
                meta_mode=normalized_meta_mode,
                compact_data=normalized_response_mode in ("summary", "ids_only"),
            )
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(exc, meta_mode=normalized_meta_mode)
        except MCPInputError as exc:
            return error_envelope(
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
                suggestions=exc.suggestions,
                details=exc.details or None,
                meta_mode=normalized_meta_mode,
            )
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while searching variants.",
                retryable=True,
                suggestions=["Retry later or search by gene symbol only."],
                meta_mode=normalized_meta_mode,
            )
        except httpx.HTTPStatusError as exc:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream could not complete the search request.",
                retryable=exc.response.status_code in {408, 429} or exc.response.status_code >= 500,
                suggestions=["Retry later or simplify the search query."],
                meta_mode=normalized_meta_mode,
            )
        except httpx.RequestError:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream was unreachable while searching variants.",
                retryable=True,
                suggestions=["Retry later or search by gene symbol only."],
                meta_mode=normalized_meta_mode,
            )
