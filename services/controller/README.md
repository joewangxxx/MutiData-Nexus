# Controller Service

This directory contains the FastAPI backend controller for MutiData-Nexus.

## Local Environment

Required environment variables for the current foundation, Coze integrations, and release hardening package:

You can place them in `services/controller/.env`; the controller settings loader now reads that local file first when a variable is not already present in the process environment.

- `DATABASE_URL` - PostgreSQL connection string
- `COZE_CALLBACK_SECRET` - shared secret used by the Coze callback handler
- `COZE_ANNOTATION_RUN_URL` - Coze run endpoint for annotation assist, defaulting to `https://zvqrc5d642.coze.site/run`
- `COZE_API_TOKEN` - bearer token used when calling the Coze run endpoint
- `COZE_RISK_RUN_URL` - Coze run endpoint for project risk analysis, defaulting to `https://d784kg4tzc.coze.site/run`
- `COZE_RISK_API_TOKEN` - bearer token used when calling the risk Coze run endpoint
- `COZE_TIMEOUT_SECONDS` - HTTP timeout for Coze dispatches, default `15`
- `RELEASE_BOOTSTRAP_DATA` - optional release-compose bootstrap toggle; when true, `app.scripts.release_bootstrap` seeds the minimal runtime dataset

## Verification

From `services/controller`:

- `python -m pytest tests -q`
- `python -m compileall app ../db`

## Release Hardening

- `GET /api/v1/ops/healthz` returns a lightweight controller health response.
- `GET /api/v1/ops/readyz` validates runtime configuration and database connectivity.
- `services/controller/Dockerfile` builds the controller image for the release stack.
- `compose.release.yaml` at the repository root wires controller, web, and PostgreSQL together for release smoke tests.
- `ops/release/smoke.ps1` runs the controller and web release smoke checks.
- `ops/release/rollback.ps1` stops the release stack.
- `docs/observability.md` describes the release observability posture for the current package.
