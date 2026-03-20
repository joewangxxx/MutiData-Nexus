# API Contract

Status: `review-ready`
Owner: `architect`
Last Updated: `2026-03-19`

## Purpose

This is the frontend/backend contract for the `Next.js` frontend and `FastAPI` control plane. It is the only approved source for REST endpoint shapes in `v1`.

## Contract Rules

- Base path: `/api/v1`
- Transport: JSON over HTTPS
- Auth: bearer token or session cookie validated by FastAPI
- Idempotency: required for all durable create, dispatch, retry, approve, reject, and cancel operations
- Compatibility: additive only inside `v1`
- Business state: FastAPI owns all state transitions and persistence
- AI engine: the frontend never calls Coze directly

## Shared Request Rules

- `Authorization` is required for all user-facing endpoints.
- `Idempotency-Key` is required for mutating endpoints that create or transition durable state.
- `X-Request-Id` is optional from the client and may be echoed in responses.
- Cursor pagination uses `cursor` and `limit` query parameters.

## Shared Response Rules

Successful responses use:

```json
{
  "data": {},
  "meta": {
    "request_id": "req_123",
    "next_cursor": null,
    "has_more": false
  }
}
```

Error responses use:

```json
{
  "error": {
    "code": "conflict",
    "message": "Task is already closed.",
    "request_id": "req_123",
    "details": []
  }
}
```

## Shared Object Shapes

### `MeResponse`

- `user`: `id`, `email`, `display_name`, `status`
- `organization`: `id`, `slug`, `name`, `status`
- `organization_role`: string
- `project_memberships`: array of `{ project_id, project_code, project_name, project_role, status }`
- `effective_permissions`: array of permission strings

### `ProjectSummary`

- `id`, `organization_id`, `code`, `name`, `description`, `status`
- `owner_user_id`, `settings`
- `counts`: annotation queue, risk queue, active workflow runs, waiting-for-human runs

### `UserSummary`

- `id`, `email`, `display_name`, `status`

### `ProjectMembership`

- `id`, `project_id`, `user_id`
- `user`: `UserSummary`
- `project_role`, `status`
- `created_at`, `updated_at`

### `Dataset`

- `id`, `project_id`
- `name`, `description`, `source_kind`, `status`
- `metadata`
- `created_at`, `updated_at`, `archived_at`

### `DashboardSummary`

- `project`: `ProjectSummary`
- `queues`: annotation and risk queue counts
- `workload`: active runs, waiting for human, waiting for Coze, failures in the last 24 hours
- `inbox`: assigned tasks, open alerts, pending approvals
- `recent_activity`: latest audit events and AI result summaries

### `SourceAsset`

- `id`, `project_id`, `dataset_id`
- `asset_kind`: `image`, `audio`, or `video`
- `uri`, `storage_key`, `mime_type`, `checksum`
- `duration_ms`, `width_px`, `height_px`, `frame_rate`, `transcript`
- `metadata`

### `AnnotationTask`

- `id`, `project_id`, `dataset_id`, `source_asset_id`
- `task_type`, `status`, `priority`
- `assigned_to_user_id`, `reviewer_user_id`, `created_by_user_id`
- `current_workflow_run_id`, `latest_ai_result_id`
- `annotation_schema`, `input_payload`, `output_payload`
- `claimed_at`, `due_at`, `submitted_at`, `reviewed_at`, `completed_at`

### `AnnotationRevision`

- `id`, `annotation_task_id`, `revision_no`, `revision_kind`
- `source_ai_result_id`, `created_by_user_id`
- `labels`, `content`, `review_notes`, `confidence_score`, `created_at`

### `AnnotationReview`

- `id`, `annotation_task_id`, `revision_id`
- `reviewed_by_user_id`, `decision`, `notes`, `created_at`

### `RiskSignal`

- `id`, `project_id`, `source_kind`, `signal_type`
- `severity`, `status`, `title`, `description`
- `signal_payload`, `observed_at`, `created_by_user_id`

### `RiskAlert`

