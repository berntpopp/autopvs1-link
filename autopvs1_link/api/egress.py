"""Default-deny outbound HTTP policy with manually validated redirects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urljoin, urlsplit

import httpx

EgressMode = Literal["disabled", "allowlist"]
_REDIRECTS = {301, 302, 303, 307, 308}


class EgressDeniedError(RuntimeError):
    """Configured policy rejected an outbound destination before network I/O."""


def normalize_origin(value: str) -> str:
    """Return a canonical bare HTTPS origin or reject the value."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError("allowed upstream origin must be a bare HTTPS origin")
    port = f":{parsed.port}" if parsed.port not in (None, 443) else ""
    return f"https://{parsed.hostname.lower()}{port}"


@dataclass(frozen=True, slots=True)
class EgressPolicy:
    """Exact-origin allowlist applied before every outbound request hop."""

    mode: EgressMode
    allowed_origins: frozenset[str]

    def require_allowed(self, url: str) -> None:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise EgressDeniedError("outbound URL is not an authenticated HTTPS destination")
        try:
            origin = normalize_origin(f"{parsed.scheme}://{parsed.netloc}")
        except ValueError as exc:
            raise EgressDeniedError("outbound URL has an invalid origin") from exc
        if self.mode != "allowlist" or origin not in self.allowed_origins:
            raise EgressDeniedError("outbound origin is not allowlisted")


async def guarded_request(
    client: httpx.AsyncClient,
    policy: EgressPolicy,
    method: str,
    url: str,
    *,
    max_redirects: int = 5,
    **kwargs: Any,
) -> httpx.Response:
    """Send one request while validating every redirect before network I/O."""
    if max_redirects < 0:
        raise ValueError("max_redirects must be non-negative")

    current = url
    request_kwargs = dict(kwargs)
    history: list[httpx.Response] = []
    for hop in range(max_redirects + 1):
        policy.require_allowed(current)
        response = await client.request(
            method,
            current,
            follow_redirects=False,
            **request_kwargs,
        )
        if response.status_code not in _REDIRECTS:
            response.history = history
            return response
        if hop == max_redirects:
            await response.aclose()
            raise EgressDeniedError("outbound redirect limit exceeded")
        location = response.headers.get("location")
        if not location:
            await response.aclose()
            raise EgressDeniedError("redirect response omitted Location")
        next_url = urljoin(str(response.url), location)
        try:
            policy.require_allowed(next_url)
        except EgressDeniedError:
            await response.aclose()
            raise
        history.append(response)
        await response.aclose()
        current = next_url
        request_kwargs.pop("params", None)
        if response.status_code == 303:
            method = "GET"
            request_kwargs.pop("content", None)
            request_kwargs.pop("data", None)
            request_kwargs.pop("json", None)
    raise AssertionError("redirect loop terminated unexpectedly")
