"""Tests for the default-deny outbound HTTP policy."""

import httpx
import pytest

from autopvs1_link.api.egress import (
    EgressDeniedError,
    EgressPolicy,
    guarded_request,
    normalize_origin,
)


def test_origin_validation_uses_httpx_url_semantics() -> None:
    with pytest.raises(ValueError, match="bare HTTPS origin"):
        normalize_origin(" https://autopvs1.bgi.com")
    assert normalize_origin("https://bücher.example") == "https://xn--bcher-kva.example"


def test_policy_denies_by_default_and_matches_exact_origin() -> None:
    disabled = EgressPolicy(mode="disabled", allowed_origins=frozenset())
    with pytest.raises(EgressDeniedError):
        disabled.require_allowed("https://autopvs1.bgi.com/variant/hg38/1-1-A-G")

    policy = EgressPolicy(
        mode="allowlist",
        allowed_origins=frozenset({"https://autopvs1.bgi.com"}),
    )
    policy.require_allowed("https://autopvs1.bgi.com/search")
    for url in (
        "https://evil.autopvs1.bgi.com/search",
        "https://autopvs1.bgi.com.evil.example/search",
        "https://user@autopvs1.bgi.com/search",
        "http://autopvs1.bgi.com/search",
    ):
        with pytest.raises(EgressDeniedError):
            policy.require_allowed(url)


@pytest.mark.asyncio
async def test_redirect_is_validated_before_second_request() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://evil.example/collect"})

    policy = EgressPolicy(
        mode="allowlist",
        allowed_origins=frozenset({"https://autopvs1.bgi.com"}),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EgressDeniedError):
            await guarded_request(
                client,
                policy,
                "GET",
                "https://autopvs1.bgi.com/search",
            )
    assert requests == ["https://autopvs1.bgi.com/search"]


@pytest.mark.asyncio
async def test_redirect_limit_is_bounded() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(307, headers={"Location": "/again"})

    policy = EgressPolicy(
        mode="allowlist",
        allowed_origins=frozenset({"https://autopvs1.bgi.com"}),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(EgressDeniedError, match="redirect limit"):
            await guarded_request(
                client,
                policy,
                "GET",
                "https://autopvs1.bgi.com/search",
                max_redirects=2,
            )
    assert requests == 3


@pytest.mark.asyncio
async def test_redirect_limit_cannot_exceed_policy_ceiling() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200)

    policy = EgressPolicy(
        mode="allowlist",
        allowed_origins=frozenset({"https://autopvs1.bgi.com"}),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="cannot exceed 5"):
            await guarded_request(
                client,
                policy,
                "GET",
                "https://autopvs1.bgi.com/search",
                max_redirects=6,
            )
    assert requests == 0
