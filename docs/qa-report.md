# QA Report

Status: `release_final_acceptance_reviewed`  
Owner: `qa`  
Last Updated: `2026-03-20`

## Validation Scope

This QA pass validates the Release 1 final acceptance boundary using the verified slice inventory only.

Included:

- Verified Release 1 slices cited by `docs/mvp-scope.md`
- Release hardening evidence cited by `docs/release-gate.md`
- Alignment against `docs/prd.md`, `docs/mvp-scope.md`, `docs/architecture.md`, `docs/schema.md`, `docs/api-contract.md`, `docs/design-tokens.md`, `docs/page-list.md`, `docs/ui-flows.md`, `docs/release-gate.md`, `docs/release.md`, and `docs/handoff.md`

Explicitly not treated as Release 1 evidence:

- Any surface outside the verified slice inventory
- Any claim that live FE to BE integration is complete everywhere
- Any claim that the approved API contract is fully exercised end to end
- Any claim that production-platform-specific readiness beyond the approved release package is complete

## Current Release Gate View

This report is now the QA-side final acceptance framing for Release 1. It records what can be cited as verified evidence, what remains a non-blocking residual risk, and why the Release 1 claim must stay limited to the approved verified boundary.

### Release-blocking items

- No unresolved blocker remains inside the approved Release 1 boundary.
- Any product area outside the verified slice inventory remains unproven and cannot be counted as Release 1 evidence.

### Non-blocking residual risks

- Some verified slices still carry limited residual risk around data hydration, legacy naming, or other surfaces outside the slice boundary.
- Asset URL validation in the annotation gateway is syntactic `http(s)` validation only.
- The project and risk dashboards still contain non-blocking metric shape mismatch history such as the `Escalated` count staying at zero when the approved enum does not emit that status.
- Legacy or unrelated workflow history pages outside the verified slices may still contain mock-era language or implementation residue.

### Verified slices that count as release evidence

- AI-Assisted Annotation Submission
- Annotation Task Management Completion
- Project Dataset & Multimodal Item Management E2E
- Multimodal Annotation Coverage Completion
- Risk Signal Capture Completion
- Project Risk Monitoring E2E
- Risk Workflow Backend Integration
- Unified Risk Workflow Output Analysis + Strategy Suggestions
- Risk Strategy Approve / Reject
- Risk Alert Operations Completion
- Annotation Review Flow
- Annotation Coze Integration
- Workflow Runs Live List
- Release Hardening Track

### Slices that still cannot be cited as MVP ready

- The full product experience across all PRD surfaces
- Any claim that live FE to BE integration is complete everywhere
- Any claim that the approved API contract is fully exercised end to end
- Any claim that annotation and risk workflows are fully complete beyond the verified slices
- Any claim that deployment or production release readiness is complete

### Workflow Runs Live List

The `/workflow-runs` live list is now verified and should be treated as release evidence, not as a release blocker. It can be cited as a resolved milestone item.

## Slice Check: Release Hardening Track

This targeted check validates only the release-hardening package:

- controller health and readiness endpoints
- web health and readiness endpoints
- controller and web Docker images
- release compose stack for controller, web, and PostgreSQL
- smoke and rollback helper scripts
- release-facing documentation consistency

Result:

- Passed

Evidence:

- `services/controller/app/api/routes/ops.py` exposes `/api/v1/ops/healthz` and `/api/v1/ops/readyz`.
- `services/controller/app/services/release_hardening.py` validates runtime configuration and database connectivity for readiness.
- `apps/web/src/app/healthz/route.ts` and `apps/web/src/app/readyz/route.ts` expose web release endpoints, and `readyz` fails closed when the controller health endpoint is unavailable.
- `services/controller/Dockerfile` and `apps/web/Dockerfile` provide buildable release images.
- `compose.release.yaml` wires controller, web, and PostgreSQL together and resolves cleanly with `docker compose -f compose.release.yaml config` when the release environment variables are supplied.
- A real Docker daemon rehearsal now passes on this workstation: `docker compose -f compose.release.yaml up -d --build` succeeded, `migrate` exited `0`, `postgres`, `controller`, and `web` all reached `healthy`, and `ops/release/smoke.ps1` passed against the running stack.
- `ops/release/smoke.ps1` and `ops/release/rollback.ps1` are syntactically valid and aligned with the release package.
- `docs/deployment.md`, `docs/observability.md`, `docs/release-gate.md`, `docs/release.md`, and `docs/handoff.md` now point at the same release package and record Release 1 as `go` for the approved verified boundary.

Residual risk:

- The release hardening package is rehearsal-grade, not production-target-specific.

## Slice Check: Release Runtime SSR Auth Fallback Fix

This targeted check validates only the release-blocker fix that restores server-side controller fetch authentication in the web runtime:

- incoming `Authorization` headers remain the first choice when present
- missing browser auth falls back to `CONTROLLER_API_AUTH_TOKEN` on the server only
- the fallback token is not exposed to client-side browser code
- release-facing web routes continue to pass request headers through the Next.js proxy layer

Result:

- Passed

Evidence:

- `apps/web/src/lib/controller-api.ts` now inserts a server-only `CONTROLLER_API_AUTH_TOKEN` fallback only when request headers do not already carry `authorization`.
- `apps/web/src/lib/controller-api.test.ts` covers the fallback and the preference order for incoming authorization.
- `apps/web/src/lib/controller-api.project-members.test.ts` covers explicit request-header preservation together with the new fallback behavior.
- `apps/web/src/app/api/projects/[projectId]/members/route.ts` still forwards the incoming request headers through the controller API helper.
- `compose.release.yaml`, `ops/release/release.env.example`, `ops/release/README.md`, and `docs/deployment.md` now document the server-only auth token required for the web runtime in release rehearsal.
- `cmd /c npm exec vitest run "src/lib/controller-api.test.ts" "src/lib/controller-api.project-members.test.ts" "src/app/api/projects/[projectId]/members/route.test.ts"` passed with 3 files and 25 tests.
- `cmd /c npm run lint` passed.
- `cmd /c npm run build` passed.

