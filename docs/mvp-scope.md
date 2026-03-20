# MVP Scope

Status: `release_boundary_reviewed`  
Owner: `pm`  
Last Updated: `2026-03-20`

## Purpose

This document is the product-side boundary for Release 1. It is intentionally narrow: it says what must be true to open Release 1, what can slip, what is already verified, and what still blocks release. It does not define architecture, schema, or API details.

## Release 1 Decision Rule

Release 1 may open only when every must-have gate below maps to at least one verified slice and no blocking item remains unresolved. Anything not listed as verified complete must be treated as unfinished until it is explicitly proven by a verified slice.

## Release 1 Must-Have Gates

| Must-have gate | Verified slices that satisfy it | Status |
|---|---|---|
| Project creation and project member management within project scope. | `Project foundation behavior`, `Project Member Management Completion` | Satisfied |
| Project-scoped datasets and multimodal data items for audio, image, and video. | `Project Dataset & Asset Catalog E2E`, `Project Dataset & Multimodal Item Management E2E` | Satisfied |
| Annotation task assignment, review, revision, completion, and status tracking. | `Annotation Task Management Completion`, `AI-Assisted Annotation Submission`, `Annotation Review Flow`, `Multimodal Annotation Coverage Completion` | Satisfied |
| Backend-triggered AI execution for annotation and risk workflows with persisted workflow records. | `Annotation Coze Integration`, `Risk Workflow Backend Integration`, `Workflow Runs Live List` | Satisfied |
| Project risk monitoring with live snapshots, events, strategy suggestions, and decision actions. | `Risk Signal Capture Completion`, `Project Risk Monitoring E2E`, `Unified Risk Workflow Output Analysis + Strategy Suggestions`, `Risk Strategy Approve / Reject`, `Risk Alert Operations Completion` | Satisfied |
| Workflow visibility through a live workflow-runs list and workflow detail drilldown. | `Workflow Runs Live List`, annotation drilldown in `AI-Assisted Annotation Submission`, risk drilldown in `Project Risk Monitoring E2E` | Satisfied |
| Backend-owned business state with auditable records for important actions and workflow outcomes. | Project, member, dataset, annotation, risk, and workflow slices listed above | Satisfied |
| Role-appropriate frontend views for annotators and project managers. | Project pages, annotation workbench, risk dashboard, workflow-runs list, member-management panel, catalog management surface | Satisfied |

## Current Verified Completes

Verified slices only. These items are complete enough to count toward Release 1 boundary judgment:

- `Project foundation behavior` is verified: project creation, project detail, project updates, member creation, and audit writes for project changes.
- `Project Member Management Completion` is verified: live member list, role/status updates, soft delete semantics, last-active-project-manager protection, and audit persistence.
- `Project Dataset & Asset Catalog E2E` is verified: live datasets and source-assets catalog APIs plus a project-scoped catalog page.
- `Project Dataset & Multimodal Item Management E2E` is verified: backend-owned dataset and source-asset metadata create/update APIs, optional dataset linkage, audit-backed idempotency, and a live catalog management surface.
- `Annotation Task Management Completion` is verified: backend-owned create, claim, and patch APIs plus live queue and task controls.
- `AI-Assisted Annotation Submission` is verified: queue, task detail, AI generate action, callback persistence, revision submission, submitted-state transition, workflow detail drilldown, source asset read path, and audit writes.
- `Annotation Review Flow` is verified: approve, reject, and revise actions on submitted revisions; task and workflow status transitions; closed-task resubmission guardrails; and audit persistence.
- `Multimodal Annotation Coverage Completion` is verified: a unified workbench for image, audio, and video previews plus queue, task detail, ai-generate, submission, review, and workflow drilldown coverage.
- `Annotation Coze Integration` is verified: backend-owned gateway, runtime-based Coze configuration, synchronous AI result persistence, callback reuse, and contract-safe error mapping.
- `Risk Signal Capture Completion` is verified: one shared project risk form with signal-only and save-and-analyze entry points, backend idempotency handling, and correct workflow dispatch behavior.
- `Project Risk Monitoring E2E` is verified: live project risk posture, risk alert detail, workflow detail linkage, risk signal persistence, risk alert persistence, and risk strategy persistence.
- `Risk Workflow Backend Integration` is verified: backend-triggered project-scoped dispatch, accepted-then-callback completion support, runtime-based Coze configuration, and contract-safe error mapping.
- `Unified Risk Workflow Output Analysis + Strategy Suggestions` is verified: risk analysis and strategy suggestions persist through one shared backend completion path.
- `Risk Strategy Approve / Reject` is verified: proposed-only decision actions, idempotent replay behavior, conflict handling, and audit persistence.
- `Risk Alert Operations Completion` is verified: `PATCH /api/v1/risk-alerts/{alert_id}` and `POST /api/v1/risk-alerts/{alert_id}/acknowledge` with idempotency propagation and audit persistence.
- `Workflow Runs Live List` is verified: live-backed list, summary metrics, and drilldown links.
- `Release Hardening Track` is verified: controller and web health checks, release Dockerfiles, compose release stack, smoke and rollback helpers, and aligned release-facing docs.

