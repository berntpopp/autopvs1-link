# Architecture

## Overview

The project follows a layered architecture with singleton managers for resource lifecycle:

```
+-------------------------------------------------------------+
|                       Entry Points                          |
+-------------------------------------------------------------+
| server.py (FastAPI + MCP HTTP)  |  mcp_server.py (STDIO)    |
+-----------------+---------------------------+---------------+
                  |                           |
+-----------------v---------------+  +--------v--------------+
|         REST API Layer          |  |     MCP Layer         |
|  - FastAPI routes               |  |  - FastMCP tools      |
|  - HTTP endpoints               |  |  - Streamable HTTP    |
|  - OpenAPI docs                 |  |    + STDIO transports |
+-----------------+---------------+  +--------+--------------+
                  |                           |
                  |    +----------------------v---+
                  |    |     Singleton Managers   |
                  |    |  - ServiceManager        |
                  |    |  - ClientManager         |
                  |    |  - Lifecycle management  |
                  |    |  - Resource pooling      |
                  |    +-----------+--------------+
                  |                |
+-----------------v----------------v-------------------+
|                Service Layer                         |
|  - AutoPVS1Service (business logic)                  |
|  - Async LRU caching with TTL                        |
|  - Performance logging                               |
+-----------------+------------------------------------+
                  |
+-----------------v------------------------------------+
|                Client Layer                          |
|  - AutoPVS1Client (HTTP scraping)                    |
|  - Rate limiting                                     |
|  - HTML parsing with BeautifulSoup                   |
+-----------------+------------------------------------+
                  |
+-----------------v------------------------------------+
|              Data Models                             |
|  - Pydantic models for type safety                   |
|  - Validation and serialization                      |
|  - AutoPVS1Data, VariantInfo, PVS1Flowchart          |
+------------------------------------------------------+
```

## Directory Structure

Target layout (post-migration):

```
autopvs1-link/
|- AGENTS.md                          # canonical agent doc
|- CLAUDE.md                          # thin pointer to AGENTS.md
|- CHANGELOG.md
|- Makefile
|- pyproject.toml                     # hatchling + uv
|- uv.lock                            # committed
|- README.md
|- .pre-commit-config.yaml
|- .python-version
|- .editorconfig
|- .dockerignore
|- .env.example, .env.docker.example
|- .github/
|  |- workflows/
|  |  |- ci.yml
|  |  |- docker.yml
|  |  |- release.yml
|  |  |- security.yml
|  |  +- container-security.yml
|  |- dependabot.yml
|  +- pull_request_template.md
|- docker/
|  |- Dockerfile                      # multi-stage, python:3.14-slim
|  |- gunicorn_conf.py
|  |- docker-compose.yml
|  |- docker-compose.dev.yml
|  |- docker-compose.prod.yml
|  |- docker-compose.npm.yml
|  +- README.md
|- docs/
|  |- architecture.md                 # this file
|  |- configuration.md
|  |- api.md
|  |- MCP_CONNECTION_GUIDE.md
|  |- mcp-tool-catalog.md             # generated
|  +- superpowers/
|     |- specs/
|     +- plans/
|- scripts/
|  +- generate_mcp_tool_catalog.py
|- .planning/
|- autopvs1_link/
|  |- __init__.py                     # version + defusedxml.defuse_stdlib()
|  |- server_manager.py               # FastAPI app factory + MCP mount
|  |- unified_server.py               # transport composer
|  |- cli.py                          # typer CLI
|  |- config.py                       # AUTOPVS1_LINK_* env prefix
|  |- logging_config.py               # asgi-correlation-id integration
|  |- api/
|  |  |- routes/                      # variant.py, cnv.py, gene.py
|  |  |- autopvs1_client.py
|  |  |- client_manager.py
|  |  +- retry.py                     # inline async_retry helper
|  |- services/
|  |  |- autopvs1_service.py
|  |  +- service_manager.py
|  |- mcp/                            # MCP subpackage
|  |  |- __init__.py
|  |  |- tools/                       # variant_tool.py, cnv_tool.py, search_tool.py, cache_tools.py
|  |  |- catalog.py
|  |  |- contracts.py
|  |  |- errors.py
|  |  |- facade.py
|  |  |- metadata.py
|  |  |- resources.py
|  |  +- service_adapters.py
|  |- middleware/
|  |  +- logging_middleware.py
|  |- observability/
|  |  |- __init__.py
|  |  |- prometheus.py                # /metrics + metric definitions
|  |  +- correlation.py
|  +- models/
|     +- autopvs1_models.py
|- server.py                          # thin typer-routed entry
|- mcp_server.py                      # thin stdio entry
+- tests/
   |- fixtures/
   |- unit/
   |- integration/
   +- conftest.py
```

