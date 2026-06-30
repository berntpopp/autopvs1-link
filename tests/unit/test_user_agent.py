"""The outbound User-Agent must identify the tool, not spoof a browser."""

import asyncio

from autopvs1_link import __version__
from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.config import APIConfig


def test_default_user_agent_identifies_the_tool() -> None:
    ua = APIConfig().user_agent
    assert ua == (
        f"autopvs1-link/{__version__} "
        "(+https://github.com/berntpopp/autopvs1-link)"
    )
    assert "Mozilla" not in ua
    assert "Chrome" not in ua


def test_client_sends_honest_user_agent() -> None:
    client = AutoPVS1Client()
    try:
        header = client.client.headers["user-agent"]
        assert header.startswith("autopvs1-link/")
        assert "Mozilla" not in header
    finally:
        asyncio.run(client.close())
