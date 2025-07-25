"""Service layer for AutoPVS1 business logic."""

import structlog
from async_lru import alru_cache

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import settings
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
)
from autopvs1_link.middleware.logging_middleware import (
    PerformanceLogger,
    log_cache_operation,
)

logger = structlog.get_logger()


class AutoPVS1Service:
    """Service for AutoPVS1 operations with caching."""

    def __init__(self, client: AutoPVS1Client):
        self.client = client

    @alru_cache(maxsize=settings.CACHE_SIZE)
    async def get_variant_data(
        self, genome_build: str, variant_id: str
    ) -> AutoPVS1Data:
        """Get variant data with caching."""
        cache_key = f"variant:{genome_build}:{variant_id}"
        
        with PerformanceLogger("variant_data_fetch", genome_build=genome_build, variant_id=variant_id):
            logger.info(
                "Fetching variant data", genome_build=genome_build, variant_id=variant_id
            )
            
            try:
                result = await self.client.get_variant_data(genome_build, variant_id)
                await log_cache_operation("fetch", cache_key)
                return result
            except Exception as e:
                await log_cache_operation("error", cache_key, error=str(e))
                raise

    @alru_cache(maxsize=settings.CACHE_SIZE)
    async def search_variants(
        self, query: str, genome_version: str = "hg19"
    ) -> AutoPVS1SearchResults:
        """Search variants with caching."""
        cache_key = f"search:{query}:{genome_version}"
        
        with PerformanceLogger("variant_search", query=query, genome_version=genome_version):
            logger.info("Searching variants", query=query, genome_version=genome_version)
            
            try:
                result = await self.client.search_variants(query, genome_version)
                await log_cache_operation("fetch", cache_key, result_count=len(result.results))
                return result
            except Exception as e:
                await log_cache_operation("error", cache_key, error=str(e))
                raise

    @alru_cache(maxsize=settings.CACHE_SIZE)
    async def get_cnv_data(self, genome_build: str, cnv_id: str) -> AutoPVS1CNVData:
        """Get CNV data with caching."""
        cache_key = f"cnv:{genome_build}:{cnv_id}"
        
        with PerformanceLogger("cnv_data_fetch", genome_build=genome_build, cnv_id=cnv_id):
            logger.info("Fetching CNV data", genome_build=genome_build, cnv_id=cnv_id)
            
            try:
                result = await self.client.get_cnv_data(genome_build, cnv_id)
                await log_cache_operation("fetch", cache_key)
                return result
            except Exception as e:
                await log_cache_operation("error", cache_key, error=str(e))
                raise

    async def clear_cache(self) -> None:
        """Clear all caches."""
        logger.info("Clearing service caches")
        self.get_variant_data.cache_clear()
        self.search_variants.cache_clear()
        self.get_cnv_data.cache_clear()

    async def get_cache_info(self) -> dict:
        """Get cache statistics."""
        return {
            "variant_cache": self.get_variant_data.cache_info()._asdict(),
            "search_cache": self.search_variants.cache_info()._asdict(),
            "cnv_cache": self.get_cnv_data.cache_info()._asdict(),
        }
