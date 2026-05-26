#!/usr/bin/env python
"""Generate docs/mcp-tool-catalog.md from the built FastMCP server."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from autopvs1_link.mcp.facade import build_mcp_server


async def render() -> str:
    mcp = build_mcp_server()
    lines: list[str] = ["# MCP Tool Catalog", ""]
    lines.append(
        "Auto-generated from `autopvs1_link.mcp.facade.build_mcp_server`. "
        "Regenerate with `uv run python scripts/generate_mcp_tool_catalog.py`."
    )
    lines.append("")
    lines.append("## Tools")
    lines.append("")
    for tool in sorted(await mcp.list_tools(), key=lambda tool: tool.name):
        lines.append(f"### `{tool.name}`")
        lines.append("")
        if tool.description:
            lines.append(tool.description.strip())
            lines.append("")
        schema = tool.parameters
        if schema:
            lines.append("#### Input Schema")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(schema, indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")
        output_schema = tool.output_schema
        if output_schema:
            lines.append("#### Output Schema")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(output_schema, indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")
    lines.append("## Resources")
    lines.append("")
    for resource in sorted(await mcp.list_resources(), key=lambda resource: str(resource.uri)):
        desc = (resource.description or "").strip()
        if desc:
            lines.append(f"- `{resource.uri}` - {desc}")
        else:
            lines.append(f"- `{resource.uri}`")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "docs" / "mcp-tool-catalog.md"
    out.write_text(asyncio.run(render()), encoding="utf-8")
    print(f"Wrote {out}")  # noqa: T201


if __name__ == "__main__":
    main()
