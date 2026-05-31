"""Unit tests for deterministic PVS1 path-gloss synthesis."""

from __future__ import annotations

from autopvs1_link.mcp.pvs1_glossary import synthesize_path_gloss


def test_joins_branch_nodes_with_ascii_arrow_and_appends_strength() -> None:
    steps = [
        {"code": "Nonsense or Frameshift"},
        {"code": "Not predicted to undergo NMD"},
        {"code": "Removes >10% of protein"},
    ]
    gloss = synthesize_path_gloss(steps, final_strength="Strong", preliminary_decision_path="NF5")
    assert gloss == (
        "Nonsense or Frameshift -> Not predicted to undergo NMD -> "
        "Removes >10% of protein -> Strong"
    )


def test_does_not_duplicate_trailing_strength_when_last_node_is_strength() -> None:
    steps = [{"code": "Nonsense or Frameshift"}, {"code": "Strong"}]
    gloss = synthesize_path_gloss(steps, final_strength="Strong", preliminary_decision_path="NF5")
    assert gloss == "Nonsense or Frameshift -> Strong"


def test_collapses_consecutive_duplicate_nodes() -> None:
    steps = [{"code": "A"}, {"code": "A"}, {"code": "B"}]
    gloss = synthesize_path_gloss(steps, final_strength="Unmet", preliminary_decision_path="NF4")
    assert gloss == "A -> B -> Unmet"


def test_empty_tree_falls_back_to_identifiers_only() -> None:
    gloss = synthesize_path_gloss([], final_strength="Unmet", preliminary_decision_path="NF4")
    assert gloss == "Decision path NF4 -> Unmet"


def test_returns_none_when_no_signal_at_all() -> None:
    assert synthesize_path_gloss([], final_strength="", preliminary_decision_path="") is None


def test_ignores_blank_node_text() -> None:
    steps = [{"code": "  "}, {"code": "Real node"}, {"code": ""}]
    gloss = synthesize_path_gloss(
        steps, final_strength="VeryStrong", preliminary_decision_path="NF1"
    )
    assert gloss == "Real node -> VeryStrong"