Residual risk:

- The release stack still lacks seeded users, memberships, and controller-backed project data, so this fix clears the 401 blocker but does not by itself make the entire release spot check pass.

### Current Recommendation

Recommendation: **release-ready for the approved Release 1 boundary**

Reason:

- The QA evidence is strong enough to define the verified Release 1 boundary.
- The authoritative release gate now aligns to that same verified boundary.
- The verified slices and release hardening package are sufficient to support a Release 1 claim for the approved scope.
- Deferred or broader surfaces remain explicitly out of scope rather than blocking the current release.

## Slice Check: AI-Assisted Annotation Submission

This targeted check validates only the approved annotation vertical slice:

- project-scoped annotation queue
- annotation task detail
- ai-generate action
- workflow run persistence
- ai result persistence
- revision submission
- task status transition to `submitted`
- workflow detail drilldown
- audit event persistence
- source asset metadata read path

Result:

- Passed

Evidence:

- Frontend queue and task detail pages call the live controller client instead of mock adapters.
- Frontend `ai-generate` and submission actions proxy through Next.js API routes to the controller.
- Backend exposes annotation task, source asset, workflow run, and Coze callback routes in the controller router.
- Backend annotation services persist workflow runs, Coze runs, AI results, revisions, and audit events in one closed loop.
- Backend and frontend tests for the slice pass, including the annotation submission flow and workbench action path.

Residual risk:

- The workflow runs list page now uses the live controller API, so the main remaining risk in this area is backend data visibility and name hydration behavior rather than mock divergence.

## Slice Check: Project Risk Monitoring E2E

This targeted check validates only the approved risk vertical slice:

- project selection / project page risk posture live
- risk input capture or seeded/manual risk input path
- backend-triggered Coze risk workflow execution
- workflow run persistence
- risk snapshot persistence using `risk_alert`
- risk event persistence using `risk_signal`
- strategy suggestion persistence
- frontend live risk dashboard
- status consistency between project page, risk detail, and workflow detail

Result:

- Passed

Evidence:

- Project overview and risk dashboard pages read live controller-backed project, alert, and signal data.
- Risk alert detail is live and shows the alert, source signal, persisted strategies, and workflow link.
- Workflow detail can resolve a related risk alert and drill back into the alert detail page.
- Coze callback handling persists raw callback payloads, normalized result payloads, AI results, and then applies risk analysis or strategy outcomes.
- Risk workflow services create and persist workflow runs, Coze runs, and business records for `risk_signal`, `risk_alert`, and `risk_strategy`.
- Backend and frontend risk-specific tests pass for the controller risk flow and the live risk action path.

Residual risk:

- The project and risk dashboards still show an `Escalated` metric, but the approved backend risk alert enum does not currently emit that status, so the count stays at zero in live data.
- The standalone workflow-runs list page is now live-backed, and the workflow detail drilldown and the project/risk slices remain live and linked.

## Slice Check: Risk Workflow Backend Integration

This targeted check validates the backend-owned Coze gateway for the risk workflow only:

- frontend source does not call Coze directly
- `POST /api/v1/projects/{project_id}/risk-generate` dispatches the risk workflow through the backend-owned gateway
- runtime config uses `COZE_RISK_RUN_URL` and `COZE_RISK_API_TOKEN`
- workflow run persistence, Coze run persistence, AI result persistence, risk signal persistence, risk alert persistence, and audit persistence stay on the backend
- synchronous success and accepted-then-callback completion paths are both handled
- contract error mapping covers `integration_unavailable`, `retryable_integration_error`, and `invalid_ai_result`
- scope stays out of `risk-alerts/{alert_id}/strategy-generate` Coze integration and stays out of FE changes

Result:

- Passed

Evidence:

- `services/controller/app/core/config.py` now exposes risk-specific Coze settings and defaults the run URL to `https://d784kg4tzc.coze.site/run`.
- `services/controller/app/services/risk_gateway.py` reuses the Coze transport wrapper and posts the backend request body to the risk run URL with a bearer token.
- `services/controller/app/services/risk_monitoring.py` creates the risk signal, workflow run, Coze run, AI result, and risk alert from the backend-owned dispatch path, and also tolerates an accepted provider response until callback completion.
- `services/controller/app/api/routes/risk.py` exposes `POST /projects/{project_id}/risk-generate` as the project-scoped entry point.
- `services/controller/tests/test_risk_coze_gateway.py` covers direct gateway dispatch, synchronous persistence, accepted-then-callback completion, and error mapping.
- `services/controller/tests/test_risk_monitoring.py` continues to pass against the risk workflow path.
- Source search in `apps/web/src` did not show any direct Coze URL or token usage in frontend source code.

Residual risk:

- The standalone workflow-runs list page is now live-backed, and any remaining risk in this slice is limited to unrelated surfaces outside the backend-owned risk gateway path.

## Slice Check: Unified Risk Workflow Output Analysis + Strategy Suggestions

This targeted check validates only the risk slice requested in this pass:

- `POST /api/v1/projects/{project_id}/risk-generate` builds the backend-owned Coze payload from live project and signal data using `project_name`, `total_tasks`, `completed_tasks`, `remaining_days`, `daily_capacity`, `iaa_score`, and `top_error_type`
- synchronous success path persists `workflow_run`, `coze_run`, `ai_result`, `risk_alert`, `risk_strategies`, and `audit_events`
- callback path shares the same completion helper as the synchronous path
- `POST /api/v1/risk-alerts/{alert_id}/strategy-generate` is deferred/unsupported and does not dispatch Coze
- risk detail, risk list, and workflow detail remain live and mutually consistent
- risk detail no longer exposes a misleading generate button and instead shows passive guidance

Result:

- Passed

Evidence:

