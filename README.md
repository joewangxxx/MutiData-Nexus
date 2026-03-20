# MutiData-Nexus

Unified AI data operations platform for multimodal annotation and project risk monitoring.

Status: `verified implementation slices with backend-owned annotation and risk Coze integrations, release hardening, and a closed Release 1 gate`

This repository is no longer scaffold-only. It contains a verified foundation slice for a Next.js frontend, a FastAPI controller service, and a PostgreSQL-oriented schema baseline. The release hardening package is also present, but the product is not release-ready yet and has not reached full MVP acceptance.

## Current State

- Frontend foundation exists in `apps/web` with a shared workspace shell and the first route family in place.
- Backend foundation exists in `services/controller` with core API routes, error handling, request context, and Coze callback handling.
- The annotation slice now uses a backend-owned Coze gateway for `POST /api/v1/annotation-tasks/{task_id}/ai-generate`; the frontend still never calls Coze directly.
- The risk slice now uses a backend-owned Coze gateway for `POST /api/v1/projects/{project_id}/risk-generate`; the frontend still never calls Coze directly.
- The release hardening package now includes controller and web health checks, Docker images, compose orchestration, smoke and rollback helpers, and observability guidance.
- Release 1 remains `no-go` because the PM boundary is still incomplete even though the verified slices and release hardening package are real.
- Database foundation exists in `db` with an Alembic baseline and PostgreSQL-first schema objects.
- Frontend business data still comes from mock adapters, so live FE to BE integration is not complete.
- QA has verified the current milestone slices, but the repository is not a product release and Release 1 is still not open.

## Repository Structure

- `apps/web` - Next.js 16 + React 19 frontend foundation, route shell, mock-backed workspace views, and UI tests.
- `services/controller` - FastAPI control plane foundation, SQLAlchemy models, core services, and API routes.
- `db` - Alembic migration environment and the initial PostgreSQL schema migration.
- `docs` - Product, architecture, QA, handoff, deployment, and release documentation.
- `AGENTS.md` and `.codex` - repository workflow, ownership, and orchestration rules.

## Implemented Foundation Slices

- Frontend shell and route foundation for dashboard, inbox, projects, project detail, annotation queue, annotation task detail, risk, workflow runs, and workflow run detail.
- Frontend design-token-backed styling with shared layout primitives and route-level composition.
- Backend endpoints for `GET /api/v1/me`, `GET|POST /api/v1/projects`, `GET|PATCH /api/v1/projects/{project_id}`, `GET /api/v1/workflow-runs`, `GET /api/v1/workflow-runs/{run_id}`, and `POST /api/v1/integrations/coze/callback`.
- Backend-owned annotation Coze dispatch through `POST /api/v1/annotation-tasks/{task_id}/ai-generate`, with persisted `workflow_runs`, `coze_runs`, `ai_results`, and audit records.
- Backend request context, shared response envelopes, and contract-specific error handling.
- PostgreSQL-first SQLAlchemy and Alembic foundation covering identity, project, dataset, source asset, annotation, risk, workflow, AI result, and audit tables.
- Verified local test and build coverage for the foundation slice.

## Stack

- Frontend: Next.js 16, React 19, TypeScript, Vitest, ESLint.
- Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, psycopg.
- Database: PostgreSQL as the source of truth.
- AI execution engine: Coze API, with the backend owning persistence and state transitions.

## Key Documents

- `docs/prd.md` - product requirements and acceptance criteria.
- `docs/architecture.md` - system design, module boundaries, and platform decisions.
- `docs/schema.md` - canonical data model.
- `docs/api-contract.md` - frozen API contract for frontend and backend work.
- `docs/qa-report.md` - verified foundation milestone and remaining risk.
- `docs/deployment.md` - current local/runtime prerequisites and backend assumptions.
- `docs/handoff.md` - milestone summary, open gaps, and recommended next steps.
- `docs/release.md` - release-facing summary for the current milestone.
- `docs/release-gate.md` - authoritative release gate.
- `docs/observability.md` - minimal release observability guide.

## Collaboration Model

- Parent thread acts as the `Orchestrator`.
- `pm`, `architect`, `designer`, `fe`, `be`, `qa`, and `general` are project-scoped roles.
- Only the `Orchestrator` writes `docs/blackboard/state.yaml`.
- `fe` and `be` remain blocked from contract drift and must escalate changes through the `Orchestrator`.

## Useful Local Commands

- Frontend: `cd apps/web && npm run dev`
- Frontend checks: `cd apps/web && npm run test` and `cd apps/web && npm run build`
- Backend: `cd services/controller && uvicorn app.main:app --reload`
- Backend checks: `cd services/controller && python -m pytest tests`

## Controller Environment

The controller reads runtime config from environment variables. See [`.env.example`](C:/Users/JoeWang/Desktop/MutiData-Nexus/services/controller/.env.example) for a local template.

- `DATABASE_URL`: PostgreSQL connection string for the source-of-truth database
- `COZE_CALLBACK_SECRET`: callback signature secret for `POST /api/v1/integrations/coze/callback`
- `COZE_ANNOTATION_RUN_URL`: annotation workflow run URL, currently `https://zvqrc5d642.coze.site/run`
- `COZE_API_TOKEN`: Bearer token used by the backend-owned Coze gateway
- `COZE_RISK_RUN_URL`: project risk workflow run URL, currently `https://d784kg4tzc.coze.site/run`
- `COZE_RISK_API_TOKEN`: Bearer token used by the backend-owned risk gateway
- `COZE_TIMEOUT_SECONDS`: timeout for outbound annotation workflow requests
- `CONTROLLER_API_URL`: base URL used by the web release readiness route to check controller health