- `id`, `project_id`, `risk_signal_id`
- `status`, `severity`, `title`, `summary`
- `assigned_to_user_id`, `detected_by_workflow_run_id`
- `next_review_at`, `resolved_at`

Interpretation:

- this object is the API representation of the current risk snapshot
- frontend risk item detail pages should treat `riskId` as `risk_alert.id` and fetch this shape with `GET /risk-alerts/{alert_id}`

### Annotation Review Rules

- `annotation_tasks` are the review container.
- `annotation_revisions` are the submitted artifacts under review.
- `annotation_reviews` record reviewer decisions for a specific task and revision.
- `POST /ai-results/{ai_result_id}/accept|reject` remains the AI suggestion review path and does not finalize submitted annotation reviews.
- `decision=revise` reopens the task for another submission cycle.

### `RiskStrategy`

- `id`, `risk_alert_id`, `project_id`
- `source_ai_result_id`, `status`, `proposal_order`
- `title`, `summary`, `strategy_payload`
- `approved_by_user_id`, `approved_at`, `applied_at`

### `WorkflowRun`

- `id`, `organization_id`, `project_id`
- `workflow_domain`, `workflow_type`
- `source_entity_type`, `source_entity_id`
- `status`, `priority`
- `requested_by_user_id`, `source`, `correlation_key`, `idempotency_key`
- `retry_of_run_id`
- `input_snapshot`, `result_summary`, `error_code`, `error_message`
- `started_at`, `completed_at`, `canceled_at`
- `steps`: array of `WorkflowStep`
- `coze_runs`: array of `CozeRun`
- `ai_results`: array of `AiResult`

### `WorkflowStep`

- `id`, `workflow_run_id`, `step_key`, `sequence_no`
- `status`, `attempt_count`
- `input_payload`, `output_payload`
- `last_error_code`, `last_error_message`
- `started_at`, `completed_at`

### `CozeRun`

- `id`, `workflow_run_id`, `step_id`
- `coze_workflow_key`, `status`, `idempotency_key`
- `external_run_id`, `attempt_no`
- `request_payload`, `response_payload`, `callback_payload`
- `http_status`, `dispatched_at`, `acknowledged_at`, `completed_at`, `last_polled_at`

### `AiResult`

- `id`, `workflow_run_id`, `coze_run_id`
- `result_type`, `status`
- `source_entity_type`, `source_entity_id`
- `raw_payload`, `normalized_payload`
- `reviewed_by_user_id`, `review_notes`, `reviewed_at`
- `applied_by_user_id`, `applied_at`

### `AuditEvent`

- `id`, `organization_id`, `project_id`
- `actor_user_id`, `action`, `reason_code`
- `entity_type`, `entity_id`
- `workflow_run_id`, `coze_run_id`
- `request_id`, `before_state`, `after_state`, `metadata`, `occurred_at`

## Endpoint Summary

### Identity and Session

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| `GET` | `/me` | Current user, memberships, and permission summary | `MeResponse` |

### Projects and Dashboard

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| `GET` | `/projects` | List visible projects | Supports `cursor`, `limit` |
| `POST` | `/projects` | Create a project | Requires `Idempotency-Key` |
| `GET` | `/projects/{project_id}` | Project detail | Returns `ProjectSummary` plus `ProjectMembership` items in `memberships` |
| `PATCH` | `/projects/{project_id}` | Update project metadata | Mutable fields: `name`, `description`, `status`, `owner_user_id`, `settings` |
| `GET` | `/projects/{project_id}/members` | List project memberships | Returns `ProjectMembership` items for project-scoped member management |
| `PATCH` | `/projects/{project_id}/members/{membership_id}` | Update a project membership | Mutable fields: `project_role`, `status`; requires `Idempotency-Key` |
| `DELETE` | `/projects/{project_id}/members/{membership_id}` | Deactivate a project membership | Soft delete / inactive transition; requires `Idempotency-Key` |
| `GET` | `/projects/{project_id}/dashboard` | Aggregated dashboard data | Returns `DashboardSummary` |

### Media and Dataset Access

For Release 1, the write-side catalog contract is metadata-only:

