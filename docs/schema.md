# Schema

Status: `review-ready`
Owner: `architect`
Last Updated: `2026-03-19`

## Purpose

This document defines the logical PostgreSQL schema for the FastAPI control plane. PostgreSQL is the source of truth for business state, workflow state, audit history, and persisted AI output.

## ORM Mapping Guidance

- Use one SQLAlchemy 2.0 model per table.
- Keep table and model names aligned so migrations stay reviewable.
- Use Alembic for every schema change.
- Prefer explicit relationships over implicit inference.
- Store large media binaries outside PostgreSQL; keep metadata and references in PostgreSQL.
- Use JSONB only where the payload is truly workflow-specific or modality-specific.
- All timestamps are `timestamptz` in UTC.

## Design Rules

- Every durable business object belongs to an organization and, when relevant, a project.
- Every workflow execution is stored before Coze is invoked.
- Every AI result is persisted twice conceptually: raw provider output and normalized platform output.
- History tables are append-only.
- Approved business-state transitions happen only after AI persistence succeeds.

## Core Enums

| Enum | Values |
|------|--------|
| `member_role` | `annotator`, `reviewer`, `project_manager`, `operator`, `admin`, `system` |
| `project_role` | `annotator`, `reviewer`, `project_manager`, `observer` |
| `organization_status` | `active`, `suspended`, `archived` |
| `user_status` | `invited`, `active`, `disabled`, `deleted` |
| `project_status` | `active`, `paused`, `archived` |
| `dataset_status` | `active`, `archived` |
| `asset_kind` | `image`, `audio`, `video` |
| `annotation_task_status` | `queued`, `claimed`, `in_progress`, `submitted`, `needs_review`, `approved`, `rejected`, `closed`, `canceled` |
| `annotation_review_decision` | `approve`, `reject`, `revise` |
| `risk_signal_status` | `open`, `triaged`, `suppressed`, `closed` |
| `risk_alert_status` | `open`, `investigating`, `mitigated`, `resolved`, `dismissed` |
| `strategy_status` | `proposed`, `approved`, `rejected`, `archived`, `applied` |
| `workflow_domain` | `annotation`, `risk_monitoring` |
| `workflow_run_status` | `draft`, `queued`, `validating`, `dispatching`, `running`, `waiting_for_human`, `succeeded`, `succeeded_with_warnings`, `failed`, `canceled`, `timed_out` |
| `workflow_step_status` | `queued`, `running`, `succeeded`, `failed`, `skipped`, `waiting` |
| `coze_run_status` | `prepared`, `submitted`, `accepted`, `running`, `succeeded`, `failed`, `retryable_failure`, `expired`, `canceled` |
| `ai_result_type` | `annotation_suggestion`, `annotation_summary`, `risk_analysis`, `risk_strategy`, `risk_summary`, `classification` |
| `ai_result_status` | `generated`, `accepted`, `rejected`, `superseded`, `applied` |
| `audit_action` | `create`, `update`, `submit`, `approve`, `reject`, `claim`, `dispatch`, `retry`, `cancel`, `close`, `acknowledge`, `archive`, `reconcile` |

For risk monitoring, `risk_analysis` and `risk_strategy` are sibling outputs of the same physical Coze workflow run. `risk_strategy` is not a separate dispatch boundary.

## Identity and Access

### `organizations`

- `id` UUID primary key
- `slug` text unique not null
- `name` text not null
- `status` `organization_status` not null
- `created_at`, `updated_at` timestamptz not null

### `users`

- `id` UUID primary key
- `email` text unique not null
- `display_name` text not null
- `status` `user_status` not null
- `created_at`, `updated_at` timestamptz not null

### `organization_memberships`

- `id` UUID primary key
- `organization_id` UUID not null references `organizations(id)`
- `user_id` UUID not null references `users(id)`
- `role` `member_role` not null
- `status` text not null
- `created_at`, `updated_at` timestamptz not null

