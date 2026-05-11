"""Enhanced service layer for AutoPVS1 business logic with advanced caching."""

import structlog

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import settings
from autopvs1_link.middleware.logging_middleware import PerformanceLogger
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
    EnhancedSearchResults,
)
from autopvs1_link.utils.cache_manager import cache_manager

logger = structlog.get_logger()


class AutoPVS1Service:
    """Service for AutoPVS1 operations with caching."""

    def __init__(self, client: AutoPVS1Client):
        self.client = client

    @cache_manager.enhanced_cache(
        maxsize=settings.cache.size,
        ttl=settings.cache.ttl_seconds,
        key_func=lambda self, genome_build, variant_id: f"variant:{genome_build}:{variant_id}",
    )
    async def get_variant_data(self, genome_build: str, variant_id: str) -> AutoPVS1Data:
        """Get variant data with enhanced caching and error handling."""
        with PerformanceLogger(
            "variant_data_fetch", genome_build=genome_build, variant_id=variant_id
        ):
            logger.info(
                "Fetching variant data",
                genome_build=genome_build,
                variant_id=variant_id,
            )

            return await self.client.get_variant_data(genome_build, variant_id)

    @cache_manager.enhanced_cache(
        maxsize=settings.cache.size,
        ttl=settings.cache.ttl_seconds,
        key_func=lambda self, query, genome_version="hg19": f"search:{query}:{genome_version}",
    )
    async def search_variants(
        self, query: str, genome_version: str = "hg19"
    ) -> AutoPVS1SearchResults:
        """Search variants with enhanced caching and error handling."""
        with PerformanceLogger("variant_search", query=query, genome_version=genome_version):
            logger.info("Searching variants", query=query, genome_version=genome_version)

            result = await self.client.search_variants(query, genome_version)
            logger.debug(
                "Search completed",
                result_count=len(result.results),
                query=query,
                genome_version=genome_version,
            )
            return result

    @cache_manager.enhanced_cache(
        maxsize=settings.cache.size,
        ttl=settings.cache.ttl_seconds,
        key_func=lambda self, query, genome_version="hg19": (
            f"enhanced_search:{query}:{genome_version}"
        ),
    )
    async def search_with_redirect_detection(
        self, query: str, genome_version: str = "hg19"
    ) -> EnhancedSearchResults:
        """Enhanced search with redirect detection and caching."""
        with PerformanceLogger("enhanced_search", query=query, genome_version=genome_version):
            logger.info(
                "Enhanced search with redirect detection",
                query=query,
                genome_version=genome_version,
            )

            result = await self.client.search_with_redirect_detection(query, genome_version)

            if result.redirected:
                logger.info(
                    "Search redirected to variant",
                    query=query,
                    variant_id=(
                        result.redirect_info.variant_id_extracted if result.redirect_info else None
                    ),
                    genome_build=(
                        result.redirect_info.genome_build_extracted
                        if result.redirect_info
                        else None
                    ),
                )
            else:
                logger.debug(
                    "Search returned multiple results",
                    query=query,
                    result_count=(
                        len(result.search_results.results) if result.search_results else 0
                    ),
                )

            return result

    @cache_manager.enhanced_cache(
        maxsize=settings.cache.size,
        ttl=settings.cache.ttl_seconds,
        key_func=lambda self, hgvs, genome_version="hg19": f"hgvs:{hgvs}:{genome_version}",
    )
    async def resolve_hgvs_notation(self, hgvs: str, genome_version: str = "hg19") -> AutoPVS1Data:
        """Direct HGVS notation resolution with caching."""
        with PerformanceLogger("hgvs_resolution", hgvs=hgvs, genome_version=genome_version):
            logger.info("Resolving HGVS notation", hgvs=hgvs, genome_version=genome_version)

            result = await self.client.resolve_hgvs_notation(hgvs, genome_version)

            logger.info(
                "HGVS resolution completed",
                hgvs=hgvs,
                resolved_variant=result.variant_info.variant_id,
                gene=result.variant_info.gene_symbol,
                final_strength=result.pvs1_flowchart.final_strength,
            )

            return result

    @cache_manager.enhanced_cache(
        maxsize=settings.cache.size,
        ttl=settings.cache.ttl_seconds,
        key_func=lambda self, genome_build, cnv_id: f"cnv:{genome_build}:{cnv_id}",
    )
    async def get_cnv_data(self, genome_build: str, cnv_id: str) -> AutoPVS1CNVData:
        """Get CNV data with enhanced caching and statistics."""
        with PerformanceLogger("cnv_data_fetch", genome_build=genome_build, cnv_id=cnv_id):
            logger.info("Fetching CNV data", genome_build=genome_build, cnv_id=cnv_id)
            return await self.client.get_cnv_data(genome_build, cnv_id)

    async def clear_cache(self) -> None:
        """Clear all caches with enhanced statistics."""
        logger.info("Clearing service caches")

        # Clear individual method caches
        self.get_variant_data.cache_clear()
        self.search_variants.cache_clear()
        self.search_with_redirect_detection.cache_clear()
        self.resolve_hgvs_notation.cache_clear()
        self.get_cnv_data.cache_clear()

        # Clear cache statistics
        cache_manager.clear_statistics()

        logger.info("Service caches and statistics cleared")

    async def get_cache_statistics(self, method_name: str = None) -> dict:
        """Get comprehensive cache statistics from cache manager (single source of truth)."""
        return cache_manager.get_statistics(method_name)

    async def clear_cache_statistics(self, method_name: str = None) -> None:
        """Clear cache statistics for a specific method or all methods."""
        cache_manager.clear_statistics(method_name)
