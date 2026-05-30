"""Shared variant-id auto-resolution for single and bulk MCP tools.

Single-tool callers and per-item bulk runners both want the same
non-canonical variant_id forms (rsID, HGVS c./p./g.) to round-trip
through Ensembl Variant Recoder and emerge as canonical SPDI before
AutoPVS1 scoring. Keeping the resolver in one place avoids the bulk
tool silently rejecting inputs that the single tool would have
auto-resolved.
"""

from __future__ import annotations

from autopvs1_link.api.autopvs1_urls import variant_url
from autopvs1_link.api.variant_recoder import (
    RecoderNotFoundError,
    RecoderUnavailableError,
)
from autopvs1_link.config import settings
from autopvs1_link.mcp import service_adapters
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.mcp.errors import MCPInputError
from autopvs1_link.mcp.validation import classify_variant_input, normalize_variant_id


def _autopvs1_variant_uri(genome_build: str, variant_id: str) -> str:
    """Compose the AutoPVS1 web page URI for a resolved canonical id."""
    return variant_url(settings.api.base_url, genome_build, variant_id)


async def resolve_or_normalize_variant_id(
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
                f"pick one and re-call with that variant_id."
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
