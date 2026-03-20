# Release Operations

This directory contains the minimal release-hardening package for the controller, web, and PostgreSQL release stack.

## What is included

- Controller health and readiness checks at `/api/v1/ops/healthz` and `/api/v1/ops/readyz`
- Web health and readiness checks at `/healthz` and `/readyz`
- Controller Docker image
- Web Docker image
- Release compose stack for controller, web, and PostgreSQL
- Smoke and rollback helper scripts
- Release environment example
- Observability guide at `docs/observability.md`

## Quick Start

1. Copy `ops/release/release.env.example` to `ops/release/release.env`.
2. Fill in the required Coze and callback secrets plus `CONTROLLER_API_AUTH_TOKEN` for the web server runtime.
3. Keep `RELEASE_BOOTSTRAP_DATA=true` if you want the release stack to seed the minimal runtime dataset automatically.
4. Run `docker compose -f compose.release.yaml up -d --build`.
5. Run `ops/release/smoke.ps1` to confirm the release stack is healthy.

## Rollback

- Use `ops/release/rollback.ps1` to stop the release stack safely.
- Re-run the compose stack after reverting to the desired revision.

## Notes

- The controller readiness check validates runtime configuration and database connectivity.
- The web readiness check validates controller availability before reporting ready.
- The web server runtime uses `CONTROLLER_API_AUTH_TOKEN` only on the server when it must fetch controller data without an incoming browser `Authorization` header.
- The release compose stack can seed the minimal runtime dataset through `RELEASE_BOOTSTRAP_DATA=true` before controller startup.
- The compose stack is intentionally minimal, but it now includes both product surfaces needed for release rehearsal.