## Current Blockers For Release 1

No blocker remains inside the named Release 1 must-have gates above. The remaining blocker is any attempt to treat unverified product surfaces outside the verified slice inventory as Release 1 evidence.

Not a blocker:

- The `workflow-runs` live list is already verified and must not be listed as a Release 1 blocker.
- Project member management is already verified and must not be listed as a Release 1 blocker.
- Dataset management and multimodal item management are already verified and must not be listed as a Release 1 blocker.
- Multimodal annotation coverage is already verified and must not be listed as a Release 1 blocker.
- Risk signal capture is already verified and must not be listed as a Release 1 blocker.
- Risk alert operations and risk strategy approve/reject are already verified and must not be listed as Release 1 blockers.
- Release hardening is already verified and must not be listed as a Release 1 blocker.

## Release 1 Allowed Deferrals

These are intentionally out of Release 1 and may move to later phases:

- Broader organization hierarchy beyond project membership.
- Advanced analytics, executive reporting, and predictive scoring.
- Additional workflow families beyond annotation and risk monitoring.
- More configurable approval policies and workflow orchestration options.
- Large-scale enterprise governance features that are not needed for the pilot.
- Mobile-native and offline-first experiences.
- Deep external system integration beyond the core product boundary.
- Warehouse-style reporting or cross-project portfolio analysis.

## In Scope For Release 1

- Frontend views for annotator workbench, PM dashboard, risk dashboard, and workflow status.
- Project creation and project member management.
- Project-scoped datasets and multimodal data items.
- Annotation tasks for audio, image, and video content.
- Backend-triggered Coze annotation workflows.
- Persisted workflow execution records.
- Project risk monitoring.
- Backend-triggered Coze risk workflows.
- Persisted risk snapshots, risk events, and strategy suggestions.
- Human review and approval boundaries for workflows that require them.
- Backend-owned business state with a single authoritative record for product data.

## Release 1 Non-Goals

- Custom model training or model fine-tuning.
- Workflow automation that removes required human approval.
- Broad enterprise admin tooling beyond the project and platform roles defined in the PM docs.
- Advanced analytics warehouse, executive reporting suite, or predictive risk engine.
- Mobile-native applications.
- Offline-first usage.
- Multi-product marketplace behavior.
- Deep external system integration beyond the core product boundary.

## Release 1 Summary

Release 1 is not release-ready until the verified-complete items above remain the only evidence the team is using to claim the boundary. At this point, the product has verified slices for project foundations, member management, dataset and catalog management, annotation task management, annotation submission and review, multimodal annotation coverage, risk signal capture, risk monitoring, risk strategy decisions, workflow execution visibility, and release hardening. Any claim outside those slices remains unproven and must stay deferred.

## Later-Phase Ideas

- Deeper reporting and trend analysis.
- Expanded operational dashboards.
- Additional workflow templates for other data operations use cases.
- Stronger cross-project portfolio views.
- More configurable approval policies.