- no binary upload
- no batch import
- no archive or retire action
- no Coze involvement
- no workflow tracking beyond the platform audit trail

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| `GET` | `/projects/{project_id}/datasets` | List datasets | Supports `cursor`, `limit` |
| `POST` | `/projects/{project_id}/datasets` | Create a dataset metadata record | Project-scoped; returns `Dataset`; requires `Idempotency-Key` |
| `PATCH` | `/datasets/{dataset_id}` | Update dataset metadata | Mutable fields: `name`, `description`, `source_kind`, `metadata`; requires `Idempotency-Key` |
| `GET` | `/projects/{project_id}/source-assets` | List media assets | Supports `cursor`, `limit`, `dataset_id`, `asset_kind` |
| `POST` | `/projects/{project_id}/source-assets` | Register a source asset metadata record | Project-scoped; `dataset_id` optional; returns `SourceAsset`; requires `Idempotency-Key` |
| `GET` | `/source-assets/{asset_id}` | Asset metadata | Returns `SourceAsset` |
| `PATCH` | `/source-assets/{asset_id}` | Update source asset metadata | Mutable fields: `dataset_id`, `storage_key`, `mime_type`, `checksum`, `duration_ms`, `width_px`, `height_px`, `frame_rate`, `transcript`, `metadata`; requires `Idempotency-Key` |
| `POST` | `/source-assets/{asset_id}/access` | Return signed or temporary access info | Used for image, audio, and video viewing |

### Annotation

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| `GET` | `/projects/{project_id}/annotation-tasks` | List annotation tasks | Filters: `status`, `assigned_to_me`, `task_type`, `asset_kind` |
| `POST` | `/projects/{project_id}/annotation-tasks` | Create or ingest tasks | Request includes `source_asset_id` or `dataset_id`, `task_type`, `priority`, optional `annotation_schema` |
| `GET` | `/annotation-tasks/{task_id}` | Task detail with latest revision | Returns `AnnotationTask` plus recent `AnnotationRevision` and `AnnotationReview` items |
| `PATCH` | `/annotation-tasks/{task_id}` | Update assignment or status | Mutable fields: `assigned_to_user_id`, `reviewer_user_id`, `priority`, `due_at`, `status` |
| `POST` | `/annotation-tasks/{task_id}/claim` | Claim task | No body required |
| `GET` | `/annotation-tasks/{task_id}/revisions` | Revision history | Returns ordered `AnnotationRevision` list |
| `POST` | `/annotation-tasks/{task_id}/submissions` | Submit annotation revision | Body: `labels`, `content`, optional `review_notes`, optional `confidence_score` |
| `GET` | `/annotation-tasks/{task_id}/reviews` | Review history | Returns ordered `AnnotationReview` list |
| `POST` | `/annotation-tasks/{task_id}/reviews` | Record reviewer decision on submitted revision | Body: `revision_id`, `decision`, optional `notes`; returns `AnnotationReview` plus updated `AnnotationTask` |
| `GET` | `/annotation-tasks/{task_id}/ai-results` | List AI suggestions for the task | Returns persisted `AiResult` records |
| `POST` | `/annotation-tasks/{task_id}/ai-generate` | Start AI-assisted annotation workflow | Body optional: `context_overrides`, `force_refresh` |
| `POST` | `/ai-results/{ai_result_id}/accept` | Accept AI result into business state | Body optional: `review_notes` |
| `POST` | `/ai-results/{ai_result_id}/reject` | Reject AI result with review notes | Body: `review_notes` required or strongly recommended |

