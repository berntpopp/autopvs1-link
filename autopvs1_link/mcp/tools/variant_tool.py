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
from autopvs1_link.mcp.envelope import MCPWarning, ToolResponse, error_envelope, ok_envelope
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.mode_validation import (
    InvalidMCPModeError,
    MetaMode,
    normalize_meta_mode,
    normalize_response_mode,
)
from autopvs1_link.mcp.presenters.variant import present_variant
from autopvs1_link.mcp.tools.mode_errors import invalid_mode_envelope
from autopvs1_link.mcp.validation import (
    classify_variant_input,
    normalize_genome_build,
    normalize_variant_id,
)

RESPONSE_MODE_SCHEMA = {"type": "string", "enum": ["ids_only", "summary", "standard", "full"]}
META_MODE_SCHEMA = {"type": "string", "enum": ["full", "compact", "minimal"]}


def _is_retryable_status(status_code: int) -> bool:
    return status_code in {408, 429} or status_code >= 500


async def _resolve_or_normalize_variant_id(
    variant_id: str,
    genome_build: str,
) -> tuple[str, list[MCPWarning]]:
    """Resolve a possibly non-canonical variant_id to canonical SPDI.

    Canonical input → no upstream call; ``normalize_variant_id`` handles
    strict format checks. rsID / HGVS input → one ``search_variants``
    upstream call, build-scoped so resolution and scoring share the same
    genome build (mitigates rsID/HGVS coords-vs-build drift). Multi-hit
    → ``requires_disambiguation`` (never silently best-guess). Zero-hit
    → ``not_found``. ``unknown`` form → ``invalid_variant_id`` raised by
    ``normalize_variant_id``.
    """
    form = classify_variant_input(variant_id)
    if form == "canonical":
        canonical = variant_id.strip().upper().removeprefix("CHR")
        return normalize_variant_id(canonical), []
    if form == "unknown":
        normalize_variant_id(variant_id)
        raise AssertionError("unreachable: unknown form should have raised")

    raw_query = variant_id.strip()
    search_result = await service_adapters.search_variants(raw_query, genome_build)
    rows = list(getattr(search_result, "results", []) or [])

    if not rows:
        raise MCPInputError(
            code="not_found",
            message=(
                f"AutoPVS1 returned no matches for {raw_query!r} on "
                f"genome_build={genome_build}. Confirm the identifier or "
                f"broaden the query via search_variants."
            ),
            suggestions=[
                "Call search_variants with a gene symbol or broader text.",
                "Confirm the genome_build matches the source identifier.",
            ],
        )

    if len(rows) > 1:
        candidates = [
            {
                "id": row.variant_id,
                "gene": row.gene,
                "variant_type": row.variant_type,
                "genome_build": row.genome_build,
                "resource_uri": row.url,
            }
            for row in rows[:5]
        ]
        raise MCPInputError(
            code="requires_disambiguation",
            message=(
                f"Auto-resolution of {raw_query!r} returned "
                f"{len(rows)} candidates; caller must pick one and "
                f"re-call get_variant_pvs1_data with the canonical id."
            ),
            suggestions=[
                f"Re-call with variant_id={c['id']!r} (gene={c['gene']}, type={c['variant_type']})."
                for c in candidates[:3]
            ],
            details={
                "candidates": candidates,
                "original_input": raw_query,
                "form": form,
                "genome_build": genome_build,
            },
        )

    sole = rows[0]
    return sole.variant_id, [
        MCPWarning(
            code="auto_resolved",
            message=(
                f"Resolved {raw_query!r} -> {sole.variant_id} via "
                f"search_variants (form={form}, "
                f"genome_build={genome_build})."
            ),
        )
    ]


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
                    "NP_000050.2:p.Glu1756fs, GRCh38(NC_000017.11):g.43091983C>A) "
                    "auto-resolves via search_variants then scores. Multiple "
                    "resolver hits return error.code='requires_disambiguation' "
                    "with candidates in details.candidates — caller picks one."
                ),
            ),
        ],
        response_mode: Annotated[
            Any,
            Field(
                description=(
                    "Response detail level. LLM-first callers should pass "
                    "'summary' (verdict + path + final strength, ~1.5KB); "
                    "widen to 'standard' (default, full decision tree with "
                    "hoisted note_text and disease_mechanisms) when the user "
                    "asks for the tree; use 'full' only for auditors who "
                    "need the ``*_raw`` upstream fields; 'ids_only' is the "
                    "batch-screen lookup tier."
                ),
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
    ) -> ToolResponse:
        """Score one SNV/indel variant with the AutoPVS1 PVS1 rules.

        Auto-resolves non-canonical inputs (rsID, HGVS c./p./g.) into
        canonical SPDI via one upstream search call before scoring;
        emits an ``auto_resolved`` warning. Ambiguous resolutions return
        ``requires_disambiguation`` with ranked candidates instead of
        silently picking one (mitigates multi-allelic mis-scoring).

        First-turn LLM callers: pass ``response_mode='summary'`` to receive
        the verdict (preliminary path + final strength) under ~1.5KB.
        Widen to ``response_mode='standard'`` only when the user asks for
        the decision tree. AutoPVS1 outputs are research-use only, not
        clinical decision support.
        """
        normalized_meta_mode: MetaMode = "full"
        try:
            normalized_meta_mode = normalize_meta_mode(meta_mode)
            normalized_response_mode = normalize_response_mode(response_mode)
            normalized_build = normalize_genome_build(genome_build)
            normalized_variant_id, resolution_warnings = await _resolve_or_normalize_variant_id(
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
