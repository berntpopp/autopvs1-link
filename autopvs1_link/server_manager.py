"""Application factory: build the FastAPI app with optional MCP mount."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp.server.http import HostOriginGuardMiddleware

from autopvs1_link import __version__
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
    # Bake the MCP route at the mcp path INSIDE the ASGI sub-app, then mount
    # that sub-app at root ("/") below. Mounting the sub-app *at* "/mcp" would
    # make Starlette's Mount emit a 307 trailing-slash redirect (/mcp -> /mcp/);
    # baking "/mcp" into the sub-app and mounting at "/" serves /mcp directly,
    # matching the rest of the GeneFoundry fleet (see gtex-link server_manager).
    # fastmcp >=3.4.4 supports strict DNS-rebinding protection with an explicit
    # allowlist. Enable it natively on the /mcp sub-app and pin the exact Host
    # and Origin values (default loopback; the proxied public host is added via
    # AUTOPVS1_LINK_SERVER_ALLOWED_HOSTS in production). The outer guard below
    # extends the same policy to /health, /api/... and /metrics.
    mcp_app = mcp.http_app(
        path="/mcp",
        json_response=True,
        stateless_http=True,
        host_origin_protection=True,
        allowed_hosts=settings.server.allowed_hosts,
        allowed_origins=settings.server.allowed_origins,
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
    app.add_middleware(RequestLoggingMiddleware, log_client_ip=settings.debug)
    cors_origins = settings.server.cors_origins_list
    # Never pair wildcard origins with credentials: browsers reject that
    # combination and it is a CORS anti-pattern (reflected-origin credential
    # exposure). Allow credentials only when an explicit allowlist is set.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_metrics(app)
    # Correlation middleware binds the X-Request-ID before downstream middleware
    # logs the request.
    install_correlation(app)
    # DNS-rebinding guard added LAST so it runs FIRST (outermost): an untrusted
    # Host (421) or Origin (403) is rejected before any other route -- FastAPI
    # native handlers and the mounted /mcp sub-app -- processes the request.
    app.add_middleware(
        HostOriginGuardMiddleware,
        allowed_hosts=settings.server.allowed_hosts,
        allowed_origins=settings.server.allowed_origins,
        mode="strict",
    )
    app.include_router(variant.router)
    app.include_router(cnv.router)
    app.include_router(gene.router)
    app.include_router(cache.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "transport": "streamable-http-stateless",
        }

    # Mount at root: the "/mcp" path is already baked into mcp_app's routes,
    # and the FastAPI routes registered above (/health, /api/...) take
    # precedence because they are matched before this catch-all mount.
    app.mount("/", mcp_app)
    return app


app = create_app()