### Risk Monitoring and Strategy

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| `GET` | `/projects/{project_id}/risk-signals` | List risk signals | Filters: `status`, `severity`, `signal_type` |
| `POST` | `/projects/{project_id}/risk-signals` | Create or ingest risk signal | Body: `source_kind`, `signal_type`, `severity`, `title`, `description`, `signal_payload`, `observed_at` |
| `POST` | `/projects/{project_id}/risk-generate` | Create a project-scoped risk signal and immediately trigger the unified risk monitoring workflow | Thin convenience entrypoint for manual or seeded project risk inputs; returns risk analysis plus strategy suggestions from one Coze run |
| `GET` | `/projects/{project_id}/risk-alerts` | List risk alerts | Current risk snapshots; filters: `status`, `severity`, `assigned_to_me` |
| `GET` | `/risk-alerts/{alert_id}` | Risk alert detail | Returns the current risk snapshot plus source signal and strategies |
| `PATCH` | `/risk-alerts/{alert_id}` | Update alert status or assignee | Mutable fields: `status`, `assigned_to_user_id`, `title`, `summary`, `severity`, `next_review_at` |
| `POST` | `/risk-alerts/{alert_id}/acknowledge` | Acknowledge alert | No body required |
| `POST` | `/risk-alerts/{alert_id}/strategy-generate` | Deferred/unsupported in MVP; reserved for future non-Coze compatibility behavior | Must not dispatch Coze in MVP |
| `GET` | `/risk-alerts/{alert_id}/strategies` | List persisted strategy proposals | Returns ordered `RiskStrategy` list |
| `POST` | `/risk-strategies/{strategy_id}/approve` | Approve a strategy proposal | Body optional: `review_notes` |
| `POST` | `/risk-strategies/{strategy_id}/reject` | Reject a strategy proposal | Body optional: `review_notes` |

### Workflow and Audit

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| `GET` | `/workflow-runs` | List workflow runs | Filters: `project_id`, `workflow_domain`, `status`, `source_entity_type`, `source_entity_id` |
| `POST` | `/workflow-runs` | Create workflow run directly when allowed | Mostly for internal or operator flows |
| `GET` | `/workflow-runs/{run_id}` | Run detail with steps and Coze attempts | Returns nested `WorkflowRun` |
| `POST` | `/workflow-runs/{run_id}/retry` | Retry failed or timed-out run | Body: `reason_code`, optional `reason_text` |
| `POST` | `/workflow-runs/{run_id}/cancel` | Cancel run | Body optional: `reason_code` |
| `GET` | `/audit-events` | Audit search | Filters: `project_id`, `entity_type`, `entity_id`, `workflow_run_id`, `actor_user_id` |

### Integration Callback

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| `POST` | `/integrations/coze/callback` | Provider webhook callback receiver | Validates provider signature and records raw payload before updating state |

## Body Shapes for Key Mutations

### `POST /projects`

Required fields:

- `organization_id`
- `code`
- `name`

Optional fields:

- `description`
- `owner_user_id`
- `settings`

### `PATCH /projects/{project_id}/members/{membership_id}`

Optional fields:

- `project_role`
- `status`

Behavior:

- `project_role` is limited to the project roles already defined in the schema
- `status` is metadata state for the membership record and is typically `active` or `inactive`
- the backend must preserve idempotency and reject changes that would leave the project with no active project manager or invalidate the current owner membership
- membership changes are audited as durable business-state transitions

### `DELETE /projects/{project_id}/members/{membership_id}`

Behavior:

- this is a soft delete / deactivate operation, not a physical row delete
- the backend marks the membership as inactive and preserves the row for traceability
- repeated DELETE calls are idempotent and should return the current inactive membership state
- the backend must reject deactivation if it would leave the project without an active project manager

### `POST /projects/{project_id}/datasets`

Required fields:

- `name`
- `source_kind`

Optional fields:

- `description`
- `metadata`

Behavior:

- `status` is initialized by the backend as `active`
- the dataset is project-scoped and cannot be reassigned across projects through this MVP contract

### `PATCH /datasets/{dataset_id}`

Optional fields:

- `name`
- `description`
- `source_kind`
- `metadata`

Behavior:

- this mutation is metadata-only
- archive and retire transitions are intentionally deferred out of MVP scope

### `POST /projects/{project_id}/source-assets`

Required fields:

- `asset_kind`
- `uri`

Optional fields:

- `dataset_id`
- `storage_key`
- `mime_type`
- `checksum`
- `duration_ms`
- `width_px`
- `height_px`
- `frame_rate`
- `transcript`
- `metadata`

Behavior:

