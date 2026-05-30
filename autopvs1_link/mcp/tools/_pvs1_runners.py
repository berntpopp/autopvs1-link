"""Internal per-item PVS1 runners shared by single and bulk MCP tools."""

from __future__ import annotations

from typing import Any

import httpx

from autopvs1_link.api.autopvs1_urls import cnv_url, variant_url
from autopvs1_link.config import settings
from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.contracts import CNVMCPData, VariantMCPData
from autopvs1_link.mcp.envelope import MCPError, MCPWarning
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.mode_validation import ResponseMode
from autopvs1_link.mcp.presenters.variant import present_cnv, present_variant
from autopvs1_link.mcp.resolution import resolve_or_normalize_variant_id
from autopvs1_link.mcp.validation import normalize_cnv_id, normalize_genome_build


def _retryable(status_code: int) -> bool:
    return status_code in {408, 429} or status_code >= 500


def _err(
    code: str,
    message: str,
    retryable: bool,
    suggestions: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> MCPError:
    return MCPError(
        code=code,
        message=message,
        retryable=retryable,
        suggestions=suggestions or [],
        details=details,
    )


def _from_input_error(exc: MCPInputError) -> MCPError:
    return _err(
        code=exc.code,
        message=str(exc),
        retryable=exc.retryable,
        suggestions=exc.suggestions,
        details=exc.details or None,
    )


async def run_variant_pvs1(
    *,
    genome_build: str,
    variant_id: str,
    response_mode: ResponseMode,
    include_unmet: Any,
) -> tuple[VariantMCPData | None, list[MCPWarning], MCPError | None]:
    """Score one variant. Return (data, warnings, error) — exactly one of data/error is non-None.

    Auto-resolves non-canonical inputs (rsID, HGVS c./p./g.) via Ensembl
    Variant Recoder before scoring, matching the single-tool behavior so
    bulk callers don't silently regress on identifiers that worked
    one-at-a-time. Multi-candidate resolutions return a per-item
    ``requires_disambiguation`` error so the caller picks the canonical
    id and re-calls; resolver outage returns the retryable
    ``external_resolver_unavailable`` code.
    """
    try:
        normalized_build = normalize_genome_build(genome_build)
    except MCPInputError as exc:
        return None, [], _from_input_error(exc)
    try:
        normalized_variant_id, resolution_warnings = await resolve_or_normalize_variant_id(
            variant_id, normalized_build
        )
    except MCPInputError as exc:
        return None, [], _from_input_error(exc)
    try:
        result = await service_adapters.get_variant(normalized_build, normalized_variant_id)
        data, warnings = present_variant(
            result,
            source_url=variant_url(settings.api.base_url, normalized_build, normalized_variant_id),
            response_mode=response_mode,
            include_unmet=include_unmet,
        )
        return data, resolution_warnings + warnings, None
    except httpx.TimeoutException:
        return (
            None,
            [],
            _err(
                "upstream_timeout",
                "AutoPVS1 upstream timed out while fetching variant data.",
                True,
                ["Retry later or confirm the AutoPVS1 service is reachable."],
            ),
        )
    except httpx.HTTPStatusError as exc:
        code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
        return (
            None,
            [],
            _err(
                code,
                "AutoPVS1 upstream could not return variant data for this request.",
                _retryable(exc.response.status_code),
                ["Confirm the genome_build and AutoPVS1 variant ID."],
            ),
        )
    except httpx.RequestError:
        return (
            None,
            [],
            _err(
                "upstream_unavailable",
                "AutoPVS1 upstream was unreachable while fetching variant data.",
                True,
                ["Retry later or confirm the AutoPVS1 service is reachable."],
            ),
        )
    except ValueError:
        return (
            None,
            [],
            _err(
                "parse_error",
                "AutoPVS1 variant HTML could not be parsed into the expected fields.",
                False,
                ["Retry after confirming the variant exists in AutoPVS1."],
            ),
        )


async def run_cnv_pvs1(
    *,
    genome_build: str,
    cnv_id: str,
    response_mode: ResponseMode,
    include_unmet: Any,
) -> tuple[CNVMCPData | None, list[MCPWarning], MCPError | None]:
    """Score one CNV. Return (data, warnings, error) — exactly one of data/error is non-None."""
    try:
        normalized_build = normalize_genome_build(genome_build)
        normalized_cnv_id = normalize_cnv_id(cnv_id)
    except MCPInputError as exc:
        return None, [], _from_input_error(exc)
    try:
        result = await service_adapters.get_cnv(normalized_build, normalized_cnv_id)
        data, warnings = present_cnv(
            result,
            source_url=cnv_url(settings.api.base_url, normalized_build, normalized_cnv_id),
            response_mode=response_mode,
            include_unmet=include_unmet,
        )
        return data, warnings, None
    except httpx.TimeoutException:
        return (
            None,
            [],
            _err(
                "upstream_timeout",
                "AutoPVS1 upstream timed out while fetching CNV data.",
                True,
                ["Retry later or confirm the AutoPVS1 service is reachable."],
            ),
        )
    except httpx.HTTPStatusError as exc:
        code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
        return (
            None,
            [],
            _err(
                code,
                "AutoPVS1 upstream could not return CNV data for this request.",
                _retryable(exc.response.status_code),
                ["Use CNV format such as 17-15000000-20000000-DEL."],
            ),
        )
    except httpx.RequestError:
        return (
            None,
            [],
            _err(
                "upstream_unavailable",
                "AutoPVS1 upstream was unreachable while fetching CNV data.",
                True,
                ["Retry later or confirm the AutoPVS1 service is reachable."],
            ),
        )
    except ValueError:
        return (
            None,
            [],
            _err(
                "parse_error",
                "AutoPVS1 CNV HTML could not be parsed into the expected fields.",
                False,
                ["Retry after confirming the CNV exists in AutoPVS1."],
            ),
        )
