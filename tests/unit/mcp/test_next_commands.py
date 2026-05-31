"""Unit tests for machine-executable next_commands builders."""

from __future__ import annotations

from autopvs1_link.mcp.next_commands import (
    bulk_retry_failed,
    error_next_commands,
    search_next_page,
    widen_response_mode,
)


class _Input:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


class _Item:
    def __init__(self, ok: bool, **kw: object) -> None:
        self.ok = ok
        self.input = _Input(**kw)


def test_widen_from_summary_targets_standard() -> None:
    cmds = widen_response_mode(
        "get_variant_pvs1_data",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
        "summary",
    )
    assert cmds == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {
                "genome_build": "hg19",
                "variant_id": "X-82763936-A-T",
                "response_mode": "standard",
            },
            "reason": "Widen to response_mode='standard' for the full decision tree.",
        }
    ]


def test_widen_from_full_returns_none() -> None:
    assert widen_response_mode("get_variant_pvs1_data", {"x": 1}, "full") is None


def test_search_next_page_only_when_cursor_present() -> None:
    args = {"query": "BRCA1", "genome_build": "hg38", "limit": 10}
    assert search_next_page(args, None) is None
    cmds = search_next_page(args, "Y2Vu")
    assert cmds == [
        {
            "tool": "search_variants",
            "arguments": {"query": "BRCA1", "genome_build": "hg38", "limit": 10, "cursor": "Y2Vu"},
            "reason": "Fetch the next page of results.",
        }
    ]


def test_bulk_retry_failed_lists_only_failed_items() -> None:
    results = [
        _Item(True, genome_build="hg19", variant_id="X-82763936-A-T"),
        _Item(False, genome_build="hg19", variant_id="BADID"),
    ]
    cmds = bulk_retry_failed("get_variant_pvs1_data", results, "variant_id")
    assert cmds == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"genome_build": "hg19", "variant_id": "BADID"},
            "reason": "Retry this failed item individually.",
        }
    ]


def test_bulk_retry_failed_none_when_all_ok() -> None:
    results = [_Item(True, genome_build="hg19", variant_id="X-82763936-A-T")]
    assert bulk_retry_failed("get_variant_pvs1_data", results, "variant_id") is None


def test_error_next_commands_builds_one_command_per_candidate() -> None:
    details = {
        "candidates": [
            {"id": "17-43045712-A-G", "genome_build": "hg38", "spdi": "..."},
            {"id": "17-43045713-A-G", "genome_build": "hg38"},
        ]
    }
    cmds = error_next_commands("requires_disambiguation", details)
    assert cmds == [
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"variant_id": "17-43045712-A-G", "genome_build": "hg38"},
            "reason": "Re-score with this disambiguated candidate id.",
        },
        {
            "tool": "get_variant_pvs1_data",
            "arguments": {"variant_id": "17-43045713-A-G", "genome_build": "hg38"},
            "reason": "Re-score with this disambiguated candidate id.",
        },
    ]


def test_error_next_commands_none_for_other_codes() -> None:
    assert error_next_commands("invalid_variant_id", {"candidates": []}) is None
    assert error_next_commands("requires_disambiguation", None) is None
    assert error_next_commands("requires_disambiguation", {"candidates": []}) is None
