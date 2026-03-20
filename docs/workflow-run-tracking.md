# Workflow Run Tracking

Status: `review-ready`
Owner: `architect`
Last Updated: `2026-03-19`

## Purpose

This document defines the durable execution model for all backend-controlled workflows. A workflow run is the authoritative trace for any annotation AI assist or project risk monitoring action.

## Execution Model

Each workflow run contains:

- one parent `workflow_runs` row
- one or more ordered `workflow_run_steps`
- zero or more `coze_runs`
- one or more `ai_results` when AI output is produced
- linked `audit_events`

## Canonical Lifecycle

The canonical lifecycle is:

1. `draft`
2. `queued`
3. `validating`
4. `dispatching`
5. `running`
6. `waiting_for_human` if review is required
7. `succeeded`, `succeeded_with_warnings`, `failed`, `canceled`, or `timed_out`

`draft` is reserved for internal staging before a run is fully queued. User-facing flows should normally observe `queued` or later.

## Allowed Transitions

| State | Allowed Next States |
|-------|---------------------|
| `draft` | `queued`, `canceled` |
| `queued` | `validating`, `canceled` |
| `validating` | `dispatching`, `failed`, `canceled` |
| `dispatching` | `running`, `failed`, `canceled` |
| `running` | `waiting_for_human`, `succeeded`, `succeeded_with_warnings`, `failed`, `timed_out` |
| `waiting_for_human` | `running`, `succeeded`, `failed`, `canceled` |
| terminal states | none without explicit retry lineage |

## Domain Lifecycles

### Annotation AI Assist

1. User opens or claims a task.
2. Backend validates task state, role, and input payload.
3. Workflow run is created with domain `annotation`.
4. Coze generates suggestion or draft annotation.
5. Raw output and normalized AI result are persisted.
6. Human accepts, rejects, or edits the suggestion.
7. Final annotation revision is persisted.

### Annotation Review

1. Annotator submits a revision for the task.
2. Backend marks the run `waiting_for_human` and keeps the task in `submitted` or `needs_review`.
3. Reviewer records a decision against the submitted revision and task.
4. `approve` marks the task `approved` and closes the run as `succeeded`.
5. `reject` marks the task `rejected` and closes the run as `failed`.
6. `revise` reopens the task as `in_progress` and returns the run to `running` for another submission cycle.

### Risk Monitoring

1. Risk signal arrives or user requests analysis.
2. Backend validates signal and project scope.
3. Workflow run is created with domain `risk_monitoring`.
4. Coze analyzes the signal context and returns risk analysis plus strategy suggestions in one completion.
5. AI results are persisted.
6. Backend creates or updates a risk alert and materializes any returned strategy suggestions.

### Project Risk Generation

1. User submits a project-scoped manual or seeded risk input through `POST /projects/{project_id}/risk-generate`.
2. Backend persists a `risk_signal` from that input.
3. Backend creates the `risk_monitoring` workflow run with the new `risk_signal` as the source entity.
4. Coze analyzes the signal context using the backend-owned risk gateway and returns both analysis and strategy suggestions.
5. Raw and normalized AI outputs are persisted.
6. Backend upserts the canonical `risk_alert` snapshot.
7. Strategy suggestions are persisted from the same run when present; there is no separate risk-strategy Coze run in MVP.

### Deferred Strategy Compatibility Endpoint

`POST /risk-alerts/{alert_id}/strategy-generate` does not create a workflow run in MVP.

- It is treated as a deferred/unsupported compatibility surface.
- It must not dispatch Coze in MVP.
- Any future behavior should be defined by a new contract revision rather than by reusing this lifecycle.

## Step Model

Recommended MVP steps:

1. `validate_request`
2. `persist_run_snapshot`
3. `prepare_context`
4. `dispatch_to_coze`
5. `await_completion`
6. `validate_output`
7. `persist_ai_result`
8. `apply_business_update`
9. `emit_audit`

## Step Semantics

- `validate_request` checks auth, RBAC, entity state, and idempotency.
- `persist_run_snapshot` writes the durable starting payload.
- `prepare_context` builds the Coze input payload from source entities and prompt configuration.
- `dispatch_to_coze` records the outbound attempt and external run identifier.
- `await_completion` reflects the in-flight wait for callback or polling.
- `validate_output` verifies the returned payload shape and business compatibility.
- `persist_ai_result` writes raw and normalized AI results to PostgreSQL.
- `apply_business_update` changes the task, alert, or strategy state only after persistence succeeds.
- `emit_audit` writes the final trace event for the transition.

## Retry Lineage

Recommended rule:

- keep the original workflow run immutable
- create a new workflow run for a manual retry
- link the new run using `retry_of_run_id`
- preserve per-attempt detail in `coze_runs.attempt_no`

This gives clearer operator history than silently reopening terminal runs.

## Reporting Requirements

The dashboard should be able to answer:

- what runs are active now
- what runs are waiting on a person
- what runs are waiting on Coze
- what AI results were generated for a project, task, or alert
- what failed, why it failed, and whether a retry exists

## Audit Requirements

Every meaningful transition emits an `audit_events` row containing:

- actor
- previous state
- next state
- entity type and ID
- workflow run ID
- Coze run ID when applicable
- machine-readable reason code

## Operational Rules

- A workflow run is not considered complete until the terminal workflow state, persisted AI state, and audit record are all written.
- Reconciliation is allowed to update an in-flight run, but it must never rewrite historical terminal data.
- Manual edits to downstream business objects must still emit audit events and preserve the originating workflow lineage.
