"""Tests for variant and CNV MCP presenters."""

from autopvs1_link.mcp.presenters.variant import format_pli_score, present_cnv, present_variant
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    CNVInfo,
    DiseaseMechanism,
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
    assert data.cnv_info["cnv_type"] == "DEL"
    assert data.cnv_info["size"] == "5000000"
    assert data.pvs1_flowchart["final_strength"] == "VeryStrong"
    assert data.upstream_service == "AutoPVS1"
    assert warnings == []


def test_present_variant_summary_omits_mechanisms_and_suppresses_inference_warning() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
            chgvs="c.1A>T",
            phgvs="p.Lys1*",
            external_links={"gnomAD": "https://example.test/variant"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            final_strength_inferred=True,
            decision_tree=[FlowchartStep(code="NF1", note_id="#1")],
            notes={"#1": "Terminal node text."},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            )
        ],
    )

    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg38/X-1-A-T",
        response_mode="summary",
    )

    payload = data.model_dump(mode="json")
    assert payload["genome_build"] == "hg38"
    assert payload["variant_info"]["variant_id"] == "X-1-A-T"
    assert payload["variant_info"]["gene_symbol"] == "GENE"
    assert payload["variant_info"]["external_links"] == {}
    assert payload["variant_info"]["chgvs"] is None
    assert payload["pvs1_flowchart"]["final_strength"] == "Strong"
    assert payload["pvs1_flowchart"]["final_strength_source"] == "inferred"
    assert payload["pvs1_flowchart"]["decision_tree"] == []
    assert payload["pvs1_flowchart"]["notes"] == {}
    assert payload["disease_mechanisms"] == []
    assert payload["source_url"] == "https://autopvs1.bgi.com/variant/hg38/X-1-A-T"
    assert payload["upstream_service"] == "AutoPVS1"
    assert [warning.code for warning in warnings] == []


def test_present_variant_full_preserves_rich_fields_and_unmet_by_default() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
            gene_url="https://example.test/gene",
            chgvs="c.1A>T",
            phgvs="p.Lys1*",
            external_links={"gnomAD": "https://example.test/variant"},
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[FlowchartStep(code="NF1", note_id="#1")],
            notes={"#1": "Resolved note text."},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Met disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            ),
            DiseaseMechanism(
                gene="GENE",
                disease="Unmet disease",
                inheritance="AD",
                clinical_validity="Limited",
                consideration="Not applicable",
                adjusted_strength="Unmet",
            ),
        ],
    )

    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg38/X-1-A-T",
        response_mode="full",
    )

    payload = data.model_dump(mode="json")
    assert payload["variant_info"]["gene_url"] == "https://example.test/gene"
    assert payload["variant_info"]["chgvs"] == "c.1A>T"
    assert payload["variant_info"]["external_links"]["gnomAD"] == "https://example.test/variant"
    assert payload["pvs1_flowchart"]["notes"] == {"#1": "Resolved note text."}
    assert payload["pvs1_flowchart"]["decision_tree"][0]["note_text"] == "Resolved note text."
    assert [row["adjusted_strength"] for row in payload["disease_mechanisms"]] == [
        "Strong",
        "Unmet",
    ]
    assert warnings == []


def test_present_variant_can_filter_unmet_mechanisms() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Met disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            ),
            DiseaseMechanism(
                gene="GENE",
                disease="Unmet disease",
                inheritance="AD",
                clinical_validity="Limited",
                consideration="Not applicable",
                adjusted_strength="Unmet",
            ),
        ],
    )

    data, _warnings = present_variant(
        parsed,
        source_url=None,
        include_unmet=False,
    )

    assert [row.adjusted_strength for row in data.disease_mechanisms] == ["Strong"]


def test_present_cnv_summary_omits_mechanisms_and_marks_asserted_strength_source() -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="1-1-2-DEL",
            cnv_type="Deletion",
            gene_symbol="GENE",
            coordinates="1-1-2-DEL",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="GENE",
                disease="Disease",
                inheritance="AD",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            )
        ],
    )

    data, warnings = present_cnv(
        parsed,
        source_url="https://autopvs1.bgi.com/cnv/hg19/1-1-2-DEL",
        response_mode="summary",
    )

    payload = data.model_dump(mode="json")
    assert payload["genome_build"] == "hg19"
    assert payload["cnv_info"]["cnv_id"] == "1-1-2-DEL"
    assert payload["cnv_info"]["gene_symbol"] == "GENE"
    assert payload["pvs1_flowchart"]["final_strength"] == "Strong"
    assert payload["pvs1_flowchart"]["final_strength_source"] == "asserted"
    assert payload["disease_mechanisms"] == []
    assert payload["source_url"] == "https://autopvs1.bgi.com/cnv/hg19/1-1-2-DEL"
    assert payload["upstream_service"] == "AutoPVS1"
    assert warnings == []


def test_present_cnv_full_preserves_rich_fields_and_unmet_by_default() -> None:
    parsed = AutoPVS1CNVData(
        genome_build="hg19",
        cnv_info=CNVInfo(
            cnv_id="17-15000000-20000000-DEL",
            cnv_type="Deletion",
            gene_symbol="MYO15A",
            coordinates="17-15000000-20000000-DEL",
            size="5Mb",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="DEL",
            final_strength="VeryStrong",
            decision_tree=[FlowchartStep(code="DEL1", note_id="#1")],
            notes={"#1": "Resolved CNV note text."},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="MYO15A",
                gene_url="https://example.test/gene",
                disease="Met disease",
                disease_url="https://example.test/disease/met",
                inheritance="AR",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="VeryStrong",
            ),
            DiseaseMechanism(
                gene="MYO15A",
                disease="Unmet disease",
                inheritance="AR",
                clinical_validity="Limited",
                consideration="Not applicable",
                adjusted_strength="Unmet",
            ),
        ],
    )

    data, warnings = present_cnv(
        parsed,
        source_url="https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
        response_mode="full",
    )

    payload = data.model_dump(mode="json")
    assert payload["cnv_info"]["cnv_type"] == "DEL"
    assert payload["cnv_info"]["size"] == "5000000"
    assert payload["pvs1_flowchart"]["notes"] == {"#1": "Resolved CNV note text."}
    assert payload["pvs1_flowchart"]["decision_tree"][0]["note_text"] == "Resolved CNV note text."
    assert [row["adjusted_strength"] for row in payload["disease_mechanisms"]] == [
        "VeryStrong",
        "Unmet",
    ]
    assert payload["disease_mechanisms"][0]["gene_url"] == "https://example.test/gene"
    assert payload["disease_mechanisms"][0]["disease_url"] == "https://example.test/disease/met"
    assert warnings == []
