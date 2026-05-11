"""Prometheus metrics for AutoPVS1-Link."""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

REGISTRY = CollectorRegistry()

HTTP_REQUESTS = Counter(
    "autopvs1_link_http_requests_total",
    "Total HTTP requests.",
    labelnames=("method", "route", "status"),
    registry=REGISTRY,
)
HTTP_IN_FLIGHT = Gauge(
    "autopvs1_link_http_in_flight",
    "In-flight HTTP requests.",
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "autopvs1_link_http_duration_seconds",
    "HTTP request duration.",
    labelnames=("method", "route"),
    registry=REGISTRY,
)
CACHE_EVENTS = Counter(
    "autopvs1_link_cache_events_total",
    "Cache hit/miss events.",
    labelnames=("event",),
    registry=REGISTRY,
)
UPSTREAM_CALLS = Counter(
    "autopvs1_link_upstream_calls_total",
    "Calls to the AutoPVS1 upstream.",
    labelnames=("outcome",),
    registry=REGISTRY,
)
UPSTREAM_DURATION = Histogram(
    "autopvs1_link_upstream_duration_seconds",
    "Upstream call duration.",
    registry=REGISTRY,
)


class _MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        HTTP_IN_FLIGHT.inc()
        start = time.perf_counter()
        route = request.scope.get("path", "<unknown>")
        try:
            response = await call_next(request)
            HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
            return response
        finally:
            HTTP_DURATION.labels(request.method, route).observe(time.perf_counter() - start)
            HTTP_IN_FLIGHT.dec()


def metrics_enabled() -> bool:
    return os.environ.get("AUTOPVS1_LINK_METRICS_ENABLED", "true").lower() == "true"


def install(app: FastAPI) -> None:
    if not metrics_enabled():
        return
    app.add_middleware(_MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
