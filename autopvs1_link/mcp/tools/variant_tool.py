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
from autopvs1_link.mcp.envelope import ToolResponse, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.next_commands import widen_response_mode
from autopvs1_link.mcp.presenters.variant import present_variant
from autopvs1_link.mcp.resolution import resolve_or_normalize_variant_id
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope
from autopvs1_link.mcp.validation import normalize_genome_build

RESPONSE_MODE_SCHEMA = {"type": "string", "enum": ["ids_only", "summary", "standard", "full"]}
META_MODE_SCHEMA = {"type": "string", "enum": ["full", "compact", "minimal"]}
_TOOL_NAME = "get_variant_pvs1_data"


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
            Field(
                description=(
                    "Variant identifier. Canonical SPDI (CHROM-POS-REF-ALT, "
                    "e.g. X-82763936-A-T) scores in one upstream call. "
                    "rsID (rs80357906) or HGVS (NM_007294.4:c.5266dup, "
                    "NP_000050.2:p.Glu1756fs, NC_000017.11:g.43091983C>A) "
                    "auto-resolves via Ensembl Variant Recoder REST "
                    "(build-scoped) then scores. Multiple resolver "
                    "candidates return error.code='requires_disambiguation' "
                    "with allele-keyed rows in details.candidates — caller "
                    "picks one. Recoder offline returns "
                    "error.code='external_resolver_unavailable' (retryable)."
                ),
            ),
        ],
        response_mode: Annotated[
            Any,
            Field(
                description=(
                    "Response detail level. Default 'summary' returns the "
                    "verdict (preliminary path + final strength) under "
                    "~1.5KB so first-turn LLM callers stay in budget. "
                    "Widen to 'standard' for the full decision tree with "
                    "hoisted note_text and disease_mechanisms when the user "
                    "asks for the tree; use 'full' only for auditors who "
                    "need the ``*_raw`` upstream fields; 'ids_only' is the "
                    "batch-screen lookup tier."
                ),
                json_schema_extra=RESPONSE_MODE_SCHEMA,
            ),
        ] = "summary",
        meta_mode: Annotated[
            Any,
            Field(
                description=(
                    "Metadata detail level: compact (default -- doi+pmid), "
                    "full (adds verbatim citation text+url), or minimal "
                    "(no citation)."
                ),
                json_schema_extra=META_MODE_SCHEMA,
            ),
        ] = "compact",
        include_unmet: Annotated[
            Any,
            Field(
                description="Include disease-mechanism rows with adjusted_strength=Unmet.",
                json_schema_extra={"type": "boolean"},
            ),
        ] = True,
    ) -> ToolResponse:
        """Score one SNV/indel variant with the AutoPVS1 PVS1 rules.

        Auto-resolves non-canonical inputs (rsID, HGVS c./p./g.) into
        canonical SPDI via one Ensembl Variant Recoder REST call before
        scoring (build-scoped — GRCh37 host for hg19, GRCh38 host for
        hg38). Emits an ``auto_resolved`` warning carrying the input,
        the resolved id, and the resolver source. Ambiguous resolutions
        return ``requires_disambiguation`` with allele-keyed candidates
        instead of
        silently picking one (mitigates multi-allelic mis-scoring).

        First-turn LLM callers get the verdict under ~1.5KB by default
        (``response_mode='summary'``). Widen to ``response_mode='standard'``
        for the full decision tree, or ``'full'`` for the audit-trail
        ``*_raw`` upstream fields. AutoPVS1 outputs are research-use only,
        not clinical decision support.
        """
        normalized_meta_mode: MetaMode = "compact"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            normalized_build = normalize_genome_build(genome_build)
            normalized_variant_id, resolution_warnings = await resolve_or_normalize_variant_id(
                variant_id, normalized_build
            )
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
            return ok_envelope(
                data,
                warnings=resolution_warnings + warnings,
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
                next_commands=widen_response_mode(
                    _TOOL_NAME,
                    {"genome_build": normalized_build, "variant_id": normalized_variant_id},
                    normalized_response_mode,
                ),
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
                message="AutoPVS1 upstream timed out while fetching variant data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except httpx.HTTPStatusError as exc:
            code = "not_found" if exc.response.status_code == 404 else "upstream_unavailable"
            return error_envelope(
                code=code,
                message="AutoPVS1 upstream could not return variant data for this request.",
                retryable=_is_retryable_status(exc.response.status_code),
                suggestions=["Confirm the genome_build and AutoPVS1 variant ID."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except httpx.RequestError:
            return error_envelope(
                code="upstream_unavailable",
                message="AutoPVS1 upstream was unreachable while fetching variant data.",
                retryable=True,
                suggestions=["Retry later or confirm the AutoPVS1 service is reachable."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
        except ValueError:
            return error_envelope(
                code="parse_error",
                message="AutoPVS1 variant HTML could not be parsed into the expected fields.",
                retryable=False,
                suggestions=["Retry after confirming the variant exists in AutoPVS1."],
                meta_mode=normalized_meta_mode,
                tool_name=_TOOL_NAME,
            )