Unique:

- `(organization_id, user_id)`

### `project_memberships`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `user_id` UUID not null references `users(id)`
- `project_role` `project_role` not null
- `status` text not null
- `created_at`, `updated_at` timestamptz not null

Unique:

- `(project_id, user_id)`

Purpose:

- owns project-scoped membership state for members who can participate in the project workspace
- `status` is intentionally text in the logical model so the API can support active/inactive lifecycle transitions without expanding the enum surface for MVP
- project member deactivation is a soft delete; the row remains for auditability and traceability
- a project membership is considered active only when `status == "active"`

## Project and Media Model

### `projects`

- `id` UUID primary key
- `organization_id` UUID not null references `organizations(id)`
- `code` text not null
- `name` text not null
- `description` text null
- `status` `project_status` not null
- `owner_user_id` UUID null references `users(id)`
- `settings` jsonb not null default `'{}'`
- `created_at`, `updated_at` timestamptz not null
- `archived_at` timestamptz null

Unique:

- `(organization_id, code)`

### `datasets`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `name` text not null
- `description` text null
- `source_kind` text not null
- `status` `dataset_status` not null
- `metadata` jsonb not null default `'{}'`
- `created_at`, `updated_at` timestamptz not null
- `archived_at` timestamptz null

### `source_assets`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `dataset_id` UUID null references `datasets(id)`
- `asset_kind` `asset_kind` not null
- `uri` text not null
- `storage_key` text null
- `mime_type` text null
- `checksum` text null
- `duration_ms` bigint null
- `width_px` integer null
- `height_px` integer null
- `frame_rate` numeric(8,3) null
- `transcript` text null
- `metadata` jsonb not null default `'{}'`
- `created_at`, `updated_at` timestamptz not null

Purpose:

- shared metadata layer for image, audio, and video assets
- supports media-specific annotation payloads without moving binary media into PostgreSQL
- `dataset_id` is nullable so a source asset can be project-scoped before dataset association

MVP write boundary:

- the release 1 catalog slice registers and updates metadata only
- upload, batch import, archive, and retire workflows are deferred

## Annotation Domain

### `annotation_tasks`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `dataset_id` UUID null references `datasets(id)`
- `source_asset_id` UUID null references `source_assets(id)`
- `task_type` text not null
- `status` `annotation_task_status` not null
- `priority` integer not null default `0`
- `assigned_to_user_id` UUID null references `users(id)`
- `reviewer_user_id` UUID null references `users(id)`
- `created_by_user_id` UUID not null references `users(id)`
- `current_workflow_run_id` UUID null references `workflow_runs(id)`
- `latest_ai_result_id` UUID null references `ai_results(id)`
- `annotation_schema` jsonb not null default `'{}'`
- `input_payload` jsonb not null default `'{}'`
- `output_payload` jsonb not null default `'{}'`
- `claimed_at`, `due_at`, `submitted_at`, `reviewed_at`, `completed_at`, `archived_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

Indexes:

- `(project_id, status, priority desc, created_at desc)`
- `(assigned_to_user_id, status)`
- `(source_asset_id, created_at desc)`

### `annotation_revisions`

- `id` UUID primary key
- `annotation_task_id` UUID not null references `annotation_tasks(id)`
- `revision_no` integer not null
- `revision_kind` text not null
- `source_ai_result_id` UUID null references `ai_results(id)`
- `created_by_user_id` UUID not null references `users(id)`
- `labels` jsonb not null default `'{}'`
- `content` jsonb not null default `'{}'`
- `review_notes` text null
- `confidence_score` numeric(5,4) null
- `created_at` timestamptz not null

Unique:

- `(annotation_task_id, revision_no)`

### `annotation_reviews`

- `id` UUID primary key
- `annotation_task_id` UUID not null references `annotation_tasks(id)`
- `revision_id` UUID not null references `annotation_revisions(id)`
- `reviewed_by_user_id` UUID not null references `users(id)`
- `decision` `annotation_review_decision` not null
- `notes` text null
- `created_at` timestamptz not null

Purpose:

- append-only human review record for a submitted annotation revision
- binds one reviewer decision to one task and one revision
- drives the task status transition after submission
- separate from `ai_results` accept/reject, which remains the AI suggestion review path

## Risk Domain

### `risk_signals`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `source_kind` text not null
- `signal_type` text not null
- `severity` integer not null
- `status` `risk_signal_status` not null
- `title` text not null
- `description` text null
- `signal_payload` jsonb not null default `'{}'`
- `observed_at` timestamptz not null
- `created_by_user_id` UUID null references `users(id)`
- `created_at`, `updated_at` timestamptz not null

Purpose:

- durable event-level input for project risk analysis
- may be created directly by ingestion flows or synthesized by `POST /projects/{project_id}/risk-generate` from manual or seeded project risk inputs
- serves as the source entity for the risk-analysis workflow run

### `risk_alerts`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `risk_signal_id` UUID null references `risk_signals(id)`
- `status` `risk_alert_status` not null
- `severity` integer not null
- `title` text not null
- `summary` text null
- `assigned_to_user_id` UUID null references `users(id)`
- `detected_by_workflow_run_id` UUID null references `workflow_runs(id)`
- `next_review_at` timestamptz null
- `resolved_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

