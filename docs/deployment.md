# Deployment

How to run `autopvs1-link` and how to connect a client to it. Configuration knobs are in
[`configuration.md`](configuration.md); the tool and REST surface is in [`api.md`](api.md).

## Transports

One codebase, three transports. Streamable HTTP is the hosted transport; the legacy SSE
transport is retired in FastMCP 3.

| Transport | How to start it | What it serves |
|-----------|-----------------|----------------|
| `unified` (default) | `make dev` — or `uv run autopvs1-link server` | REST API **and** MCP at `/mcp` on one port |
| `http` | `uv run autopvs1-link mcp --http --port 3000` | MCP over Streamable HTTP at `/mcp` |
| `stdio` | `make mcp-serve` — or `uv run autopvs1-link mcp` / `uv run python mcp_server.py` | MCP over stdio, for Claude Desktop and similar |

`AUTOPVS1_LINK_TRANSPORT` (`stdio` | `http` | `unified`) selects the default. Two console
scripts ship in `pyproject.toml`: `autopvs1-link` (the Typer CLI: `server`, `mcp`, `config`,
`health`, `cache`, `clear-cache`) and `autopvs1-link-mcp` (the stdio MCP entry point).

Local `make dev` publishes OpenAPI docs at `http://localhost:8000/docs`. The Docker
development stack publishes them at `http://localhost:8012/docs` (see below).

## Connecting a client

### Hosted (Streamable HTTP)

```bash
claude mcp add --transport http autopvs1 https://autopvs1-link.genefoundry.org/mcp
```

The hosted instance is also federated by
[`genefoundry-router`](https://github.com/berntpopp/genefoundry-router) under the namespace
token `autopvs1`, where its tools surface as `autopvs1_<tool>`.

### Claude Desktop (stdio)

The repository ships this snippet as `claude-desktop-config.json`:

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

Then ask, for example:

> Analyze the PVS1 criteria for variant X:g.83508928A>T in hg19.

## Docker

A multi-stage `Dockerfile` on `python:3.14-slim` and four Compose stacks (base, dev, prod,
npm) live under [`docker/`](../docker). **[`docker/README.md`](../docker/README.md) is the
runbook** — overlays, Nginx Proxy Manager wiring, monitoring, and port-conflict
troubleshooting. The Make targets:

```bash
make docker-build        # Build the image
make docker-up           # Start the dev stack
make docker-down         # Stop it
make docker-logs         # Follow logs
make docker-prod-config  # Render the prod Compose config (no deploy)
make docker-npm-config   # Render the NPM Compose config (no deploy)
```

The container listens on port `8000`. The **development stack publishes it on host port
`8012`** (`AUTOPVS1_LINK_HOST_PORT`), deliberately not `8000`, so this server can run beside
sibling `-link` projects on one workstation. Override the *host* port for local collisions;
leave `AUTOPVS1_LINK_PORT=8000` alone — that is the port inside the container.

The production and NPM overlays publish **no** host ports and are digest-pinned: they require
`AUTOPVS1_LINK_IMAGE` and refuse to render without it (`make docker-prod-config` substitutes a
zeroed placeholder digest for the syntax check; real deploys export the verified digest).

## Egress policy in production

Outbound network access is **denied by default** (`AUTOPVS1_LINK_API_EGRESS_MODE=disabled`).
The supplied production Compose overlay is a *public research profile*: it switches to
`allowlist` mode and permits the current AutoPVS1 and build-specific Ensembl services, which
receive the variant identifiers submitted to it.

**Do not use that profile for patient-derived data or clinical decision support.** A controlled
deployment either keeps egress disabled or replaces both the API base URL and the allowed
origins with operator-approved, self-hosted services. Docker networking is not an egress
firewall; a regulated environment also needs a host- or network-layer default-deny policy.
Origin, redirect and allowlist semantics are specified in
[`configuration.md`](configuration.md).

## Trust boundary

This server is **unauthenticated by design**. It must be reachable only through
`genefoundry-router` or a reverse proxy that owns edge authentication — never published
directly to the internet. See [`SECURITY.md`](../SECURITY.md).
