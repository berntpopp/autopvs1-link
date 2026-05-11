"""Typer CLI for AutoPVS1-Link."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Annotated

import httpx
import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from autopvs1_link.config import settings
from autopvs1_link.logging_config import configure_logging

app = typer.Typer(
    name="autopvs1-link",
    help="AutoPVS1 Link - Genetic variant analysis tool with MCP and REST API support.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def print_banner() -> None:
    """Print the AutoPVS1 Link banner."""
    banner_text = Text()
    banner_text.append("AutoPVS1", style="bold blue")
    banner_text.append("-", style="white")
    banner_text.append("Link", style="bold green")

    banner = Panel(
        banner_text,
        title="Genetic Variant Analysis Tool",
        subtitle=f"v{settings.version}",
        border_style="blue",
    )
    console.print(banner)


def _settings_dict() -> dict[str, object]:
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "version": settings.version,
        "api": settings.api.model_dump(),
        "cache": settings.cache.model_dump(),
        "server": settings.server.model_dump(),
        "logging": settings.logging.model_dump(),
        "mcp": settings.mcp.model_dump(),
    }


def print_config_table() -> None:
    """Print current configuration in a formatted table."""
    table = Table(title="Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=25)
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")

    table.add_row("API Base URL", settings.api.base_url, "AutoPVS1 service endpoint")
    table.add_row("Request Timeout", f"{settings.api.request_timeout}s", "HTTP request timeout")
    table.add_row("Max Retries", str(settings.api.max_retries), "Maximum HTTP retries")
    table.add_row("Rate Limit", f"{settings.api.rate_limit_delay}s", "Delay between requests")

    table.add_row("Cache Enabled", str(settings.cache.enabled), "Cache functionality")
    table.add_row("Cache Size", str(settings.cache.size), "Maximum cache entries")
    table.add_row("Cache TTL", f"{settings.cache.ttl_hours}h", "Cache time-to-live")

    table.add_row("Server Host", settings.server.host, "Server bind address")
    table.add_row("Server Port", str(settings.server.port), "Server listen port")
    table.add_row("CORS Origins", settings.server.cors_origins, "Allowed CORS origins")

    table.add_row("Environment", settings.environment, "Deployment environment")
    table.add_row("Debug Mode", str(settings.debug), "Debug mode status")
    table.add_row("Log Level", settings.logging.level, "Logging level")

    console.print(table)


@app.callback()
def main_callback(
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    """AutoPVS1 Link - Genetic variant analysis tool with MCP and REST API support."""
    if version:
        console.print(f"AutoPVS1-Link v{settings.version}", style="bold green")
        raise typer.Exit()


@app.command()
def server(
    host: Annotated[str | None, typer.Option(help="Host to bind the server to")] = None,
    port: Annotated[int | None, typer.Option(help="Port to bind the server to")] = None,
    transport: Annotated[str, typer.Option(help="Transport: stdio | http | unified")] = "unified",
    reload: Annotated[bool, typer.Option(help="Enable auto-reload")] = False,
    workers: Annotated[int | None, typer.Option(help="Number of workers")] = None,
    log_level: Annotated[str | None, typer.Option("--log-level", help="Log level")] = None,
) -> None:
    """Start the unified FastAPI server with both REST API and MCP support."""
    configure_logging()

    server_host = host or settings.server.host
    server_port = port or settings.server.port
    server_workers = workers or settings.server.workers
    server_reload = reload or settings.server.reload
    server_log_level = log_level or settings.logging.level.lower()

    if transport == "stdio":
        from autopvs1_link.unified_server import run_mcp_stdio

        asyncio.run(run_mcp_stdio())  # type: ignore[no-untyped-call]
        return

    print_banner()
    console.print("Starting AutoPVS1 Link Server...", style="bold green")
    console.print(f"   Host: {server_host}")
    console.print(f"   Port: {server_port}")
    console.print(f"   Workers: {server_workers}")
    console.print(f"   Reload: {server_reload}")
    console.print(f"   Log Level: {server_log_level}")
    console.print("")
    console.print(f"API docs: http://{server_host}:{server_port}/docs", style="blue")
    console.print(f"Health: http://{server_host}:{server_port}/health", style="blue")
    console.print("")

    try:
        uvicorn.run(
            "autopvs1_link.server_manager:app",
            host=server_host,
            port=server_port,
            reload=server_reload,
            workers=server_workers if not server_reload else 1,
            log_level=server_log_level,
        )
    except KeyboardInterrupt:
        console.print("Server stopped by user", style="yellow")


@app.command()
def mcp(
    http: Annotated[bool, typer.Option(help="Use HTTP transport (Streamable HTTP)")] = False,
    port: Annotated[int, typer.Option(help="Port for HTTP transport")] = 3000,
) -> None:
    """Start the MCP (Model Context Protocol) server."""
    configure_logging()

    if http:
        console.print("Starting MCP Server (Streamable HTTP)...", style="bold blue")
        console.print(f"   Endpoint: http://localhost:{port}/mcp")
        uvicorn.run(
            "autopvs1_link.server_manager:app",
            host="127.0.0.1",
            port=port,
            log_level=settings.logging.level.lower(),
        )
    else:
        console.print("Starting MCP Server (STDIO transport)...", style="bold blue")
        from autopvs1_link.unified_server import run_mcp_stdio

        asyncio.run(run_mcp_stdio())  # type: ignore[no-untyped-call]


@app.command()
def config(
    output_format: Annotated[
        str, typer.Option("--format", help="Output format: table | json")
    ] = "table",
) -> None:
    """Show current configuration settings."""
    if output_format == "table":
        print_config_table()
    elif output_format == "json":
        console.print(json.dumps(_settings_dict(), indent=2))
    else:
        console.print(f"Unsupported format: {output_format}", style="red")
        raise typer.Exit(code=2)


@app.command()
def health() -> None:
    """Check the health status of all components."""
    asyncio.run(_health_async())


async def _health_async() -> None:
    console.print("Checking component health...", style="bold blue")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.server.host}:{settings.server.port}/health",
                timeout=5.0,
            )
            health_data = response.json()

            table = Table(title="Health Status", show_header=True, header_style="bold magenta")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="dim")

            overall_status = health_data.get("status", "unknown")
            table.add_row(
                "Overall",
                overall_status,
                f"Version: {health_data.get('version', 'unknown')}",
            )

            client_health = health_data.get("client", {})
            table.add_row(
                "HTTP Client",
                client_health.get("status", "unknown"),
                client_health.get("base_url", ""),
            )
            service_health = health_data.get("service_health", {})
            table.add_row(
                "Service",
                service_health.get("status", "unknown"),
                "AutoPVS1 Service Layer",
            )
            console.print(table)

    except httpx.ConnectError:
        console.print("Server is not running", style="red")
        console.print("   Start the server with: autopvs1-link server", style="dim")
    except Exception as e:
        console.print(f"Health check failed: {e}", style="red")


@app.command()
def cache() -> None:
    """Show cache statistics."""
    asyncio.run(_cache_async())


async def _cache_async() -> None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.server.host}:{settings.server.port}/api/cache/stats",
                timeout=5.0,
            )
            cache_stats = response.json()

            table = Table(title="Cache Statistics", show_header=True, header_style="bold magenta")
            table.add_column("Method", style="cyan")
            table.add_column("Hits", style="green")
            table.add_column("Misses", style="red")
            table.add_column("Hit Rate", style="blue")
            table.add_column("Total", style="dim")

            for method, stats in cache_stats.items():
                if isinstance(stats, dict):
                    hits = stats.get("hits", 0)
                    misses = stats.get("misses", 0)
                    total = hits + misses
                    hit_rate = (hits / total * 100) if total > 0 else 0
                    table.add_row(method, str(hits), str(misses), f"{hit_rate:.1f}%", str(total))

            console.print(table)
    except httpx.ConnectError:
        console.print("Server is not running", style="red")
    except Exception as e:
        console.print(f"Cache stats failed: {e}", style="red")


@app.command(name="clear-cache")
def clear_cache(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
) -> None:
    """Clear all service caches."""
    if not yes:
        confirm = typer.confirm("Are you sure you want to clear all caches?")
        if not confirm:
            console.print("Aborted.", style="yellow")
            raise typer.Exit()
    asyncio.run(_clear_cache_async())


async def _clear_cache_async() -> None:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.server.host}:{settings.server.port}/api/cache/clear",
                timeout=5.0,
            )
            result = response.json()
            if result.get("status") == "success":
                console.print("All caches cleared successfully", style="green")
            else:
                console.print(f"Failed to clear caches: {result.get('error')}", style="red")
    except httpx.ConnectError:
        console.print("Server is not running", style="red")
    except Exception as e:
        console.print(f"Clear cache failed: {e}", style="red")


def main() -> None:
    """Entry-point shim used by `[project.scripts] autopvs1-link`."""
    app()


if __name__ == "__main__":
    main()
    sys.exit(0)