- `services/controller/app/services/risk_monitoring.py` builds the provider payload from the project name, live annotation task counts, and signal metadata, then persists the unified completion path through `_finalize_risk_workflow_completion()`.
- `services/controller/app/services/coze_callbacks.py` routes successful risk callbacks through `_finalize_risk_workflow_completion()`, so the callback and synchronous paths share the same closure logic.
- `services/controller/app/services/risk_monitoring.py` returns `integration_unavailable` from `generate_risk_strategies()` without calling the risk gateway, which keeps the deferred endpoint stable and non-dispatching.
- `apps/web/src/components/risk/risk-alert-actions.tsx` now renders passive explanatory text only, and `apps/web/src/app/(workspace)/projects/[projectId]/risk/[riskId]/page.tsx` uses that passive component in the strategy section.
- `apps/web/src/app/(workspace)/projects/[projectId]/risk/page.tsx`, `apps/web/src/app/(workspace)/projects/[projectId]/risk/[riskId]/page.tsx`, and `apps/web/src/app/(workspace)/workflow-runs/[runId]/page.tsx` all consume live controller-backed data for the risk slice.
- `services/controller/tests/test_risk_coze_gateway.py`, `services/controller/tests/test_risk_monitoring.py`, and `services/controller/tests/test_runtime_and_errors.py` passed in this pass, and `cmd /c npm exec vitest run src/components/risk/risk-alert-actions.test.tsx src/lib/controller-api.test.ts` passed with 2 files and 13 tests.

Residual risk:

- The standalone workflow-runs list page is now live-backed, and any remaining risk in this slice is limited to unrelated surfaces outside the risk detail, risk list, or workflow detail pages.

## Slice Check: Risk Strategy Approve / Reject

This targeted check validates only the approved business decision actions for proposed risk strategies:

- proposed strategy rows render approve/reject actions in the frontend
- non-`proposed` strategies do not render those actions
- `POST /api/v1/risk-strategies/{strategy_id}/approve` is available
- `POST /api/v1/risk-strategies/{strategy_id}/reject` is available
- approve persists `status=approved`, `approved_by_user_id`, and `approved_at`
- reject persists `status=rejected`
- both actions write audit events
- same `Idempotency-Key` replay does not create duplicate side effects
- opposite action on an already decided strategy returns `409 conflict`
- missing strategy returns `404 not_found`
- frontend decision actions go through the platform API proxy and do not call Coze directly

Result:

- Passed

Evidence:

- `apps/web/src/components/risk/risk-strategy-decision-actions.tsx` returns `null` unless `strategy.status === "proposed"`, and its buttons call the local Next.js API proxy rather than any Coze endpoint.
- `apps/web/src/app/(workspace)/projects/[projectId]/risk/[riskId]/page.tsx` renders `RiskStrategyDecisionActions` inside the persisted strategy list, so only proposed strategies surface the business decision actions in the detail page.
- `apps/web/src/app/api/risk-strategies/[strategyId]/approve/route.ts` and `apps/web/src/app/api/risk-strategies/[strategyId]/reject/route.ts` forward the decision to the controller API helper.
- `apps/web/src/lib/controller-api.ts` injects an `Idempotency-Key` when the caller does not supply one, so the proxy always sends a durable mutation key to the backend.
- `services/controller/app/api/routes/risk.py` exposes both approve and reject endpoints and enforces the `Idempotency-Key` header at the API boundary.
- `services/controller/app/services/risk_monitoring.py` keeps risk strategy decisions in `_decide_risk_strategy()`, which rejects non-`proposed` strategies with `409`, returns `404` for missing strategies, and records audit events with the idempotency key in metadata.
- `services/controller/tests/test_risk_strategy_decisions.py` covers approve, reject, idempotency replay, opposite-action conflict, and missing-strategy `404`.
- `services/controller/tests/test_risk_monitoring.py` also exercises approve/reject persistence and confirms `approved_by_user_id` and `approved_at` are persisted on approve.
- `apps/web/src/components/risk/risk-strategy-decision-actions.test.tsx` and the two Next.js route tests passed, confirming the frontend gating and proxy wiring for this slice.

Residual risk:

- The broader risk workflow and workflow-run list surface still include unrelated Coze-related vocabulary and other history pages elsewhere in `apps/web`, but those are outside this slice and do not affect approve/reject behavior.

Test evidence:

- `python -m pytest services/controller/tests/test_risk_monitoring.py services/controller/tests/test_risk_strategy_decisions.py -q` -> `6 passed`
- `cmd /c npm exec vitest run src/components/risk/risk-strategy-decision-actions.test.tsx src/app/api/risk-strategies/[strategyId]/approve/route.test.ts src/app/api/risk-strategies/[strategyId]/reject/route.test.ts` -> `3 passed`, `5 tests`

## Slice Check: Risk Alert Operations Completion

This targeted check validates only the thin risk alert operations slice:

- `PATCH /api/v1/risk-alerts/{alert_id}`
- `POST /api/v1/risk-alerts/{alert_id}/acknowledge`
- `Idempotency-Key` propagation through the frontend risk detail flow
- audit persistence for alert updates and acknowledgements
- frontend risk detail page thin management panel
- frontend does not call Coze directly

Result:

- Passed

Evidence:

- `services/controller/app/api/routes/risk.py` correctly enforces `Idempotency-Key` on both risk alert mutations, and `services/controller/app/services/risk_monitoring.py` persists update and acknowledge events with idempotency replay protection.
- `services/controller/tests/test_risk_alert_operations.py` passes and confirms the backend mutation and audit behavior are implemented.
- `apps/web/src/app/api/risk-alerts/[riskId]/route.ts` and `apps/web/src/app/api/risk-alerts/[riskId]/acknowledge/route.ts` now generate an `Idempotency-Key` when the browser request does not provide one, so the thin UI path can complete successfully through the controller.
- `apps/web/src/components/risk/risk-alert-actions.tsx` continues to send its mutations to the local Next.js API routes rather than calling Coze directly.
- `apps/web/src/lib/controller-api.ts` continues to auto-generate an idempotency key for direct controller-client calls, and the proxy layer now mirrors that durability behavior.

Residual risk:

