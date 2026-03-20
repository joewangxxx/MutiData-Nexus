# MutiData-Nexus Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP of MutiData-Nexus as one unified platform for multimodal annotation and project risk monitoring.

**Architecture:** The implementation should follow the approved design package: one role-aware frontend dashboard, one backend controller service, PostgreSQL as the source of truth, and Coze as the external AI execution engine. FE and BE may work in parallel only after the API contract is reviewed, approved, and frozen by the Orchestrator.

**Tech Stack:** Frontend stack TBD, backend stack TBD, PostgreSQL, Coze API, repo structure to be finalized in Phase 0.

---

## Proposed Repo Structure

- `apps/web/` for the dashboard
- `services/controller/` for the backend controller
- `packages/contracts/` for shared API schemas and generated types
- `db/` for migrations, seed data, and database docs
- `docs/decisions/` for stack and deployment ADRs

## Phase 0: Finalize Technical Choices and Freeze Design

**Outcome:** Implementation can begin without ambiguity or silent contract drift.

- [ ] Review `docs/prd.md`, `docs/mvp-scope.md`, `docs/architecture.md`, `docs/schema.md`, `docs/api-contract.md`, `docs/coze-integration.md`, `docs/workflow-run-tracking.md`, and `docs/information-architecture.md`.
- [ ] Choose the frontend stack and record it in `docs/decisions/frontend-stack.md`.
- [ ] Choose the backend stack and record it in `docs/decisions/backend-stack.md`.
- [ ] Confirm the API contract version to implement and freeze `docs/api-contract.md` for the first build.
- [ ] Confirm the first-pass database migration plan from `docs/schema.md`.
- [ ] Update `docs/blackboard/state.yaml` only after Orchestrator approval; do not open FE/BE work before this review completes.

## Phase 1: Initialize the Monorepo Skeleton

**Outcome:** The repository has stable homes for frontend, backend, contracts, and database work.

- [ ] Create `apps/web/`, `services/controller/`, `packages/contracts/`, `db/migrations/`, and `docs/decisions/`.
- [ ] Add workspace-level tooling and package management files once the stack is chosen.
- [ ] Add `README.md` updates that explain the selected runtime and local development shape.
- [ ] Add CI placeholders for lint, test, and build commands without wiring feature logic yet.

## Phase 2: Identity, Organizations, Projects, and Audit Baseline

**Outcome:** The source-of-truth platform model exists before workflow features are layered on top.

- [ ] Implement the PostgreSQL tables for organizations, users, memberships, projects, and audit events from `docs/schema.md`.
- [ ] Implement backend models and service methods for organization membership, project listing, project creation, and project detail retrieval.
- [ ] Implement the API endpoints for `GET /me`, `GET /projects`, `POST /projects`, `GET /projects/{project_id}`, and `PATCH /projects/{project_id}` from `docs/api-contract.md`.
- [ ] Add audit emission for every project or membership mutation.
- [ ] Add backend tests covering authorization, membership filtering, and audit insertion.

## Phase 3: Annotation Workflow MVP

**Outcome:** Annotators can receive, claim, submit, and revise multimodal tasks inside the platform.

- [ ] Implement the PostgreSQL tables for datasets, source assets, annotation tasks, and annotation revisions.
- [ ] Implement backend task queue queries, task claim logic, submission handling, and revision history.
- [ ] Implement the annotation API endpoints defined in `docs/api-contract.md`.
- [ ] Add role-aware authorization rules from `docs/roles-and-permissions.md`.
- [ ] Build the frontend annotation queue, task detail, and submission flow according to `docs/information-architecture.md`.
- [ ] Add integration tests for task status transitions, submission review, and conflict handling.

## Phase 4: Risk Monitoring MVP

**Outcome:** Project managers can see project health, inspect risk signals, and act on alerts in the same product.

- [ ] Implement the PostgreSQL tables for risk signals and risk alerts.
- [ ] Implement backend ingestion, triage, update, and acknowledge logic for risk entities.
- [ ] Implement the risk-monitoring API endpoints defined in `docs/api-contract.md`.
- [ ] Build frontend project-manager views for risk monitor, alert detail, and acknowledgement flows based on `docs/information-architecture.md`.
- [ ] Add audit events for alert creation, acknowledgement, and resolution.
- [ ] Add tests for signal ingestion, alert lifecycle changes, and permission boundaries.

## Phase 5: Workflow Run Tracking and Coze Integration

**Outcome:** AI-assisted execution is durable, traceable, and safe to retry.

- [ ] Implement the PostgreSQL tables for workflow runs, workflow steps, and Coze runs.
- [ ] Implement the backend state machine described in `docs/workflow-run-tracking.md`.
- [ ] Implement Coze request preparation, dispatch, reconciliation, validation, and retry behavior from `docs/coze-integration.md`.
- [ ] Expose the workflow-run endpoints from `docs/api-contract.md`.
- [ ] Add operator-visible status and trace data to the frontend where required by the information architecture.
- [ ] Add test coverage for idempotency, retry safety, validation failures, and lost-callback recovery.

## Phase 6: Unified Dashboard Composition

**Outcome:** Annotators and project managers can work from one shared shell instead of two disconnected products.

- [ ] Implement the global shell, project switcher, inbox, and search entry points described in `docs/information-architecture.md`.
- [ ] Implement role-aware dashboard modules for annotators and project managers.
- [ ] Implement the project dashboard aggregate endpoint or equivalent data composition path approved in `docs/api-contract.md`.
- [ ] Ensure cross-links exist between tasks, alerts, workflow runs, and audit history.
- [ ] Add frontend tests for navigation, role-aware visibility, and dashboard data loading states.

## Phase 7: Hardening, QA, and Release Readiness

**Outcome:** The MVP is stable enough for FE/BE handoff to QA and release coordination.

- [ ] Verify every acceptance criterion in `docs/prd.md` and every MVP boundary in `docs/mvp-scope.md`.
- [ ] Run end-to-end checks for annotation flows, risk-monitoring flows, workflow-run visibility, and audit traceability.
- [ ] Hand the implementation to `qa` for validation into `docs/qa-report.md`.
- [ ] Fix blocking defects and re-run the agreed verification suite.
- [ ] Hand final validated artifacts to `general` for `README.md`, `docs/deployment.md`, `docs/handoff.md`, and `docs/release.md`.

## Implementation Gates

- FE and BE do not start until the Orchestrator marks the API contract approved.
- FE and BE do not change the API contract directly.
- QA starts only after implementation artifacts exist.
- Release docs start only after QA has a recommendation.

## Major Open Items Before Phase 1

- Frontend framework selection
- Backend framework selection
- Authentication provider and session strategy
- Coze completion mode confirmation: webhook, polling, or hybrid
- Retention policy for prompts, outputs, and payload snapshots
