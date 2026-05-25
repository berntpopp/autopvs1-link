"""Tests for variant and CNV MCP presenters."""

from autopvs1_link.mcp.presenters.variant import format_pli_score, present_cnv, present_variant
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    CNVInfo,
    FlowchartStep,
    PVS1Flowchart,
    VariantInfo,
)


def test_format_pli_score_for_llm_display() -> None:
    assert format_pli_score(None) is None
    assert format_pli_score(0.0) == "0"
    assert format_pli_score(3.29e-20) == "3.29e-20"
    assert format_pli_score(0.0005) == "5.00e-04"
    assert format_pli_score(0.000999) == "9.99e-04"
    assert format_pli_score(0.72) == "0.72"
    assert format_pli_score(0.123456) == "0.1235"


def test_present_variant_adds_note_text_invalid_link_warning_and_inference_warning() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T",
            variant_type="Nonsense",
            gene_symbol="POU3F4",
            pli_score=3.29e-20,
            external_links={"gnomAD": "https://gnomad.broadinstitute.org/variant/X-82763936-A-T"},
            invalid_external_links={"ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            final_strength_inferred=True,
            decision_tree=[
                FlowchartStep(
                    code="Role of region in protein function is unknown",
                    note_id="#1",
                )
            ],
            notes={"#1": "Resolved note text."},
        ),
        disease_mechanisms=[],
    )

    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
    )

    assert data.upstream_service == "AutoPVS1"
    assert data.source_url == "https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T"
    assert data.variant_info["pli_score"] == 3.29e-20
    assert data.variant_info["pli_score_display"] == "3.29e-20"
    assert data.variant_info["external_links"]["ClinVar"] is None
    assert data.pvs1_flowchart["decision_tree"][0]["note_text"] == "Resolved note text."
    assert {warning.code for warning in warnings} == {
        "invalid_external_link",
        "final_strength_inferred",
    }


def test_present_cnv_shapes_cnv_payload() -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="17-15000000-20000000-DEL",
            cnv_type="Deletion",
            gene_symbol="MYO15A",
            coordinates="17-15000000-20000000-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="VeryStrong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )

    data, warnings = present_cnv(
        parsed,
        source_url="https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
    )

    assert data.genome_build == "hg19"
    assert data.cnv_info["gene_symbol"] == "MYO15A"
    assert data.pvs1_flowchart["final_strength"] == "VeryStrong"
    assert data.upstream_service == "AutoPVS1"
    assert warnings == []