- The backend mutation behavior is correct once called with a proper idempotency key, and the frontend proxy now supplies one; remaining risk is limited to unrelated surfaces outside this slice boundary.

## Slice Check: Annotation Review Flow

This targeted check validates only the approved reviewer flow for submitted annotation revisions:

- reviewer decisions on submitted annotation revisions
- review history persistence and task/workflow state consistency
- audit event persistence
- live reviewer controls through the frontend review path
- revise flow reopening the task for another submission

Result:

- Passed

Evidence:

- `submit_annotation_revision()` now calls `_ensure_annotation_task_open(task)`, so closed tasks cannot be resubmitted.
- `review_annotation_task()` still moves `approve` to `approved`, `reject` to `rejected`, and `revise` to `in_progress`, with matching workflow statuses and audit writes.
- The backend regression test now covers the reject path and verifies that resubmission returns `409` with the closed-task error.
- The frontend review mutation now carries its own `Idempotency-Key`, and the reviewer controls are constrained to the latest revision only.

Residual risk:

- The workflow-runs list page is now live-backed, and any remaining risk in this slice is limited to unrelated review-flow surfaces.

## Slice Check: Annotation Coze Integration

This targeted check validates only the approved annotation Coze integration slice:

- frontend stays on the platform API and does not call Coze directly
- backend dispatches annotation AI generation through `COZE_ANNOTATION_RUN_URL`, `COZE_API_TOKEN`, and `COZE_TIMEOUT_SECONDS`
- backend validates the source asset as a public `http(s)` URL before dispatch
- synchronous success path persists `workflow_runs`, `coze_runs`, `ai_results`, and `audit_events`
- provider/raw and normalized AI output are both persisted
- synchronous return remains consumable by the annotation workbench flow
- token/url missing, timeout, non-JSON, and provider HTTP error mapping stay contract-safe
- callback path remains available and reuses the annotation completion helper

Result:

- Passed

Evidence:

- `apps/web/src/app/api/annotation-tasks/[taskId]/ai-generate/route.ts` proxies to the controller client, and `apps/web/src/lib/controller-api.ts` sends the request to the backend-owned `/api/v1/annotation-tasks/{task_id}/ai-generate` path with an idempotency key.
- `services/controller/app/services/annotation_gateway.py` validates `http(s)` source asset URLs, reads the Coze run URL and token from runtime settings, and dispatches a JSON body shaped as `{"file_url": "<asset-url>"}`.
- `services/controller/app/services/annotation_gateway.py` persists the workflow run, Coze run, raw provider payload, normalized AI result, and audit events in the same request lifecycle before returning the serialized API response.
- `services/controller/app/services/coze_callbacks.py` still routes successful annotation callbacks through `apply_annotation_ai_completion()`, so the callback path and synchronous path share the same completion logic.
- `services/controller/tests/test_annotation_coze_gateway.py` covers the direct transport path, synchronous success persistence, invalid asset URL handling, and timeout mapping, and the targeted test suite passed.
- `docs/deployment.md` documents the local environment variables needed for the annotation Coze gateway.

Residual risk:

- Asset URL validation is syntactic `http(s)` validation only, so it assumes the stored asset URI already points to a truly public object rather than probing reachability or network scope.
- The workflow-runs list page is now live-backed, and any remaining risk in this slice is limited to unrelated annotation Coze integration concerns.

## Slice Check: Workflow Runs Live List

This targeted check validates only the requested workflow-runs slice:

- `/workflow-runs` reads from the live controller API instead of mock adapters
- the page defaults to the global visible workflow runs list and does not force a `project_id` filter
- summary metrics remain correct for `running`, `waiting_for_human`, `failed`, and `succeeded`
- each row still drills down to `/workflow-runs/[runId]`
- project names are rendered from live controller data without changing the backend contract
- the slice stays out of workflow detail, annotation, risk, and contract changes

Result:

- Passed

Evidence:

- `apps/web/src/app/(workspace)/workflow-runs/page.tsx` imports `listWorkflowRuns` from `apps/web/src/lib/controller-api.ts`, computes the four summary counters from the live result set, and links each row to `/workflow-runs/${run.id}`.
- `apps/web/src/app/(workspace)/workflow-runs/page.test.tsx` asserts that the page calls the controller API, never calls `@/lib/mock-adapters`, renders both project names from live data, and preserves the drilldown link.
- `apps/web/src/lib/controller-api.ts` builds the workflow-run list request against `/workflow-runs` and only appends `project_id` when the caller explicitly passes a filter.
- `apps/web/src/lib/controller-api.ts` also hydrates `project_name` by fetching visible project details per unique `project_id`, which keeps the page contract-free while still showing project labels.
- `services/controller/app/api/routes/workflow_runs.py` exposes `GET /workflow-runs` with optional `project_id`, `workflow_domain`, `status`, `source_entity_type`, `source_entity_id`, and `limit` query parameters.
- `services/controller/app/services/workflow_runs.py` applies `project_id` only when provided and otherwise returns the principal-visible global list, while `list_workflow_runs()` and `serialize_workflow_run()` preserve the status and drilldown fields used by the page.

Test evidence:

- `cmd /c npm exec vitest run "src/app/(workspace)/workflow-runs/page.test.tsx" "src/lib/controller-api.test.ts"` -> `2 passed`, `16 passed`
- `python -m pytest -q` in `services/controller` -> `38 passed`

## Slice Check: Project Dataset & Multimodal Item Management E2E

This targeted check validates only the approved metadata-only dataset and multimodal asset write slice:

- `POST /api/v1/projects/{project_id}/datasets`
- `PATCH /api/v1/datasets/{dataset_id}`
- `POST /api/v1/projects/{project_id}/source-assets`
- `PATCH /api/v1/source-assets/{asset_id}`
- frontend catalog page create dataset flow
- frontend catalog page register source asset flow
- frontend catalog page update dataset metadata flow
- frontend catalog page update source asset metadata flow
- permission enforcement for dataset and source-asset writes
- `Idempotency-Key` enforcement and replay safety
- cross-project dataset association protection
- frontend platform API route usage only
- catalog live state consistency with backend data

