# Backend Stack Decision

Status: `approved`
Owner: `orchestrator`
Last Updated: `2026-03-18`

## Decision

Use `FastAPI` as the backend control plane with `SQLAlchemy 2.0` as the ORM, `Alembic` for schema migrations, and `PostgreSQL` as the source of truth.

## Selected Shape

- API framework: `FastAPI`
- Schema and validation: `Pydantic v2`
- ORM: `SQLAlchemy 2.0`
- Migrations: `Alembic`
- Database: `PostgreSQL`
- Test baseline: `pytest`
- Integration client: dedicated `Coze` service layer owned by the backend

## Why This Stack

- It matches the repository constraint set by the project brief.
- It supports explicit REST contracts, durable workflow execution records, and audit-heavy business state.
- It keeps Coze behind a dedicated integration boundary so AI execution does not become a source of truth.
- It gives BE a straightforward path to model-first database work and contract-driven endpoint delivery.

## Architectural Direction

- Build the backend as a modular monolith first.
- Separate API routers, service logic, persistence models, and Coze integration code.
- Persist workflow runs before any Coze dispatch.
- Persist every AI output as raw and normalized payloads before downstream state changes are applied.

## Notes for BE

- Treat `docs/api-contract.md` as read-only.
- Use `docs/schema.md`, `docs/coze-integration.md`, and `docs/workflow-run-tracking.md` as the implementation baseline.
- Preserve a dedicated place for retry, reconciliation, and callback handling logic.
