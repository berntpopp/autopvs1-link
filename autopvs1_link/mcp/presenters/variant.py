"""MCP presenters for variant and CNV service results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from autopvs1_link.mcp.contracts import CNVMCPData, VariantMCPData
from autopvs1_link.mcp.envelope import MCPWarning
from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData, AutoPVS1Data


def _dump(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)


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
) -> tuple[dict[str, Any], list[MCPWarning]]:
    raw = _dump(flowchart)
    warnings: list[MCPWarning] = []
    notes = raw.get("notes") or {}
    presented_steps: list[dict[str, Any]] = []

    for step in raw.get("decision_tree", []):
        step_data = _dump(step) if isinstance(step, BaseModel) else dict(step)
        note_id = step_data.get("note_id")
        if note_id and note_id in notes:
            step_data["note_text"] = notes[note_id]
        presented_steps.append(step_data)

    raw["decision_tree"] = presented_steps
    if raw.get("final_strength_inferred"):
        warnings.append(
            MCPWarning(
                code="final_strength_inferred",
                message="final_strength was inferred from the terminal decision_tree node.",
            )
        )
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


def present_variant(
    parsed: AutoPVS1Data | dict[str, Any],
    *,
    source_url: str | None,
) -> tuple[VariantMCPData, list[MCPWarning]]:
    """Shape parsed variant data for MCP callers."""
    raw = _dump(parsed)
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

    flowchart, flowchart_warnings = _present_flowchart(raw["pvs1_flowchart"])
    warnings.extend(flowchart_warnings)

    data = VariantMCPData(
        genome_build=raw["genome_build"],
        variant_info=variant_info,
        pvs1_flowchart=flowchart,
        disease_mechanisms=list(raw.get("disease_mechanisms") or []),
        source_url=source_url,
    )
    return data, warnings


def present_cnv(
    parsed: AutoPVS1CNVData | dict[str, Any],
    *,
    source_url: str | None,
) -> tuple[CNVMCPData, list[MCPWarning]]:
    """Shape parsed CNV data for MCP callers."""
    raw = _dump(parsed)
    flowchart, warnings = _present_flowchart(raw["pvs1_flowchart"])
    data = CNVMCPData(
        genome_build=raw["genome_build"],
        cnv_info=dict(raw["cnv_info"]),
        pvs1_flowchart=flowchart,
        disease_mechanisms=list(raw.get("disease_mechanisms") or []),
        source_url=source_url,
    )
    return data, warnings
