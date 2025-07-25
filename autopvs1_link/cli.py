"""Rich CLI interface for AutoPVS1 Link with enhanced developer experience."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from autopvs1_link.config import settings
from autopvs1_link.logging_config import configure_logging

console = Console()


def print_banner() -> None:
    """Print the AutoPVS1 Link banner."""
    banner_text = Text()
    banner_text.append("AutoPVS1", style="bold blue")
    banner_text.append("-", style="white")
    banner_text.append("Link", style="bold green")
    
    banner = Panel(
        banner_text,
        title="🧬 Genetic Variant Analysis Tool",
        subtitle=f"v{settings.version}",
        border_style="blue",
    )
    console.print(banner)


def print_config_table() -> None:
    """Print current configuration in a formatted table."""
    table = Table(title="Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan", width=25)
    table.add_column("Value", style="green")
    table.add_column("Description", style="dim")

    # API Configuration
    table.add_row("API Base URL", settings.api.base_url, "AutoPVS1 service endpoint")
    table.add_row("Request Timeout", f"{settings.api.request_timeout}s", "HTTP request timeout")
    table.add_row("Max Retries", str(settings.api.max_retries), "Maximum HTTP retries")
    table.add_row("Rate Limit", f"{settings.api.rate_limit_delay}s", "Delay between requests")
    
    # Cache Configuration
    table.add_row("Cache Enabled", str(settings.cache.enabled), "Cache functionality")
    table.add_row("Cache Size", str(settings.cache.size), "Maximum cache entries")
    table.add_row("Cache TTL", f"{settings.cache.ttl_hours}h", "Cache time-to-live")
    
    # Server Configuration
    table.add_row("Server Host", settings.server.host, "Server bind address")
    table.add_row("Server Port", str(settings.server.port), "Server listen port")
    table.add_row("CORS Origins", settings.server.cors_origins, "Allowed CORS origins")
    
    # Environment
    table.add_row("Environment", settings.environment, "Deployment environment")
    table.add_row("Debug Mode", str(settings.debug), "Debug mode status")
    table.add_row("Log Level", settings.logging.level, "Logging level")

    console.print(table)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.option("--config", is_flag=True, help="Show configuration and exit")
@click.pass_context
def main(ctx: click.Context, version: bool, config: bool) -> None:
    """AutoPVS1 Link - Genetic variant analysis tool with MCP and REST API support."""
    print_banner()
    
    if version:
        console.print(f"Version: {settings.version}", style="bold green")
        sys.exit(0)
    
    if config:
        print_config_table()
        sys.exit(0)
    
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@main.command()
@click.option("--host", default=None, help="Host to bind the server to")
@click.option("--port", default=None, type=int, help="Port to bind the server to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
@click.option("--workers", default=None, type=int, help="Number of workers")
@click.option("--log-level", default=None, help="Log level")
def server(
    host: Optional[str],
    port: Optional[int],
    reload: bool,
    workers: Optional[int],
    log_level: Optional[str],
) -> None:
    """Start the unified FastAPI server with both REST API and MCP support."""
    configure_logging()
    
    # Override settings with CLI options
    server_host = host or settings.server.host
    server_port = port or settings.server.port
    server_workers = workers or settings.server.workers
    server_reload = reload or settings.server.reload
    server_log_level = log_level or settings.logging.level.lower()
    
    console.print("🚀 Starting AutoPVS1 Link Server...", style="bold green")
    console.print(f"   Host: {server_host}")
    console.print(f"   Port: {server_port}")
    console.print(f"   Workers: {server_workers}")
    console.print(f"   Reload: {server_reload}")
    console.print(f"   Log Level: {server_log_level}")
    console.print("")
    console.print("📚 API Documentation: http://localhost:8000/docs", style="blue")
    console.print("🔗 Health Check: http://localhost:8000/health", style="blue")
    console.print("")
    
    try:
        uvicorn.run(
            "autopvs1_link.unified_server:app",
            host=server_host,
            port=server_port,
            reload=server_reload,
            workers=server_workers if not server_reload else 1,
            log_level=server_log_level,
        )
    except KeyboardInterrupt:
        console.print("🛑 Server stopped by user", style="yellow")


@main.command()
@click.option("--stdio", is_flag=True, help="Use STDIO transport (default)")
@click.option("--http", is_flag=True, help="Use HTTP transport")
@click.option("--port", default=3000, type=int, help="Port for HTTP transport")
def mcp(stdio: bool, http: bool, port: int) -> None:
    """Start the MCP (Model Context Protocol) server."""
    configure_logging()
    
    if http:
        console.print("🔌 Starting MCP Server (HTTP transport)...", style="bold blue")
        console.print(f"   Port: {port}")
        console.print(f"   Endpoint: http://localhost:{port}")
        
        import uvicorn
        uvicorn.run(
            "autopvs1_link.unified_server:mcp_app",
            host="localhost",
            port=port,
            log_level=settings.logging.level.lower(),
        )
    else:
        console.print("🔌 Starting MCP Server (STDIO transport)...", style="bold blue")
        console.print("   Ready for MCP client connections via STDIO")
        
        from autopvs1_link.unified_server import run_mcp_stdio
        asyncio.run(run_mcp_stdio())


@main.command()
@click.option("--format", "output_format", 
              type=click.Choice(["table", "json", "yaml"]), 
              default="table", 
              help="Output format")
def config(output_format: str) -> None:
    """Show current configuration settings."""
    if output_format == "table":
        print_config_table()
    elif output_format == "json":
        import json
        config_dict = {
            "environment": settings.environment,
            "debug": settings.debug,
            "version": settings.version,
            "api": settings.api.model_dump(),
            "cache": settings.cache.model_dump(),
            "server": settings.server.model_dump(),
            "logging": settings.logging.model_dump(),
            "mcp": settings.mcp.model_dump(),
        }
        console.print(json.dumps(config_dict, indent=2))
    elif output_format == "yaml":
        try:
            import yaml
            config_dict = {
                "environment": settings.environment,
                "debug": settings.debug,
                "version": settings.version,
                "api": settings.api.model_dump(),
                "cache": settings.cache.model_dump(),
                "server": settings.server.model_dump(),
                "logging": settings.logging.model_dump(),
                "mcp": settings.mcp.model_dump(),
            }
            console.print(yaml.dump(config_dict, default_flow_style=False))
        except ImportError:
            console.print("❌ PyYAML not installed. Use 'pip install pyyaml'", style="red")


@main.command()
async def health() -> None:
    """Check the health status of all components."""
    import httpx
    
    console.print("🔍 Checking component health...", style="bold blue")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://{settings.server.host}:{settings.server.port}/health",
                timeout=5.0
            )
            health_data = response.json()
            
            # Create health status table
            table = Table(title="Health Status", show_header=True, header_style="bold magenta")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="dim")
            
            overall_status = health_data.get("status", "unknown")
            status_style = "green" if overall_status == "healthy" else "red"
            
            table.add_row("Overall", overall_status, f"Version: {health_data.get('version', 'unknown')}")
            
            # Client health
            client_health = health_data.get("client", {})
            client_status = client_health.get("status", "unknown")
            client_style = "green" if client_status == "healthy" else "red"
            table.add_row("HTTP Client", client_status, client_health.get("base_url", ""))
            
            # Service health
            service_health = health_data.get("service_health", {})
            service_status = service_health.get("status", "unknown")
            service_style = "green" if service_status == "healthy" else "red"
            table.add_row("Service", service_status, "AutoPVS1 Service Layer")
            
            console.print(table)
            
            # Cache information
            if "cache_info" in service_health:
                cache_info = service_health["cache_info"]
                console.print("\n📊 Cache Statistics:", style="bold blue")
                for method, stats in cache_info.items():
                    if isinstance(stats, dict):
                        hit_rate = stats.get("hit_rate", 0) * 100
                        console.print(f"   {method}: {hit_rate:.1f}% hit rate ({stats.get('hits', 0)} hits, {stats.get('misses', 0)} misses)")
            
    except httpx.ConnectError:
        console.print("❌ Server is not running", style="red")
        console.print("   Start the server with: autopvs1-link server", style="dim")
    except Exception as e:
        console.print(f"❌ Health check failed: {e}", style="red")


@main.command()
async def cache() -> None:
    """Show cache statistics and manage cache."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            # Get cache stats
            response = await client.get(
                f"http://{settings.server.host}:{settings.server.port}/api/cache/stats",
                timeout=5.0
            )
            cache_stats = response.json()
            
            # Create cache statistics table
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
                    
                    table.add_row(
                        method,
                        str(hits),
                        str(misses),
                        f"{hit_rate:.1f}%",
                        str(total)
                    )
            
            console.print(table)
            
    except httpx.ConnectError:
        console.print("❌ Server is not running", style="red")
    except Exception as e:
        console.print(f"❌ Cache stats failed: {e}", style="red")


@main.command()
@click.confirmation_option(prompt="Are you sure you want to clear all caches?")
async def clear_cache() -> None:
    """Clear all cache entries."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{settings.server.host}:{settings.server.port}/api/cache/clear",
                timeout=5.0
            )
            result = response.json()
            
            if result.get("status") == "success":
                console.print("✅ All caches cleared successfully", style="green")
            else:
                console.print(f"❌ Failed to clear caches: {result.get('error')}", style="red")
                
    except httpx.ConnectError:
        console.print("❌ Server is not running", style="red")
    except Exception as e:
        console.print(f"❌ Clear cache failed: {e}", style="red")


# Make async commands work with click
def async_command(f):
    """Decorator to make async commands work with click."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Apply async decorator to async commands
health = async_command(health)
cache = async_command(cache)
clear_cache = async_command(clear_cache)


if __name__ == "__main__":
    main()