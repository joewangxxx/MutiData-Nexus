# Coze Integration

Status: `review-ready`
Owner: `architect`
Last Updated: `2026-03-19`

## Purpose

This document defines how the FastAPI control plane uses Coze as the AI engine for:

- multimodal annotation assistance
- project risk analysis and strategy suggestions

Coze is never the source of truth. PostgreSQL persists every workflow run, every Coze attempt, every AI result, and every audit event needed to explain the outcome.

## Integration Boundary

The backend owns:

- workflow creation and state transitions
- idempotency and retry policy
- prompt assembly and request validation
- signature verification for callbacks
- normalization of Coze output into platform-owned records
- business-state changes after AI persistence

Coze owns only model execution and provider-side run state.

## Workflow Keys

Recommended Coze workflow keys for the MVP:

| Platform workflow | Coze workflow key | Output type |
|------------------|-------------------|-------------|
| Annotation assist | `annotation_suggestion_v1` | label suggestions, draft content, confidence, rationale |
| Project risk monitoring | `risk_monitoring_v1` | severity analysis, summary, evidence, recommended action, strategy suggestions |

The workflow key is stored on `coze_runs.coze_workflow_key` and must be stable enough for audit and retry handling.

Backend Coze configuration is environment-driven. Recommended variables:

- `COZE_ANNOTATION_RUN_URL`
- `COZE_API_TOKEN`
- `COZE_RISK_RUN_URL`
- `COZE_RISK_API_TOKEN`
- `COZE_TIMEOUT_SECONDS`

## Integration Model

Recommendation: **webhook-first with polling reconciliation**

- FastAPI dispatches work to Coze.
- Coze returns completion by webhook when available.
- A polling reconciler repairs stale in-flight runs.
- Both paths converge into the same `coze_runs`, `ai_results`, and `workflow_runs` records.

## Dispatch Envelope

FastAPI builds each Coze request from:

- organization and project identifiers
- workflow run identifiers
- source entity snapshots
- user-visible instructions and approval context
- expected output schema
- prompt version or template version

Every dispatch must include:

- a FastAPI-generated idempotency key
- a backend-generated correlation key
- the source entity type and ID
- the workflow run ID

## Dispatch Flow

1. FastAPI validates request, permissions, and idempotency.
2. FastAPI creates `workflow_runs` and `workflow_run_steps`.
3. FastAPI inserts a `coze_runs` row in `prepared`.
4. FastAPI builds the Coze request from workflow context, entity snapshots, and prompt configuration.
5. FastAPI sends the request to Coze.
6. FastAPI records request metadata, provider response metadata, and the external run ID when returned.
7. Completion arrives by callback or reconciler polling.
8. FastAPI persists the raw output and the normalized `ai_results` record or records, depending on the workflow output shape.
9. If the result passes validation, FastAPI applies the business update and closes the run.

### Project Risk Monitoring

`POST /api/v1/projects/{project_id}/risk-generate` follows the same dispatch model as other backend-owned Coze integrations, with one extra preprocessing step:

1. FastAPI validates the project-scoped risk input.
2. FastAPI persists a new `risk_signal` row from the request payload.
3. FastAPI creates the workflow run using that `risk_signal` as the source entity.
4. FastAPI builds the Coze request for `risk_monitoring_v1` using `COZE_RISK_RUN_URL` and `COZE_RISK_API_TOKEN`.
5. FastAPI records request metadata and dispatch outcome in `coze_runs`.
6. Completion arrives by callback or reconciler polling.
7. FastAPI persists the raw output and normalized `ai_results` records for both risk analysis and any returned strategy suggestions.
8. FastAPI upserts the canonical `risk_alert` snapshot from the normalized analysis result.
9. FastAPI materializes `risk_strategies` from the same workflow output when present.
10. No separate strategy-generation Coze run is triggered by `risk-generate`.

## Callback Handling

FastAPI exposes:

- `POST /api/v1/integrations/coze/callback`

Callback requirements:

- verify signature or shared secret
- require provider external run ID
- store the raw callback payload in `coze_runs.callback_payload`
- update `coze_runs.status`
- generate or update the normalized `ai_results`
- advance the linked workflow run only after persistence succeeds

The callback handler must be idempotent because providers may retry delivery.

## Polling Reconciliation

The backend also runs a reconciliation loop for `coze_runs` still in:

- `submitted`
- `accepted`
- `running`

Polling rules:

- only poll stale runs beyond the expected callback delay
- update `last_polled_at`
- reconcile provider state into existing rows, never create duplicates
- stop polling terminal runs
- record an audit event when reconciliation changes state

## Retry Strategy

### Safe Automatic Retries

- HTTP `429`
- network timeout before confirmed acceptance
- transient `5xx`
- temporary DNS or provider availability failure

### Manual or Guarded Retries

- provider accepted the run but completion state is unknown
- webhook missing after provider acceptance
- output validation failed but the provider returned syntactically complete content

### Never Auto-Retry

- invalid request payload
- missing required project or task state
- authorization failure
- terminal business conflict

### Retry Mechanics

- Use one logical idempotency key per workflow action.
- Persist each attempt in `coze_runs.attempt_no`.
- Keep the original `workflow_runs` row immutable.
- Use bounded exponential backoff.
- After max attempts, mark the workflow run failed and require operator or project-manager action.

## AI Result Persistence Rule

Every Coze completion produces:

1. a raw provider payload in `coze_runs.response_payload` or `callback_payload`
2. one or more normalized rows in `ai_results`

The business entity update happens only after that persistence step completes.

## Normalization Rules

The backend should normalize Coze output into a platform schema before it is consumed downstream.

### Annotation Output

Normalized output should include:

- `labels`
- `content`
- `confidence_score`
- `rationale`
- optional `segments` or `timecodes` for audio and video tasks

### Risk Analysis Output

Normalized output should include:

- `severity`
- `summary`
- `evidence`
- `recommended_action`
- `confidence_score`

### Risk Strategy Output

Normalized output should include:

- `title`
- `summary`
- `steps`
- `owner_hint`
- `due_window`
- `rationale`

These strategy suggestions are emitted by the same physical risk monitoring workflow as the analysis result.

## Validation Pipeline

Before any AI output affects product state:

- validate schema for the expected result type
- check entity compatibility, such as the target task or risk alert still being valid
- optionally require human review depending on workflow type
- mark `ai_results.status` as `accepted`, `rejected`, `superseded`, or `applied`

## Failure Handling Strategy

| Failure Point | Detection | Handling |
|--------------|-----------|----------|
| Pre-dispatch validation | FastAPI request validation or policy checks | Reject request, persist audit event, do not create a Coze attempt |
| Dispatch failure | request timeout, provider `5xx`, `429` | Persist failed attempt, retry if safe |
| Lost callback | run accepted but no webhook within timeout window | Poll Coze, reconcile state into existing run |
| Invalid AI payload | schema validation fails | Persist raw output, create rejected `ai_results`, fail workflow |
| Partial persistence failure | raw output saved but business entity update failed | Keep workflow failed, preserve compensating audit record, allow retry or manual repair |
| Duplicate logical action | reused idempotency key | Return original result and do not dispatch duplicate work |

## Security Notes

- Coze credentials remain outside PostgreSQL.
- Source content sent to Coze should be minimized to only what the workflow requires.
- Sensitive payload retention should be configurable later without changing the logical model.
- Callback secrets and signing material belong in backend secret storage, not in the database.