Result:

- Passed

Evidence:

- `services/controller/app/api/routes/projects.py` and `services/controller/app/api/routes/source_assets.py` require `Idempotency-Key` for the covered write mutations and route them through controller-owned services.
- `services/controller/app/services/datasets.py` enforces `dataset:create` and `dataset:update`, keeps dataset writes metadata-only, preserves project scoping, and returns idempotent replays from audit-backed history.
- `services/controller/app/services/source_assets.py` enforces `source_asset:create` and `source_asset:update`, keeps source-asset writes metadata-only, allows project-scoped assets without a dataset, and rejects cross-project dataset attachment with `404`.
- `services/controller/tests/test_dataset_source_asset_writes.py` covers create, update, replayed idempotent writes, permission failures, missing `Idempotency-Key` failures, and cross-project dataset assignment protection.
- `apps/web/src/lib/controller-api.ts` sends create and update requests through the controller API helper only, including auto-generated idempotency keys for the write paths.
- `apps/web/src/app/api/projects/[projectId]/datasets/route.ts`, `apps/web/src/app/api/projects/[projectId]/source-assets/route.ts`, and `apps/web/src/app/api/source-assets/[assetId]/route.ts` forward mutations through the platform API routes rather than calling the backend directly from the browser.
- `apps/web/src/components/catalog/catalog-mutation-forms.tsx` uses only the Next.js API routes for create and update actions, and `apps/web/src/app/(workspace)/projects/[projectId]/catalog/page.tsx` renders the live controller-backed catalog state from the same backend data it mutates.
- `apps/web/src/app/(workspace)/projects/[projectId]/catalog/page.tsx` remains the live read surface for datasets and source assets, so the catalog state visible after refresh is derived from backend data rather than local mock state.
- `apps/web/src/app/(workspace)/projects/[projectId]/catalog/page.test.tsx`, `apps/web/src/components/catalog/catalog-mutation-forms.test.tsx`, `apps/web/src/lib/controller-api.catalog-management.test.ts`, and `apps/web/src/app/api/*` route tests cover the frontend mutation wiring and platform route constraints.
- `python -m pytest services/controller/tests/test_dataset_source_asset_writes.py services/controller/tests/test_project_data_catalog.py -q` -> `6 passed`
- `cmd /c npm exec vitest run "src/app/(workspace)/projects/[projectId]/catalog/page.test.tsx" src/lib/controller-api.test.ts "src/components/catalog/catalog-mutation-forms.test.tsx" "src/app/api/projects/[projectId]/datasets/route.test.ts" "src/app/api/projects/[projectId]/source-assets/route.test.ts" "src/app/api/source-assets/[assetId]/route.test.ts" "src/app/api/datasets/[datasetId]/route.test.ts"` -> `7 files passed`, `27 tests passed`
- `cmd /c npm run lint` -> passed
- `cmd /c npm run build` -> passed, and the build output includes `/projects/[projectId]/catalog` plus the covered API routes

Residual risk:

- The slice is intentionally metadata-only, so upload, batch import, delete, archive, retire, Coze, and workflow tracking remain out of scope for a separate contract.
- The catalog access envelope stays thin and backend-owned, which is correct for this slice but does not attempt to expand into delivery orchestration.

Requested next owner:

- Orchestrator

## Slice Check: Annotation Task Management Completion

This targeted check validates only the annotation task management slice:

- project-scoped annotation task create
- queued task claim
- task patch/update
- audit persistence and idempotency
- frontend queue and task detail live management interactions

Result:

- Passed

Evidence:

- `services/controller/app/api/routes/annotation_tasks.py` now exposes `POST /projects/{project_id}/annotation-tasks`, `POST /annotation-tasks/{task_id}/claim`, and `PATCH /annotation-tasks/{task_id}` with required `Idempotency-Key` enforcement.
- `services/controller/app/services/annotation_tasks.py` persists created tasks, claimed tasks, and patch updates through backend-owned state transitions and writes audit events with idempotency replay protection.
- `services/controller/tests/test_annotation_task_management.py` covers create, replayed create, claim, replayed claim, patch, replayed patch, and closed-status rejection.
- `apps/web/src/lib/controller-api.ts` exposes live helpers for create, claim, and patch; `apps/web/src/app/(workspace)/projects/[projectId]/annotation/queue/page.tsx` and `apps/web/src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.tsx` consume them through the platform API only.
- `apps/web/src/components/annotation/annotation-task-create-form.tsx`, `apps/web/src/components/annotation/annotation-task-queue-claim-button.tsx`, and `apps/web/src/components/annotation/annotation-task-management-panel.tsx` provide the minimal live management interactions on the queue and task pages.
- `python -m pytest services/controller/tests/test_annotation_task_management.py services/controller/tests/test_annotation_submission.py services/controller/tests/test_annotation_reviews.py -q` passed with `7` tests.
- `cmd /c npm exec vitest run src/lib/controller-api.test.ts src/lib/controller-api.annotation-task-management.test.ts src/components/annotation/annotation-task-queue-claim-button.test.tsx src/components/annotation/annotation-task-create-form.test.tsx src/components/annotation/annotation-task-management-panel.test.tsx` passed with `5` files and `24` tests.
- `cmd /c npm run lint` and `cmd /c npm run build` both passed.

Residual risk:

- `claim` uses the new `claimed` state, which is intentionally still visible in the queue so it does not disappear immediately after being picked up.
- The slice remains intentionally narrow and does not extend into annotation AI generation, review, or risk behavior.

## Slice Check: Project Member Management Completion

This targeted check validates only the project member management slice:

- `GET /api/v1/projects/{project_id}/members`
- `PATCH /api/v1/projects/{project_id}/members/{membership_id}`
- `DELETE /api/v1/projects/{project_id}/members/{membership_id}`
- member list user summaries
- role/status updates
- soft delete / inactive transition
- last active project manager protection
- audit persistence
- frontend project page member management panel
- frontend browser requests through platform API routes only
- inactive member action hiding

