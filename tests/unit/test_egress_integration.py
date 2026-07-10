"""Integration tests proving external callers use the central policy."""

import httpx
import pytest

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.api.egress import EgressDeniedError
from autopvs1_link.api.variant_recoder import VariantRecoderClient
from autopvs1_link.config import settings


@pytest.mark.asyncio
async def test_disabled_policy_blocks_bgi_before_http(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def forbidden(*args: object, **kwargs: object) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("network must not be reached")

    monkeypatch.setattr(settings.api, "egress_mode", "disabled")
    monkeypatch.setattr(httpx.AsyncClient, "request", forbidden)
    client = AutoPVS1Client()
    try:
        with pytest.raises(EgressDeniedError):
            await client.get_variant_data("hg38", "1-1-A-G")
    finally:
        await client.close()
    assert calls == 0


@pytest.mark.asyncio
async def test_disabled_policy_blocks_ensembl_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def forbidden(*args: object, **kwargs: object) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("network must not be reached")

    monkeypatch.setattr(settings.api, "egress_mode", "disabled")
    monkeypatch.setattr(httpx.AsyncClient, "request", forbidden)
    with pytest.raises(EgressDeniedError):
        await VariantRecoderClient().recode("rs80357906", "hg38")
    assert calls == 0


@pytest.mark.asyncio
async def test_allowed_bgi_request_uses_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.api, "egress_mode", "allowlist")
    monkeypatch.setattr(
        settings.api,
        "allowed_upstream_origins",
        "https://autopvs1.bgi.com",
    )
    request = httpx.Request("GET", "https://autopvs1.bgi.com/variant/hg38/1-1-A-G")
    response = httpx.Response(200, request=request, text="<html></html>")
    calls: list[str] = []

    async def allowed(_self: object, method: str, url: str, **kwargs: object) -> httpx.Response:
        calls.append(f"{method} {url}")
        return response

    monkeypatch.setattr(httpx.AsyncClient, "request", allowed)
    monkeypatch.setattr(AutoPVS1Client, "_build_variant_data", lambda *args: object())
    client = AutoPVS1Client()
    try:
        await client.get_variant_data("hg38", "1-1-A-G")
    finally:
        await client.close()
    assert calls == ["GET https://autopvs1.bgi.com/variant/hg38/1-1-A-G"]