Purpose:

- persisted current-state snapshot for a project risk item
- canonical object behind the risk item detail page
- linked to one source signal and zero or more strategy records
- updated by the unified risk-monitoring workflow after the normalized AI result is persisted
- strategy suggestions, when present, are produced by the same workflow run and materialized into `risk_strategies`

Indexes:

- `(project_id, status, severity desc, created_at desc)`
- `(assigned_to_user_id, status)`

### `risk_strategies`

- `id` UUID primary key
- `project_id` UUID not null references `projects(id)`
- `risk_alert_id` UUID not null references `risk_alerts(id)`
- `source_ai_result_id` UUID null references `ai_results(id)`
- `status` `strategy_status` not null
- `proposal_order` integer not null default `1`
- `title` text not null
- `summary` text not null
- `strategy_payload` jsonb not null default `'{}'`
- `approved_by_user_id` UUID null references `users(id)`
- `approved_at` timestamptz null
- `applied_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

## Workflow and AI Execution

### `workflow_runs`

- `id` UUID primary key
- `organization_id` UUID not null references `organizations(id)`
- `project_id` UUID not null references `projects(id)`
- `workflow_domain` `workflow_domain` not null
- `workflow_type` text not null
- `source_entity_type` text not null
- `source_entity_id` UUID not null
- `status` `workflow_run_status` not null
- `priority` integer not null default `0`
- `requested_by_user_id` UUID null references `users(id)`
- `source` text not null
- `correlation_key` text null
- `idempotency_key` text null
- `retry_of_run_id` UUID null references `workflow_runs(id)`
- `input_snapshot` jsonb not null default `'{}'`
- `result_summary` jsonb not null default `'{}'`
- `error_code` text null
- `error_message` text null
- `started_at`, `completed_at`, `canceled_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

Unique:

- `(organization_id, idempotency_key)` when `idempotency_key` is present

Indexes:

- `(project_id, workflow_domain, status, created_at desc)`
- `(source_entity_type, source_entity_id, created_at desc)`

### `workflow_run_steps`

