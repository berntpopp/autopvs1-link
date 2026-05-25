"""HTML parsers for AutoPVS1 pages."""

from __future__ import annotations

import re
from contextlib import suppress

import structlog
from bs4 import BeautifulSoup, Tag

from autopvs1_link.models.autopvs1_models import (
    CNVInfo,
    DiseaseMechanism,
    FlowchartStep,
    PVS1Flowchart,
    SearchResult,
    VariantInfo,
)

logger = structlog.get_logger()

PVS1_STRENGTH_LABELS = {
    "VeryStrong",
    "Strong",
    "Moderate",
    "Supporting",
    "Not applicable",
    "Unmet",
    "Strong_RWS",
    "Moderate_RWS",
    "Supporting_RWS",
}


def _href(tag: Tag | None) -> str | None:
    if tag is None:
        return None
    value = tag.get("href")
    return value if isinstance(value, str) else None


def _collapse_html_text(tag: Tag) -> str:
    """Return visible text with HTML layout whitespace collapsed."""
    return re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()


def _match_strength_candidate(candidate: str) -> str:
    """Match a strength label at the start of candidate text."""
    candidate = re.sub(r"\s+", " ", candidate).strip()
    for strength in sorted(PVS1_STRENGTH_LABELS, key=len, reverse=True):
        if candidate == strength or candidate.startswith(f"{strength} "):
            return strength
    return ""


def _extract_strength_after_label(text: str, pattern: re.Pattern[str]) -> str:
    """Extract the first recognized strength immediately after a final-strength label."""
    match = pattern.search(text)
    if not match:
        return ""
    return _match_strength_candidate(match.group(1))


def _contains_flowchart_tree(tag: Tag) -> bool:
    """Return whether tag is or contains the decision-tree markup."""
    is_tree = tag.name == "ul" and "tree" in tag.get_attribute_list("class")
    return is_tree or tag.select_one("ul.tree") is not None


def _extract_strength_from_next_sibling(tag: Tag) -> str:
    """Extract a strength from the first non-tree sibling after tag."""
    for sibling in tag.next_siblings:
        if isinstance(sibling, Tag):
            if _contains_flowchart_tree(sibling):
                return ""
            candidate = _collapse_html_text(sibling)
        else:
            candidate = re.sub(r"\s+", " ", str(sibling)).strip()
        if candidate:
            return _match_strength_candidate(candidate)
    return ""


def _extract_strength_from_label_sibling(text_node: object) -> str:
    """Extract a strength from a sibling after the label or its field container."""
    parent = getattr(text_node, "parent", None)
    if not isinstance(parent, Tag):
        return ""

    strength = _extract_strength_from_next_sibling(parent)
    if strength:
        return strength

    container = parent.parent
    if isinstance(container, Tag) and not _contains_flowchart_tree(container):
        return _extract_strength_from_next_sibling(container)
    return ""


def _extract_explicit_final_strength(flowchart_col: Tag) -> str:
    """Extract an explicit final-strength label if the HTML exposes one."""
    final_strength_pattern = re.compile(r"Final\s+Strength\s*:\s*(.+)", re.IGNORECASE)
    for text_node in flowchart_col.find_all(string=final_strength_pattern):
        strength = _extract_strength_after_label(str(text_node), final_strength_pattern)
        if strength:
            return strength

    final_strength_label_pattern = re.compile(r"Final\s+Strength\s*:", re.IGNORECASE)
    for text_node in flowchart_col.find_all(string=final_strength_label_pattern):
        parent = text_node.parent
        candidate_tags = [parent]
        if isinstance(parent, Tag):
            candidate_tags.append(parent.parent)
        for tag in candidate_tags:
            if not isinstance(tag, Tag) or _contains_flowchart_tree(tag):
                continue
            strength = _extract_strength_after_label(
                _collapse_html_text(tag), final_strength_pattern
            )
            if strength:
                return strength
        strength = _extract_strength_from_label_sibling(text_node)
        if strength:
            return strength
    return ""


def _infer_terminal_strength(flowchart_codes: list[Tag]) -> str:
    """Infer final strength only when the terminal decision-tree code is recognized."""
    if not flowchart_codes:
        return ""

    text = _collapse_html_text(flowchart_codes[-1])
    if text in PVS1_STRENGTH_LABELS:
        logger.debug("Found final strength", strength=text, method="terminal_code")
        return text
    return ""


