"""MCP presenters for variant and CNV service results."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.contracts import CNVMCPData, VariantMCPData
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.mcp.mode_validation import ResponseMode, normalize_response_mode
from autopvs1_link.mcp.pvs1_glossary import synthesize_path_gloss
from autopvs1_link.mcp.untrusted_content import (
    UntrustedText,
    enforce_untrusted_text_limits,
    fence_untrusted_text,
)
from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData, AutoPVS1Data

_UNTRUSTED_SOURCE = "autopvs1"

CNV_ID_RE = re.compile(
    r"^(?P<chrom>[1-9]|1[0-9]|2[0-2]|X|Y|MT)-(?P<start>[1-9][0-9]*)-"
    r"(?P<end>[1-9][0-9]*)-(?P<type>DEL|DUP)$"
)


def _dump(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)


def _normalize_response_mode(response_mode: Any) -> ResponseMode:
    return normalize_response_mode(response_mode)


def _normalize_include_unmet(include_unmet: Any) -> bool:
    if isinstance(include_unmet, bool):
        return include_unmet
    if isinstance(include_unmet, str):
        normalized = include_unmet.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return True


def format_pli_score(value: float | None) -> str | None:
    """Format pLI for stable LLM display without changing the numeric value."""
    if value is None:
        return None
    if value == 0:
        return "0"
    if 0 < abs(value) < 1e-3:
        return f"{value:.2e}"
    return f"{value:.4g}"


_AMBIGUOUS_VERDICT_STRENGTHS = frozenset(
    {
        "Moderate",
        "Supporting",
        "Unmet",
        "PVS1_Not_Applicable",
        "PVS1_Not_Determined",
    }
)

# Mirrors autopvs1_parsers.PVS1_STRENGTH_LABELS plus the two sentinel
# verdicts the client assigns when a section is missing/incompatible.
# Anything outside this set means the scraped HTML shape changed.
_KNOWN_FINAL_STRENGTHS = frozenset(
    {
        "VeryStrong",
        "Strong",
        "Moderate",
        "Supporting",
        "Not applicable",
        "Unmet",
        "Strong_RWS",
        "Moderate_RWS",
        "Supporting_RWS",
        "PVS1_Not_Applicable",
        "PVS1_Not_Determined",
    }
)


class UpstreamFormatError(ValueError):
    """Scraped HTML does not satisfy the reviewed AutoPVS1 result contract."""


def _terminal_note(
    *,
    presented_steps: list[dict[str, Any]],
    notes: dict[str, str],
    preliminary_decision_path: str,
) -> str | None:
    """Return the one-line rationale for the leaf of the decision tree.

    Prefers the last step's hoisted ``note_text`` because that is the
    actual leaf the path landed on. Falls back to
    ``notes[preliminary_decision_path]`` when the upstream tree is empty
    (some non-applicable verdicts arrive with no steps). Returns ``None``
    when neither source provides a non-empty note so callers can drop the
    field instead of shipping an empty string.
    """
    for step in reversed(presented_steps):
        text = step.get("note_text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    fallback = notes.get(preliminary_decision_path)
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return None


def _fence_prose(raw_text: str, *, record_id: str, fenced: list[UntrustedText]) -> dict[str, Any]:
    """Fence one upstream scraped-prose leaf and record it for limit enforcement."""
    obj = fence_untrusted_text(raw_text, source=_UNTRUSTED_SOURCE, record_id=record_id)
    fenced.append(obj)
    return obj.model_dump(mode="json")


def _fence_step(
    step: dict[str, Any], *, record_id: str, fenced: list[UntrustedText]
) -> dict[str, Any]:
    """Fence a decision-tree step's upstream prose leaves (``code`` is the
    PVS1 criterion description itself; ``description``/``note_text`` are
    optional companion prose). ``note_id`` is a short marker, not prose."""
    out = dict(step)
    code = out.get("code")
    if isinstance(code, str):
        out["code"] = _fence_prose(code, record_id=record_id, fenced=fenced)
    description = out.get("description")
    if isinstance(description, str) and description:
        out["description"] = _fence_prose(description, record_id=record_id, fenced=fenced)
    note_text = out.get("note_text")
    if isinstance(note_text, str) and note_text:
        out["note_text"] = _fence_prose(note_text, record_id=record_id, fenced=fenced)
    return out


def _fence_flowchart_output(
    raw: dict[str, Any], *, record_id: str
) -> tuple[dict[str, Any], list[UntrustedText]]:
    """Fence every AutoPVS1 scraped-prose leaf in the shaped flowchart dict.

    Runs once, after the mode-branching has settled on the final wire shape.
    Each scraped prose is emitted exactly once (Response-Envelope v1.1
    no-duplication): ``decision_tree`` carries ``code`` + ``note_text`` in
    standard/full; ``terminal_note`` and ``path_gloss`` appear only in
    summary mode where ``decision_tree`` is absent, so nothing is fenced
    twice.
    """
    fenced: list[UntrustedText] = []
    if "decision_tree" in raw:
        raw["decision_tree"] = [
            _fence_step(step, record_id=record_id, fenced=fenced) for step in raw["decision_tree"]
        ]
    if raw.get("terminal_note"):
        raw["terminal_note"] = _fence_prose(
            raw["terminal_note"], record_id=record_id, fenced=fenced
        )
    if raw.get("path_gloss"):
        raw["path_gloss"] = _fence_prose(raw["path_gloss"], record_id=record_id, fenced=fenced)
    return raw, fenced


def _present_flowchart(
    flowchart: BaseModel | dict[str, Any],
    *,
    response_mode: ResponseMode,
    record_id: str,
) -> tuple[dict[str, Any], list[MCPWarning], list[UntrustedText]]:
    raw = _dump(flowchart)
    warnings: list[MCPWarning] = []
    notes = raw.get("notes") or {}
    final_strength_inferred = bool(raw.pop("final_strength_inferred", False))
    raw["final_strength_source"] = "inferred" if final_strength_inferred else "asserted"

    final_strength = str(raw.get("final_strength") or "")
    if final_strength not in _KNOWN_FINAL_STRENGTHS:
        raise UpstreamFormatError(f"unrecognized final strength from AutoPVS1: {final_strength!r}")
    if final_strength in {"PVS1_Not_Applicable", "PVS1_Not_Determined"}:
        warnings.append(
            MCPWarning(
                code="pvs1_not_applicable",
                message=(
                    "AutoPVS1 returned a sentinel strength "
                    f"'{final_strength}' indicating PVS1 is not applicable "
                    "to this variant. Treat as a non-PVS1-scorable result."
                ),
            )
        )

    raw_decision_tree = [
        _dump(step) if isinstance(step, BaseModel) else dict(step)
        for step in raw.get("decision_tree", [])
    ]
    # The list is typed ``list[dict[str, Any]]`` on the contract so the
    # outer Pydantic exclude_none does not recurse into it. Strip null
    # fields here so the audit-mode wire payload matches the same
    # null-free contract the rest of the data layer follows.
    raw_decision_tree = [
        {key: value for key, value in step.items() if value is not None}
        for step in raw_decision_tree
    ]
    presented_steps: list[dict[str, Any]] = []
    for step in raw_decision_tree:
        step_data = dict(step)
        note_id = step_data.get("note_id")
        if note_id and note_id in notes:
            step_data["note_text"] = notes[note_id]
        presented_steps.append(step_data)

    raw["decision_tree"] = presented_steps
    path_gloss = synthesize_path_gloss(
        presented_steps,
        final_strength=final_strength,
        preliminary_decision_path=str(raw.get("preliminary_decision_path") or ""),
    )
    if response_mode == "summary":
        summary: dict[str, Any] = {
            "preliminary_decision_path": raw["preliminary_decision_path"],
            "final_strength": raw["final_strength"],
            "final_strength_source": raw["final_strength_source"],
        }
        # Surface the leaf rationale when the verdict is ambiguous so a
        # summary-mode caller can explain why a non-Strong/Very-Strong
        # outcome landed where it did, without paying the round-trip to
        # widen to standard. Strong / Very_Strong verdicts already
        # convey the rationale via the path code and the note adds no
        # signal worth ~80 bytes.
        if final_strength in _AMBIGUOUS_VERDICT_STRENGTHS:
            note = _terminal_note(
                presented_steps=presented_steps,
                notes=notes,
                preliminary_decision_path=raw["preliminary_decision_path"],
            )
            if note is not None:
                summary["terminal_note"] = note
        # path_gloss embeds the scraped node text. It rides here ONLY because
        # summary mode strips decision_tree, so it is the single carrier of
        # that prose — never a duplicate (Response-Envelope v1.1).
        if path_gloss is not None:
            summary["path_gloss"] = path_gloss
        raw = summary
    else:
        # standard/full: decision_tree is the single canonical carrier of
        # every scraped code + hoisted note_text. Drop the duplicative notes
        # legend and do NOT re-embed the same prose in path_gloss or a
        # decision_tree_raw audit copy (v1.1 no-duplication rule).
        raw.pop("notes", None)
    raw, fenced = _fence_flowchart_output(raw, record_id=record_id)
    return raw, warnings, fenced


def _present_external_links(
    raw_info: dict[str, Any],
) -> tuple[dict[str, str | None], dict[str, str | None], list[MCPWarning]]:
    """Return (links_for_display, raw_links_audit, warnings).

    ``links_for_display`` nulls invalid URLs. ``raw_links_audit`` preserves
    every label's URL as upstream returned it — including the invalid
    sentinel URLs that get nulled in ``links_for_display``. The caller
    decides whether to expose the audit dict (full mode only).
    """
    warnings: list[MCPWarning] = []
    links: dict[str, str | None] = dict(raw_info.get("external_links") or {})
    invalid_links: dict[str, str] = dict(raw_info.get("invalid_external_links") or {})

    for label, url in list(links.items()):
        if not url or url.rstrip("/").endswith("/variation/na"):
            invalid_links[label] = url or ""

    raw_audit: dict[str, str | None] = {}
    for label, url in links.items():
        raw_audit[label] = url
    for label, url in invalid_links.items():
        raw_audit[label] = url or None
        links[label] = None
        warnings.append(
            MCPWarning(
                code="invalid_external_link",
                message=f"{label} link from upstream AutoPVS1 was invalid and was nulled.",
            )
        )

    return links, raw_audit, warnings


def _invalid_links_from_variant(parsed: AutoPVS1Data | dict[str, Any]) -> dict[str, str]:
    """Read parser-internal invalid links before excluded fields are dumped."""
    if isinstance(parsed, AutoPVS1Data):
        return dict(parsed.variant_info.invalid_external_links)
    variant_info = dict(parsed.get("variant_info") or {})
    return dict(variant_info.get("invalid_external_links") or {})


def _enrich_cnv_info(cnv_info: dict[str, Any]) -> dict[str, Any]:
    cnv_id = str(cnv_info.get("cnv_id") or cnv_info.get("coordinates") or "").strip().upper()
    match = CNV_ID_RE.fullmatch(cnv_id)
    if not match:
        return cnv_info

    start = int(match.group("start"))
    end = int(match.group("end"))
    cnv_info["cnv_type"] = match.group("type")
    cnv_info["size"] = end - start
    return cnv_info


def _fence_disease_mechanisms(
    rows: list[dict[str, Any]], *, record_id: str, fenced: list[UntrustedText]
) -> list[dict[str, Any]]:
    """Fence each row's scraped ``disease`` name; ``gene``/inheritance/validity
    /consideration/adjusted_strength stay bare — they are short controlled
    vocabulary (HGNC symbol, ClinGen categories), not free prose."""
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        row = dict(row)
        disease = row.get("disease")
        if isinstance(disease, str):
            row["disease"] = _fence_prose(
                disease, record_id=f"{record_id}#disease:{index}", fenced=fenced
            )
        out.append(row)
    return out


def present_variant(
    parsed: AutoPVS1Data | dict[str, Any],
    *,
    source_url: str | None,
    response_mode: Any = "standard",
    include_unmet: Any = True,
) -> tuple[VariantMCPData, list[MCPWarning]]:
    """Shape parsed variant data for MCP callers."""
    raw = _dump(parsed)
    mode = _normalize_response_mode(response_mode)
    # cHGVS is upstream's own "{transcript}:{variant}" notation (e.g.
    # "NM_000307.5:c.604A>T") when AutoPVS1 extracted one; fall back to
    # "{genome_build}:{variant_id}" (always present) otherwise.
    raw_variant_info = raw.get("variant_info") or {}
    record_id = str(raw_variant_info.get("chgvs") or "").strip() or (
        f"{raw['genome_build']}:{raw_variant_info.get('variant_id', '')}"
    )

    if mode == "ids_only":
        return (
            VariantMCPData(
                genome_build=raw["genome_build"],
                variant_info={"variant_id": raw["variant_info"]["variant_id"]},
                pvs1_flowchart=None,
                disease_mechanisms=[],
                source_url=source_url,
            ),
            [],
        )

    warnings: list[MCPWarning] = []

    variant_info = dict(raw["variant_info"])
    invalid_external_links = _invalid_links_from_variant(parsed)
    if invalid_external_links:
        variant_info["invalid_external_links"] = invalid_external_links
    variant_info["pli_score_display"] = format_pli_score(variant_info.get("pli_score"))
    external_links, external_links_raw, link_warnings = _present_external_links(variant_info)
    variant_info["external_links"] = external_links
    variant_info.pop("invalid_external_links", None)
    variant_info.pop("_invalid_external_link_urls", None)
    warnings.extend(link_warnings)
    if mode == "full":
        variant_info["external_links_raw"] = external_links_raw
    if mode == "summary":
        variant_info = {
            key: variant_info[key]
            for key in ("variant_id", "variant_type", "gene_symbol")
            if key in variant_info
        }
        # external_links is gone from the wire in summary mode; the
        # ``invalid_external_link`` warning would dangle, pointing at a
        # field the caller cannot see. Drop it so summary callers do not
        # see warnings about suppressed fields.
        warnings = [w for w in warnings if w.code != "invalid_external_link"]

    flowchart, flowchart_warnings, fenced_objects = _present_flowchart(
        raw["pvs1_flowchart"], response_mode=mode, record_id=record_id
    )
    warnings.extend(flowchart_warnings)
    disease_mechanisms = list(raw.get("disease_mechanisms") or [])
    if mode == "summary":
        disease_mechanisms = []
    elif not _normalize_include_unmet(include_unmet):
        disease_mechanisms = [
            row
            for row in disease_mechanisms
            if str(row.get("adjusted_strength", "")).strip().lower() != "unmet"
        ]
    disease_mechanisms = _fence_disease_mechanisms(
        disease_mechanisms, record_id=record_id, fenced=fenced_objects
    )
    # One limits call over every untrusted_text object this response emits
    # (flowchart prose + disease-mechanism names combined), not per-record —
    # the 128-object / 8 MiB-total ceilings must bound the whole payload.
    enforce_untrusted_text_limits(fenced_objects)

    data = VariantMCPData(
        genome_build=raw["genome_build"],
        variant_info=variant_info,
        pvs1_flowchart=flowchart,
        disease_mechanisms=disease_mechanisms,
        source_url=source_url,
    )
    return data, warnings


def present_cnv(
    parsed: AutoPVS1CNVData | dict[str, Any],
    *,
    source_url: str | None,
    response_mode: Any = "standard",
    include_unmet: Any = True,
) -> tuple[CNVMCPData, list[MCPWarning]]:
    """Shape parsed CNV data for MCP callers."""
    raw = _dump(parsed)
    mode = _normalize_response_mode(response_mode)
    raw_cnv_info = raw.get("cnv_info") or {}
    record_id = f"{raw['genome_build']}:{raw_cnv_info.get('cnv_id', '')}"

    if mode == "ids_only":
        return (
            CNVMCPData(
                genome_build=raw["genome_build"],
                cnv_info={"cnv_id": raw["cnv_info"]["cnv_id"]},
                pvs1_flowchart=None,
                disease_mechanisms=[],
                source_url=source_url,
            ),
            [],
        )

    flowchart, warnings, fenced_objects = _present_flowchart(
        raw["pvs1_flowchart"], response_mode=mode, record_id=record_id
    )
    disease_mechanisms = list(raw.get("disease_mechanisms") or [])
    if mode == "summary":
        disease_mechanisms = []
    elif not _normalize_include_unmet(include_unmet):
        disease_mechanisms = [
            row
            for row in disease_mechanisms
            if str(row.get("adjusted_strength", "")).strip().lower() != "unmet"
        ]
    disease_mechanisms = _fence_disease_mechanisms(
        disease_mechanisms, record_id=record_id, fenced=fenced_objects
    )
    # One limits call over every untrusted_text object this response emits.
    enforce_untrusted_text_limits(fenced_objects)
    cnv_info = _enrich_cnv_info(dict(raw["cnv_info"]))
    if mode == "summary":
        cnv_info = {
            key: cnv_info[key]
            for key in ("cnv_id", "cnv_type", "gene_symbol", "coordinates")
            if key in cnv_info
        }
    data = CNVMCPData(
        genome_build=raw["genome_build"],
        cnv_info=cnv_info,
        pvs1_flowchart=flowchart,
        disease_mechanisms=disease_mechanisms,
        source_url=source_url,
    )
    return data, warnings
