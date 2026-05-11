# Docker deployment for AutoPVS1-Link

## Files

- `Dockerfile` - multi-stage build on `python:3.14-slim`.
- `gunicorn_conf.py` - production process config (uvicorn workers).
- `docker-compose.yml` - base service definition.
- `docker-compose.dev.yml` - overlay: bind-mount + uvicorn reload.
- `docker-compose.prod.yml` - overlay: production env, resource limits.
- `docker-compose.npm.yml` - overlay: Nginx Proxy Manager network/labels.

## Quick start

```bash
make docker-build
make docker-up
curl http://127.0.0.1:8000/health
make docker-down
```

## Production preview

```bash
make docker-prod-config
make docker-npm-config
```

These render the merged Compose configuration without starting containers,
the same way the `docker.yml` CI workflow validates them.
