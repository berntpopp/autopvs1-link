---
name: release-readiness
description: Use before tagging, publishing, or promoting AutoPVS1-Link builds.
---

# Release Readiness

Follow `AGENTS.md` first.

## Workflow

1. Confirm the worktree only contains intended release changes.
2. Run `make ci-local`, then any `docker-*-config` validation targets the Makefile exposes.
3. Build the Docker image with `make docker-build`.
4. Check README, changelog, MCP safety language, and deployment docs for drift.
5. Confirm destructive MCP tools remain opt-in.
6. Record residual risks before handoff.
