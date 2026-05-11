# Configuration

## Environment Variables

All settings can be supplied via environment variables (or a local `.env`
file). The canonical prefix is `AUTOPVS1_LINK_`. Sub-prefixes scope settings
to a sub-config (`AUTOPVS1_LINK_API_*`, `AUTOPVS1_LINK_CACHE_*`,
`AUTOPVS1_LINK_SERVER_*`, `AUTOPVS1_LINK_LOG_*`, `AUTOPVS1_LINK_MCP_*`).

### Server

```bash
AUTOPVS1_LINK_HOST=127.0.0.1
AUTOPVS1_LINK_PORT=8000
AUTOPVS1_LINK_TRANSPORT=unified            # stdio | http | unified
AUTOPVS1_LINK_SERVER_CORS_ORIGINS=*
```

### API client

```bash
AUTOPVS1_LINK_API_BASE_URL=https://autopvs1.bgi.com
AUTOPVS1_LINK_API_REQUEST_TIMEOUT=30
AUTOPVS1_LINK_API_MAX_RETRIES=3
AUTOPVS1_LINK_API_RATE_LIMIT_DELAY=1.0
```

### Caching

```bash
AUTOPVS1_LINK_CACHE_SIZE=256
AUTOPVS1_LINK_CACHE_TTL_HOURS=24
```

### Logging

```bash
AUTOPVS1_LINK_LOG_LEVEL=INFO
AUTOPVS1_LINK_LOG_JSON_FORMAT=false
```

### Observability

```bash
AUTOPVS1_LINK_METRICS_ENABLED=true     # gates the /metrics endpoint
```

### MCP

```bash
AUTOPVS1_LINK_ENABLE_DESTRUCTIVE_TOOLS=false   # gates the clear_cache tool
```

## Performance Tuning

```bash
# High-performance configuration
AUTOPVS1_LINK_CACHE_SIZE=1024
AUTOPVS1_LINK_CACHE_TTL_HOURS=48
AUTOPVS1_LINK_API_REQUEST_TIMEOUT=45
```

```bash
# Memory-optimized configuration
AUTOPVS1_LINK_CACHE_SIZE=128
AUTOPVS1_LINK_CACHE_TTL_HOURS=12
AUTOPVS1_LINK_API_REQUEST_TIMEOUT=20
```

## Migration from `AUTOPVS1_*` to `AUTOPVS1_LINK_*`

Starting with this release, the env-var prefix migrates from `AUTOPVS1_*` to
`AUTOPVS1_LINK_*` to align with the rest of the `*-link` server family.

### Compatibility shim

For one release cycle, settings reads both prefixes. If only the legacy
prefix is set the value is honoured and a single `DeprecationWarning` is
emitted at startup, naming each old-prefixed variable. When both are set,
the new prefix wins.

### Common renames

| Legacy variable                  | New variable                          |
|----------------------------------|---------------------------------------|
| `AUTOPVS1_API_BASE_URL`          | `AUTOPVS1_LINK_API_BASE_URL`          |
| `AUTOPVS1_API_REQUEST_TIMEOUT`   | `AUTOPVS1_LINK_API_REQUEST_TIMEOUT`   |
| `AUTOPVS1_CACHE_SIZE`            | `AUTOPVS1_LINK_CACHE_SIZE`            |
| `AUTOPVS1_CACHE_TTL_HOURS`       | `AUTOPVS1_LINK_CACHE_TTL_HOURS`       |
| `AUTOPVS1_SERVER_CORS_ORIGINS`   | `AUTOPVS1_LINK_SERVER_CORS_ORIGINS`   |
| `AUTOPVS1_LOG_LEVEL`             | `AUTOPVS1_LINK_LOG_LEVEL`             |
| `AUTOPVS1_LOG_JSON_FORMAT`       | `AUTOPVS1_LINK_LOG_JSON_FORMAT`       |
| `AUTOPVS1_MCP_*`                 | `AUTOPVS1_LINK_MCP_*`                 |

### Removal timeline

The compat shim ships in this release and is removed in the next minor
release after that. Update deployment configs (.env files, docker-compose
overrides, CI secret names) at your earliest convenience.