def parse_variant_info(soup: BeautifulSoup, variant_id: str) -> VariantInfo:
    """Parse variant information from the HTML."""
    info_col = soup.select_one(".container .row .col-lg-6")
    if not info_col:
        info_col = soup.select_one(".container .row .col-lg-12")
    if not info_col:
        raise ValueError("Could not find variant info section")

    h3_element = info_col.find("h3")
    if not h3_element:
        raise ValueError("Could not find variant title")
    h3_text = h3_element.get_text().strip()
    h3_text = h3_text.replace("🆔", "").strip()
    if ": " in h3_text:
        variant_type, variant_name = h3_text.split(": ", 1)
    else:
        variant_type = "Unknown"
        variant_name = variant_id

    gene_p = None
    for p in info_col.find_all("p"):
        if p.get_text().strip().startswith("Gene:"):
            gene_p = p
            break

    if isinstance(gene_p, Tag):
        gene_i = gene_p.find("i")
        gene_symbol = gene_i.text.strip() if isinstance(gene_i, Tag) else ""
        gene_link = gene_p.find("a")
        gene_url = _href(gene_link if isinstance(gene_link, Tag) else None)
    else:
        gene_symbol = ""
        gene_url = None

    pli_text = extract_field_value(info_col, "pLI:")
    pli_score = None
    if pli_text and pli_text not in ["-", "na"]:
        with suppress(ValueError):
            pli_score = float(pli_text)

    haploinsuff_text = extract_field_value(info_col, "Haploinsufficiency:")
    haploinsufficiency = haploinsuff_text
    haploinsuff_url = None
    haploinsuff_p = find_field_paragraph(info_col, "Haploinsufficiency:")
    if haploinsuff_p:
        haploinsuff_link = haploinsuff_p.find("a")
        if isinstance(haploinsuff_link, Tag):
            haploinsufficiency = haploinsuff_link.text.strip()
            haploinsuff_url = _href(haploinsuff_link)

    external_links: dict[str, str] = {}
    for link in info_col.find_all("a", class_="btn"):
        link_text = link.text.strip()
        link_url = _href(link if isinstance(link, Tag) else None)
        if link_text and link_url:
            external_links[link_text] = link_url

    return VariantInfo(
        variant_id=variant_name.strip(),
        variant_type=variant_type.strip(),
        gene_symbol=gene_symbol,
        gene_url=gene_url,
        pli_score=pli_score,
        haploinsufficiency=haploinsufficiency,
        haploinsufficiency_url=haploinsuff_url,
        chgvs=extract_field_value(info_col, "cHGVS:"),
        phgvs=extract_field_value(info_col, "pHGVS:"),
        exon=extract_field_value(info_col, "Exon:"),
        intron=extract_field_value(info_col, "Intron:"),
        external_links=external_links,
    )


def parse_pvs1_flowchart(soup: BeautifulSoup) -> PVS1Flowchart:
    """Parse PVS1 flowchart information."""
    flowchart_columns = soup.select(".container .row .col-lg-6")
    flowchart_col: Tag | None = None

    for col in flowchart_columns:
        if col.select("ul.tree"):
            flowchart_col = col
            break

    if not flowchart_col and len(flowchart_columns) > 1:
        flowchart_col = flowchart_columns[1]

    if not flowchart_col:
        raise ValueError("Could not find flowchart section in HTML")

    figcaption = flowchart_col.find("figcaption")
    preliminary_path = ""
    if figcaption:
        preliminary_path = figcaption.text.replace("Preliminary Decision Path: ", "").strip()

    flowchart_codes = flowchart_col.select("ul.tree code")
    final_strength = ""
    final_strength_inferred = False

    explicit_strength = _extract_explicit_final_strength(flowchart_col)
    if explicit_strength:
        final_strength = explicit_strength
    else:
        final_strength = _infer_terminal_strength(flowchart_codes)
        final_strength_inferred = bool(final_strength)

    decision_tree = []
    for code in flowchart_codes:
        code_text = code.text.strip()
        if code_text:
            decision_tree.append(FlowchartStep(code=code_text))

    notes = {}
    note_elements = flowchart_col.find_all("b", style=re.compile(r"color:#CD5C5C"))
    for note_elem in note_elements:
        note_id = note_elem.text.strip()
        next_elem = note_elem.find_next_sibling()
        if next_elem and hasattr(next_elem, "text"):
            notes[note_id] = next_elem.text.strip()

    return PVS1Flowchart(
        preliminary_decision_path=preliminary_path,
        final_strength=final_strength,
        final_strength_inferred=final_strength_inferred,
        decision_tree=decision_tree,
        notes=notes,
    )


