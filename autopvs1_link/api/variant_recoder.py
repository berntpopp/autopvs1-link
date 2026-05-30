"""Ensembl Variant Recoder REST client.

Resolves rsID / HGVS-c / HGVS-p / HGVS-g inputs to canonical SPDI
(``CHROM-POS-REF-ALT``) so :func:`autopvs1_link.mcp.tools.variant_tool`
can score variants the user supplied in any of the common community
forms. AutoPVS1's own search box does not index rsIDs and only
partially handles HGVS via redirects, so we delegate authoritative
resolution to Ensembl REST.

Build mapping (see `caveats` in docs/superpowers/plans/...):
    hg38 -> https://rest.ensembl.org
    hg19 -> https://grch37.rest.ensembl.org

The same rsID returns DIFFERENT genomic coordinates between the two
hosts; the build is encoded by the host, not by a query parameter.
Cache keys MUST therefore include the build.

Why ``vcf_string`` not ``spdi`` (api caveat):
    ``vcf_string`` is already in ``CHR-POS-REF-ALT`` format with VCF
    1-based coordinates and left-anchored ref/alt for indels (e.g.
    ``17-43057065-G-GG`` for a dup). SPDI uses 0-based interbase
    coordinates with contig-prefixed sequences (``NC_000017.11:...``)
    and would require translation. ``vcf_string`` matches AutoPVS1's
    accepted shape directly.

Multi-allelic handling:
    The response is always a top-level JSON array. Each array element
    is a dict keyed by ALT allele letter(s) (``"G"``, ``"-"`` for
    deletions, multi-base for MNVs). Multi-allelic rsIDs return
    multiple allele keys side-by-side under one array element. We
    surface every allele key as a separate candidate so the caller can
    disambiguate; we never collapse to "first allele wins" (mitigates
    multi-allelic mis-scoring, the VEP #989 failure pattern).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
import structlog

logger = structlog.get_logger()

# Ensembl REST hosts. The build is encoded by host: there is no
# ``assembly`` query parameter for /variant_recoder.
_HOST_GRCH37 = "https://grch37.rest.ensembl.org"
_HOST_GRCH38 = "https://rest.ensembl.org"

# Some lookups take 10-15s of upstream runtime (observed x-runtime
# 13.4s for rs80357906). Default httpx 5s timeout is unreliable here.
_RECODER_TIMEOUT_SECONDS = 30.0

# Filter ``vcf_string`` entries to only the canonical chromosome
# representation. The list also contains LRG_* and HG*_PATCH/NW_*
# alternative-assembly anchors that AutoPVS1 will not accept.
_CANONICAL_CHROM_RE = re.compile(r"^(?:[1-9]|1[0-9]|2[0-2]|X|Y|MT)$")


@dataclass(frozen=True, slots=True)
class RecoderCandidate:
    """One canonical SPDI candidate returned by Variant Recoder."""

    variant_id: str
    """Canonical ``CHROM-POS-REF-ALT`` (AutoPVS1 format)."""

    allele_key: str
    """The ALT allele key as returned by Ensembl (``"G"``, ``"-"`` for
    deletions, multi-base for MNVs). Useful for disambiguation
    suggestions surfaced to the caller."""

    spdi: str
    """SPDI representation (``NC_*:pos:ref:alt``). Included so callers
    can cite the canonical genomic position alongside the AutoPVS1 id."""

    synonym_ids: tuple[str, ...]
    """Synonym identifiers from Ensembl's ``id`` field (RS / COSV).
    Empty when Ensembl returned none."""


class RecoderError(Exception):
    """Base exception for Ensembl Variant Recoder client errors."""


class RecoderNotFoundError(RecoderError):
    """Ensembl returned HTTP 400 with a 'not found' / 'unable to parse' message.

    For an LLM-MCP caller this means the input identifier is not
    recognized as a real dbSNP rs or a parseable HGVS notation — not a
    transient error. The variant tool maps this to ``error.code=not_found``.
    """


class RecoderUnavailableError(RecoderError):
    """Recoder is unreachable, rate-limited, or returned a 5xx.

    Includes httpx network errors, timeouts, 429 (rate limit), and 5xx.
    Mapped to ``error.code=external_resolver_unavailable`` (retryable).
    """


def _host_for_build(genome_build: str) -> str:
    if genome_build == "hg19":
        return _HOST_GRCH37
    if genome_build == "hg38":
        return _HOST_GRCH38
    raise ValueError(f"Unsupported genome_build for recoder: {genome_build!r}")


def _is_not_found_message(message: str) -> bool:
    """Heuristic match against Ensembl's 400 error strings.

    The error response has no machine-readable code, so we discriminate
    "not found" / "parse failure" (both LLM-facing ``not_found``) from
    transient upstream errors purely by message inspection.
    """
    lower = message.lower()
    return any(
        marker in lower
        for marker in (
            "no variant found",
            "unable to parse",
            "could not get a slice",
            "could not get a transcript",
            "can not find internal name",
        )
    )


def _extract_canonical_vcf_string(vcf_strings: list[Any]) -> str | None:
    """Pick the first canonical-chrom-anchored entry from a vcf_string list.

    Ensembl returns parallel entries on LRG_* and HG*_PATCH/NW_* contigs
    alongside the canonical chromosome representation. AutoPVS1 only
    accepts plain chromosome ids, so we filter to those.
    """
    for raw in vcf_strings:
        if not isinstance(raw, str):
            continue
        parts = raw.split("-", 1)
        if not parts or not _CANONICAL_CHROM_RE.fullmatch(parts[0]):
            continue
        return raw
    return None


def _extract_canonical_spdi(spdi_strings: list[Any]) -> str | None:
    """Pick the first NC_*-anchored entry from an spdi list."""
    for raw in spdi_strings:
        if isinstance(raw, str) and raw.startswith("NC_"):
            return raw
    return None


def _parse_recoder_response(payload: Any) -> list[RecoderCandidate]:
    """Walk Ensembl's array-of-allele-dicts response into a flat candidate list.

    The response shape (see caveats):
      ``[{"G": {...}, "T": {...}}, {"A": {...}}]``
    Each per-allele dict carries ``vcf_string``, ``spdi``, ``id`` lists.
    We yield one candidate per allele key per array element.
    """
    if not isinstance(payload, list):
        return []
    candidates: list[RecoderCandidate] = []
    for element in payload:
        if not isinstance(element, dict):
            continue
        for allele_key, allele_data in element.items():
            if not isinstance(allele_data, dict):
                continue
            vcf_strings = allele_data.get("vcf_string") or []
            spdi_strings = allele_data.get("spdi") or []
            synonym_ids = allele_data.get("id") or []
            vcf_string = _extract_canonical_vcf_string(vcf_strings)
            if vcf_string is None:
                continue
            spdi = _extract_canonical_spdi(spdi_strings) or ""
            candidates.append(
                RecoderCandidate(
                    variant_id=vcf_string,
                    allele_key=str(allele_key),
                    spdi=spdi,
                    synonym_ids=tuple(s for s in synonym_ids if isinstance(s, str)),
                )
            )
    return candidates


class VariantRecoderClient:
    """Thin async client around Ensembl's variant_recoder endpoint."""

    def __init__(self, timeout_seconds: float = _RECODER_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout_seconds

    async def recode(self, input_id: str, genome_build: str) -> list[RecoderCandidate]:
        """Resolve ``input_id`` (rsID or HGVS) to canonical SPDI candidates.

        Raises :class:`RecoderNotFoundError` for inputs Ensembl rejects as
        unknown / unparseable (HTTP 400 with a 'not found' / 'unable to
        parse' body). Raises :class:`RecoderUnavailableError` for network
        failures, timeouts, 429 (rate limit), and 5xx responses.

        Returns ``[]`` only when Ensembl returns 200 with an empty array
        — exceedingly rare in practice; treated by callers as
        ``not_found``.
        """
        host = _host_for_build(genome_build)
        # URL-encode the path segment; HGVS uses ``:`` and ``>`` which
        # strict reverse proxies reject if not percent-encoded.
        encoded_id = quote(input_id, safe="")
        url = (
            f"{host}/variant_recoder/human/{encoded_id}"
            "?vcf_string=1&fields=id,spdi,vcf_string&content-type=application/json"
        )
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
        except httpx.TimeoutException as exc:
            logger.warning("Recoder timeout", input_id=input_id, build=genome_build)
            raise RecoderUnavailableError(
                f"Variant Recoder timed out resolving {input_id!r} on {genome_build}"
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Recoder transport error",
                input_id=input_id,
                build=genome_build,
                error=str(exc),
            )
            raise RecoderUnavailableError(
                f"Variant Recoder transport error resolving {input_id!r}"
            ) from exc

        if response.status_code == 400:
            try:
                body = response.json()
            except ValueError:
                body = {}
            message = body.get("error") if isinstance(body, dict) else None
            if isinstance(message, str) and _is_not_found_message(message):
                raise RecoderNotFoundError(message)
            raise RecoderNotFoundError(
                f"Variant Recoder rejected {input_id!r}: "
                f"{message if isinstance(message, str) else response.text[:200]}"
            )
        if response.status_code == 429 or response.status_code >= 500:
            raise RecoderUnavailableError(
                f"Variant Recoder returned HTTP {response.status_code} resolving {input_id!r}"
            )
        if response.status_code != 200:
            # 4xx other than 400/429: treat as not_found rather than
            # transient. Callers should not retry malformed-id 4xx.
            raise RecoderNotFoundError(
                f"Variant Recoder returned HTTP {response.status_code} for {input_id!r}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RecoderUnavailableError(
                f"Variant Recoder returned non-JSON body for {input_id!r}"
            ) from exc
        return _parse_recoder_response(payload)


_default_client: VariantRecoderClient | None = None


def get_recoder_client() -> VariantRecoderClient:
    """Return the process-wide singleton recoder client."""
    global _default_client
    if _default_client is None:
        _default_client = VariantRecoderClient()
    return _default_client
