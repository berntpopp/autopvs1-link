"""Smoke tests for MCP tool registration."""

import inspect
from typing import Any, get_args, get_type_hints

import pytest
from fastmcp import FastMCP

from autopvs1_link.mcp.facade import build_mcp_server

JsonSchema = dict[str, Any]


def _annotation_uses_any(annotation: Any) -> bool:
    if annotation is Any:
        return True
    return any(_annotation_uses_any(arg) for arg in get_args(annotation))


def _non_null_schema(schema: JsonSchema) -> JsonSchema:
    for branch in schema.get("anyOf", []):
        if branch.get("type") != "null":
            return branch
    return schema


def _schema_allows_null(schema: dict) -> bool:
    return schema.get("type") == "null" or any(
        branch.get("type") == "null" for branch in schema.get("anyOf", [])
    )


def _assert_optional_enum_is_coherent(schema: dict) -> None:
    assert _schema_allows_null(schema)
    if "enum" in schema:
        assert None in schema["enum"]


def _enum_values(schema: dict) -> set[str]:
    values = {value for value in schema.get("enum", []) if isinstance(value, str)}
    for branch in schema.get("anyOf", []):
        values.update(value for value in branch.get("enum", []) if isinstance(value, str))
    return values


def _assert_optional_genome_build_schema(schema: dict) -> None:
    _assert_optional_enum_is_coherent(schema)
    assert {"hg19", "hg38"} <= _enum_values(schema)


