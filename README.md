# AutoPVS1 Link

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![FastMCP](https://img.shields.io/badge/FastMCP-3.2+-orange.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A unified server providing both REST API and MCP (Model Context Protocol)
interfaces for accessing PVS1 variant classification data from
[AutoPVS1](https://autopvs1.bgi.com). Built with FastAPI and FastMCP for
seamless integration with AI assistants and web applications.

## Modern stack (May 2026)

- Python 3.12+ (3.13 / 3.14 supported)
- `uv` for dependency management with committed `uv.lock`
- `hatchling` build backend
- `ruff` for both lint and format (Black removed)
- `mypy` strict
- FastAPI + Pydantic 2.11+
- FastMCP 3.2+ with Streamable HTTP transport (SSE retired)
- Observability: `structlog` + `asgi-correlation-id` + `prometheus-client`
- `defusedxml` for XML/HTML hardening
- `gunicorn` + `uvicorn` workers in production (Docker)
- Multi-stage Dockerfile on `python:3.14-slim`

## Quick start

### Installation

```bash
git clone https://github.com/berntpopp/autopvs1-link.git
cd autopvs1-link

# Install with development dependencies
uv sync --group dev
```

### Run

```bash
# Unified server (REST + MCP) on http://127.0.0.1:8000
make dev

# Or via the CLI
uv run autopvs1-link server

# MCP stdio (for Claude Desktop and similar)
uv run autopvs1-link mcp

# MCP over Streamable HTTP
uv run autopvs1-link mcp --http --port 3000
```

### Claude Desktop integration

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "autopvs1-link": {
      "command": "python",
      "args": ["-m", "autopvs1_link.cli", "mcp"]
    }
  }
}
```

Then ask Claude:

> Analyze the PVS1 criteria for variant X:g.83508928A>T in hg19.

## API

### REST endpoints

OpenAPI docs at `http://localhost:8000/docs` for local `make dev`.
The Docker development stack publishes the container on
`http://localhost:8012` by default to avoid collisions with sibling projects.

```
GET  /variant/{genome_build}/{variant_id}              # PVS1 analysis for a variant
GET  /variant/search?q={gene}&genome_version={build}   # Variant search
GET  /cnv/{genome_build}/{cnv_id}                      # PVS1 analysis for a CNV
GET  /health                                           # Health probe
GET  /metrics                                          # Prometheus metrics
GET  /api/cache/stats                                  # Cache stats
POST /api/cache/clear                                  # Clear caches
```

See [`docs/api.md`](docs/api.md) for the full reference.

### MCP tools and resources

Default tools (7):

- `get_variant_pvs1_data(genome_build, variant_id)`
- `get_cnv_pvs1_data(genome_build, cnv_id)`
- `search_variants(query, genome_build=None, limit=10, cursor=None)`
- `get_server_health()`
- `get_server_capabilities()`

Bulk tools:

- `get_variants_pvs1_data_bulk(items, ...)`
- `get_cnvs_pvs1_data_bulk(items, ...)`

Opt-in destructive tool:

- `clear_cache()` - registered only when
  `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`

### GeneFoundry router / namespace token

