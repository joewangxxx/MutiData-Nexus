# MutiData-Nexus Agent Workflow

This repository uses a parent-thread orchestration model to scaffold and build a unified AI data operations platform that combines:

1. A multimodal data annotation workflow
2. A project risk monitoring workflow

The platform target is a coordinated system with a frontend dashboard, a backend control service, PostgreSQL as the source of truth, and Coze API integration as the AI execution engine. This file defines how project-scoped agents collaborate before product features are implemented.

## Orchestrator

- The parent thread is the `Orchestrator`.
- Only the `Orchestrator` may write `docs/blackboard/state.yaml`.
- All project agents treat the blackboard as read-only context.
- The `Orchestrator` is responsible for opening and closing workflow gates, assigning next owners, and recording approved status changes.

## Role Ownership

| Role | Primary Ownership | Required Deliverables | Hard Limits |
|------|-------------------|-----------------------|-------------|
| `pm` | Product requirements and acceptance criteria | `docs/prd.md` | Must not define architecture, schema, or API details as final |
| `architect` | System design, schema, API contract, Coze integration design | `docs/architecture.md`, `docs/schema.md`, `docs/api-contract.md` | Must not bypass PM acceptance criteria |
| `designer` | Dashboard UX direction and design token system | `docs/design-tokens.md` | Must not approve API or database changes |
| `fe` | Frontend implementation after contract approval | Future frontend code and tests | Blocked until API contract exists; cannot edit API contract |
| `be` | Backend implementation after contract approval | Future backend code and tests | Blocked until API contract exists; cannot edit API contract |
| `qa` | Validation after implementation | `docs/qa-report.md` | Runs after implementation only |
| `general` | Cross-project docs and release handoff | `README.md`, `docs/deployment.md`, `docs/handoff.md`, `docs/release.md` | Must not redefine product scope or technical contracts |

## Workflow Gates

1. `pm` defines the PRD and acceptance criteria in `docs/prd.md`.
2. `architect` defines system architecture, API contract, database schema, and Coze integration design in the architecture docs.
3. `designer` defines dashboard design tokens in `docs/design-tokens.md`.
4. `fe` and `be` remain blocked until `docs/api-contract.md` is approved and the blackboard marks `api_contract_ready: true`.
5. `fe` and `be` may work in parallel only after the API contract gate opens.
6. `fe` and `be` cannot silently change the API contract. If implementation pressure reveals a contract issue, they must escalate to the `Orchestrator`, which routes the change back through `architect` and, when scope changes, `pm`.
7. `qa` validates after implementation artifacts exist and records findings in `docs/qa-report.md`.
8. `general` produces repository-facing documentation after the delivery shape is stable.

## Retry Policy

- `fe` max retries: `3`
- `be` max retries: `3`
- On the third failed attempt, the owning agent must stop, summarize evidence, propose the next-best alternative, and escalate to the `Orchestrator`.

## Required Read Order

Every agent must read these items before working:

1. `AGENTS.md`
2. `.codex/config.toml`
3. Its own `.codex/agents/<role>.toml`
4. `docs/blackboard/state.yaml`
5. The docs it owns or depends on

## Handoff Protocol

Each handoff must include:

- Files read and files changed
- Decisions made
- Assumptions or open questions
- Evidence for gate changes
- Requested next owner

The `Orchestrator` updates the blackboard after reviewing the handoff. Child agents do not update workflow state directly.

## Current Repository Intent

- This repository started as a workflow scaffold and design package.
- The approved implementation stack is `Next.js + React` for the frontend, `FastAPI` for the backend control plane, `PostgreSQL` for persistence, and `SQLAlchemy 2.0 + Alembic` for ORM and migrations.
- Product implementation may begin only after the `Orchestrator` opens the blackboard gates for `api_contract_ready`, `schema_ready`, and `design_tokens_ready`.
- The immediate implementation goal is to build the repository skeleton and MVP platform modules without silent contract drift.