@pytest.mark.asyncio
async def test_build_mcp_server_registers_expected_tools(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", raising=False)
    mcp: FastMCP = build_mcp_server()
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert {
        "get_server_capabilities",
        "get_server_health",
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
        "search_variants",
    } <= tool_names
    assert "clear_cache" not in tool_names


@pytest.mark.asyncio
async def test_clear_cache_is_registered_only_when_destructive_tools_enabled(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS", "true")

    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    assert "clear_cache" in tools
    schema = tools["clear_cache"].parameters
    assert schema.get("properties", {}) == {}
    assert "_" not in schema.get("properties", {})
    # outputSchema is suppressed (Tool-Surface Budget Standard v1).
    assert tools["clear_cache"].output_schema is None


@pytest.mark.asyncio
async def test_data_tools_use_direct_arguments_for_llm_discovery() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    variant_schema = tools["get_variant_pvs1_data"].parameters
    assert set(variant_schema["properties"]) == {
        "genome_build",
        "variant_id",
        "response_mode",
        "meta_mode",
        "include_unmet",
    }
    assert variant_schema["required"] == ["genome_build", "variant_id"]
    assert _enum_values(variant_schema["properties"]["response_mode"]) == {
        "ids_only",
        "summary",
        "standard",
        "full",
    }
    assert _enum_values(variant_schema["properties"]["meta_mode"]) == {
        "full",
        "compact",
        "minimal",
    }

    search_schema = tools["search_variants"].parameters
    assert set(search_schema["properties"]) == {
        "query",
        "genome_build",
        "limit",
        "cursor",
        "genome_version",
        "response_mode",
        "meta_mode",
    }
    assert search_schema["required"] == ["query"]
    assert "deprecated" in search_schema["properties"]["genome_version"]["description"].lower()
    _assert_optional_genome_build_schema(search_schema["properties"]["genome_build"])
    _assert_optional_genome_build_schema(search_schema["properties"]["genome_version"])
    assert _schema_allows_null(search_schema["properties"]["cursor"])
    assert _enum_values(search_schema["properties"]["response_mode"]) == {
        "ids_only",
        "summary",
        "standard",
        "full",
    }
    assert _enum_values(search_schema["properties"]["meta_mode"]) == {
        "full",
        "compact",
        "minimal",
    }


@pytest.mark.asyncio
async def test_search_variants_parameters_use_clean_runtime_annotations() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    signature = inspect.signature(tools["search_variants"].fn)
    type_hints = get_type_hints(tools["search_variants"].fn, include_extras=True)

    for name in (
        "query",
        "genome_build",
        "limit",
        "cursor",
        "genome_version",
        "response_mode",
        "meta_mode",
    ):
        assert name in signature.parameters
        assert not _annotation_uses_any(type_hints[name])


@pytest.mark.asyncio
async def test_data_tools_have_titles_and_annotations_and_no_output_schema() -> None:
    mcp: FastMCP = build_mcp_server()
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    for name in (
        "get_server_capabilities",
        "get_server_health",
        "get_variant_pvs1_data",
        "get_cnv_pvs1_data",
    ):
        tool = tools[name]
        assert tool.title
        # outputSchema is suppressed (Tool-Surface Budget Standard v1); the runtime
        # envelope shape is verified via call_tool in test_tool_runtime instead.
        assert tool.output_schema is None
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True


@pytest.mark.asyncio
async def test_workflow_prompts_are_registered_for_variant_and_cnv_classification() -> None:
    mcp: FastMCP = build_mcp_server()
    prompts = {prompt.name: prompt for prompt in await mcp.list_prompts()}

    assert {"classify_variant", "classify_cnv"} <= set(prompts)
    assert prompts["classify_variant"].title == "Classify SNV/Indel with AutoPVS1"
    assert prompts["classify_cnv"].title == "Classify CNV with AutoPVS1"


@pytest.mark.asyncio
async def test_classify_variant_prompt_renders_canonical_tool_guidance() -> None:
    mcp: FastMCP = build_mcp_server()

    rendered = await mcp.render_prompt(
        "classify_variant",
        {
            "genome_build": "hg19",
            "variant_id": "X-82763936-A-T",
        },
    )

    message = rendered.messages[0].content.text
    assert "get_variant_pvs1_data" in message
    assert "search_variants" in message
    assert "clear_cache" not in message


@pytest.mark.asyncio
async def test_classify_cnv_prompt_renders_canonical_tool_guidance() -> None:
    mcp: FastMCP = build_mcp_server()

    rendered = await mcp.render_prompt(
        "classify_cnv",
        {
            "genome_build": "hg19",
            "cnv_id": "17-15000000-20000000-DEL",
        },
    )

    message = rendered.messages[0].content.text
    assert "get_cnv_pvs1_data" in message
    assert "search_variants" in message
    assert "clear_cache" not in message


@pytest.mark.asyncio
async def test_classify_variant_prompt_explains_payload_sizing_and_error_handling() -> None:
    mcp: FastMCP = build_mcp_server()
    rendered = await mcp.render_prompt(
        "classify_variant",
        {"genome_build": "hg19", "variant_id": "X-82763936-A-T"},
    )
    body = rendered.messages[0].content.text
    assert "response_mode" in body
    assert "summary" in body
    assert "pvs1_not_applicable" in body
    assert "not_found" in body
    assert "upstream_timeout" in body
    assert "isError" in body


@pytest.mark.asyncio
async def test_classify_cnv_prompt_explains_payload_sizing_and_error_handling() -> None:
    mcp: FastMCP = build_mcp_server()
    rendered = await mcp.render_prompt(
        "classify_cnv",
        {"genome_build": "hg19", "cnv_id": "17-15000000-20000000-DEL"},
    )
    body = rendered.messages[0].content.text
    assert "response_mode" in body
    assert "pvs1_not_applicable" in body
    assert "invalid_cnv_id" in body


@pytest.mark.asyncio
async def test_pvs1_workflow_help_prompt_is_registered_with_arguments() -> None:
    mcp: FastMCP = build_mcp_server()
    prompts = {prompt.name: prompt for prompt in await mcp.list_prompts()}
    assert "pvs1_workflow_help" in prompts
    help_prompt = prompts["pvs1_workflow_help"]
    assert help_prompt.title
    assert help_prompt.description
    args = {arg.name: arg for arg in help_prompt.arguments or []}
    assert "task" in args
    assert args["task"].description
    assert any(
        token in (args["task"].description or "")
        for token in ("clinical_review", "batch_screen", "search_first")
    )


@pytest.mark.asyncio
async def test_pvs1_workflow_help_clinical_review_describes_tool_chain() -> None:
    mcp: FastMCP = build_mcp_server()
    rendered = await mcp.render_prompt(
        "pvs1_workflow_help",
        {"task": "clinical_review"},
    )
    body = rendered.messages[0].content.text
    assert "get_variant_pvs1_data" in body
    assert "response_mode" in body
    assert "research-use" in body or "research use" in body


@pytest.mark.asyncio
async def test_pvs1_workflow_help_batch_screen_describes_bulk_chain() -> None:
    mcp: FastMCP = build_mcp_server()
    rendered = await mcp.render_prompt(
        "pvs1_workflow_help",
        {"task": "batch_screen"},
    )
    body = rendered.messages[0].content.text
    assert "get_variants_pvs1_data_bulk" in body
    assert "continue_on_error" in body


@pytest.mark.asyncio
async def test_pvs1_workflow_help_search_first_describes_resolution_chain() -> None:
    mcp: FastMCP = build_mcp_server()
    rendered = await mcp.render_prompt(
        "pvs1_workflow_help",
        {"task": "search_first"},
    )
    body = rendered.messages[0].content.text
    assert "search_variants" in body
    assert "next_cursor" in body


def test_workflow_help_summaries_match_workflow_help_bodies() -> None:
    """Drift guard: every task with a body must also have a one-line
    summary so the guided menu fallback covers every supported task."""
    from autopvs1_link.mcp.prompts import (
        _WORKFLOW_HELP_BODIES,
        _WORKFLOW_HELP_SUMMARIES,
    )

    assert set(_WORKFLOW_HELP_BODIES) == set(_WORKFLOW_HELP_SUMMARIES)


@pytest.mark.asyncio
async def test_pvs1_workflow_help_unknown_task_returns_guided_menu() -> None:
    """Item 5: the unknown-task path should be a guided menu, not a terse
    'pick one of: a, b, c' one-liner. A real LLM caller needs the task
    name AND a one-line description so it can route the next call without
    a second discovery turn — and a verb-noun call-to-action so it knows
    what to do after picking."""
    mcp: FastMCP = build_mcp_server()
    rendered = await mcp.render_prompt(
        "pvs1_workflow_help",
        {"task": "totally_not_a_task"},
    )
    body = rendered.messages[0].content.text

    # All three valid task keys must be advertised.
    for key in ("clinical_review", "batch_screen", "search_first"):
        assert key in body, key

    # Each task name must be paired with a short description on the same
    # bullet line (not just the bare key).
    for key in ("clinical_review", "batch_screen", "search_first"):
        marker = f"- {key}:"
        assert marker in body, f"expected guided-menu bullet '{marker}' in body"

    # Verb-noun CTA at the end so the LLM knows what to do next.
    body_lower = body.lower()
    assert "call pvs1_workflow_help" in body_lower
    assert "task=" in body_lower
