"""Enhanced client for scraping AutoPVS1 data with retry logic and circuit breaker."""

import re
from typing import Optional

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from autopvs1_link.config import settings
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
    CNVInfo,
    DiseaseMechanism,
    FlowchartStep,
    PVS1Flowchart,
    SearchResult,
    VariantInfo,
)
from autopvs1_link.utils.retry_handler import retry_handler

logger = structlog.get_logger()


class AutoPVS1Client:
    """A client for scraping data from autopvs1.bgi.com."""

    def __init__(self) -> None:
        self.base_url = settings.api.base_url
        headers = {"User-Agent": settings.api.user_agent}
        self.client = httpx.AsyncClient(
            timeout=settings.api.request_timeout,
            headers=headers,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def get_variant_data(
        self, genome_build: str, variant_id: str
    ) -> AutoPVS1Data:
        """Scrape PVS1 data for a specific variant with enhanced error handling."""
        url = f"{self.base_url}/variant/{genome_build}/{variant_id}"
        logger.info(
            "Fetching variant data",
            url=url,
            genome_build=genome_build,
            variant_id=variant_id,
        )

        try:
            response = await retry_handler.http_request_with_retry(
                self.client, "GET", url
            )
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(
                "Failed to fetch variant data",
                url=url,
                genome_build=genome_build,
                variant_id=variant_id,
                error=str(e),
            )
            raise

        variant_info = self._parse_variant_info(soup, variant_id)

        # Check if this variant is compatible with PVS1
        incompatible_text = soup.find(
            "p", string=re.compile(r"incompatible with.*PVS1")
        )
        if incompatible_text:
            # Create a simple "not applicable" flowchart
            pvs1_flowchart = PVS1Flowchart(
                preliminary_decision_path="not_applicable",
                final_strength="PVS1_Not_Applicable",
                decision_tree=[],
                notes={
                    "note_1": "This variant type is incompatible with PVS1 criterion"
                },
            )
            disease_mechanisms = []
        else:
            try:
                pvs1_flowchart = self._parse_pvs1_flowchart(soup)
                disease_mechanisms = self._parse_disease_mechanisms(soup)
            except ValueError:
                # Fallback if flowchart parsing fails
                pvs1_flowchart = PVS1Flowchart(
                    preliminary_decision_path="unknown",
                    final_strength="PVS1_Not_Determined",
                    decision_tree=[],
                    notes={"note_1": "Could not parse PVS1 flowchart"},
                )
                disease_mechanisms = []

        return AutoPVS1Data(
            genome_build=genome_build,
            variant_info=variant_info,
            pvs1_flowchart=pvs1_flowchart,
            disease_mechanisms=disease_mechanisms,
        )

    async def search_variants(
        self, query: str, genome_version: str = "hg19"
    ) -> AutoPVS1SearchResults:
        """Search for variants by gene or other criteria with enhanced error handling."""
        url = f"{self.base_url}/search"
        params = {"q": query, "genome_version": genome_version}
        logger.info(
            "Searching variants", query=query, genome_version=genome_version, url=url
        )

        try:
            response = await retry_handler.http_request_with_retry(
                self.client, "GET", url, params=params
            )
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(
                "Failed to search variants",
                url=url,
                query=query,
                genome_version=genome_version,
                error=str(e),
            )
            raise

        results = self._parse_search_results(soup, genome_version)

        return AutoPVS1SearchResults(
            query=query, genome_version=genome_version, results=results
        )

    async def get_cnv_data(self, genome_build: str, cnv_id: str) -> AutoPVS1CNVData:
        """Scrape PVS1 data for a CNV with enhanced error handling."""
        url = f"{self.base_url}/cnv/{genome_build}/{cnv_id}"
        logger.info(
            "Fetching CNV data", url=url, genome_build=genome_build, cnv_id=cnv_id
        )

        try:
            response = await retry_handler.http_request_with_retry(
                self.client, "GET", url
            )
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(
                "Failed to fetch CNV data",
                url=url,
                genome_build=genome_build,
                cnv_id=cnv_id,
                error=str(e),
            )
            raise

        cnv_info = self._parse_cnv_info(soup, cnv_id)
        pvs1_flowchart = self._parse_pvs1_flowchart(soup)
        disease_mechanisms = self._parse_disease_mechanisms(soup)

        return AutoPVS1CNVData(
            genome_build=genome_build,
            cnv_info=cnv_info,
            pvs1_flowchart=pvs1_flowchart,
            disease_mechanisms=disease_mechanisms,
        )

    def _parse_variant_info(self, soup: BeautifulSoup, variant_id: str) -> VariantInfo:
        """Parse variant information from the HTML."""
        # Try different column layouts
        info_col = soup.select_one(".container .row .col-lg-6")
        if not info_col:
            info_col = soup.select_one(".container .row .col-lg-12")
        if not info_col:
            raise ValueError("Could not find variant info section")

        # Extract variant type and name from h3
        h3_element = info_col.find("h3")
        if not h3_element:
            raise ValueError("Could not find variant title")
        h3_text = h3_element.get_text().strip()
        # Remove the icon text and extract variant info
        h3_text = h3_text.replace("🆔", "").strip()
        if ": " in h3_text:
            variant_type, variant_name = h3_text.split(": ", 1)
        else:
            # Fallback if format is different
            variant_type = "Unknown"
            variant_name = variant_id

        # Extract gene information
        gene_p = info_col.find("p", string=re.compile(r"Gene:"))
        if not gene_p:
            # Find p element containing Gene:
            for p in info_col.find_all("p"):
                if p.get_text().strip().startswith("Gene:"):
                    gene_p = p
                    break

        if gene_p:
            gene_i = gene_p.find("i")
            gene_symbol = gene_i.text.strip() if gene_i else ""
            # Try to find a link for the gene
            gene_link = gene_p.find("a")
            gene_url = gene_link.get("href") if gene_link else None
        else:
            gene_symbol = ""
            gene_url = None

        # Extract other fields
        pli_text = self._extract_field_value(info_col, "pLI:")
        pli_score = None
        if pli_text and pli_text not in ["-", "na"]:
            try:
                pli_score = float(pli_text)
            except ValueError:
                # Keep as string if it can't be converted to float
                pass

        haploinsuff_text = self._extract_field_value(info_col, "Haploinsufficiency:")
        haploinsufficiency = haploinsuff_text
        haploinsuff_url = None
        # Try to find the haploinsufficiency link
        haploinsuff_p = self._find_field_paragraph(info_col, "Haploinsufficiency:")
        if haploinsuff_p:
            haploinsuff_link = haploinsuff_p.find("a")
            if haploinsuff_link:
                haploinsufficiency = haploinsuff_link.text.strip()
                haploinsuff_url = haploinsuff_link.get("href")

        # Extract external links
        external_links = {}
        for link in info_col.find_all("a", class_="btn"):
            link_text = link.text.strip()
            link_url = link.get("href")
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
            chgvs=self._extract_field_value(info_col, "cHGVS:"),
            phgvs=self._extract_field_value(info_col, "pHGVS:"),
            exon=self._extract_field_value(info_col, "Exon:"),
            intron=self._extract_field_value(info_col, "Intron:"),
            external_links=external_links,
        )

    def _parse_pvs1_flowchart(self, soup: BeautifulSoup) -> PVS1Flowchart:
        """Parse PVS1 flowchart information.

        Extracts the PVS1 decision flowchart including the preliminary decision path,
        final strength determination, decision tree steps, and explanatory notes.

        The parsing logic is designed to handle the specific HTML structure used by
        AutoPVS1, but includes fallback mechanisms for robustness.

        Args:
            soup: BeautifulSoup object of the variant page HTML

        Returns:
            PVS1Flowchart object with parsed flowchart data

        Raises:
            ValueError: If the flowchart section cannot be found
        """
        # Find the flowchart column (typically the second col-lg-6 div)
        flowchart_columns = soup.select(".container .row .col-lg-6")
        flowchart_col = None

        # Prefer the column that contains the flowchart tree structure
        for col in flowchart_columns:
            if col.select("ul.tree"):
                flowchart_col = col
                break

        # Fallback to second column if no tree found
        if not flowchart_col and len(flowchart_columns) > 1:
            flowchart_col = flowchart_columns[1]

        if not flowchart_col:
            raise ValueError("Could not find flowchart section in HTML")

        # Extract preliminary decision path
        figcaption = flowchart_col.find("figcaption")
        preliminary_path = ""
        if figcaption:
            preliminary_path = figcaption.text.replace(
                "Preliminary Decision Path: ", ""
            ).strip()

        # Extract final strength from the deepest nested code element
        # NOTE: This heuristic searches for the PVS1 strength determination in reverse order
        # through all <code> elements in the decision tree. This approach is somewhat brittle
        # as it relies on the AutoPVS1 website's specific HTML structure where the final
        # strength appears as the last relevant <code> tag. If the website structure changes
        # (e.g., additional <code> tags are added elsewhere), this parsing may break.
        # A more robust approach would traverse the ul.tree structure to find the leaf node
        # of the longest decision path, but the current heuristic works reliably with the
        # existing HTML format.
        final_strength = ""
        flowchart_codes = flowchart_col.select("ul.tree code")
        if flowchart_codes:
            # Search in reverse order to find the final strength determination
            # Valid PVS1 strengths: Strong, Moderate, Supporting, Not applicable, Unmet
            valid_strengths = ["Strong", "Moderate", "Supporting", "Not applicable", "Unmet"]
            for code in reversed(flowchart_codes):
                text = code.text.strip()
                if text in valid_strengths:
                    final_strength = text
                    logger.debug(
                        "Found final strength",
                        strength=final_strength,
                        method="reverse_search",
                    )
                    break

        # Fallback: If no strength found in reverse search, try alternative methods
        if not final_strength:
            # Try to find strength in the deepest nested list structure
            deepest_li = flowchart_col.select("ul.tree li ul li ul li ul li")
            if deepest_li:
                for li in deepest_li:
                    code = li.find("code")
                    if code:
                        text = code.text.strip()
                        if text in ["Strong", "Moderate", "Supporting", "Not applicable", "Unmet"]:
                            final_strength = text
                            logger.debug(
                                "Found final strength",
                                strength=final_strength,
                                method="deepest_nesting",
                            )
                            break

        # Parse decision tree steps
        decision_tree = []
        for code in flowchart_codes:
            code_text = code.text.strip()
            if code_text:
                step = FlowchartStep(code=code_text)
                decision_tree.append(step)

        # Parse notes (marked with color:#CD5C5C;)
        notes = {}
        note_elements = flowchart_col.find_all("b", style=re.compile(r"color:#CD5C5C"))
        for note_elem in note_elements:
            note_id = note_elem.text.strip()
            # Find the corresponding note text
            next_elem = note_elem.find_next_sibling()
            if next_elem and hasattr(next_elem, "text"):
                notes[note_id] = next_elem.text.strip()

        return PVS1Flowchart(
            preliminary_decision_path=preliminary_path,
            final_strength=final_strength,
            decision_tree=decision_tree,
            notes=notes,
        )

    def _parse_disease_mechanisms(self, soup: BeautifulSoup) -> list[DiseaseMechanism]:
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
                # Extract gene info
                gene_cell = cols[0]
                gene_link = gene_cell.find("a")
                gene_symbol = (
                    gene_link.find("i").text
                    if gene_link and gene_link.find("i")
                    else gene_cell.text.strip()
                )
                gene_url = gene_link.get("href") if gene_link else None

                # Extract disease info
                disease_cell = cols[1]
                disease_link = disease_cell.find("a")
                disease = (
                    disease_link.text.strip()
                    if disease_link
                    else disease_cell.text.strip()
                )
                disease_url = disease_link.get("href") if disease_link else None

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

    def _parse_search_results(
        self, soup: BeautifulSoup, genome_version: str
    ) -> list[SearchResult]:
        """Parse search results from the search page."""
        results: list[SearchResult] = []

        # Find the results table
        table = soup.find("table", {"id": "dtBasicExample"})
        if not table:
            logger.warning("No search results table found")
            return results

        tbody = table.find("tbody")
        if not tbody:
            logger.warning("No table body found in search results")
            return results

        # Parse each result row
        for row in tbody.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 8:  # Need at least 8 columns
                continue

            try:
                # Extract gene symbol (column 1, inside <i> tag)
                gene_cell = cols[1]
                gene_i = gene_cell.find("i")
                gene_symbol = gene_i.text.strip() if gene_i else gene_cell.text.strip()

                # Extract variant consequence/type (column 3)
                variant_type = cols[3].text.strip()

                # Extract variant URLs for the requested genome version
                if genome_version == "hg19":
                    variant_cell = cols[6]  # hg19 variant ID column
                elif genome_version == "hg38":
                    variant_cell = cols[7]  # hg38 variant ID column
                else:
                    # Default to hg19
                    variant_cell = cols[6]

                variant_link = variant_cell.find("a")
                if not variant_link:
                    continue

                variant_url = variant_link.get("href", "")
                variant_id = variant_link.text.strip()

                # Create SearchResult
                result = SearchResult(
                    variant_id=variant_id,
                    gene=gene_symbol,
                    variant_type=variant_type,
                    genome_build=genome_version,
                    url=variant_url,
                )
                results.append(result)

            except (AttributeError, IndexError) as e:
                logger.warning("Error parsing search result row", error=str(e))
                continue

        logger.info(
            "Parsed search results", count=len(results), genome_version=genome_version
        )
        return results

    def _parse_cnv_info(self, soup: BeautifulSoup, cnv_id: str) -> CNVInfo:
        """Parse CNV information from the HTML."""
        info_col = soup.select_one(".container .row .col-lg-6")
        if not info_col:
            raise ValueError("Could not find CNV info section")

        # Extract CNV type and ID from h3
        h3_text = info_col.find("h3").text.strip()
        parts = h3_text.split(": ", 1)
        cnv_type = parts[0] if len(parts) > 1 else "CNV"
        cnv_name = parts[1] if len(parts) > 1 else cnv_id

        # Extract gene information
        gene_symbol = ""
        gene_p = info_col.find("p", string=re.compile(r"Gene:"))
        if gene_p:
            gene_link = gene_p.find("a")
            if gene_link and gene_link.find("i"):
                gene_symbol = gene_link.find("i").text

        return CNVInfo(
            cnv_id=cnv_name,
            cnv_type=cnv_type,
            gene_symbol=gene_symbol,
            coordinates=cnv_id,  # Use the ID as coordinates for now
        )

    def _extract_field_value(self, container: Tag, field_name: str) -> Optional[str]:
        """Extract field value from a container by field name.
        
        Handles HTML structure like: <p><b>Field:</b> value</p>
        """
        # First try to find paragraph containing the field name in a <b> tag
        for p in container.find_all("p"):
            b_tag = p.find("b")
            if b_tag and field_name in b_tag.text:
                # Extract the text after the <b> tag
                full_text = p.get_text()
                if ":" in full_text:
                    return full_text.split(":", 1)[1].strip()
        
        # Fallback to original method
        field_p = container.find("p", string=re.compile(re.escape(field_name)))
        if field_p:
            field_text = field_p.text
            if ":" in field_text:
                return field_text.split(":", 1)[1].strip()
        return None

    def _find_field_paragraph(self, container: Tag, field_name: str) -> Optional[Tag]:
        """Find the paragraph containing a specific field name."""
        for p in container.find_all("p"):
            b_tag = p.find("b")
            if b_tag and field_name in b_tag.text:
                return p
        
        # Fallback to string search
        return container.find("p", string=re.compile(re.escape(field_name)))

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
