"""Unified server supporting both REST API and MCP protocols with STDIO protection."""

import asyncio
import io
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from autopvs1_link.api.routes import cnv, variant
from autopvs1_link.config import settings
from autopvs1_link.logging_config import configure_logging
from autopvs1_link.middleware.logging_middleware import RequestLoggingMiddleware
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1CNVData,
    AutoPVS1Data,
    AutoPVS1SearchResults,
)
from autopvs1_link.services.service_manager import get_managed_service
from autopvs1_link.utils.retry_handler import retry_handler

logger = structlog.get_logger()


class STDIOProtection:
    """Context manager to protect STDIO during MCP operations."""

    def __init__(self, suppress_output: bool = True):
        self.suppress_output = suppress_output
        self.original_stdout = None
        self.original_stderr = None
        self.null_buffer = None

    def __enter__(self):
        if self.suppress_output:
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            self.null_buffer = io.StringIO()
            sys.stdout = self.null_buffer
            sys.stderr = self.null_buffer
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.suppress_output and self.original_stdout:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.original_stdout = None
            self.original_stderr = None
            if self.null_buffer:
                self.null_buffer.close()


@contextmanager
def stdio_protection(suppress_output: bool = True):
    """Context manager for STDIO protection."""
    protection = STDIOProtection(suppress_output)
    with protection:
        yield protection


# Unified server manager for lifecycle management
class UnifiedServerManager:
    """Manages the lifecycle of both FastAPI and MCP components."""

    def __init__(self):
        self._initialized = False
        self._client_manager = None
        self._service_manager = None

    async def initialize(self):
        """Initialize all managers and services."""
        if self._initialized:
            return

        configure_logging()

        # Initialize managers
        from autopvs1_link.api.client_manager import get_client_manager
        from autopvs1_link.services.service_manager import get_service_manager

        self._client_manager = await get_client_manager()
        self._service_manager = await get_service_manager()

        # Pre-initialize services for connection pooling
        await self._client_manager.get_client()
        await self._service_manager.get_service()

        logger.info("Unified server manager initialized")
        self._initialized = True

    async def shutdown(self):
        """Shutdown all managers and clean up resources."""
        if not self._initialized:
            return

        logger.info("Shutting down unified server manager")

        # Shutdown services
        from autopvs1_link.api.client_manager import shutdown_clients
        from autopvs1_link.services.service_manager import shutdown_services

        await shutdown_services()
        await shutdown_clients()

        self._initialized = False
        logger.info("Unified server manager shutdown complete")

    async def get_health_status(self) -> dict:
        """Get comprehensive health status."""
        if not self._initialized:
            return {"status": "not_initialized"}

        client_health = await self._client_manager.health_check()
        service_health = await self._service_manager.health_check()
        circuit_breaker_status = retry_handler.get_all_circuit_breaker_status()

        overall_status = (
            "healthy"
            if client_health["status"] == "healthy"
            and service_health["status"] == "healthy"
            else "unhealthy"
        )

        return {
            "status": overall_status,
            "service": "autopvs1-link",
            "version": settings.version,
            "environment": settings.environment,
            "client": client_health,
            "service_health": service_health,
            "circuit_breakers": circuit_breaker_status,
            "cache_enabled": settings.cache.enabled,
        }


