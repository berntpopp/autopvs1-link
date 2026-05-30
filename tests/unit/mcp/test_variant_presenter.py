"""Tests for variant and CNV MCP presenters."""

import json

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


def test_present_variant_adds_note_text_and_invalid_link_warning() -> None:
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
    assert data.pvs1_flowchart["final_strength_source"] == "inferred"
    assert {warning.code for warning in warnings} == {"invalid_external_link"}


def test_present_variant_emits_pvs1_not_applicable_warning() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="1-1-A-T",
            variant_type="Intergenic",
            gene_symbol="XK",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="not_applicable",
            final_strength="PVS1_Not_Applicable",
            decision_tree=[],
            notes={"note_1": "This variant type is incompatible with PVS1 criterion"},
        ),
        disease_mechanisms=[],
    )
    data, warnings = present_variant(parsed, source_url=None)
    assert "pvs1_not_applicable" in {w.code for w in warnings}
    assert data.pvs1_flowchart["final_strength"] == "PVS1_Not_Applicable"


def test_present_variant_emits_pvs1_not_applicable_for_not_determined() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="1-1-A-T",
            variant_type="Unknown",
            gene_symbol="XK",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="not_determined",
            final_strength="PVS1_Not_Determined",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    _, warnings = present_variant(parsed, source_url=None)
    assert any(w.code == "pvs1_not_applicable" for w in warnings)


def test_present_variant_no_warning_for_scorable_strength() -> None:
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF1",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    _, warnings = present_variant(parsed, source_url=None)
    assert not any(w.code == "pvs1_not_applicable" for w in warnings)


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
    assert data.cnv_info["size"] == 5000000
    assert data.pvs1_flowchart["final_strength"] == "VeryStrong"
    assert data.upstream_service == "AutoPVS1"
    assert warnings == []


def test_present_variant_summary_omits_mechanisms_and_emits_no_warnings() -> None:
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
    # Summary trims variant_info to {variant_id, variant_type, gene_symbol}
    # so external_links drops to its widened None default; standard mode
    # still surfaces the dict explicitly.
    assert payload["variant_info"]["external_links"] is None
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
    assert payload["cnv_info"]["size"] == 5000000
    assert payload["pvs1_flowchart"]["notes"] == {"#1": "Resolved CNV note text."}
    assert payload["pvs1_flowchart"]["decision_tree"][0]["note_text"] == "Resolved CNV note text."
    assert [row["adjusted_strength"] for row in payload["disease_mechanisms"]] == [
        "VeryStrong",
        "Unmet",
    ]
    assert payload["disease_mechanisms"][0]["gene_url"] == "https://example.test/gene"
    assert payload["disease_mechanisms"][0]["disease_url"] == "https://example.test/disease/met"
    assert warnings == []


def _canonical_parsed() -> AutoPVS1Data:
    """The X-82763936-A-T POU3F4 case used as the size-diff anchor."""
    return AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T",
            variant_type="Nonsense",
            gene_symbol="POU3F4",
            pli_score=3.29e-20,
            chgvs="c.220A>T",
            phgvs="p.Lys74*",
            external_links={
                "gnomAD": "https://gnomad.broadinstitute.org/variant/X-82763936-A-T",
                "ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na",
            },
            invalid_external_links={
                "dbSNP": "https://www.ncbi.nlm.nih.gov/snp/variation/na",
            },
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            final_strength_inferred=True,
            decision_tree=[
                FlowchartStep(code="NF1", note_id="#1"),
                FlowchartStep(code="NF5", note_id="#2"),
            ],
            notes={"#1": "Note one.", "#2": "Note two."},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="POU3F4",
                disease="DFNX2",
                inheritance="XL",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            ),
        ],
    )