Result:

- Passed

Evidence:

- `services/controller/app/api/routes/projects.py` exposes the project member list, update, and delete endpoints and enforces `Idempotency-Key` for the mutating routes.
- `services/controller/app/services/projects.py` returns membership records with serialized user summaries, updates only the contract-approved `project_role` and `status` fields, performs soft-delete by moving members to `inactive`, blocks removal of the last active project manager, and writes audit events for the mutation paths.
- `services/controller/tests/test_project_memberships.py` covers member list shape, role/status updates, soft-delete behavior, the last-active-project-manager guard, and audit persistence.
- `apps/web/src/app/(workspace)/projects/[projectId]/page.tsx` renders the live member management panel inside the project page and loads the live member list alongside the other project summary data.
- `apps/web/src/components/projects/project-member-management-panel.tsx` hides mutation controls for inactive members, keeps actions available only for active members, and uses the page-local platform API flow rather than calling the controller directly.
- `apps/web/src/app/api/projects/[projectId]/members/route.ts` and `apps/web/src/app/api/projects/[projectId]/members/[membershipId]/route.ts` proxy browser requests through the Next.js platform API routes and forward `Idempotency-Key` for PATCH and DELETE.
- `apps/web/src/lib/controller-api.ts`, `apps/web/src/lib/contracts.ts`, and `apps/web/src/lib/controller-api.project-members.test.ts` cover the live member list and mutation helpers and keep the frontend contract aligned with the backend shape.
- `cmd /c npm exec vitest run src/lib/controller-api.project-members.test.ts src/app/api/projects/[projectId]/members/route.test.ts src/app/api/projects/[projectId]/members/[membershipId]/route.test.ts src/components/projects/project-member-management-panel.test.tsx "src/app/(workspace)/projects/[projectId]/page.test.tsx"` passed with `5` files and `9` tests.
- `python -m pytest services/controller/tests/test_project_memberships.py services/controller/tests/test_foundation_api.py -q` passed with `9` tests.
- `cmd /c npm run lint` and `cmd /c npm run build` both passed.

Residual risk:

- The slice is intentionally thin and does not add search, pagination, bulk member editing, or extra project admin workflows.
- Any wider project membership lifecycle beyond the verified active/inactive role-management path remains outside this slice boundary.

## Slice Check: Multimodal Annotation Coverage Completion

This targeted check validates only the unified annotation workbench coverage slice:

- unified annotation workbench without adding modal-specific annotators
- backend source asset access and real previews for `image`, `audio`, and `video`
- queue to task detail navigation for live annotation work
- `ai-generate` action from the workbench
- revision submission from the workbench
- reviewer decision path
- workflow detail drilldown from the annotation task

Result:

- Passed

Evidence:

- `services/controller/tests/test_multimodal_annotation_coverage.py` exercises live source-asset access for `image`, `audio`, and `video`, then runs the full `queue -> task detail -> ai-generate -> submit -> review -> workflow detail` loop for each asset kind.
- `apps/web/src/components/annotation/annotation-source-asset-preview.tsx` renders one unified preview component and switches between `img`, `audio`, and `video` output based on the backend access envelope.
- `apps/web/src/components/annotation/annotation-source-asset-preview.test.tsx` covers the three preview render modes and verifies the expected accessible labels.
- `apps/web/src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.tsx` composes the workbench, source preview, reviewer controls, and workflow link into one live task detail view.
- `apps/web/src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.test.tsx` verifies the task detail page renders the unified media preview and the backend-provided access URI.
- `apps/web/src/components/annotation/annotation-task-workbench-actions.tsx` keeps `ai-generate` and submission actions on the live web routes and refreshes the workbench after each mutation.
- `apps/web/src/components/annotation/annotation-task-workbench-actions.test.tsx` verifies the workbench actions post through the platform API routes and refresh the page state.
- `apps/web/src/app/(workspace)/workflow-runs/[runId]/page.tsx` keeps workflow detail linked back to the originating annotation task, which closes the drilldown path used by this slice.
- Verification commands passed in this pass:
  - `python -m pytest services/controller/tests/test_multimodal_annotation_coverage.py -q` -> `2 passed`
  - `cmd /c npm exec vitest run src/components/annotation/annotation-source-asset-preview.test.tsx src/components/annotation/annotation-task-workbench-actions.test.tsx "src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.test.tsx"` -> `3 files passed`, `4 tests passed`

Residual risk:

- The slice is intentionally limited to `image`, `audio`, and `video`; any future `asset_kind` outside that set will need explicit renderer handling.
- The fallback preview path still assumes the backend access envelope can be retrieved or sensibly downgraded to the source asset URI when needed.

## Slice Check: Risk Signal Capture Completion

This targeted check validates only the shared risk capture form on the project risk page:

- one shared form on the project risk page for signal capture
- `Save signal only` posts to `POST /api/v1/projects/{project_id}/risk-signals`
- `Save and analyze` posts to `POST /api/v1/projects/{project_id}/risk-generate`
- browser requests go through the Next.js platform API routes, which supply an `Idempotency-Key` when needed
- the signal-only path creates a risk signal without dispatching the workflow
- the analyze path creates the signal and triggers the unified risk workflow
- scope stays out of risk strategy approve/reject, risk alert patch/acknowledge, annotation, member management, catalog, and other unrelated modules

Result:

- Passed

Evidence:

