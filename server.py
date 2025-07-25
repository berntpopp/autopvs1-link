#!/usr/bin/env python
"""Main server for AutoPVS1 Link."""
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autopvs1_link.api.routes import cnv, variant
from autopvs1_link.config import settings
from autopvs1_link.logging_config import configure_logging
from autopvs1_link.middleware.logging_middleware import RequestLoggingMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    configure_logging()
    logger.info("AutoPVS1 Link server starting up")

    # Initialize managers
    from autopvs1_link.api.client_manager import get_client_manager
    from autopvs1_link.services.service_manager import get_service_manager

    client_manager = await get_client_manager()
    service_manager = await get_service_manager()

    # Pre-initialize client and service for connection pooling
    await client_manager.get_client()
    await service_manager.get_service()

    logger.info("Client and service managers initialized")

    yield

    # Shutdown managers
    logger.info("AutoPVS1 Link server shutting down")
    from autopvs1_link.api.client_manager import shutdown_clients
    from autopvs1_link.services.service_manager import shutdown_services

    await shutdown_services()
    await shutdown_clients()
    logger.info("All managers shut down successfully")


app = FastAPI(
    title="AutoPVS1 Link Server",
    description="API for scraping PVS1 data from autopvs1.bgi.com",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
if settings.CORS_ORIGINS:
    origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
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


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to the AutoPVS1 Link Server!",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    from autopvs1_link.api.client_manager import get_client_manager
    from autopvs1_link.services.service_manager import get_service_manager

    # Get health status from managers
    client_manager = await get_client_manager()
    service_manager = await get_service_manager()

    client_health = await client_manager.health_check()
    service_health = await service_manager.health_check()

    overall_status = (
        "healthy"
        if client_health["status"] == "healthy"
        and service_health["status"] == "healthy"
        else "unhealthy"
    )

    return {
        "status": overall_status,
        "service": "autopvs1-link",
        "version": "1.0.0",
        "client": client_health,
        "service_health": service_health,
    }


@app.get("/api/cache/stats", tags=["Management"])
async def get_cache_stats():
    """Get cache statistics."""
    from autopvs1_link.services.service_manager import get_service_manager

    service_manager = await get_service_manager()
    return await service_manager.get_cache_statistics()


@app.post("/api/cache/clear", tags=["Management"])
async def clear_cache():
    """Clear all caches."""
    from autopvs1_link.services.service_manager import get_service_manager

    service_manager = await get_service_manager()
    return await service_manager.clear_all_caches()


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
