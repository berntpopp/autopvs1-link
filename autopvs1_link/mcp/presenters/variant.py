"""MCP presenters for variant and CNV service results."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.contracts import CNVMCPData, VariantMCPData
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.mcp.mode_validation import ResponseMode, normalize_response_mode
from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData, AutoPVS1Data

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


def _present_flowchart(
    flowchart: BaseModel | dict[str, Any],
    *,
    response_mode: ResponseMode,
) -> tuple[dict[str, Any], list[MCPWarning]]:
    raw = _dump(flowchart)
    warnings: list[MCPWarning] = []
    notes = raw.get("notes") or {}
    presented_steps: list[dict[str, Any]] = []
    final_strength_inferred = bool(raw.pop("final_strength_inferred", False))
    raw["final_strength_source"] = "inferred" if final_strength_inferred else "asserted"

    for step in raw.get("decision_tree", []):
        step_data = _dump(step) if isinstance(step, BaseModel) else dict(step)
        note_id = step_data.get("note_id")
        if note_id and note_id in notes:
            step_data["note_text"] = notes[note_id]
        presented_steps.append(step_data)

    raw["decision_tree"] = presented_steps
    if final_strength_inferred and response_mode != "summary":
        warnings.append(
            MCPWarning(
                code="final_strength_inferred",
                message="final_strength was inferred from the terminal decision_tree node.",
            )
        )
    if response_mode == "summary":
        raw = {
            "preliminary_decision_path": raw["preliminary_decision_path"],
            "final_strength": raw["final_strength"],
            "final_strength_source": raw["final_strength_source"],
        }
    return raw, warnings


def _present_external_links(
    raw_info: dict[str, Any],
) -> tuple[dict[str, str | None], list[MCPWarning]]:
    warnings: list[MCPWarning] = []
    links: dict[str, str | None] = dict(raw_info.get("external_links") or {})
    invalid_links: dict[str, str] = dict(raw_info.get("invalid_external_links") or {})

    for label, url in list(links.items()):
        if not url or url.rstrip("/").endswith("/variation/na"):
            invalid_links[label] = url or ""

    for label, url in invalid_links.items():
        links[label] = None
        warnings.append(
            MCPWarning(
                code="invalid_external_link",
                message=f"{label} link from upstream AutoPVS1 was invalid and was nulled.",
            )
        )
        raw_info.setdefault("_invalid_external_link_urls", {})[label] = url

    return links, warnings


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
    cnv_info["size"] = str(end - start)
    return cnv_info


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
    warnings: list[MCPWarning] = []

    variant_info = dict(raw["variant_info"])
    invalid_external_links = _invalid_links_from_variant(parsed)
    if invalid_external_links:
        variant_info["invalid_external_links"] = invalid_external_links
    variant_info["pli_score_display"] = format_pli_score(variant_info.get("pli_score"))
    external_links, link_warnings = _present_external_links(variant_info)
    variant_info["external_links"] = external_links
    variant_info.pop("invalid_external_links", None)
    variant_info.pop("_invalid_external_link_urls", None)
    warnings.extend(link_warnings)
    if mode == "summary":
        variant_info = {
            key: variant_info[key]
            for key in ("variant_id", "variant_type", "gene_symbol")
            if key in variant_info
        }

    flowchart, flowchart_warnings = _present_flowchart(raw["pvs1_flowchart"], response_mode=mode)
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
    flowchart, warnings = _present_flowchart(raw["pvs1_flowchart"], response_mode=mode)
    disease_mechanisms = list(raw.get("disease_mechanisms") or [])
    if mode == "summary":
        disease_mechanisms = []
    elif not _normalize_include_unmet(include_unmet):
        disease_mechanisms = [
            row
            for row in disease_mechanisms
            if str(row.get("adjusted_strength", "")).strip().lower() != "unmet"
        ]
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