- `dataset_id` may be omitted so the asset can remain project-scoped
- `uri` must reference a usable media location or registered access URL; the backend does not upload bytes in this slice
- the source asset remains project-scoped and can later be associated with a dataset by metadata update

### `PATCH /source-assets/{asset_id}`

Optional fields:

- `dataset_id`
- `storage_key`
- `mime_type`
- `checksum`
- `duration_ms`
- `width_px`
- `height_px`
- `frame_rate`
- `transcript`
- `metadata`

Behavior:

- this mutation is metadata-only
- file upload, batch import, archive, and retire behavior are deferred out of MVP scope

### `POST /projects/{project_id}/annotation-tasks`

Required fields:

- `task_type`

At least one of:

- `source_asset_id`
- `dataset_id`

Optional fields:

- `assigned_to_user_id`
- `reviewer_user_id`
- `priority`
- `annotation_schema`
- `input_payload`

### `POST /annotation-tasks/{task_id}/submissions`

Required fields:

- `labels`
- `content`

Optional fields:

- `review_notes`
- `confidence_score`

### `POST /annotation-tasks/{task_id}/reviews`

Required fields:

- `revision_id`
- `decision`

Optional fields:

- `notes`

Decision values:

- `approve`
- `reject`
- `revise`

### `POST /annotation-tasks/{task_id}/ai-generate`

Optional fields:

- `context_overrides`
- `force_refresh`

MVP behavior:

- `workflow_run`
- `coze_run`
- `ai_result` placeholder or populated record once persistence completes

### `POST /projects/{project_id}/risk-signals`

Required fields:

- `source_kind`
- `signal_type`
- `severity`
- `title`
- `observed_at`

Optional fields:

- `description`
- `signal_payload`
- `created_by_user_id`

### `POST /projects/{project_id}/risk-generate`

Required fields:

- `source_kind`
- `signal_type`
- `severity`
- `title`
- `observed_at`

Optional fields:

- `description`
- `signal_payload`
- `context_overrides`

Interpretation:

- the backend first persists a `risk_signal` row scoped to the project
- the backend then creates a `workflow_run` whose source entity is that `risk_signal`
- the workflow dispatches the single physical risk monitoring Coze run and persists the raw and normalized AI outputs
- the backend upserts the canonical `risk_alert` snapshot from the normalized risk analysis result
- the backend also persists any returned strategy suggestions from the same run into `risk_strategies`
- `POST /risk-alerts/{alert_id}/strategy-generate` is deferred/unsupported in MVP and must not dispatch Coze

MVP behavior:

- `risk_signal`
- `workflow_run`
- `coze_run`
- `ai_result`
- `risk_strategies`
- `risk_alert`

### `POST /risk-alerts/{alert_id}/strategy-generate`

Optional fields:

- `proposal_count`
- `context_overrides`

MVP behavior:

- deferred/unsupported compatibility only
- no `workflow_run` or `coze_run` is created
- the backend returns a stable unsupported response until a future contract revision defines behavior

### `POST /workflow-runs/{run_id}/retry`

Required fields:

- `reason_code`

Optional fields:

- `reason_text`

### `POST /integrations/coze/callback`

Required fields:

- provider signature or shared-secret proof in headers
- provider external run identifier in body
- raw provider status and payload in body

## Error Handling

Error codes:

- `bad_request`
- `validation_error`
- `unauthorized`
- `forbidden`
- `not_found`
- `conflict`
- `idempotency_replay`
- `workflow_run_conflict`
- `integration_unavailable`
- `retryable_integration_error`
- `invalid_ai_result`
- `callback_signature_invalid`

HTTP status mapping:

- `400` for malformed requests
- `401` for missing or invalid auth
- `403` for permission failures
- `404` for missing resources
- `409` for conflict or duplicate idempotency
- `422` for schema validation failures
- `502` or `503` for upstream provider failures

## Contract Governance

1. FE and BE do not change this file directly.
2. Missing fields or endpoints are escalated, not improvised.
3. FastAPI is authoritative for validation and permission enforcement.
4. Any breaking change requires a new API version.
