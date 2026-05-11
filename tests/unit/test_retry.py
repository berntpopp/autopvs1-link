"""Tests for the inline retry helper."""

import httpx
import pytest

from autopvs1_link.api.retry import async_retry


@pytest.mark.asyncio
async def test_async_retry_returns_on_first_success() -> None:
    calls = 0

    async def op() -> int:
        nonlocal calls
        calls += 1
        return 42

    result = await async_retry(op, max_attempts=3, base_delay=0.01)
    assert result == 42
    assert calls == 1


@pytest.mark.asyncio
async def test_async_retry_retries_on_httpx_transport_error() -> None:
    calls = 0

    async def op() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ConnectError("boom")
        return "ok"

    result = await async_retry(op, max_attempts=4, base_delay=0.01)
    assert result == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_async_retry_raises_after_max_attempts() -> None:
    async def op() -> None:
        raise httpx.ConnectError("boom")

    with pytest.raises(httpx.ConnectError):
        await async_retry(op, max_attempts=2, base_delay=0.01)


@pytest.mark.asyncio
async def test_async_retry_does_not_retry_value_error() -> None:
    calls = 0

    async def op() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        await async_retry(op, max_attempts=5, base_delay=0.01)
    assert calls == 1
