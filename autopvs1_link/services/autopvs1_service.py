"""Enhanced service layer for AutoPVS1 business logic with advanced caching."""

import structlog

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import settings
from autopvs1_link.middleware.logging_middleware import PerformanceLogger
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
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
    async def get_variant_data(
        self, genome_build: str, variant_id: str
    ) -> AutoPVS1Data:
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
        with PerformanceLogger(
            "variant_search", query=query, genome_version=genome_version
        ):
            logger.info(
                "Searching variants", query=query, genome_version=genome_version
            )

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
        key_func=lambda self, genome_build, cnv_id: f"cnv:{genome_build}:{cnv_id}",
    )
    async def get_cnv_data(self, genome_build: str, cnv_id: str) -> AutoPVS1CNVData:
        """Get CNV data with enhanced caching and statistics."""
        with PerformanceLogger(
            "cnv_data_fetch", genome_build=genome_build, cnv_id=cnv_id
        ):
            logger.info("Fetching CNV data", genome_build=genome_build, cnv_id=cnv_id)
            return await self.client.get_cnv_data(genome_build, cnv_id)

    async def clear_cache(self) -> None:
        """Clear all caches with enhanced statistics."""
        logger.info("Clearing service caches")

        # Clear individual method caches
        self.get_variant_data.cache_clear()
        self.search_variants.cache_clear()
        self.get_cnv_data.cache_clear()

        # Clear cache statistics
        cache_manager.clear_statistics()

        logger.info("Service caches and statistics cleared")

    async def get_cache_info(self) -> dict:
        """Get enhanced cache statistics with detailed metrics."""
        # Get basic cache info
        cache_info = {
            "variant_cache": self.get_variant_data.cache_info()._asdict(),
            "search_cache": self.search_variants.cache_info()._asdict(),
            "cnv_cache": self.get_cnv_data.cache_info()._asdict(),
        }

        # Get enhanced statistics
        enhanced_stats = cache_manager.get_statistics()

        # Merge both sets of statistics
        for method_name in ["get_variant_data", "search_variants", "get_cnv_data"]:
            if method_name in enhanced_stats:
                cache_key = (
                    f"{method_name.replace('get_', '').replace('_data', '_cache')}"
                )
                if cache_key in cache_info:
                    cache_info[cache_key].update(enhanced_stats[method_name])

        return cache_info

    async def get_cache_statistics(self, method_name: str = None) -> dict:
        """Get detailed cache statistics for debugging and monitoring."""
        return cache_manager.get_statistics(method_name)

    async def clear_cache_statistics(self, method_name: str = None) -> None:
        """Clear cache statistics for a specific method or all methods."""
        cache_manager.clear_statistics(method_name)
