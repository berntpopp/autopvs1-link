"""MCP tool: get_variant_pvs1_data."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from autopvs1_link.api.autopvs1_urls import variant_url
from autopvs1_link.api.variant_recoder import (
    RecoderNotFoundError,
    RecoderUnavailableError,
)
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


def _autopvs1_variant_uri(genome_build: str, variant_id: str) -> str:
    """Compose the AutoPVS1 web page URI for a resolved canonical id."""
    return variant_url(settings.api.base_url, genome_build, variant_id)


async def _resolve_or_normalize_variant_id(
    variant_id: str,
    genome_build: str,
) -> tuple[str, list[MCPWarning]]:
    """Resolve a possibly non-canonical variant_id to canonical SPDI.

    Canonical input → no upstream call; ``normalize_variant_id`` handles
    strict format checks. rsID / HGVS input → one Ensembl Variant
    Recoder call (build-scoped so the GRCh37 vs GRCh38 host matches the
    caller's ``genome_build``; the SAME rsID returns different
    coordinates between the two hosts). Multi-allele or multi-candidate
    result → ``requires_disambiguation`` (never silently best-guess —
    mitigates the multi-allelic mis-scoring failure mode, VEP #989).
    Zero candidates / Ensembl 'not found' → ``not_found``. Recoder
    timeout / 5xx / network error → ``external_resolver_unavailable``
    (retryable). ``unknown`` form → ``invalid_variant_id`` raised by
    ``normalize_variant_id``.

    AutoPVS1's own search endpoint is not used for rsID/HGVS resolution
    because it does not index dbSNP rsIDs and only partially handles
    HGVS via redirect; Ensembl REST is the authoritative resolver and
    its result is then passed to AutoPVS1 for scoring as canonical SPDI.
    """
    form = classify_variant_input(variant_id)
    if form == "canonical":
        canonical = variant_id.strip().upper().removeprefix("CHR")
        return normalize_variant_id(canonical), []
    if form == "unknown":
        normalize_variant_id(variant_id)
        raise AssertionError("unreachable: unknown form should have raised")

    raw_query = variant_id.strip()
    try:
        candidates = await service_adapters.recode_variant(raw_query, genome_build)
    except RecoderNotFoundError as exc:
        raise MCPInputError(
            code="not_found",
            message=(
                f"Ensembl Variant Recoder did not recognize {raw_query!r} "
                f"on genome_build={genome_build}. Confirm the identifier "
                f"or supply a canonical CHROM-POS-REF-ALT variant_id."
            ),
            suggestions=[
                "Confirm the rsID/HGVS exists in current dbSNP / RefSeq.",
                "Confirm the genome_build matches the source identifier.",
                "Supply a canonical CHROM-POS-REF-ALT variant_id directly.",
            ],
            details={
                "original_input": raw_query,
                "form": form,
                "genome_build": genome_build,
                "resolver_source": "ensembl_variant_recoder",
                "resolver_message": str(exc),
            },
        ) from exc
    except RecoderUnavailableError as exc:
        raise MCPInputError(
            code="external_resolver_unavailable",
            message=(
                "Ensembl Variant Recoder is currently unreachable while "
                f"resolving {raw_query!r}. The rest of AutoPVS1-Link is "
                "unaffected — retry shortly or supply a canonical "
                "CHROM-POS-REF-ALT variant_id to skip resolution."
            ),
            retryable=True,
            suggestions=[
                "Retry the call in a few seconds.",
                "Supply a canonical CHROM-POS-REF-ALT variant_id (no resolver hop needed).",
            ],
            details={
                "original_input": raw_query,
                "form": form,
                "genome_build": genome_build,
                "resolver_source": "ensembl_variant_recoder",
                "resolver_message": str(exc),
            },
        ) from exc

    if not candidates:
        raise MCPInputError(
            code="not_found",
            message=(
                f"Ensembl Variant Recoder returned no canonical-chrom "
                f"candidates for {raw_query!r} on genome_build={genome_build}."
            ),
            suggestions=[
                "Confirm the rsID/HGVS resolves to a primary-assembly chromosome.",
                "Supply a canonical CHROM-POS-REF-ALT variant_id directly.",
            ],
            details={
                "original_input": raw_query,
                "form": form,
                "genome_build": genome_build,
                "resolver_source": "ensembl_variant_recoder",
            },
        )

    if len(candidates) > 1:
        candidate_rows = [
            {
                "id": c.variant_id,
                "spdi": c.spdi,
                "allele_key": c.allele_key,
                "synonym_ids": list(c.synonym_ids),
                "genome_build": genome_build,
                "resource_uri": _autopvs1_variant_uri(genome_build, c.variant_id),
            }
            for c in candidates[:5]
        ]
        raise MCPInputError(
            code="requires_disambiguation",
            message=(
                f"Auto-resolution of {raw_query!r} returned "
                f"{len(candidates)} canonical candidates; caller must "
                f"pick one and re-call get_variant_pvs1_data with that "
                f"variant_id."
            ),
            suggestions=[
                f"Re-call with variant_id={c['id']!r} (allele={c['allele_key']})."
                for c in candidate_rows[:3]
            ],
            details={
                "candidates": candidate_rows,
                "original_input": raw_query,
                "form": form,
                "genome_build": genome_build,
                "resolver_source": "ensembl_variant_recoder",
            },
        )

    sole = candidates[0]
    return sole.variant_id, [
        MCPWarning(
            code="auto_resolved",
            message=(
                f"Resolved {raw_query!r} -> {sole.variant_id} via "
                f"Ensembl Variant Recoder (form={form}, "
                f"genome_build={genome_build}, allele={sole.allele_key})."
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
        canonical SPDI via one Ensembl Variant Recoder REST call before
        scoring (build-scoped — GRCh37 host for hg19, GRCh38 host for
        hg38). Emits an ``auto_resolved`` warning carrying the input,
        the resolved id, and the resolver source. Ambiguous resolutions
        return ``requires_disambiguation`` with allele-keyed candidates
        instead of
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