def test_present_variant_full_exposes_raw_fields_for_audit() -> None:
    parsed = _canonical_parsed()
    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="full",
    )
    payload = data.model_dump(mode="json")

    assert payload["variant_info"]["external_links_raw"] == {
        "gnomAD": "https://gnomad.broadinstitute.org/variant/X-82763936-A-T",
        "ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na",
        "dbSNP": "https://www.ncbi.nlm.nih.gov/snp/variation/na",
    }
    raw_tree = payload["pvs1_flowchart"]["decision_tree_raw"]
    assert raw_tree is not None
    assert [step["code"] for step in raw_tree] == ["NF1", "NF5"]
    # raw tree has NO injected note_text (audit before notes inlining)
    assert all("note_text" not in step for step in raw_tree)


def test_present_variant_standard_omits_raw_fields() -> None:
    parsed = _canonical_parsed()
    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="standard",
    )
    payload = data.model_dump(mode="json", exclude_none=False)
    assert payload["variant_info"].get("external_links_raw") is None
    assert payload["pvs1_flowchart"].get("decision_tree_raw") is None


def test_present_variant_full_bytes_strictly_greater_than_standard() -> None:
    parsed = _canonical_parsed()
    full_data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="full",
    )
    std_data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="standard",
    )
    # Serialize both modes with the same exclude_none setting so the only
    # delta is the new raw audit fields, not asymmetric Pydantic defaults.
    full_json = json.dumps(
        full_data.model_dump(mode="json", exclude_none=True),
        separators=(",", ":"),
    )
    std_json = json.dumps(
        std_data.model_dump(mode="json", exclude_none=True),
        separators=(",", ":"),
    )

    # Direct regression guard: the raw fields are the difference.
    assert "external_links_raw" in full_json
    assert "decision_tree_raw" in full_json
    assert "external_links_raw" not in std_json
    assert "decision_tree_raw" not in std_json

    assert len(full_json) > len(std_json), (
        f"full payload ({len(full_json)}B) must exceed standard ({len(std_json)}B)"
    )


def test_present_variant_ids_only_keeps_only_identifier_genome_build_and_source_url() -> None:
    """ids_only is the lowest-bandwidth lookup tier.

    The payload must carry the upstream identifier plus enough context to
    re-fetch it (genome_build + source_url). Everything else — pvs1_flowchart,
    disease_mechanisms, external_links, variant_type, gene_symbol, etc — is
    stripped. ``exclude_none=True`` is required because the contract widens
    pvs1_flowchart to optional rather than removing it from the model.
    """
    parsed = _canonical_parsed()
    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="ids_only",
    )
    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["genome_build"] == "hg19"
    assert payload["source_url"] == "https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T"
    assert payload["variant_info"] == {"variant_id": "X-82763936-A-T"}
    # Everything else must not appear in the compact-mode payload.
    assert "pvs1_flowchart" not in payload
    assert payload.get("disease_mechanisms", []) == []
    # No warnings should leak from skipped flowchart/links work.
    assert warnings == []


def test_present_variant_ids_only_bytes_strictly_smaller_than_summary() -> None:
    """ids_only must be strictly more compact than summary on the canonical case."""
    parsed = _canonical_parsed()
    ids_only_data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="ids_only",
    )
    summary_data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="summary",
    )
    ids_only_bytes = len(
        json.dumps(ids_only_data.model_dump(mode="json", exclude_none=True), separators=(",", ":"))
    )
    summary_bytes = len(
        json.dumps(summary_data.model_dump(mode="json", exclude_none=True), separators=(",", ":"))
    )
    assert ids_only_bytes < summary_bytes, (
        f"ids_only ({ids_only_bytes}B) must be smaller than summary ({summary_bytes}B)"
    )


def test_present_cnv_ids_only_keeps_only_cnv_id_genome_build_and_source_url() -> None:
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
        disease_mechanisms=[
            DiseaseMechanism(
                gene="MYO15A",
                disease="Deafness",
                inheritance="AR",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="VeryStrong",
            ),
        ],
    )
    data, warnings = present_cnv(
        parsed,
        source_url="https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
        response_mode="ids_only",
    )
    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["genome_build"] == "hg19"
    assert payload["source_url"] == "https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL"
    assert payload["cnv_info"] == {"cnv_id": "17-15000000-20000000-DEL"}
    assert "pvs1_flowchart" not in payload
    assert payload.get("disease_mechanisms", []) == []
    assert warnings == []
