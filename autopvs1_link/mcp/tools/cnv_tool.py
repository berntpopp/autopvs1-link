"""MCP tool: get_cnv_pvs1_data."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.api.autopvs1_urls import cnv_url
from autopvs1_link.config import settings
from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from autopvs1_link.mcp.contracts import CNVMCPEnvelope
from autopvs1_link.mcp.envelope import ToolResponse, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.presenters.variant import present_cnv
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope
from autopvs1_link.mcp.validation import normalize_cnv_id, normalize_genome_build

RESPONSE_MODE_SCHEMA = {"type": "string", "enum": ["ids_only", "summary", "standard", "full"]}
META_MODE_SCHEMA = {"type": "string", "enum": ["full", "compact", "minimal"]}
_TOOL_NAME = "get_cnv_pvs1_data"


def _is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 429} or status_code >= 500


def register(mcp: FastMCP) -> None:
    """Register the get_cnv_pvs1_data tool."""

    @mcp.tool(
        name="get_cnv_pvs1_data",
        title="Get CNV PVS1 Data",
        output_schema=CNVMCPEnvelope.model_json_schema(),
        annotations=READ_ONLY_OPEN_WORLD,
    )
    async def get_cnv_pvs1_data(
        genome_build: Annotated[
            str,
            Field(
                description="Genome build: hg19 or hg38.",
                json_schema_extra={"enum": ["hg19", "hg38"]},
            ),
        ],
        cnv_id: Annotated[
            str,
            Field(
                description=(
                    "AutoPVS1 CNV ID in {chrom}-{start}-{end}-{TYPE} form, "
                    "for example 17-15000000-20000000-DEL. TYPE is DEL or DUP."
                ),
            ),
        ],
        response_mode: Annotated[
            Any,
            Field(
                description=(
                    "Response detail level. Default 'summary' returns the "
                    "verdict (preliminary path + final strength) under "
                    "~1.5KB. Widen to 'standard' for the full decision "
                    "tree with hoisted note_text and disease_mechanisms "
                    "when the user asks for the tree; use 'full' only "
                    "for auditors who need the ``*_raw`` upstream "
                    "fields; 'ids_only' is the batch-screen lookup tier."
                ),
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "summary",
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
    ) -> ToolResponse:
        """Score one copy-number variant with the AutoPVS1 PVS1 rules.

        First-turn LLM callers get the verdict under ~1.5KB by default
        (``response_mode='summary'``). Widen to ``response_mode='standard'``
        for the full decision tree. AutoPVS1 outputs are research-use only,
        not clinical decision support.
        """
        normalized_meta_mode: MetaMode = "full"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            normalized_build = normalize_genome_build(genome_build)
            normalized_cnv_id = normalize_cnv_id(cnv_id)
            result = await service_adapters.get_cnv(normalized_build, normalized_cnv_id)
            data, warnings = present_cnv(
                result,
                source_url=cnv_url(
                    settings.api.base_url,
                    normalized_build,
                    normalized_cnv_id,
                ),
                response_mode=normalized_response_mode,
                include_unmet=include_unmet,
            )
            return ok_envelope(
                data,
                warnings=warnings,
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except InvalidMCPModeError as exc:
            return invalid_mode_envelope(exc, meta_mode=normalized_meta_mode, tool_name=_TOOL_NAME)
        except MCPInputError as exc:
            return error_envelope(
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
                suggestions=exc.suggestions,
                details=exc.details or None,
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while fetching CNV data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except httpx.HTTPStatusError as exc:
            code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
            return error_envelope(
                code=code,
                message="AutoPVS1 upstream could not return CNV data for this request.",
                retryable=_is_retryable_status(exc.response.status_code),
                suggestions=["Use CNV format such as 17-15000000-20000000-DEL."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except httpx.RequestError:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream was unreachable while fetching CNV data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except ValueError:
            return error_envelope(
                code="parse_error",
                message="AutoPVS1 CNV HTML could not be parsed into the expected fields.",
                retryable=False,
                suggestions=["Retry after confirming the CNV exists in AutoPVS1."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
