# Docker Deployment

AutoPVS1-Link uses the same Compose layering style as the sibling Link
projects. The container listens on port `8000`; the local development stack
publishes it to host port `8012` by default so PubTator-Link, GeneReview-Link,
and AutoPVS1-Link can run side by side on the same workstation.

## Files

- `Dockerfile` - multi-stage build on `python:3.14-slim`.
- `gunicorn_conf.py` - production process config with uvicorn workers.
- `docker-compose.yml` - base local service definition.
- `docker-compose.dev.yml` - bind mounts plus uvicorn reload.
- `docker-compose.prod.yml` - production env, resource limits, no published
  host ports.
- `docker-compose.npm.yml` - Nginx Proxy Manager network exposure, no
  published host ports.

## Local Development

```bash
make docker-build
make docker-up
curl http://127.0.0.1:8012/health
make docker-down
```

Override only the workstation host port when another service already uses it:

```bash
AUTOPVS1_LINK_HOST_PORT=8112 make docker-up
curl http://127.0.0.1:8112/health
```

Keep `AUTOPVS1_LINK_PORT=8000` unless the app inside the container must bind a
different port.

## Compose Overlays

Layer overlays explicitly:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
```

Production overlays reset host port publishing. Expose the service through a
reverse proxy, another container on the Compose network, or a local-only
override file.

```bash
make docker-prod-config
make docker-npm-config
```

These render merged Compose configuration without starting containers, matching
the Docker CI validation path.

## Nginx Proxy Manager

Use production and NPM overlays together:

```bash
docker compose \
  --env-file .env.docker \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  -f docker/docker-compose.npm.yml \
  up -d --build
```

The NPM overlay attaches `autopvs1-link` to the external
`nginx-proxy-manager_default` network and exposes container port `8000` without
publishing a workstation host port.

Configure Nginx Proxy Manager with:

- Forward hostname: `autopvs1_link_server`
- Forward port: `8000`
- Scheme: `http`
- Websockets support: enabled

The REST API is available at `/`, and the MCP endpoint is available at `/mcp`.

## Monitoring

- Local health check: `curl http://127.0.0.1:8012/health`
- Local API docs: `http://127.0.0.1:8012/docs`
- Local MCP endpoint: `http://127.0.0.1:8012/mcp`
- Container logs: `docker compose -f docker/docker-compose.yml logs -f autopvs1-link`

## Troubleshooting

### Port Conflicts

Set a different host published port:

```bash
AUTOPVS1_LINK_HOST_PORT=8112 make docker-up
```

Do not change `AUTOPVS1_LINK_PORT` for ordinary workstation conflicts; that is
the application port inside the container.

### NPM Cannot Reach The App

Confirm the service is attached to `nginx-proxy-manager_default` and proxy to
`autopvs1_link_server:8000`. Do not use the workstation host port for NPM.