- `id` UUID primary key
- `workflow_run_id` UUID not null references `workflow_runs(id)`
- `step_key` text not null
- `sequence_no` integer not null
- `status` `workflow_step_status` not null
- `attempt_count` integer not null default `0`
- `input_payload` jsonb not null default `'{}'`
- `output_payload` jsonb not null default `'{}'`
- `last_error_code` text null
- `last_error_message` text null
- `started_at`, `completed_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

Unique:

- `(workflow_run_id, step_key)`
- `(workflow_run_id, sequence_no)`

### `coze_runs`

- `id` UUID primary key
- `workflow_run_id` UUID not null references `workflow_runs(id)`
- `step_id` UUID null references `workflow_run_steps(id)`
- `coze_workflow_key` text not null
- `status` `coze_run_status` not null
- `idempotency_key` text not null
- `external_run_id` text null
- `attempt_no` integer not null default `1`
- `request_payload` jsonb not null default `'{}'`
- `response_payload` jsonb not null default `'{}'`
- `callback_payload` jsonb not null default `'{}'`
- `http_status` integer null
- `dispatched_at`, `acknowledged_at`, `completed_at`, `last_polled_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

Unique:

- `(workflow_run_id, idempotency_key)`
- `external_run_id` when present

### `ai_results`

- `id` UUID primary key
- `organization_id` UUID not null references `organizations(id)`
- `project_id` UUID not null references `projects(id)`
- `workflow_run_id` UUID not null references `workflow_runs(id)`
- `coze_run_id` UUID null references `coze_runs(id)`
- `result_type` `ai_result_type` not null
- `status` `ai_result_status` not null
- `source_entity_type` text not null
- `source_entity_id` UUID not null
- `raw_payload` jsonb not null default `'{}'`
- `normalized_payload` jsonb not null default `'{}'`
- `reviewed_by_user_id` UUID null references `users(id)`
- `review_notes` text null
- `reviewed_at` timestamptz null
- `applied_by_user_id` UUID null references `users(id)`
- `applied_at` timestamptz null
- `created_at`, `updated_at` timestamptz not null

Purpose:

- durable persistence for every AI output, even if the output is later rejected or superseded
- for risk monitoring, one workflow run may persist both `risk_analysis` and `risk_strategy` AI results before `risk_strategies` are materialized

## Audit and Traceability

### `audit_events`

- `id` UUID primary key
- `organization_id` UUID not null references `organizations(id)`
- `project_id` UUID null references `projects(id)`
- `actor_user_id` UUID null references `users(id)`
- `action` `audit_action` not null
- `reason_code` text not null
- `entity_type` text not null
- `entity_id` UUID not null
- `workflow_run_id` UUID null references `workflow_runs(id)`
- `coze_run_id` UUID null references `coze_runs(id)`
- `request_id` text null
- `before_state` jsonb not null default `'{}'`
- `after_state` jsonb not null default `'{}'`
- `metadata` jsonb not null default `'{}'`
- `occurred_at` timestamptz not null

## Relationship Summary

- `projects` own datasets, source assets, annotation tasks, risk signals, risk alerts, workflow runs, and AI results.
- `annotation_tasks` connect media assets to human and AI annotation work.
- `annotation_reviews` record human review decisions for submitted annotation revisions, while `ai_results` accept/reject records AI suggestion decisions.
- `risk_signals` can escalate into `risk_alerts`; unified risk-monitoring runs can also persist `risk_strategy` outputs that materialize into `risk_strategies`.
- `workflow_runs` own workflow steps and link to Coze attempts.
- `ai_results` link raw Coze output to human review and downstream business entities.
- `audit_events` provide immutable explainability across all domains.

## Index Strategy

- Queue tables: `(project_id, status, priority, created_at)`
- Run tables: `(project_id, workflow_domain, status, created_at)`
- AI results: `(project_id, result_type, status, created_at)`
- Alerts: `(project_id, status, severity, created_at)`
- Audit events: `(organization_id, occurred_at desc)` and `(project_id, occurred_at desc)`

## MVP Notes

- Image, audio, and video are supported through shared `source_assets` metadata plus modality-specific JSON payloads.
- Advanced geometric or timeline substructures can remain in JSON for MVP.
- Later phases can split out detailed segment tables if performance or analytics require it.
