# Deployment Notes

Status: `release_hardening_ready`
Owner: `general`
Last Updated: `2026-03-20`

This document covers the current local and release-hardening runtime assumptions for the platform. It now includes the minimal release package, but it still does not describe a full production deployment process.

## Current Readiness

- The frontend and backend foundation slices run and verify locally.
- The release hardening package now exists for controller and web, so the stack can be rehearsed with Docker Compose.
- The frontend still uses mock adapters for business data, so end-to-end FE to BE deployment is not a production claim.
- Production infrastructure, CI/CD, and cloud-target-specific orchestration are not defined yet.
- See `docs/observability.md` for the minimal release smoke and readiness signal guide.

## Verified Local Prerequisites

- Node.js 24.x and npm 11.x for the frontend workspace.
- Python 3.11.x for the controller service.
- PostgreSQL reachable at the configured `DATABASE_URL`.
- Alembic available through the controller service environment.

## Backend Runtime Assumptions

- PostgreSQL is the system of record and the controller defaults to `postgresql+psycopg://postgres:postgres@localhost:5432/mutidata_nexus`.
- The controller expects `psycopg[binary]` support so the intended database driver path is available locally.
- The Alembic environment is rooted at `db/alembic` and uses the controller models as migration metadata.
- Coze callback handling expects a `COZE_CALLBACK_SECRET` value for signature validation in non-mock flows.
- The live annotation Coze gateway expects `COZE_ANNOTATION_RUN_URL`, `COZE_API_TOKEN`, and optional `COZE_TIMEOUT_SECONDS`.
- The release controller health check is exposed at `/api/v1/ops/healthz`.
- The release controller readiness check is exposed at `/api/v1/ops/readyz` and fails closed when runtime configuration or the database is unavailable.
- The release web readiness check is exposed at `/readyz` and fails closed when the controller health endpoint is unavailable.

## Suggested Local Setup

1. Start a PostgreSQL instance and create the `mutidata_nexus` database.
2. Export `DATABASE_URL` if your local database is not using the default controller URL.
3. Export `COZE_CALLBACK_SECRET` if you need to test signed callback handling.
4. Export `COZE_ANNOTATION_RUN_URL` for the annotation workflow endpoint. The current approved value is `https://zvqrc5d642.coze.site/run`.
5. Export `COZE_API_TOKEN` for backend-owned Bearer authentication to Coze.
6. Optionally export `COZE_TIMEOUT_SECONDS` to tune outbound annotation workflow timeouts.
7. Export `COZE_RISK_RUN_URL` and `COZE_RISK_API_TOKEN` for project risk monitoring.
8. Export `CONTROLLER_API_AUTH_TOKEN` for the web server runtime when SSR controller requests need a server-only Bearer token fallback in release rehearsal.
9. Export `RELEASE_BOOTSTRAP_DATA=true` if you want the release compose stack to seed the minimal runtime dataset automatically before controller startup.
10. Export `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`, `CONTROLLER_PORT`, and `WEB_PORT` if you are rehearsing the release compose stack.
11. Run the frontend from `apps/web`.
12. Run the controller service from `services/controller`.
13. Apply Alembic migrations from the `db` directory against the target PostgreSQL database.

## Release Rehearsal

The minimal release package can be rehearsed with:

```powershell
docker compose -f compose.release.yaml up -d --build
```

Then run the smoke helper:

```powershell
ops/release/smoke.ps1
```

The smoke helper checks:

- Controller `/api/v1/ops/healthz`
- Controller `/api/v1/ops/readyz`
- Web `/healthz`
- Web `/readyz`

For release-runtime business pages, the web server may also need `CONTROLLER_API_AUTH_TOKEN` so SSR controller fetches can authenticate even when the browser request itself does not carry an `Authorization` header.

When `RELEASE_BOOTSTRAP_DATA=true`, the release compose stack runs a one-shot bootstrap step that seeds the minimal runtime dataset before controller startup.

## Annotation Coze Integration Notes

- The frontend never calls Coze directly.
- `POST /api/v1/annotation-tasks/{task_id}/ai-generate` now dispatches through the backend-owned gateway.
- The controller reads the task, validates a public `http(s)` asset URL, sends `{"file_url": "<asset-url>"}` to Coze, and persists:
  - outbound `workflow_runs`
  - outbound `coze_runs`
  - normalized `ai_results`
  - audit events
- The current integration path treats the provided `/run` endpoint as a synchronous response path and persists the returned payload in the same request lifecycle.

## Current Verification Commands

- Frontend build and test checks are run from `apps/web`.
- Backend verification is run from `services/controller` with `pytest` and Python compilation checks.
- The verified foundation milestone has already passed these checks in QA, but that does not imply production readiness.
- Release rehearsal should additionally include `docker compose -f compose.release.yaml config` and the release smoke helper.

## Not Yet Defined

- A production cloud target and its environment-specific manifests.
- Migration automation in a production CI/CD pipeline.
- Production incident paging and alert routing.
- Centralized log aggregation and metrics backend wiring.
