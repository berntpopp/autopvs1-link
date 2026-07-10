"""Parsed-shape validation for scraped PVS1 final_strength."""

import pytest

from autopvs1_link.mcp.presenters.variant import UpstreamFormatError, present_variant
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1Data,
    PVS1Flowchart,
    VariantInfo,
)


def _variant(final_strength: str) -> AutoPVS1Data:
    return AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="17-43045712-G-A",
            variant_type="SNV",
            gene_symbol="BRCA1",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="nonsense",
            final_strength=final_strength,
        ),
        disease_mechanisms=[],
    )


def test_empty_final_strength_fails_closed() -> None:
    with pytest.raises(UpstreamFormatError, match="unrecognized final strength"):
        present_variant(_variant(""), source_url=None)


def test_unrecognized_final_strength_fails_closed() -> None:
    with pytest.raises(UpstreamFormatError, match="unrecognized final strength"):
        present_variant(_variant("Bananas"), source_url=None)


def test_recognized_final_strength_emits_no_drift_warning() -> None:
    _data, warnings = present_variant(_variant("Strong"), source_url=None)
    assert not any(w.code == "upstream_format_unrecognized" for w in warnings)
