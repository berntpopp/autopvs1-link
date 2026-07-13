# Multi-stage Dockerfile for AutoPVS1-Link.

# --- Builder ---
FROM python:3.14-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY uv.lock pyproject.toml README.md ./

# Reproducible builder bootstrap (F-19): copy uv from the fleet's digest-pinned
# installer image instead of bootstrapping a floating pip/uv.
COPY --from=ghcr.io/astral-sh/uv:0.8.7@sha256:1e26f9a868360eeb32500a35e05787ffff3402f01a8dc8168ef6aee44aef0aab /uv /usr/local/bin/uv

RUN uv sync --frozen --no-dev --active

# --- Prepared filesystem ---
FROM python:3.14-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1 AS prepared

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/home/app/web" \
    AUTOPVS1_LINK_HOST=0.0.0.0 \
    AUTOPVS1_LINK_PORT=8000 \
    AUTOPVS1_LINK_TRANSPORT=unified \
    TMPDIR=/tmp/autopvs1-link

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --home /home/app --create-home --shell /usr/sbin/nologin app && \
    mkdir -p /tmp/autopvs1-link /var/cache/autopvs1-link && \
    chown -R app:app /tmp/autopvs1-link /var/cache/autopvs1-link /home/app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /home/app/web

COPY --chown=app:app ./autopvs1_link ./autopvs1_link
COPY --chown=app:app ./server.py ./mcp_server.py ./pyproject.toml ./README.md ./
COPY --chown=app:app ./docker/gunicorn_conf.py ./

RUN /opt/venv/bin/pip install -e . --no-deps

RUN rm -rf /root/.cache/pip /usr/local/lib/python*/ensurepip/_bundled/*.whl \
    && find / -xdev -type d -name __pycache__ -prune -exec rm -rf '{}' + \
    && find / -xdev -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

RUN find / -xdev -perm /6000 -exec chmod a-s '{}' + \
    && test -z "$(find / -xdev -perm /6000 -print -quit)"

RUN actual="$(find / -xdev -type f -links +1 -printf '%i %p\n' | sort -k2,2)" \
    && expected="$(printf '%s %s\n%s %s\n' \
         "$(stat -c '%i' /usr/bin/perl)" /usr/bin/perl \
         "$(stat -c '%i' /usr/bin/perl5.40.1)" /usr/bin/perl5.40.1 | sort -k2,2)" \
    && { test "$actual" = "$expected" || { printf 'unexpected hardlinks:\n%s\n' "$actual"; exit 1; }; } \
    && rm -f /usr/bin/perl5.40.1

# --- Production ---
FROM scratch AS production
COPY --from=prepared / /

ARG APP_VERSION=0.0.0
ARG VCS_REF=unknown
ARG BUILD_DATE=1970-01-01T00:00:00Z
LABEL org.opencontainers.image.title="AutoPVS1-Link" \
      org.opencontainers.image.description="Research-use FastAPI and MCP server for AutoPVS1 PVS1 variant data." \
      org.opencontainers.image.source="https://github.com/berntpopp/autopvs1-link" \
      org.opencontainers.image.url="https://github.com/berntpopp/autopvs1-link" \
      org.opencontainers.image.documentation="https://github.com/berntpopp/autopvs1-link#readme" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="GeneFoundry"
ENV APP_VERSION="${APP_VERSION}" \
    VCS_REF="${VCS_REF}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONPATH="/home/app/web" \
    AUTOPVS1_LINK_HOST=0.0.0.0 \
    AUTOPVS1_LINK_PORT=8000 \
    AUTOPVS1_LINK_TRANSPORT=unified \
    TMPDIR=/tmp/autopvs1-link

WORKDIR /home/app/web

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["gunicorn", "-c", "gunicorn_conf.py", "autopvs1_link.server_manager:app"]
