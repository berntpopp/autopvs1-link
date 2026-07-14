# autopvs1-link

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/berntpopp/autopvs1-link/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/autopvs1-link/actions/workflows/ci.yml)
[![Conformance](https://github.com/berntpopp/autopvs1-link/actions/workflows/conformance.yml/badge.svg)](https://github.com/berntpopp/autopvs1-link/actions/workflows/conformance.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An MCP (Model Context Protocol) server — and a REST API on the same process — serving PVS1
loss-of-function evidence for variants and CNVs from
[AutoPVS1](https://autopvs1.bgi.com), the automated ACMG PVS1 interpreter.

> [!IMPORTANT]
> Research use only. Not clinical decision support. Do not use for diagnosis,
> treatment, triage, or patient management.

## Why

**AutoPVS1 has no API.** It is a web form that renders results as HTML, so every programmatic
consumer has to scrape and parse the page. This server does that once, defensively, and hands
back typed JSON: the PVS1 strength, the flowchart decision path, and the disease-mechanism rows.

Doing it properly is the whole point. Parsers are pinned to committed HTML fixtures so an
upstream DOM change fails CI instead of silently returning wrong evidence; a 1.0s courtesy
delay and a 24h cache keep a chatty agent from hammering a service that never asked for the
traffic; and every scraped payload carries a provenance note saying the fields came from
unversioned HTML and may drift. Bulk and CNV entry points, which the web form has no
equivalent for, come for free.

## Quick start

Use the hosted deployment — no install, no upstream scraping of your own:

```bash
claude mcp add --transport http autopvs1 https://autopvs1-link.genefoundry.org/mcp
```

To run it locally (Python 3.12+, [uv](https://github.com/astral-sh/uv)):

```bash
uv sync --group dev
cp .env.example .env
make dev            # REST + MCP on http://127.0.0.1:8000 (MCP at /mcp)
```

There is no data build — the server holds no local corpus and fetches from AutoPVS1 live.
But **outbound network access is denied by default**, so a fresh checkout answers nothing
until you opt in explicitly:

```bash
AUTOPVS1_LINK_API_EGRESS_MODE=allowlist
AUTOPVS1_LINK_API_ALLOWED_UPSTREAM_ORIGINS=https://autopvs1.bgi.com,https://rest.ensembl.org,https://grch37.rest.ensembl.org
```

Those public services receive the variant identifiers you submit. Do not point this profile at
patient-derived data — see [Configuration](docs/configuration.md) for the controlled-deployment
alternative, and [Deployment](docs/deployment.md) for stdio (Claude Desktop) and Docker.

## Tools

| Tool | Purpose |
|------|---------|
| `get_variant_pvs1_data` | PVS1 evidence for one SNV/indel (e.g. `X-82763936-A-T`) — strength, flowchart, disease mechanisms |
| `get_cnv_pvs1_data` | PVS1 evidence for one CNV (e.g. `17-15000000-20000000-DEL`) |
| `get_variants_pvs1_data_bulk` | Batch the SNV/indel lookup over many identifiers in one call |
| `get_cnvs_pvs1_data_bulk` | Batch the CNV lookup over many identifiers in one call |
| `search_variants` | Find AutoPVS1 variant records by gene or free text; cursor-paginated |
| `get_server_health` | Local server health, version, and destructive-tool registration — never calls upstream |
| `get_server_capabilities` | Compact discovery payload pointing at `autopvs1-link://capabilities` |

Leaf names are unprefixed per
[Tool-Naming Standard v1](https://github.com/berntpopp/genefoundry-router/blob/main/docs/TOOL-NAMING-STANDARD-v1.md) —
namespacing is the gateway's job. Behind `genefoundry-router` this server mounts under the
canonical namespace token `autopvs1`, so the tools above surface as `autopvs1_<tool>` (e.g.
`autopvs1_get_variant_pvs1_data`, the pinned entry point).

A destructive `clear_cache` tool exists but is **off the default surface**; it registers only
when `AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=true`. Two MCP resources and two classification
prompts ship alongside the tools. Response envelopes, `response_mode` / `meta_mode` token
controls, pagination, and error codes are documented in the
[API reference](docs/api.md); full schemas are in the generated
[tool catalog](docs/mcp-tool-catalog.md).

## Data & provenance

- **Upstream**: [AutoPVS1](https://autopvs1.bgi.com) (BGI). Genome builds `hg19` and `hg38`;
  omitting the build defaults to `hg38` and returns a warning.
- **Refresh model**: none — this server mirrors nothing. Every answer is scraped live from
  AutoPVS1's HTML and cached in memory (default 256 entries, 24h TTL). Upstream requests are
  spaced by a 1.0s rate-limit delay by contract; do not shorten it.
- **Fragility**: AutoPVS1's HTML is not a versioned contract. Scrape-tier responses carry an
  `upstream_provenance` note saying so, and `_meta.unsafe_for_clinical_use` is always `true`.
- **Citation** — cite AutoPVS1, not this wrapper:
  > Xiang J, Peng J, Baxter S, Peng Z. AutoPVS1: An automatic classification tool for PVS1
  > interpretation of null variants. *Human Mutation*. 2020;41(9):1488-1498.
  > DOI [10.1002/humu.24051](https://doi.org/10.1002/humu.24051), PMID 32442321.

## Documentation

- [Architecture](docs/architecture.md) — layered design, the technology stack, and the fleet federation contract.
- [Configuration](docs/configuration.md) — every `AUTOPVS1_LINK_*` variable, the egress policy, and the legacy-prefix migration.
- [Deployment](docs/deployment.md) — transports, Claude Desktop stdio, Docker, and the reverse-proxy boundary.
- [API reference](docs/api.md) — REST endpoints, the response envelope, resources, and prompts.
- [Tool catalog](docs/mcp-tool-catalog.md) — generated input/output schemas for every tool.
- [MCP evaluation checklist](docs/mcp-evaluation-checklist.md) — the MCP contract checks.
- [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md) · [AGENTS.md](AGENTS.md)

## Contributing

Read [`AGENTS.md`](AGENTS.md) for engineering conventions — it is the contributor guide.
`make ci-local` is the definition-of-done gate: format, lint, line budget, README standard,
mypy, and tests. New parser behaviour needs an HTML fixture under `tests/fixtures/`.

## License

Code: [MIT](LICENSE) © Bernt Popp. Data: PVS1 classifications are produced by the upstream
AutoPVS1 service and remain subject to its terms; this repository redistributes none of them
and asserts no licence over them. Research use only — mirror AutoPVS1's disclaimers and the
citation above.
