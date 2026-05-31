"""Deterministic one-line gloss for a PVS1 decision path.

The gloss is a faithful compression of the decision-tree branch the
variant actually traversed (already parsed from the AutoPVS1 HTML) plus
the terminal strength. It introduces NO hand-authored clinical mappings:
every word comes from upstream scraped text, so the gloss is grounded and
fixture-testable. It exists to fill the summary-mode gap where the full
``decision_tree`` is stripped, so a caller can explain *why* a verdict
landed without paying a round-trip to widen to ``standard``.

ASCII ``->`` is used as the separator per the repo ASCII rule.
"""

from __future__ import annotations

from typing import Any

_ARROW = " -> "


def synthesize_path_gloss(
    steps: list[dict[str, Any]],
    *,
    final_strength: str,
    preliminary_decision_path: str,
) -> str | None:
    """Return a one-line rationale for the decision path, or ``None``.

    ``steps`` are the presented decision-tree steps (each a dict with a
    ``code`` field holding the upstream branch-node text). Consecutive
    duplicate node texts are collapsed. The terminal ``final_strength`` is
    appended unless the last node already is that strength. When there are
    no usable steps, falls back to ``"Decision path {code} -> {strength}"``
    using only the bare identifiers (no invented meaning). Returns ``None``
    only when there is no signal at all so callers drop the field instead
    of shipping an empty string.
    """
    texts: list[str] = []
    for step in steps:
        text = str(step.get("code") or "").strip()
        if text and (not texts or texts[-1] != text):
            texts.append(text)
    strength = (final_strength or "").strip()
    path = (preliminary_decision_path or "").strip()

    if not texts:
        if not path and not strength:
            return None
        return f"Decision path {path or 'unknown'}{_ARROW}{strength or 'unknown'}"

    gloss = _ARROW.join(texts)
    if strength and texts[-1].lower() != strength.lower():
        gloss = f"{gloss}{_ARROW}{strength}"
    return gloss
