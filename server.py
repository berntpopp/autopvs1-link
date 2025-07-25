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

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    configure_logging()
    logger.info("AutoPVS1 Link server starting up")
    yield
    logger.info("AutoPVS1 Link server shutting down")


app = FastAPI(
    title="AutoPVS1 Link Server",
    description="API for scraping PVS1 data from autopvs1.bgi.com",
    version="1.0.0",
    lifespan=lifespan,
)

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
    return {"status": "healthy", "service": "autopvs1-link"}


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
