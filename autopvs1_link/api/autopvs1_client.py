"""Enhanced client for scraping AutoPVS1 data with retry logic."""

from __future__ import annotations

import re

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from autopvs1_link.api import autopvs1_parsers, autopvs1_validation
from autopvs1_link.api.autopvs1_urls import cnv_url, search_display_url, search_url, variant_url
from autopvs1_link.api.autopvs1_validation import (
    detect_hgvs_pattern,
    extract_variant_from_redirect_url,
)
from autopvs1_link.api.egress import guarded_request
from autopvs1_link.api.retry import async_retry
from autopvs1_link.config import settings
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
    CNVInfo,
    DiseaseMechanism,
    EnhancedSearchResults,
    PVS1Flowchart,
    RedirectInfo,
    SearchResult,
    VariantInfo,
)

logger = structlog.get_logger()

HGVS_PATTERNS = autopvs1_validation.HGVS_PATTERNS


class AutoPVS1Client:
    """A client for scraping data from autopvs1.bgi.com."""

    def __init__(self) -> None:
        self.base_url = settings.api.base_url
        self.policy = settings.api.egress_policy
        headers = {"User-Agent": settings.api.user_agent}
        self.client = httpx.AsyncClient(
            timeout=settings.api.request_timeout,
            headers=headers,
            follow_redirects=False,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def get_variant_data(self, genome_build: str, variant_id: str) -> AutoPVS1Data:
        """Scrape PVS1 data for a specific variant with enhanced error handling."""
        url = variant_url(self.base_url, genome_build, variant_id)
        logger.info(
            "Fetching variant data",
            url=url,
            genome_build=genome_build,
            variant_id=variant_id,
        )

        try:

            async def _fetch_variant() -> httpx.Response:
                resp = await guarded_request(self.client, self.policy, "GET", url)
                resp.raise_for_status()
                return resp

            response = await async_retry(
                _fetch_variant,
                max_attempts=settings.api.max_retries,
                base_delay=settings.api.retry_delay,
            )
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            # ``error_type`` only: str(e) can embed the variant-bearing upstream
            # URL (e.g. httpx.HTTPStatusError), which is GDPR Art. 9 data.
            logger.error(
                "Failed to fetch variant data",
                url=url,
                genome_build=genome_build,
                variant_id=variant_id,
                error_type=type(e).__name__,
            )
            raise

        return self._build_variant_data(soup, genome_build, variant_id)

    async def search_variants(
        self, query: str, genome_version: str = "hg19"
    ) -> AutoPVS1SearchResults:
        """Search for variants by gene or other criteria with enhanced error handling."""
        url = search_url(self.base_url)
        params = {"q": query, "genome_version": genome_version}
        logger.info("Searching variants", query=query, genome_version=genome_version, url=url)

        try:

            async def _search_request() -> httpx.Response:
                resp = await guarded_request(self.client, self.policy, "GET", url, params=params)
                resp.raise_for_status()
                return resp

            response = await async_retry(
                _search_request,
                max_attempts=settings.api.max_retries,
                base_delay=settings.api.retry_delay,
            )
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(
                "Failed to search variants",
                url=url,
                query=query,
                genome_version=genome_version,
                error_type=type(e).__name__,
            )
            raise

        results = autopvs1_parsers.parse_search_results(soup, genome_version)
        return AutoPVS1SearchResults(query=query, genome_version=genome_version, results=results)

    async def search_with_redirect_detection(
        self, query: str, genome_version: str = "hg19"
    ) -> EnhancedSearchResults:
        """Search with automatic redirect detection for HGVS notation."""
        url = search_url(self.base_url)
        params = {"q": query, "genome_version": genome_version}
        original_url = search_display_url(self.base_url, query, genome_version)

        logger.info(
            "Enhanced search with redirect detection",
            query=query,
            genome_version=genome_version,
            url=url,
            hgvs_detected=detect_hgvs_pattern(query),
        )

        try:

            async def _enhanced_search_request() -> httpx.Response:
                resp = await guarded_request(self.client, self.policy, "GET", url, params=params)
                resp.raise_for_status()
                return resp

            response = await async_retry(
                _enhanced_search_request,
                max_attempts=settings.api.max_retries,
                base_delay=settings.api.retry_delay,
            )
            final_url = str(response.url)

            if response.history and "/variant/" in final_url:
                logger.info(
                    "Search redirected to variant page",
                    query=query,
                    original_url=original_url,
                    final_url=final_url,
                    redirect_count=len(response.history),
                )
                return await self._handle_redirect_to_variant(
                    response, query, genome_version, original_url, final_url
                )

            logger.info("Search returned normal results page", query=query, url=final_url)
            return await self._handle_search_results_page(
                response, query, genome_version, original_url, final_url
            )

        except Exception as e:
            logger.error(
                "Failed enhanced search",
                url=url,
                query=query,
                genome_version=genome_version,
                error_type=type(e).__name__,
            )
            raise

    async def resolve_hgvs_notation(self, hgvs: str, genome_version: str = "hg19") -> AutoPVS1Data:
        """Direct HGVS notation resolution to variant data."""
        if not detect_hgvs_pattern(hgvs):
            logger.warning("Query doesn't appear to be HGVS notation", query=hgvs)

        enhanced_result = await self.search_with_redirect_detection(hgvs, genome_version)

        if enhanced_result.is_single_variant and enhanced_result.variant_data:
            return enhanced_result.variant_data
        raise ValueError(
            f"HGVS notation '{hgvs}' did not resolve to a single variant. "
            f"Got {len(enhanced_result.search_results.results) if enhanced_result.search_results else 0} results."
        )

    async def get_cnv_data(self, genome_build: str, cnv_id: str) -> AutoPVS1CNVData:
        """Scrape PVS1 data for a CNV with enhanced error handling."""
        url = cnv_url(self.base_url, genome_build, cnv_id)
        logger.info("Fetching CNV data", url=url, genome_build=genome_build, cnv_id=cnv_id)

        try:

            async def _fetch_cnv() -> httpx.Response:
                resp = await guarded_request(self.client, self.policy, "GET", url)
                resp.raise_for_status()
                return resp

            response = await async_retry(
                _fetch_cnv,
                max_attempts=settings.api.max_retries,
                base_delay=settings.api.retry_delay,
            )
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as e:
            logger.error(
                "Failed to fetch CNV data",
                url=url,
                genome_build=genome_build,
                cnv_id=cnv_id,
                error_type=type(e).__name__,
            )
            raise

        return AutoPVS1CNVData(
            genome_build=genome_build,
            cnv_info=autopvs1_parsers.parse_cnv_info(soup, cnv_id),
            pvs1_flowchart=autopvs1_parsers.parse_pvs1_flowchart(soup),
            disease_mechanisms=autopvs1_parsers.parse_disease_mechanisms(soup),
        )

    def _build_variant_data(
        self, soup: BeautifulSoup, genome_build: str, variant_id: str
    ) -> AutoPVS1Data:
        variant_info = autopvs1_parsers.parse_variant_info(soup, variant_id)
        pvs1_flowchart, disease_mechanisms = self._parse_variant_pvs1_sections(soup)
        return AutoPVS1Data(
            genome_build=genome_build,
            variant_info=variant_info,
            pvs1_flowchart=pvs1_flowchart,
            disease_mechanisms=disease_mechanisms,
        )

    def _parse_variant_pvs1_sections(
        self, soup: BeautifulSoup
    ) -> tuple[PVS1Flowchart, list[DiseaseMechanism]]:
        incompatible_pattern = re.compile(r"incompatible with.*PVS1")
        incompatible_text = next(
            (p for p in soup.find_all("p") if incompatible_pattern.search(p.get_text())),
            None,
        )
        if incompatible_text:
            return (
                PVS1Flowchart(
                    preliminary_decision_path="not_applicable",
                    final_strength="PVS1_Not_Applicable",
                    decision_tree=[],
                    notes={"note_1": "This variant type is incompatible with PVS1 criterion"},
                ),
                [],
            )

        try:
            return (
                autopvs1_parsers.parse_pvs1_flowchart(soup),
                autopvs1_parsers.parse_disease_mechanisms(soup),
            )
        except ValueError:
            return (
                PVS1Flowchart(
                    preliminary_decision_path="unknown",
                    final_strength="PVS1_Not_Determined",
                    decision_tree=[],
                    notes={"note_1": "Could not parse PVS1 flowchart"},
                ),
                [],
            )

    def _parse_variant_info(self, soup: BeautifulSoup, variant_id: str) -> VariantInfo:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.parse_variant_info(soup, variant_id)

    def _parse_pvs1_flowchart(self, soup: BeautifulSoup) -> PVS1Flowchart:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.parse_pvs1_flowchart(soup)

    def _parse_disease_mechanisms(self, soup: BeautifulSoup) -> list[DiseaseMechanism]:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.parse_disease_mechanisms(soup)

    def _parse_search_results(self, soup: BeautifulSoup, genome_version: str) -> list[SearchResult]:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.parse_search_results(soup, genome_version)

    def _parse_cnv_info(self, soup: BeautifulSoup, cnv_id: str) -> CNVInfo:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.parse_cnv_info(soup, cnv_id)

    def _extract_field_value(self, container: Tag, field_name: str) -> str | None:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.extract_field_value(container, field_name)

    def _find_field_paragraph(self, container: Tag, field_name: str) -> Tag | None:
        """Compatibility wrapper for parser tests and existing callers."""
        return autopvs1_parsers.find_field_paragraph(container, field_name)

    def _detect_hgvs_pattern(self, query: str) -> bool:
        """Compatibility wrapper for parser tests and existing callers."""
        return detect_hgvs_pattern(query)

    def _extract_variant_from_redirect_url(self, url: str) -> tuple[str | None, str | None]:
        """Compatibility wrapper for parser tests and existing callers."""
        return extract_variant_from_redirect_url(url)

    async def _handle_redirect_to_variant(
        self,
        response: httpx.Response,
        query: str,
        genome_version: str,
        original_url: str,
        final_url: str,
    ) -> EnhancedSearchResults:
        """Handle redirect to variant page by parsing variant data."""
        genome_build, variant_id = extract_variant_from_redirect_url(final_url)
        soup = BeautifulSoup(response.text, "lxml")
        variant_data = self._build_variant_data(
            soup, genome_build or genome_version, variant_id or "unknown"
        )
        redirect_info = RedirectInfo(
            original_url=original_url,
            final_url=final_url,
            redirect_detected=True,
            variant_id_extracted=variant_id,
            genome_build_extracted=genome_build,
        )
        return EnhancedSearchResults(
            query=query,
            genome_version=genome_version,
            redirected=True,
            variant_data=variant_data,
            redirect_info=redirect_info,
        )

    async def _handle_search_results_page(
        self,
        response: httpx.Response,
        query: str,
        genome_version: str,
        original_url: str,
        final_url: str,
    ) -> EnhancedSearchResults:
        """Handle normal search results page."""
        soup = BeautifulSoup(response.text, "lxml")
        results = autopvs1_parsers.parse_search_results(soup, genome_version)
        search_results = AutoPVS1SearchResults(
            query=query, genome_version=genome_version, results=results
        )
        return EnhancedSearchResults(
            query=query,
            genome_version=genome_version,
            redirected=False,
            search_results=search_results,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
