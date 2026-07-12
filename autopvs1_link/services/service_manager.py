"""Service manager for centralized AutoPVS1Service lifecycle management."""

import asyncio
import threading
from typing import Optional

import structlog

from autopvs1_link.api.client_manager import get_client_manager
from autopvs1_link.services.autopvs1_service import AutoPVS1Service

logger = structlog.get_logger()


class ServiceManager:
    """Singleton manager for AutoPVS1Service instances with proper lifecycle management."""

    _instance: Optional["ServiceManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ServiceManager":
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ServiceManager instance."""
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._service: AutoPVS1Service | None = None
        self._service_lock = asyncio.Lock()

        logger.info("ServiceManager initialized")

    async def get_service(self) -> AutoPVS1Service:
        """Get or create the singleton AutoPVS1Service instance."""
        if self._service is None:
            async with self._service_lock:
                if self._service is None:
                    logger.info("Creating new AutoPVS1Service instance")
                    # Get managed client from client manager
                    client_manager = await get_client_manager()
                    client = await client_manager.get_client()
                    self._service = AutoPVS1Service(client)

        return self._service

    async def health_check(self) -> dict:
        """Perform health check on the managed service."""
        try:
            service = await self.get_service()
            cache_info = await service.get_cache_statistics()

            return {
                "status": "healthy",
                "service_initialized": service is not None,
                "cache_info": cache_info,
            }
        except Exception as e:
            # Log the exception CLASS only: str(e) can embed the variant-bearing
            # upstream URL (GDPR Art. 9 / finding F-03).
            logger.error("Service health check failed", error_type=type(e).__name__)
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    async def clear_all_caches(self) -> dict:
        """Clear all service caches."""
        try:
            service = await self.get_service()
            await service.clear_cache()
            logger.info("All service caches cleared")

            return {
                "status": "success",
                "message": "All caches cleared successfully",
            }
        except Exception as e:
            logger.error("Error clearing caches", error_type=type(e).__name__)
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_cache_statistics(self) -> dict:
        """Get cache statistics from the service."""
        try:
            service = await self.get_service()
            return await service.get_cache_statistics()
        except Exception as e:
            logger.error("Error getting cache statistics", error_type=type(e).__name__)
            return {
                "error": str(e),
            }

    async def shutdown(self) -> None:
        """Shutdown the service manager and clean up resources."""
        logger.info("Shutting down ServiceManager")

        if self._service:
            try:
                # Clear caches before shutdown
                await self._service.clear_cache()
                logger.info("Service caches cleared during shutdown")
            except Exception as e:
                logger.error("Error during service shutdown", error_type=type(e).__name__)
            finally:
                self._service = None


# Global service manager instance
_service_manager: ServiceManager | None = None


async def get_service_manager() -> ServiceManager:
    """Get the global service manager instance."""
    global _service_manager
    if _service_manager is None:
        _service_manager = ServiceManager()
    return _service_manager


async def get_managed_service() -> AutoPVS1Service:
    """Get managed service dependency for FastAPI."""
    service_manager = await get_service_manager()
    return await service_manager.get_service()


async def shutdown_services() -> None:
    """Shutdown all managed services."""
    global _service_manager
    if _service_manager:
        await _service_manager.shutdown()
        _service_manager = None
