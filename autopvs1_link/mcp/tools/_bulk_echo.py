"""Safe reflection of bulk per-item ``input`` rows.

The bulk per-item envelope echoes the caller's request as ``results[*].input`` for
correlation. Raw caller input must never be reflected verbatim: an HGVS-shaped or
otherwise free-form identifier can carry instruction prose that no code-point
strip removes. These helpers rebuild the echoed item with each identifier reduced
to its strict, non-free-form form (canonical SPDI / rsID / CNV grammar / known
genome build) or a fixed redaction marker — the same value then also flows into
``next_commands`` via ``bulk_retry_failed``.
"""

from __future__ import annotations

from autopvs1_link.mcp.contracts import BulkCNVPVS1InputItem, BulkVariantPVS1InputItem
from autopvs1_link.mcp.validation import (
    safe_echo_cnv_id,
    safe_echo_genome_build,
    safe_echo_variant_id,
)


def echo_variant_input(item: BulkVariantPVS1InputItem) -> BulkVariantPVS1InputItem:
    """Return a variant item safe to reflect in ``results[*].input``."""
    return BulkVariantPVS1InputItem(
        genome_build=safe_echo_genome_build(item.genome_build),
        variant_id=safe_echo_variant_id(item.variant_id),
    )


def echo_cnv_input(item: BulkCNVPVS1InputItem) -> BulkCNVPVS1InputItem:
    """Return a CNV item safe to reflect in ``results[*].input``."""
    return BulkCNVPVS1InputItem(
        genome_build=safe_echo_genome_build(item.genome_build),
        cnv_id=safe_echo_cnv_id(item.cnv_id),
    )
