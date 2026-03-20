# RBAC Proposal

Status: `review-ready`
Owner: `architect`
Last Updated: `2026-03-18`

## Purpose

This document defines the technical role-based access control model for the FastAPI backend and Next.js frontend. It translates the product personas into enforceable backend rules.

## Design Principles

- Authorization is enforced in FastAPI, not in the frontend.
- PostgreSQL stores the durable role and membership state.
- Organization scope and project scope are evaluated separately.
- Approval actions are explicit permissions.
- Audit access is broader than mutation access for operational roles.
- Hidden UI is not security; the backend remains authoritative.

## Role Model

### Organization Roles

- `admin`
- `operator`
- `project_manager`
- `annotator`
- `reviewer`
- `system`

### Project Roles

- `project_manager`
- `annotator`
- `reviewer`
- `observer`

Users may have one organization role and zero or more project memberships.

## Authorization Inputs

FastAPI evaluates access using:

- authenticated `user_id`
- `organization_id`
- organization role
- project membership role
- target resource type
- requested action
- resource ownership or assignment where relevant

## Permission Model

Permissions are evaluated as `<resource>:<action>`.

### Permission Catalog

- `project:read`
- `project:create`
- `project:update`
- `project:archive`
- `dataset:read`
- `source_asset:read`
- `source_asset:access`
- `annotation_task:read`
- `annotation_task:create`
- `annotation_task:claim`
- `annotation_task:submit`
- `annotation_task:update`
- `annotation_review:approve`
- `annotation_review:reject`
- `risk_signal:read`
- `risk_signal:create`
- `risk_alert:read`
- `risk_alert:update`
- `risk_alert:acknowledge`
- `risk_strategy:generate`
- `risk_strategy:approve`
- `risk_strategy:reject`
- `workflow_run:read`
- `workflow_run:retry`
- `workflow_run:cancel`
- `audit_event:read`
- `membership:manage`
- `settings:manage`

## Resource Access Matrix

| Resource Action | Annotator | Reviewer | Project Manager | Operator | Admin | Observer |
|----------------|-----------|----------|-----------------|----------|-------|----------|
| `project:read` | assigned projects | assigned projects | yes | yes | yes | read-only |
| `project:create` | no | no | yes | yes | yes | no |
| `project:update` | no | no | yes | limited | yes | no |
| `project:archive` | no | no | yes | limited | yes | no |
| `dataset:read` | assigned projects | assigned projects | yes | yes | yes | read-only |
| `source_asset:read` | assigned projects | assigned projects | yes | yes | yes | read-only |
| `source_asset:access` | assigned assets | project assets | yes | yes | yes | no |
| `annotation_task:read` | own or assigned | project-level | yes | yes | yes | read-only |
| `annotation_task:create` | no | no | yes | yes | yes | no |
| `annotation_task:claim` | yes | no | yes | no | yes | no |
| `annotation_task:submit` | yes | no | no | no | yes | no |
| `annotation_task:update` | own tasks | no | yes | limited | yes | no |
| `annotation_review:approve` | no | yes | yes | no | yes | no |
| `annotation_review:reject` | no | yes | yes | no | yes | no |
| `risk_signal:read` | project-level | project-level | yes | yes | yes | read-only |
| `risk_signal:create` | limited | limited | yes | yes | yes | no |
| `risk_alert:read` | project-level | project-level | yes | yes | yes | read-only |
| `risk_alert:update` | no | no | yes | yes | yes | no |
| `risk_alert:acknowledge` | no | no | yes | yes | yes | no |
| `risk_strategy:generate` | no | no | yes | yes | yes | no |
| `risk_strategy:approve` | no | no | yes | no | yes | no |
| `risk_strategy:reject` | no | no | yes | no | yes | no |
| `workflow_run:read` | own/project-limited | project-limited | project-wide | org-wide | org-wide | read-only |
| `workflow_run:retry` | no | no | yes | yes | yes | no |
| `workflow_run:cancel` | no | no | yes | yes | yes | no |
| `audit_event:read` | own/project-limited | project-limited | project-wide | org-wide | org-wide | project-limited |
| `membership:manage` | no | no | project-scoped only | org-scoped only | yes | no |
| `settings:manage` | no | no | project-scoped only | org-scoped only | yes | no |

## Role Grants

### Annotator

- Read assigned projects, assets, tasks, own workflow runs, and own AI results.
- Claim tasks assigned to their scope.
- Submit annotation revisions.
- Cannot approve reviews or manage risk strategy decisions.

### Reviewer

- Read project-scoped tasks, revisions, alerts, and workflow history.
- Approve or reject annotation reviews.
- Cannot submit annotation work as if they were the task owner.

### Project Manager

- Read and update project-scoped data.
- Create and manage tasks, signals, alerts, and strategies.
- Approve or reject annotation reviews and risk strategies.
- Retry or cancel workflow runs when business policy allows.
- Manage project memberships and settings within their scope.

### Operator

- Read org-wide operational data.
- Create or ingest risk signals.
- Update or acknowledge alerts.
- Retry or cancel workflow runs.
- Manage operational settings and access recovery tasks.

### Admin

- Full access across the organization.
- Can manage memberships, settings, and all workflow actions.

### System

- Reserved for backend service credentials and automation jobs.
- Can perform integration and reconciliation actions that human users cannot.
- Every system action must still emit audit history.

### Observer

- Read-only access to project-scoped data.
- No mutation or approval permissions.

## Enforcement Pattern in FastAPI

1. Router validates authentication.
2. Dependency resolves organization role and project membership.
3. Policy layer checks `resource:action`.
4. Service layer executes only after authorization passes.
5. Audit event records granted or denied sensitive actions when required.

## Frontend Implications for Next.js

- The frontend uses role-aware navigation and hides actions the user cannot perform.
- Permission summary is returned from `GET /me` so Next.js can render the correct experience.
- UI state must never be used as the source of truth for access control.

## Data Model Mapping

Current schema support:

- `organization_memberships` for org-scoped role
- `project_memberships` for project-scoped role
- `users`, `projects`, and assignment fields on tasks and alerts

Recommended extension:

- `permission_overrides` table later if custom per-project policy becomes necessary

## Approval Boundaries

- Annotation approval is separate from annotation submission.
- Risk strategy approval is separate from AI generation.
- Workflow retry and cancel are operationally sensitive actions.
- Permission changes are operator or admin actions only.

## MVP vs Later

### MVP

- Fixed role matrix.
- Organization-level role plus project-level membership.
- Policy checks hard-coded in backend modules.

### Later

- Configurable policy rules.
- Delegated approvals.
- Conditional approvals by severity or workflow type.
- Temporary access grants and richer audit reporting.