This server is a member of the GeneFoundry `*-link` MCP fleet and conforms to
the [GeneFoundry Tool-Naming & Normalization Standard v1](https://github.com/berntpopp/autopvs1-link/issues/24).
Tool names are left **unprefixed** (`get_variant_pvs1_data`, not
`autopvs1_get_variant_pvs1_data`): namespacing is the gateway's job. When the
`genefoundry-router` mounts this server it applies the canonical **namespace
token `autopvs1`**, so tools surface at the gateway as `autopvs1_<tool>` (for
example `autopvs1_get_variant_pvs1_data`). The stable `serverInfo.name` is
**`autopvs1-link`** (lowercase, hyphenated, matching the namespace; set in
`autopvs1_link/mcp/server_info.py`).

All tool names use the canonical verb set (`get`, `search`) and stay well under
the 50-char limit. The sole exception is the gated, off-by-default `clear_cache`
tool, whose `clear` verb is a documented exception for destructive cache
management (it never pollutes the default surface). Tools also carry domain
`tags` (`variant`, `cnv`/`copy-number`, `classification`, `discovery`, `bulk`,
`meta`) so the gateway can filter and curate the surfaced toolset. The
`tests/unit/mcp/test_tool_names.py` CI guard enforces this contract.

Resources (2):

- `autopvs1-link://cache/statistics` - read-only cache stats snapshot
- `autopvs1-link://capabilities` - detailed MCP usage guidance

Prompts (2):

- `classify_variant` - canonical variant classification workflow guidance
- `classify_cnv` - canonical CNV classification workflow guidance

Cache statistics expose stable method-keyed counters and cache-key-shape
metadata for the configured service methods.

MCP tool responses use the GeneFoundry Response-Envelope Standard v1 flat
banner: `{"success": true, "result"|"results", "_meta"}` on success,
`{"success": false, "error_code", "message", "retryable", "recovery_action",
"_meta"}` on failure (with MCP `isError: true`).
Read tools accept `response_mode` (`summary`, `standard`, `full`) and
`meta_mode` (`full`, `compact`, `minimal`) so agents can control token cost
while preserving research-use framing. Variant and CNV tools also accept
`include_unmet` to filter disease-mechanism rows. Validation and upstream
failures return stable `error_code` values; CNV colon-form validation errors
include a structured `details.corrected_id` when a corrected AutoPVS1 ID
can be derived. Search pagination uses `limit` plus the returned
`pagination.next_cursor`; omitting `genome_build` defaults to `hg38` with a warning.
Outputs are research-use AutoPVS1 data, not clinical decision support; cite
AutoPVS1 (`10.1002/humu.24051`) where appropriate.

The auto-generated tool catalog with full schemas lives in
[`docs/mcp-tool-catalog.md`](docs/mcp-tool-catalog.md).

## Configuration

Settings are read from the `AUTOPVS1_LINK_*` env-var family (or a local
`.env` file). The legacy `AUTOPVS1_*` prefix is still accepted for one
release with a `DeprecationWarning`. See
[`docs/configuration.md`](docs/configuration.md) for the full migration
table and tunable knobs.

```bash
AUTOPVS1_LINK_API_BASE_URL=https://autopvs1.bgi.com
AUTOPVS1_LINK_API_REQUEST_TIMEOUT=30
AUTOPVS1_LINK_CACHE_SIZE=256
AUTOPVS1_LINK_LOG_LEVEL=INFO
AUTOPVS1_LINK_METRICS_ENABLED=true
AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=false
```

## Development

```bash
make install         # Install + sync dev deps
make format          # Run ruff format
make lint            # Run ruff check
make typecheck       # Run mypy strict
make test            # Run tests
make test-cov        # Run tests with coverage report
make ci-local        # format-check + lint + typecheck + test (the CI gate)
```

Pre-commit hooks ship in `.pre-commit-config.yaml`:

```bash
uv run pre-commit install
```

## Docker

Multi-stage Dockerfile on `python:3.14-slim` and four Compose stacks (base,
dev, prod, npm) live under `docker/`. See
[`docker/README.md`](docker/README.md) for usage.

```bash
make docker-build    # Build image
make docker-up       # Start dev stack
make docker-down     # Stop
make docker-logs     # Follow logs
```

## Documentation

- [`docs/architecture.md`](docs/architecture.md) - layered architecture
- [`docs/configuration.md`](docs/configuration.md) - env-var reference
- [`docs/api.md`](docs/api.md) - REST + MCP surface
- [`docs/mcp-tool-catalog.md`](docs/mcp-tool-catalog.md) - generated tool schemas
- [`docs/mcp-evaluation-checklist.md`](docs/mcp-evaluation-checklist.md) - MCP contract checks
- [`SECURITY.md`](SECURITY.md) - vulnerability reporting + required repo security settings
- [`AGENTS.md`](AGENTS.md) - shared instructions for agentic coding tools
- [`CHANGELOG.md`](CHANGELOG.md) - release notes

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run `make ci-local` and make sure it passes
4. Open a Pull Request

## License

MIT - see [LICENSE](LICENSE).

## Acknowledgments

- [AutoPVS1](https://autopvs1.bgi.com) for providing the PVS1 variant classification service
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [FastMCP](https://github.com/jlowin/fastmcp) for MCP integration
- [Pydantic](https://docs.pydantic.dev/) for data validation and settings
