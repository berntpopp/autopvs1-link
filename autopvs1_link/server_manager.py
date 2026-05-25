"""Application factory: build the FastAPI app with optional MCP mount."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from autopvs1_link.api.client_manager import shutdown_clients
from autopvs1_link.api.routes import cache, cnv, gene, variant
from autopvs1_link.config import settings
from autopvs1_link.mcp.facade import build_mcp_server
from autopvs1_link.middleware.logging_middleware import RequestLoggingMiddleware
from autopvs1_link.observability.correlation import install as install_correlation
from autopvs1_link.observability.prometheus import install as install_metrics
from autopvs1_link.services.service_manager import shutdown_services


def create_app() -> FastAPI:
    """Construct the FastAPI app, including the MCP Streamable-HTTP mount."""
    # Build the MCP server first so its lifespan can be chained.
    mcp = build_mcp_server()
    mcp_app = mcp.http_app(
        path="/",
        json_response=True,
        stateless_http=True,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_app.lifespan(app))
            try:
                yield
            finally:
                await shutdown_services()
                await shutdown_clients()

    app = FastAPI(
        title="AutoPVS1-Link",
        version=settings.version,
        description="Unified REST + MCP server for AutoPVS1.",
        lifespan=lifespan,
    )
    app.add_middleware(RequestLoggingMiddleware)
    install_metrics(app)
    # Correlation middleware added LAST so it runs FIRST on requests, binding
    # the X-Request-ID before downstream middleware logs the request.
    install_correlation(app)
    app.include_router(variant.router)
    app.include_router(cnv.router)
    app.include_router(gene.router)
    app.include_router(cache.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/mcp", mcp_app)
    return app


app = create_app()