## Core Components

### Singleton Managers

`ServiceManager` (`autopvs1_link/services/service_manager.py`):

- Thread-safe singleton pattern with async locks
- Manages AutoPVS1Service lifecycle
- Provides health checks and cache management
- Handles graceful shutdown

`ClientManager` (`autopvs1_link/api/client_manager.py`):

- Thread-safe singleton for AutoPVS1Client instances
- Built-in rate limiting (1 second between requests)
- Connection pooling and resource cleanup
- Health monitoring

### Service Layer

`AutoPVS1Service` (`autopvs1_link/services/autopvs1_service.py`):

- Business logic with async LRU caching
- Cache configuration: 256 entries, 24-hour TTL
- Performance logging with structured context
- Methods: `get_variant_data()`, `search_variants()`, `get_cnv_data()`

### Client Layer

`AutoPVS1Client` (`autopvs1_link/api/autopvs1_client.py`):

- HTTP client using httpx with async support
- HTML parsing with BeautifulSoup + lxml (defused via `defusedxml`)
- Parses variant info, PVS1 flowcharts, disease mechanisms
- Handles both variants and CNVs

### Data Models

`Pydantic Models` (`autopvs1_link/models/autopvs1_models.py`):

- `VariantInfo`: Genetic variant details
- `PVS1Flowchart`: Decision tree and strength
- `DiseaseMechanism`: Gene-disease associations
- `AutoPVS1Data`: Complete variant analysis
- `AutoPVS1CNVData`: CNV-specific analysis
- `AutoPVS1SearchResults`: Search results

### Configuration

`Settings` (`autopvs1_link/config.py`):

- Pydantic settings with environment variable support
- Default values for all configuration options
- Supports `.env` file for local development
- Env prefix `AUTOPVS1_LINK_` (legacy `AUTOPVS1_` still read with one
  `DeprecationWarning` for one release cycle)

## Key Patterns

### Singleton Pattern with Thread Safety

```python
class ServiceManager:
    _instance: Optional["ServiceManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ServiceManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

### Async Context Managers for Resource Management

```python
@asynccontextmanager
async def get_client_context(self) -> AsyncGenerator[AutoPVS1Client, None]:
    await self._rate_limit()
    client = await self.get_client()
    try:
        yield client
    except Exception as e:
        logger.error("Error during client operation", error=str(e))
        raise
```

### Structured Logging with Context

```python
logger.info(
    "Fetching variant data",
    genome_build=genome_build,
    variant_id=variant_id,
)
```

Correlation IDs are automatically bound by the `asgi-correlation-id`
middleware so every log line carries the active request id.

### Async LRU Caching

```python
@alru_cache(maxsize=settings.cache.size)
async def get_variant_data(self, genome_build: str, variant_id: str) -> AutoPVS1Data:
    ...
```

### FastAPI Lifespan Management

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await shutdown_services()
    await shutdown_clients()
```

## Important Considerations

### Rate Limiting

- Built-in 1-second delay between requests to be respectful to upstream
- Configurable via ClientManager settings
- Async rate limiting implementation

### Error Handling

- Comprehensive exception handling in all layers
- Structured error logging with context
- Graceful degradation for parsing failures

### Data Accuracy

- HTML parsing depends on stable DOM structure
- Always verify critical clinical interpretations
- Cache may serve stale data (TTL: 24h default)

### Dependencies

- Requires internet access to `autopvs1.bgi.com`
- Service availability depends on upstream status
- No offline mode available

## Related Resources

- AutoPVS1 service: https://autopvs1.bgi.com
- FastAPI: https://fastapi.tiangolo.com/
- FastMCP: https://github.com/jlowin/fastmcp
- Model Context Protocol: https://spec.modelcontextprotocol.io/