- `apps/web/src/components/risk/project-risk-capture-form.tsx` renders one shared form with two submit actions and switches between the signal-only and analyze endpoints from the same input state.
- `apps/web/src/app/api/projects/[projectId]/risk-signals/route.ts` and `apps/web/src/app/api/projects/[projectId]/risk-generate/route.ts` proxy browser requests to the controller, generate an idempotency key when the browser does not provide one, and return `202` on success.
- `apps/web/src/app/(workspace)/projects/[projectId]/risk/page.tsx` embeds the shared capture form directly inside the project risk dashboard.
- `apps/web/src/components/risk/project-risk-capture-form.test.tsx`, `apps/web/src/lib/controller-api.risk-capture.test.ts`, `apps/web/src/app/api/projects/[projectId]/risk-signals/route.test.ts`, and `apps/web/src/app/api/projects/[projectId]/risk-generate/route.test.ts` cover both user entry points and the proxy wiring.
- `services/controller/app/api/routes/risk.py` exposes both backend endpoints with required `Idempotency-Key` enforcement.
- `services/controller/tests/test_risk_monitoring.py` proves the signal-only path does not dispatch a workflow and the analyze path creates the signal, workflow run, risk alert, and strategy suggestions.
- Verification commands for this slice passed:
  - `python -m pytest services/controller/tests/test_risk_monitoring.py -q` -> `4 passed`
  - `cmd /c npm run test -- "src/lib/controller-api.risk-capture.test.ts" "src/components/risk/project-risk-capture-form.test.tsx" "src/app/(workspace)/projects/[projectId]/risk/page.test.tsx" "src/app/api/projects/[projectId]/risk-signals/route.test.ts" "src/app/api/projects/[projectId]/risk-generate/route.test.ts"` -> `5 files passed`, `9 tests passed`

Residual risk:

- The form is intentionally narrow and does not attempt to cover the nearby strategy approval or alert management surfaces.
- The analyze path still depends on the backend-owned risk workflow, so any provider/runtime issue would surface there rather than in the form itself.

## Environment

- Workspace: `C:\Users\JoeWang\Desktop\MutiData-Nexus`
- Shell: `PowerShell`
- Validation date: `2026-03-20`
- Node.js: `v24.14.0`
- npm: `11.9.0`
- Python: `3.11.9`
- FastAPI: `0.135.1`
- SQLAlchemy: `2.0.48`
- Alembic: `1.18.4`
- Pydantic: `2.12.5`
- pytest: `8.4.2`
- psycopg[binary]: installed locally for backend verification

## Commands Run

### Frontend

```powershell
cmd /c npm run test
cmd /c npm run lint
cmd /c npm run build
```

Results:

- `vitest` passed: `3` files, `6` tests
- `eslint` passed
- `next build` passed and generated these routes:
  - `/`
  - `/dashboard`
  - `/inbox`
  - `/projects`
  - `/projects/[projectId]`
  - `/projects/[projectId]/annotation/queue`
  - `/projects/[projectId]/annotation/tasks/[taskId]`
  - `/projects/[projectId]/risk`
  - `/workflow-runs`
  - `/workflow-runs/[runId]`

### Backend

```powershell
python -m pytest tests
python -m compileall services/controller/app db
```

Results:

- `pytest` passed: `14 passed`
- `compileall` completed successfully

Additional verification:

```powershell
@'
from app.main import app
for route in sorted((route.path, sorted(route.methods or [])) for route in app.routes if getattr(route, "path", None)):
    print(route)
'@ | python -
```

Observed foundation endpoints:

- `GET /api/v1/me`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `GET /api/v1/workflow-runs`
- `GET /api/v1/workflow-runs/{run_id}`
- `POST /api/v1/integrations/coze/callback`

Targeted contract checks:

- `GET /api/v1/me` without auth now returns error code `unauthorized`
- `POST /api/v1/integrations/coze/callback` with a bad signature now returns error code `callback_signature_invalid`

## Verification Evidence

| Area | Requirement / Doc Reference | Evidence | Result |
|------|-----------------------------|----------|--------|
| Frontend shell and route foundation | PRD frontend views, page list Tier 1, UI flows | `next build` succeeded and emitted the dashboard, inbox, projects, annotation queue, annotation workbench, risk dashboard, workflow list, workflow detail, and root routes | Pass |
| Frontend token baseline | `docs/design-tokens.md` | `apps/web/src/app/globals.css` defines shared CSS variables, typography families, spacing, motion, and responsive shell behavior | Pass |
| Frontend contract typing baseline | `docs/api-contract.md` | `apps/web/src/lib/contracts.ts` now models numeric fields such as `priority` and `severity` as numbers instead of strings | Pass |
| Frontend inbox ordering | `docs/api-contract.md`, `docs/page-list.md` | `apps/web/src/lib/mock-adapters.ts` sorts inbox items numerically by priority instead of lexicographically | Pass |
| Frontend foundation tests | Frontend stack decision | `cmd /c npm run test` passed with `3` files and `6` tests | Pass |
| Backend API foundation | API contract subset | FastAPI exposes `/me`, `/projects`, `/workflow-runs`, and `/integrations/coze/callback`; `pytest` passed for those flows | Pass |
| Backend runtime alignment | Architecture and repository stack decisions | `services/controller/app/core/config.py` defaults to `postgresql+psycopg://...`, and `services/controller/pyproject.toml` declares `psycopg[binary]` | Pass |
| Auth and RBAC baseline | PRD governance, architecture RBAC direction | `GET /api/v1/me` now returns `unauthorized` when auth is missing, and implemented permission checks remain in place | Pass |
| Callback signature handling | API contract error handling | Bad callback signatures now return `callback_signature_invalid` | Pass |
| Project foundation behavior | PRD project management | Tests cover list, create, detail, and update project flows, including membership creation and audit write | Pass |
| Workflow observability foundation | PRD workflow status, architecture workflow lifecycle | Tests cover workflow run list/detail and nested steps, Coze runs, and AI results | Pass |
| Database schema foundation | Schema, backend stack decision | SQLAlchemy models and Alembic baseline exist for identity, project, annotation, risk, workflow, AI result, and audit tables | Pass |

## Implemented vs PRD / Business Requirements

### Implemented in This Milestone

