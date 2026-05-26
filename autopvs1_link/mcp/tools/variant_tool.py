"""MCP tool: get_variant_pvs1_data."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.api.autopvs1_urls import variant_url
from autopvs1_link.config import settings
from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import VariantMCPEnvelope
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.presenters.variant import present_variant
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope
from autopvs1_link.mcp.validation import normalize_genome_build, normalize_variant_id

RESPONSE_MODE_SCHEMA = {"type": "string", "enum": ["summary", "standard", "full"]}
META_MODE_SCHEMA = {"type": "string", "enum": ["full", "compact", "minimal"]}


def _is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 429} or status_code >= 500


def register(mcp: FastMCP) -> None:
    """Register the get_variant_pvs1_data tool."""

    @mcp.tool(
        name="get_variant_pvs1_data",
        title="Get Variant PVS1 Data",
        output_schema=VariantMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def get_variant_pvs1_data(
        genome_build: Annotated[
            str,
            Field(
                description="Genome build: hg19 or hg38.",
                json_schema_extra={"enum": ["hg19", "hg38"]},
            ),
        ],
        variant_id: Annotated[
            str,
            Field(description="Variant identifier, for example X-82763936-A-T."),
        ],
        response_mode: Annotated[
            Any,
            Field(
                description="Response detail level: summary, standard, or full.",
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "standard",
        meta_mode: Annotated[
            Any,
            Field(
                description="Metadata detail level: full, compact, or minimal.",
                json_schema_extra=META_MODE_SCHEMA,
            ),
        ] = "full",
        include_unmet: Annotated[
            Any,
            Field(
                description="Include disease-mechanism rows with adjusted_strength=Unmet.",
                json_schema_extra={"type": "boolean"},
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Use this to score one SNV/indel variant with AutoPVS1 PVS1 rules."""
        normalized_meta_mode: MetaMode = "full"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            normalized_build = normalize_genome_build(genome_build)
            normalized_variant_id = normalize_variant_id(variant_id)
            result = await service_adapters.get_variant(normalized_build, normalized_variant_id)
            data, warnings = present_variant(
                result,
                source_url=variant_url(
                    settings.api.base_url,
                    normalized_build,
                    normalized_variant_id,
                ),
                response_mode=normalized_response_mode,
                include_unmet=include_unmet,
            )
            return ok_envelope(data, warnings=warnings, meta_mode=normalized_meta_mode)
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(exc, meta_mode=normalized_meta_mode)
        except MCPInputError as exc:
            return error_envelope(
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
                suggestions=exc.suggestions,
                meta_mode=normalized_meta_mode,
            )
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while fetching variant data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
                meta_mode=normalized_meta_mode,
            )
        except httpx.HTTPStatusError as exc:
            code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
            return error_envelope(
                code=code,
                message="AutoPVS1 upstream could not return variant data for this request.",
                retryable=_is_retryable_status(exc.response.status_code),
                suggestions=["Confirm the genome_build and AutoPVS1 variant ID."],
                meta_mode=normalized_meta_mode,
            )
        except httpx.RequestError:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream was unreachable while fetching variant data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
                meta_mode=normalized_meta_mode,
            )
        except ValueError:
            return error_envelope(
                code="parse_error",
                message="AutoPVS1 variant HTML could not be parsed into the expected fields.",
                retryable=False,
                suggestions=["Retry after confirming the variant exists in AutoPVS1."],
                meta_mode=normalized_meta_mode,
            )