# Global server manager
server_manager = UnifiedServerManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for unified server."""
    logger.info("AutoPVS1 Link unified server starting up")

    # Initialize server manager
    await server_manager.initialize()

    yield

    # Shutdown server manager
    await server_manager.shutdown()
    logger.info("AutoPVS1 Link unified server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="AutoPVS1 Link Unified Server",
    description="Unified API for scraping PVS1 data from autopvs1.bgi.com with MCP support",
    version=settings.version,
    lifespan=lifespan,
)

# Add middleware with STDIO protection
with stdio_protection(settings.mcp.enable_stdio_protection):
    app.add_middleware(RequestLoggingMiddleware)

    # Add CORS middleware
    if settings.server.cors_origins:
        origins = [origin.strip() for origin in settings.server.cors_origins.split(",")]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

# Include routers
app.include_router(variant.router)
app.include_router(cnv.router)


# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with server information."""
    return {
        "message": "Welcome to the AutoPVS1 Link Unified Server!",
        "version": settings.version,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/health",
        "mcp_enabled": True,
        "features": [
            "REST API",
            "MCP Protocol",
            "Advanced Caching",
            "Circuit Breaker",
            "Retry Logic",
            "STDIO Protection",
        ],
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Enhanced health check endpoint."""
    return await server_manager.get_health_status()


@app.get("/api/cache/stats", tags=["Management"])
async def get_cache_stats():
    """Get enhanced cache statistics."""
    from autopvs1_link.services.service_manager import get_service_manager

    service_manager_inst = await get_service_manager()
    return await service_manager_inst.get_cache_statistics()


@app.post("/api/cache/clear", tags=["Management"])
async def clear_cache():
    """Clear all caches and statistics."""
    from autopvs1_link.services.service_manager import get_service_manager

    service_manager_inst = await get_service_manager()
    return await service_manager_inst.clear_all_caches()


@app.get("/api/circuit-breakers", tags=["Management"])
async def get_circuit_breaker_status():
    """Get circuit breaker status for all services."""
    return {
        "circuit_breakers": retry_handler.get_all_circuit_breaker_status(),
        "global_enabled": True,
    }


# MCP Tool definitions with STDIO protection
with stdio_protection(settings.mcp.enable_stdio_protection):
    # Create MCP server from FastAPI app
    mcp_custom_names = {
        "get_variant_pvs1_data": "get_variant_analysis",
        "search_variants": "search_genetic_variants",
        "get_cnv_pvs1_data": "get_cnv_analysis",
    }

    # Create MCP instance from FastAPI
    mcp = FastMCP.from_fastapi(
        app=app,
        name=settings.mcp.name,
        mcp_names=mcp_custom_names if settings.mcp.custom_tool_names else None,
    )


# Direct MCP tool definitions for better control
@mcp.tool()
async def get_variant_analysis(genome_build: str, variant_id: str) -> AutoPVS1Data:
    """Get comprehensive PVS1 analysis data for a genetic variant.

    Args:
        genome_build: Genome build version (e.g., 'hg19', 'hg38')
        variant_id: Unique identifier for the variant

    Returns:
        Complete PVS1 analysis including variant info, flowchart, and disease mechanisms
    """
    with stdio_protection(settings.mcp.enable_stdio_protection):
        logger.info(
            "MCP tool: get_variant_analysis",
            genome_build=genome_build,
            variant_id=variant_id,
        )
        service = await get_managed_service()
        return await service.get_variant_data(genome_build, variant_id)


@mcp.tool()
async def search_genetic_variants(
    query: str, genome_version: str = "hg19"
) -> AutoPVS1SearchResults:
    """Search for genetic variants by gene name or other criteria.

    Args:
        query: Search query (gene name, variant identifier, etc.)
        genome_version: Genome version to search (default: 'hg19')

    Returns:
        Search results containing matching variants with their basic information
    """
    with stdio_protection(settings.mcp.enable_stdio_protection):
        logger.info(
            "MCP tool: search_genetic_variants",
            query=query,
            genome_version=genome_version,
        )
        service = await get_managed_service()
        return await service.search_variants(query, genome_version)


@mcp.tool()
async def get_cnv_analysis(genome_build: str, cnv_id: str) -> AutoPVS1CNVData:
    """Get comprehensive PVS1 analysis data for a copy number variant (CNV).

    Args:
        genome_build: Genome build version (e.g., 'hg19', 'hg38')
        cnv_id: Unique identifier for the CNV

    Returns:
        Complete PVS1 analysis for CNV including info, flowchart, and disease mechanisms
    """
    with stdio_protection(settings.mcp.enable_stdio_protection):
        logger.info(
            "MCP tool: get_cnv_analysis", genome_build=genome_build, cnv_id=cnv_id
        )
        service = await get_managed_service()
        return await service.get_cnv_data(genome_build, cnv_id)


@mcp.tool()
async def get_cache_statistics() -> dict:
    """Get detailed cache performance statistics for all service methods.

    Returns:
        Comprehensive cache statistics including hit rates, timing, and error counts
    """
    with stdio_protection(settings.mcp.enable_stdio_protection):
        logger.info("MCP tool: get_cache_statistics")
        service = await get_managed_service()
        return await service.get_cache_statistics()


@mcp.tool()
async def clear_all_caches() -> dict:
    """Clear all service caches and reset cache statistics.

    Returns:
        Status of the cache clearing operation
    """
    with stdio_protection(settings.mcp.enable_stdio_protection):
        logger.info("MCP tool: clear_all_caches")
        service = await get_managed_service()
        await service.clear_cache()
        return {
            "status": "success",
            "message": "All caches and statistics cleared",
            "timestamp": asyncio.get_event_loop().time(),
        }


# Create MCP app for HTTP transport
mcp_app = mcp


# STDIO MCP runner with enhanced protection
async def run_mcp_stdio():
    """Run MCP server with STDIO transport and comprehensive protection."""
    with stdio_protection(settings.mcp.enable_stdio_protection):
        # Initialize server manager
        await server_manager.initialize()

        try:
            logger.info("Starting MCP server with STDIO transport")
            # Run MCP with STDIO
            await mcp.run_stdio()
        except KeyboardInterrupt:
            logger.info("MCP server interrupted by user")
        except Exception as e:
            logger.error("MCP server error", error=str(e))
            raise
        finally:
            # Ensure cleanup
            await server_manager.shutdown()


def main():
    """Main entry point for unified server."""
    configure_logging()
    print_startup_banner()

    try:
        uvicorn.run(
            "autopvs1_link.unified_server:app",
            host=settings.server.host,
            port=settings.server.port,
            reload=settings.server.reload,
            workers=settings.server.workers if not settings.server.reload else 1,
            log_level=settings.logging.level.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


def print_startup_banner():
    """Print startup banner with server information."""
    print("\n" + "=" * 60)
    print("🧬 AutoPVS1 Link Unified Server")
    print("=" * 60)
    print(f"Version: {settings.version}")
    print(f"Environment: {settings.environment}")
    print(f"Host: {settings.server.host}:{settings.server.port}")
    print(f"Debug: {settings.debug}")
    print(f"Cache: {'Enabled' if settings.cache.enabled else 'Disabled'}")
    print(
        f"STDIO Protection: {'Enabled' if settings.mcp.enable_stdio_protection else 'Disabled'}"
    )
    print("\nFeatures:")
    print("  ✓ REST API with OpenAPI documentation")
    print("  ✓ MCP (Model Context Protocol) support")
    print("  ✓ Advanced caching with statistics")
    print("  ✓ Circuit breaker pattern")
    print("  ✓ Retry logic with exponential backoff")
    print("  ✓ Request correlation tracking")
    print("  ✓ STDIO protection for MCP")
    print("\nEndpoints:")
    print(f"  📚 API Docs: http://{settings.server.host}:{settings.server.port}/docs")
    print(f"  🔍 Health: http://{settings.server.host}:{settings.server.port}/health")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
