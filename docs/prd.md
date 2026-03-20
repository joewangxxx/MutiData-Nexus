# Product Requirements Document

Status: `draft`  
Owner: `pm`  
Last Updated: `2026-03-18`

## Product Summary

MutiData-Nexus is a unified AI data operations platform that combines multimodal annotation and project risk monitoring in one product. The backend owns all business state, PostgreSQL is the system of record, and Coze is the AI execution engine only. The frontend exposes role-specific work surfaces for annotators and project managers so teams can create work, execute workflows, review AI output, and monitor risk without losing traceability.

## Problem Statement

Annotation work, project membership, and risk monitoring are often tracked in separate tools. That creates duplicate updates, inconsistent status, weak auditability, and slow handoffs between operational work and project oversight. Teams need one product where project structure, datasets, work execution, and risk visibility stay aligned.

## Product Goals

- Provide a single product for project setup, member management, annotation work, and risk monitoring.
- Keep the canonical state for projects, members, datasets, tasks, workflow runs, and risk records in the backend.
- Support backend-triggered AI workflows for annotation and risk monitoring while preserving human review where required.
- Give annotators and project managers role-appropriate views of their work and the current workflow status.
- Preserve an auditable record of important actions, approvals, and AI-assisted workflow outcomes.

## Target Users

- Annotators: complete assigned audio, image, and video tasks and submit work for review.
- Project managers or project owners: create projects, manage members, assign work, and oversee delivery and risk.
- Reviewers or approvers: validate submitted work and approve task-level outcomes when human approval is required.
- Platform operators: manage platform access, operational readiness, and governance controls outside product business state.

## Product Principles

- Backend-owned business state is authoritative; the frontend is the interaction surface.
- Coze produces AI-assisted outputs, but it never becomes the source of truth for product state.
- Human approval boundaries must be visible and consistent across annotation and risk workflows.
- Product state must be understandable to non-technical users from the dashboard views alone.
- Auditability matters for both completed work and workflow execution history.

## Core Experience

### Project Administration

The platform must let project managers create projects, manage project members, and keep project ownership clear.

### Dataset and Multimodal Data Management

The platform must let project teams organize datasets and multimodal data items as first-class product objects. Data items must support audio, image, and video content, and each item must remain linked to its owning project and dataset.

### Annotation Work

The platform must let annotators work from an annotation workbench, see assigned tasks, open the underlying data item, review AI suggestions, apply labels or notes, and submit completed work for review.

### Risk Monitoring

The platform must let project managers monitor project risk from a risk dashboard, review current risk snapshots, inspect risk events, evaluate strategy suggestions, and track follow-up ownership and resolution.

### Workflow Status

The platform must expose workflow status for backend-triggered annotation and risk workflows so users can see what is running, what has completed, and what needs attention.

### Shared Platform Behavior

The platform must present role-specific frontend views, record who changed what and when, and keep workflow status aligned with backend-owned business state.

## Functional Requirements

### Project and Member Management

- The product must support project creation and project ownership assignment.
- The product must support adding, removing, and updating project members within the project boundary.
- The product must allow member roles to be visible at the project level so users know who can act on each project.

### Dataset and Data Item Management

- The product must support datasets as project-scoped containers for multimodal data items.
- The product must support audio, image, and video data items.
- The product must preserve the relationship between a project, its datasets, and its data items.

### Annotation Tasks

- The product must support annotation tasks for audio, image, and video work.
- The product must support task assignment, task review, task completion, and task status tracking.
- The product must allow AI-assisted suggestions to be reviewed before they are accepted into final task outcomes when review is required.

### AI Workflow Execution

- The product must support backend-triggered Coze annotation workflows.
- The product must support backend-triggered Coze risk workflows.
- The product must treat Coze as an execution engine that returns workflow outputs, not as a source of business state.

### Workflow Records

- The product must persist workflow execution records for annotation and risk workflows.
- Workflow records must capture enough information for users to understand what ran, when it ran, and what outcome was produced.
- Workflow records must remain available even after the underlying work item or risk item is closed.

### Risk Monitoring

- The product must support project risk monitoring as a first-class workflow.
- The product must persist risk snapshots, risk events, and strategy suggestions.
- The product must allow project managers to review risk state and track which actions were taken in response.

### Source of Truth and State Ownership

- The product must maintain one authoritative record for projects, members, datasets, data items, tasks, workflow runs, risk snapshots, risk events, and strategy suggestions.
- The product must keep backend state and frontend views consistent.
- The product must ensure Coze output is only finalized when the backend persists the result into business state.

### Frontend Views

- The product must provide an annotator workbench view.
- The product must provide a PM dashboard view.
- The product must provide a risk dashboard view.
- The product must provide a workflow status view.

### Governance

- The product must enforce role-based access and approval boundaries.
- The product must make approval ownership explicit for project-level actions, task-level actions, and operational access actions.
- The product must prevent silent changes to business state outside the backend-controlled workflow path.

## Product Constraints

- The frontend dashboard is the user-facing surface for daily work.
- The backend control service owns business state and workflow state transitions.
- PostgreSQL is the source of truth for product records.
- Coze API is the AI execution engine only.
- Technical design, schemas, API shapes, and implementation details are owned by architecture documentation.

## Success Metrics

- Project managers can create projects and manage members without leaving the product.
- Annotators can complete assigned multimodal tasks from one workbench.
- Risk monitoring data is visible and traceable in the same product as annotation work.
- AI assistance reduces manual effort without removing the required approval boundary.
- The recorded workflow history matches the visible state in the dashboard.

## Acceptance Criteria

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| AC-001 | Unified product scope | The PRD defines one product that includes project creation, member management, multimodal annotation, workflow status, and risk monitoring. |
| AC-002 | User roles | The PRD names annotators, project managers or project owners, reviewers or approvers, and platform operators with distinct responsibilities. |
| AC-003 | Approval boundaries | The PRD states which role approves task outcomes, project-level changes, and operational access changes. |
| AC-004 | Dataset coverage | The PRD treats datasets and multimodal data items as first-class product objects linked to a project. |
| AC-005 | Annotation coverage | The PRD requires annotation tasks for audio, image, and video content, including assignment, review, completion, and status tracking. |
| AC-006 | Annotation workflow execution | The PRD requires backend-triggered Coze annotation workflows and persisted execution records. |
| AC-007 | Risk workflow execution | The PRD requires backend-triggered Coze risk workflows and persisted risk snapshots, risk events, and strategy suggestions. |
| AC-008 | Frontend surfaces | The PRD requires annotator workbench, PM dashboard, risk dashboard, and workflow status views. |
| AC-009 | State ownership | The PRD states that the backend owns all business state and that Coze is an AI engine only. |
| AC-010 | Traceability | The PRD requires auditable records of important actions, approvals, and workflow outcomes. |
| AC-011 | MVP handoff readiness | The PRD and companion scope docs are specific enough for architecture and engineering to derive schema and API decisions without additional product decisions. |

## Deferred Questions

The following topics are intentionally deferred to later product or architecture decisions and do not block PM handoff:

- Whether later releases should add broader organization hierarchy beyond project-level membership.
- Whether later releases should add advanced analytics or cross-project reporting beyond the MVP dashboards.
- Whether later releases should add additional workflow families beyond annotation and risk monitoring.
