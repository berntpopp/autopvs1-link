"""asgi-correlation-id wiring."""

from __future__ import annotations

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI


def install(app: FastAPI) -> None:
    """Install the correlation-id middleware on the given FastAPI app."""
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        update_request_header=True,
    )
