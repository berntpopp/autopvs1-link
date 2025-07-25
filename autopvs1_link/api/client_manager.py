"""Client manager for centralized AutoPVS1Client lifecycle management."""
import asyncio
import threading
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import structlog

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import settings

logger = structlog.get_logger()


class ClientManager:
    """Singleton manager for AutoPVS1Client instances with proper lifecycle management."""

    _instance: Optional["ClientManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ClientManager":
        """Create or return the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the ClientManager instance."""
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._client: Optional[AutoPVS1Client] = None
        self._client_lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._last_request_time = 0.0
        self._request_delay = 1.0  # 1 second between requests to be respectful

        logger.info("ClientManager initialized")

    async def get_client(self) -> AutoPVS1Client:
        """Get or create the singleton AutoPVS1Client instance."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    logger.info("Creating new AutoPVS1Client instance")
                    self._client = AutoPVS1Client()

        return self._client

    @asynccontextmanager
    async def get_client_context(self) -> AsyncGenerator[AutoPVS1Client, None]:
        """Get client instance with rate limiting and proper resource management."""
        # Implement basic rate limiting to be respectful
        await self._rate_limit()
        
        client = await self.get_client()
        try:
            yield client
        except Exception as e:
            logger.error("Error during client operation", error=str(e))
            raise

    async def _rate_limit(self) -> None:
        """Simple rate limiting to be respectful to the AutoPVS1 service."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._request_delay:
            wait_time = self._request_delay - time_since_last
            logger.debug("Rate limiting: waiting", wait_time=wait_time)
            await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()

    async def health_check(self) -> dict:
        """Perform health check on the managed client."""
        try:
            client = await self.get_client()
            # Simple health check - verify client is initialized
            return {
                "status": "healthy",
                "client_initialized": client is not None,
                "base_url": settings.AUTOPVS1_BASE_URL,
                "last_request": self._last_request_time,
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "base_url": settings.AUTOPVS1_BASE_URL,
            }

    async def shutdown(self) -> None:
        """Shutdown the client manager and clean up resources."""
        logger.info("Shutting down ClientManager")
        self._shutdown_event.set()
        
        if self._client:
            try:
                await self._client.close()
                logger.info("AutoPVS1Client closed successfully")
            except Exception as e:
                logger.error("Error closing AutoPVS1Client", error=str(e))
            finally:
                self._client = None


# Global client manager instance
_client_manager: Optional[ClientManager] = None


async def get_client_manager() -> ClientManager:
    """Get the global client manager instance."""
    global _client_manager
    if _client_manager is None:
        _client_manager = ClientManager()
    return _client_manager


async def get_managed_client() -> AsyncGenerator[AutoPVS1Client, None]:
    """Get managed client dependency for FastAPI with rate limiting."""
    client_manager = await get_client_manager()
    async with client_manager.get_client_context() as client:
        yield client


async def shutdown_clients() -> None:
    """Shutdown all managed clients."""
    global _client_manager
    if _client_manager:
        await _client_manager.shutdown()
        _client_manager = None