"""Route-level bound-input + fixed-error guard for the legacy REST surface.

Finding F-03: the legacy REST variant/gene routes logged and reflected caller
genomic identifiers and raw exception prose, and the variant path had no
route-level length/grammar constraint. The MCP path already enforces the
desired policy; this module ports it to REST by *reusing* the MCP validators
(no new sanitizers): every caller-supplied identifier is length-bounded and
grammar-checked BEFORE any I/O, logging, or cache use. On rejection the caller
receives a FIXED, enumerated message that never embeds the raw input, and the
route logs only the error code/class.
"""

from __future__ import annotations

import re

from autopvs1_link.mcp.validation import (
    VALID_GENOME_BUILDS,
    classify_variant_input,
    contains_forbidden_codepoint,
)

# Generous ceilings: the longest legitimate HGVS description is far shorter, but
# these bound oversize / DoS inputs before any upstream call is attempted.
MAX_VARIANT_ID_CHARS = 256
MAX_GENE_QUERY_CHARS = 128

# REST-only, reference-free short HGVS forms the legacy route documents and
# resolves (``g.``/``m.``) but the MCP classifier does not cover. The tail is a
# numeric position plus ONE structured HGVS change op -- never an arbitrary
# letter run -- so instruction prose such as ``g.1IGNORE`` is rejected here.
_HGVS_POS = r"[*-]?\d+(?:[+-]\d+)?"
_HGVS_CHANGE = (
    r"(?:[ACGTUN]*>[ACGTUN]+|delins[ACGTUN]+|del[ACGTUN]*|dup[ACGTUN]*"
    r"|ins[ACGTUN0-9]+|inv[ACGTUN]*|[ACGTUN]+|=)"
)
_REST_SHORT_HGVS_RE = re.compile(
    rf"^[gm]\.{_HGVS_POS}(?:_{_HGVS_POS})?{_HGVS_CHANGE}$",
    re.IGNORECASE,
)

# Conservative gene-symbol / partial-id grammar: a closed character class with
# no internal whitespace, rejecting prose and SQL/shell metacharacters.
_GENE_QUERY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@:+-]*$")

# Fixed, caller-safe messages. None embeds any caller-supplied value.
_VARIANT_MSG = "Variant identifier is missing or invalid."
_GENE_MSG = "Gene query is missing or invalid."
_BUILD_MSG = "Genome build must be hg19 or hg38."


class RestInputError(ValueError):
    """A REST identifier failed length/grammar validation before any I/O.

    Carries a fixed enumerated ``code`` and a FIXED caller-safe ``message``;
    neither ever embeds the rejected raw input, upstream body, or exception
    prose. Raised strictly before upstream calls, logging, or cache use.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_variant_id(raw: object) -> str:
    """Return the trimmed variant id if it passes length + grammar checks.

    Accepts canonical AutoPVS1 ids, rsIDs, transcript/protein/genomic HGVS (the
    MCP classifier's forms) and the REST-only reference-free ``g.``/``m.`` forms.
    Raises :class:`RestInputError` -- BEFORE any I/O -- on anything else.
    """
    if not isinstance(raw, str) or contains_forbidden_codepoint(raw):
        raise RestInputError("invalid_variant_id", _VARIANT_MSG)
    value = raw.strip()
    if not value or len(value) > MAX_VARIANT_ID_CHARS:
        raise RestInputError("invalid_variant_id", _VARIANT_MSG)
    if classify_variant_input(value) != "unknown" or _REST_SHORT_HGVS_RE.fullmatch(value):
        return value
    raise RestInputError("invalid_variant_id", _VARIANT_MSG)


def validate_gene_query(raw: object) -> str:
    """Return the trimmed gene query if it passes length + grammar checks."""
    if not isinstance(raw, str) or contains_forbidden_codepoint(raw):
        raise RestInputError("invalid_gene_query", _GENE_MSG)
    value = raw.strip()
    if not value or len(value) > MAX_GENE_QUERY_CHARS or not _GENE_QUERY_RE.fullmatch(value):
        raise RestInputError("invalid_gene_query", _GENE_MSG)
    return value


def validate_genome_build(raw: object) -> str:
    """Return the trimmed genome build if it is a recognized AutoPVS1 build."""
    if not isinstance(raw, str) or contains_forbidden_codepoint(raw):
        raise RestInputError("invalid_genome_build", _BUILD_MSG)
    value = raw.strip()
    if value not in VALID_GENOME_BUILDS:
        raise RestInputError("invalid_genome_build", _BUILD_MSG)
    return value
