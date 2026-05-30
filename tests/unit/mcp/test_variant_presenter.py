"""Tests for variant and CNV MCP presenters."""

import json

from autopvs1_link.mcp.envelope import ok_envelope
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

_EXTERNAL_LINK_DICTS = {"external_links", "external_links_raw"}


def _has_null_field(node: object, path: str = "") -> str | None:
    """Return the dotted path of the first null FIELD inside ``node``.

    Recurses into nested objects but NOT into ``external_links``-style
    dicts, where null values are semantically meaningful (an upstream link
    we deliberately nulled because it was invalid; the matching warning
    carries the same info).
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if value is None:
                return f"{path}.{key}" if path else key
            if key in _EXTERNAL_LINK_DICTS:
                continue
            hit = _has_null_field(value, f"{path}.{key}" if path else key)
            if hit:
                return hit
    if isinstance(node, list):
        for idx, value in enumerate(node):
            hit = _has_null_field(value, f"{path}[{idx}]")
            if hit:
                return hit
    return None


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

    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["genome_build"] == "hg38"
    assert payload["variant_info"]["variant_id"] == "X-1-A-T"
    assert payload["variant_info"]["gene_symbol"] == "GENE"
    # Summary trims variant_info to {variant_id, variant_type, gene_symbol}
    # and the wire payload drops null-default keys, so external_links and
    # chgvs disappear entirely.
    assert "external_links" not in payload["variant_info"]
    assert "chgvs" not in payload["variant_info"]
    assert payload["pvs1_flowchart"]["final_strength"] == "Strong"
    assert payload["pvs1_flowchart"]["final_strength_source"] == "inferred"
    assert payload["pvs1_flowchart"]["decision_tree"] == []
    # ``notes`` is duplicative in summary mode and drops from the wire.
    assert "notes" not in payload["pvs1_flowchart"]
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


def test_present_variant_standard_drops_notes_dict_because_steps_carry_text() -> None:
    """``notes`` is duplicative in standard mode; ``note_text`` is hoisted per step.

    Regression for an LLM-consumer report that the top-level ``notes`` dict
    repeated content already on each ``decision_tree`` step, costing tokens
    for no parseability gain. Audit-trail use cases keep the dict via
    ``response_mode='full'``.
    """
    parsed = _canonical_parsed()
    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="standard",
    )
    payload = data.model_dump(mode="json", exclude_none=True)
    assert "notes" not in payload["pvs1_flowchart"], (
        "standard mode must drop notes dict (steps carry note_text)"
    )
    # The resolved note text still has to ride along on each step.
    note_texts = [step.get("note_text") for step in payload["pvs1_flowchart"]["decision_tree"]]
    assert "Note one." in note_texts
    assert "Note two." in note_texts


def test_ok_envelope_standard_mode_data_has_no_null_leaves() -> None:
    """Wire payload in standard mode must contain zero null leaves.

    Regression for an LLM-consumer report flagging ~15-25% wasted tokens on
    ``decision_tree_raw: null``, ``external_links_raw: null``, per-step
    ``description: null``/``note_text: null``, etc. Standard mode's wire
    shape is the dominant cost path for first-turn LLM calls.
    """
    parsed = _canonical_parsed()
    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="standard",
    )
    envelope = ok_envelope(data, warnings=warnings)
    hit = _has_null_field(envelope["data"])
    assert hit is None, f"standard-mode wire data must drop null fields; first hit: {hit}"
    # And the specific fields the LLM-consumer flagged are gone:
    assert "decision_tree_raw" not in envelope["data"]["pvs1_flowchart"]
    assert "external_links_raw" not in envelope["data"]["variant_info"]
    # Inner dict nulls inside external_links are semantically intentional and stay.
    assert envelope["data"]["variant_info"]["external_links"]["ClinVar"] is None


def test_ok_envelope_full_mode_data_has_no_null_fields() -> None:
    """Full mode also drops null fields; raw audit fields stay populated."""
    parsed = _canonical_parsed()
    data, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="full",
    )
    envelope = ok_envelope(data, warnings=warnings)
    hit = _has_null_field(envelope["data"])
    assert hit is None, f"full-mode wire data must drop null fields; first hit: {hit}"
    # And the audit fields are still present:
    assert "decision_tree_raw" in envelope["data"]["pvs1_flowchart"]
    assert "external_links_raw" in envelope["data"]["variant_info"]


def test_present_variant_summary_drops_invalid_external_link_warning() -> None:
    """``invalid_external_link`` references a field that is gone in summary mode.

    Regression: summary mode trims variant_info to {variant_id, variant_type,
    gene_symbol} — ``external_links`` is dropped. But the warning continued
    to ride along, telling callers about a field they could not see. The
    warning is meaningful only when ``external_links`` is on the wire.
    """
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T",
            variant_type="Nonsense",
            gene_symbol="POU3F4",
            external_links={"gnomAD": "https://example.test/v"},
            invalid_external_links={
                "ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na",
            },
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    _, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="summary",
    )
    codes = [w.code for w in warnings]
    assert "invalid_external_link" not in codes, (
        "summary mode hides external_links from the wire; the warning is dangling"
    )


def test_present_variant_standard_still_emits_invalid_external_link_warning() -> None:
    """Standard mode keeps ``external_links`` so the warning is still useful."""
    parsed = AutoPVS1Data(
        genome_build="hg19",
        variant_info=VariantInfo(
            variant_id="X-82763936-A-T",
            variant_type="Nonsense",
            gene_symbol="POU3F4",
            external_links={"gnomAD": "https://example.test/v"},
            invalid_external_links={
                "ClinVar": "https://www.ncbi.nlm.nih.gov/clinvar/variation/na",
            },
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[],
    )
    _, warnings = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="standard",
    )
    codes = [w.code for w in warnings]
    assert "invalid_external_link" in codes


def test_present_variant_full_keeps_notes_dict_for_audit() -> None:
    """``notes`` survives in full mode so auditors can cross-check the legend."""
    parsed = _canonical_parsed()
    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg19/X-82763936-A-T",
        response_mode="full",
    )
    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["pvs1_flowchart"]["notes"] == {
        "#1": "Note one.",
        "#2": "Note two.",
    }


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


# ---------------------------------------------------------------------------
# Summary-mode terminal_note for ambiguous verdicts (v1.2 polish)
# ---------------------------------------------------------------------------


def test_present_variant_summary_emits_terminal_note_for_moderate_verdict() -> None:
    """An ambiguous verdict must hoist the leaf rationale into summary mode.

    Pre-fix: rs80357906-style Moderate verdicts shipped summary with an
    empty decision_tree and no rationale, forcing a second round-trip to
    standard tier just to read the why. Now the leaf step's note_text
    rides along under ``terminal_note`` for Moderate / Supporting /
    Unmet / PVS1_Not_* sentinels.
    """
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF6",
            final_strength="Moderate",
            final_strength_inferred=True,
            decision_tree=[FlowchartStep(code="NF6", note_id="#6")],
            notes={"#6": "Truncated > 10% of CDS but downstream of distal-disease cutoff."},
        ),
    )

    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg38/X-1-A-T",
        response_mode="summary",
    )

    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["pvs1_flowchart"]["final_strength"] == "Moderate"
    assert payload["pvs1_flowchart"]["terminal_note"].startswith("Truncated > 10%")


def test_present_variant_summary_omits_terminal_note_for_strong_verdict() -> None:
    """Strong/Very_Strong verdicts already convey rationale via path code.

    No need to spend ~80 bytes echoing the leaf note when the verdict is
    unambiguous — keep summary mode lean for the common case.
    """
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF1",
            final_strength="Strong",
            decision_tree=[FlowchartStep(code="NF1", note_id="#1")],
            notes={"#1": "Stop codon in canonical NMD-target exon."},
        ),
    )

    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg38/X-1-A-T",
        response_mode="summary",
    )

    payload = data.model_dump(mode="json", exclude_none=True)
    assert "terminal_note" not in payload["pvs1_flowchart"]


def test_present_variant_summary_terminal_note_falls_back_to_notes_legend() -> None:
    """When the decision tree is empty, fall back to notes[preliminary_decision_path].

    Some non-applicable verdicts arrive with no steps but a populated
    notes legend keyed by the path code.
    """
    parsed = AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-1-A-T",
            variant_type="Nonsense",
            gene_symbol="GENE",
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="not_applicable",
            final_strength="PVS1_Not_Applicable",
            decision_tree=[],
            notes={"not_applicable": "PVS1 does not apply: gene is not LoF-intolerant."},
        ),
    )

    data, _ = present_variant(
        parsed,
        source_url="https://autopvs1.bgi.com/variant/hg38/X-1-A-T",
        response_mode="summary",
    )

    payload = data.model_dump(mode="json", exclude_none=True)
    assert payload["pvs1_flowchart"]["terminal_note"].startswith("PVS1 does not apply")