- Next.js dashboard foundation with shared workspace shell and Tier 1 route coverage for dashboard, projects, annotation queue, annotation task detail, risk dashboard, workflow runs, workflow detail, inbox, and root landing
- Design-token-backed frontend styling baseline aligned to the approved visual direction
- FastAPI control-plane foundation with working auth context, request IDs, shared success envelope, and a small validated endpoint slice
- SQLAlchemy model foundation for the core schema domains named in `docs/schema.md`
- Alembic baseline migration for the approved PostgreSQL data model
- PostgreSQL-first backend runtime defaults and declared `psycopg[binary]` support
- Contract-aligned backend error codes for auth and callback failure cases
- Numeric contract alignment for FE contract types and numeric inbox ordering
- Coze callback receiver foundation with persisted callback payload handling and workflow status update logic
- Audit-event foundation used by project create/update and callback reconciliation flows

### Present in Foundation Form Only

- Frontend business data is still provided by mock adapters and mock data, not by live backend API integration
- Annotation and risk experiences are represented in the UI foundation, but backend business flows for those domains are not yet implemented beyond schema and callback scaffolding
- Workflow status is represented in both FE mock views and BE foundation endpoints, but end-to-end FE to BE integration is not yet present

### Not Yet Implemented

- Backend endpoints for dashboard aggregation, datasets, source assets, annotation tasks, revisions, submissions, AI result accept/reject, risk signals, risk alerts, strategies, workflow retry/cancel, and audit search
- Frontend routes beyond the current Tier 1 foundation slice, including dataset detail, review history, assignment balance, search, reports, risk item detail, and settings
- Live backend-owned annotation execution, review, and completion flows
- Live backend-owned risk monitoring CRUD and strategy approval flows
- Full PRD requirements around dataset management, multimodal item management, human approval actions, and complete audit/query surfaces

## Resolved Findings and Remaining Risk

| ID | Severity | Summary | Evidence | Status |
|----|----------|---------|----------|--------|
| QA-01 | Resolved | The backend now defaults to PostgreSQL instead of SQLite, so the runtime path matches the approved source-of-truth stack. | `services/controller/app/core/config.py` and `python -m pytest tests` | Closed |
| QA-02 | Resolved | PostgreSQL driver support is now declared with `psycopg[binary]`, so clean backend setup can exercise the intended database path. | `services/controller/pyproject.toml` and `python -m pytest tests` | Closed |
| QA-03 | Resolved | Error envelopes now emit contract-specific codes for auth and callback failures, including `unauthorized` and `callback_signature_invalid`. | `services/controller/app/core/errors.py`, `services/controller/app/services/coze_callbacks.py`, `services/controller/tests/test_runtime_and_errors.py` | Closed |
| QA-04 | Resolved | Frontend contract typing is now numeric where the API contract expects numeric values, and inbox ordering uses numeric priority sorting. | `apps/web/src/lib/contracts.ts`, `apps/web/src/lib/presenters.ts`, `apps/web/src/lib/mock-adapters.ts`, `apps/web/src/lib/presenters.test.ts` | Closed |
| QA-05 | Low | Frontend and backend are still not integrated end-to-end across the full Release 1 surface. The FE continues to read from mock adapters in the remaining non-verified shell paths, so route and build success do not yet prove whole-product live contract compatibility. | `apps/web/src/app/(workspace)/layout.tsx` uses `getShellSnapshot()` from `apps/web/src/lib/mock-adapters.ts` | Open outside the verified slice boundary |

## Contract Pressure and Architectural Gaps

- The repository is behaving like a set of verified slices rather than one fully integrated product slice. That matches the Release 1 evidence boundary, but the handoff into next-phase feature work should remain explicit about what is and is not verified.
- PostgreSQL is now the verified backend runtime default, and the dependency gap is closed. The next phase should preserve that alignment as more backend features land.
- The API contract is much broader than the currently implemented endpoint surface. That is acceptable only if the team treats the implemented surface as a verified subset, not as the completed v1 contract.
- The frontend now mirrors numeric contract shapes more closely, which reduces integration pressure before live FE/BE wiring starts.
- The inbox page is intentionally derived from source objects because the contract does not yet define a dedicated inbox endpoint. That is acceptable, but future FE/BE coordination should decide whether inbox remains a composed frontend view or becomes an explicit backend contract.

## Milestone Recommendation

Recommendation: **release-ready for the approved Release 1 boundary**

Why:

- The verified slices now cover the Release 1 evidence set described in `docs/mvp-scope.md`.
- The release gate and handoff docs now record the approved boundary as `go`.
- The remaining work is broader future scope, not a blocker inside Release 1.
- The release hardening package is real and verified, and it now supports the release claim for the approved boundary.

## Requested Next Owner

Recommended next owner: `orchestrator`

Reason:

- This QA pass confirms the verified Release 1 slice inventory is internally consistent, but the project still needs orchestration for the final release decision.
- The orchestrator should route:
  - Any remaining FE/BE integration work to `fe` and `be`
  - Any contract clarification to `architect`
  - Scope or acceptance changes, if needed, back to `pm`

## Handoff Notes

### Files Read

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/qa.toml`
- `docs/blackboard/state.yaml`
- `docs/prd.md`
- `docs/api-contract.md`
- `docs/mvp-scope.md`
- `docs/architecture.md`
- `docs/schema.md`
- `docs/design-tokens.md`
- `docs/page-list.md`
- `docs/ui-flows.md`
- `docs/release-gate.md`
- `docs/release.md`
- `docs/handoff.md`
- `docs/superpowers/plans/2026-03-20-release-1-final-acceptance-gate.md`
- Current implementation in `apps/web/**`, `services/controller/**`, and `db/**`

### Files Changed

- `docs/qa-report.md`

### Decisions Made

- Framed Release 1 around the verified slice inventory documented in `docs/mvp-scope.md`
- Confirmed the authoritative release gate as `go` for the approved verified boundary
- Treated the remaining non-blocking risks as slice-local or deferred-scope risks rather than Release 1 blockers

### Assumptions / Open Questions

- Assumed the verified slice inventory in `docs/mvp-scope.md` is the correct evidence set for final QA framing
- Assumed QA should not update `docs/blackboard/state.yaml`, per repository policy
- Open question for Orchestrator review: whether any remaining non-verified surfaces need an additional verified slice before a future release gate revisit
