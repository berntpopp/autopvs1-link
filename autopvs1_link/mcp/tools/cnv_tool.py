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
from autopvs1_link.mcp.envelope import error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.presenters.variant import present_cnv
from autopvs1_link.mcp.validation import normalize_cnv_id, normalize_genome_build


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
    ) -> dict[str, Any]:
        """Use this to score one copy-number variant with AutoPVS1 PVS1 rules."""
        try:
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
            )
            return ok_envelope(data, warnings=warnings)
        except MCPInputError as exc:
            return exc.to_envelope()
        except httpx.TimeoutException:
            return error_envelope(
                code="upstream_timeout",
                message="AutoPVS1 upstream timed out while fetching CNV data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
            )
        except httpx.HTTPStatusError as exc:
            code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
            return error_envelope(
                code=code,
                message="AutoPVS1 upstream could not return CNV data for this request.",
                retryable=_is_retryable_status(exc.response.status_code),
                suggestions=["Use CNV format such as 17-15000000-20000000-DEL."],
            )
        except httpx.RequestError:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream was unreachable while fetching CNV data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
            )
        except ValueError:
            return error_envelope(
                code="parse_error",
                message="AutoPVS1 CNV HTML could not be parsed into the expected fields.",
                retryable=False,
                suggestions=["Retry after confirming the CNV exists in AutoPVS1."],
            )