def parse_disease_mechanisms(soup: BeautifulSoup) -> list[DiseaseMechanism]:
    """Parse disease mechanism table."""
    table = soup.find("table", class_="table-bordered")
    if not table:
        return []

    disease_mechanisms = []
    tbody = table.find("tbody")
    if not tbody:
        return []

    for row in tbody.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) >= 6:
            gene_cell = cols[0]
            gene_link = gene_cell.find("a")
            gene_i = gene_link.find("i") if isinstance(gene_link, Tag) else None
            gene_symbol = gene_i.text if isinstance(gene_i, Tag) else gene_cell.text.strip()
            gene_url = _href(gene_link if isinstance(gene_link, Tag) else None)

            disease_cell = cols[1]
            disease_link = disease_cell.find("a")
            disease = (
                disease_link.text.strip()
                if isinstance(disease_link, Tag)
                else disease_cell.text.strip()
            )
            disease_url = _href(disease_link if isinstance(disease_link, Tag) else None)

            disease_mechanisms.append(
                DiseaseMechanism(
                    gene=gene_symbol,
                    gene_url=gene_url,
                    disease=disease,
                    disease_url=disease_url,
                    inheritance=cols[2].text.strip(),
                    clinical_validity=cols[3].text.strip(),
                    consideration=cols[4].text.strip(),
                    adjusted_strength=cols[5].text.strip(),
                )
            )

    return disease_mechanisms


def parse_search_results(soup: BeautifulSoup, genome_version: str) -> list[SearchResult]:
    """Parse search results from the search page."""
    results: list[SearchResult] = []
    table = soup.find("table", {"id": "dtBasicExample"})
    if not table:
        logger.warning("No search results table found")
        return results

    tbody = table.find("tbody")
    if not tbody:
        logger.warning("No table body found in search results")
        return results

    for row in tbody.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        try:
            gene_cell = cols[1]
            gene_i = gene_cell.find("i")
            gene_symbol = gene_i.text.strip() if gene_i else gene_cell.text.strip()
            variant_type = cols[3].text.strip()

            if genome_version == "hg19":
                variant_cell = cols[6]
            elif genome_version == "hg38":
                variant_cell = cols[7]
            else:
                variant_cell = cols[6]

            variant_link = variant_cell.find("a")
            if not variant_link:
                continue

            results.append(
                SearchResult(
                    variant_id=variant_link.text.strip(),
                    gene=gene_symbol,
                    variant_type=variant_type,
                    genome_build=genome_version,
                    url=_href(variant_link if isinstance(variant_link, Tag) else None) or "",
                )
            )
        except (AttributeError, IndexError) as e:
            logger.warning("Error parsing search result row", error=str(e))
            continue

    logger.info("Parsed search results", count=len(results), genome_version=genome_version)
    return results


def parse_cnv_info(soup: BeautifulSoup, cnv_id: str) -> CNVInfo:
    """Parse CNV information from the HTML."""
    info_col = soup.select_one(".container .row .col-lg-6")
    if not info_col:
        raise ValueError("Could not find CNV info section")

    h3 = info_col.find("h3")
    h3_text = h3.text.strip() if h3 else cnv_id
    parts = h3_text.split(": ", 1)
    cnv_type = parts[0] if len(parts) > 1 else "CNV"
    cnv_name = parts[1] if len(parts) > 1 else cnv_id

    gene_symbol = ""
    gene_p = None
    for p in info_col.find_all("p"):
        if p.get_text().strip().startswith("Gene:"):
            gene_p = p
            break
    if isinstance(gene_p, Tag):
        gene_link = gene_p.find("a")
        gene_i = gene_link.find("i") if isinstance(gene_link, Tag) else None
        if isinstance(gene_i, Tag):
            gene_symbol = gene_i.text

    return CNVInfo(
        cnv_id=cnv_name,
        cnv_type=cnv_type,
        gene_symbol=gene_symbol,
        coordinates=cnv_id,
    )


def extract_field_value(container: Tag, field_name: str) -> str | None:
    """Extract field value from a container by field name."""
    for p in container.find_all("p"):
        b_tag = p.find("b")
        if b_tag and field_name in b_tag.text:
            full_text = p.get_text()
            if ":" in full_text:
                return full_text.split(":", 1)[1].strip()

    field_p = find_field_paragraph(container, field_name)
    if field_p:
        field_text = field_p.get_text()
        if ":" in field_text:
            return field_text.split(":", 1)[1].strip()
    return None


def find_field_paragraph(container: Tag, field_name: str) -> Tag | None:
    """Find the paragraph containing a specific field name."""
    for p in container.find_all("p"):
        b_tag = p.find("b")
        if b_tag and field_name in b_tag.text:
            return p

    return None
