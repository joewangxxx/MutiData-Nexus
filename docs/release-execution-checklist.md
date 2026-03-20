# Release Execution Checklist

Status: `spot_check_blocked_by_seed_data`
Owner: `orchestrator`
Last Updated: `2026-03-20`

This checklist is the parent-thread execution runbook for the approved Release 1 boundary. It turns the verified release gate into concrete release steps. It must be used together with [release-gate.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/release-gate.md), [deployment.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/deployment.md), [observability.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/observability.md), and [handoff.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/handoff.md).

## Current Execution Outcome

Current status: `HOLD`

Preflight, release build, and smoke validation were executed on `2026-03-20` and completed successfully for the current release workstation, but the formal business-surface spot check remains held behind release-runtime data readiness.

Resolved findings:

- Docker daemon access is now available on the current workstation.
- `docker compose -f compose.release.yaml config` succeeds when the release shell is populated with the required environment variables.
- A non-conflicting release port set has been selected for this workstation.
- The web runtime now propagates a server-only auth fallback through `CONTROLLER_API_AUTH_TOKEN`, so controller SSR fetches are no longer failing because the `Authorization` header is missing.

Next action:

- Hold the current release execution.
- Treat release-runtime seed/bootstrap data and residual mock-backed project navigation as the current blocking issues.
- Route the next blocker through the Orchestrator before rerunning Phase 5.
- Do not declare release execution successful until the affected pages pass a rerun of Phase 5 with real release-runtime data.

## Scope Guard

This runbook applies only to the approved Release 1 boundary.

Do not treat these items as part of this release unless they are separately verified later:

- Any product area outside the verified slice inventory
- Broader enterprise governance or analytics surfaces
- Additional workflow families beyond annotation and risk monitoring
- Production-platform-specific automation that is not already documented

## Entry Criteria

All of the following must be true before execution starts:

- [x] `docs/release-gate.md` is `go`
- [x] `docs/qa-report.md` recommends release-ready for the approved Release 1 boundary
- [x] [docs/blackboard/state.yaml](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/blackboard/state.yaml) has `implementation_complete: true`
- [x] [docs/blackboard/state.yaml](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/blackboard/state.yaml) has `release_ready: true`
- [x] Release compose rehearsal has passed locally
- [x] Smoke and rollback helpers exist and have been verified syntactically

## Execution Owners

- Orchestrator: owns release coordination and blackboard state
- General: owns release-facing docs and handoff alignment
- QA: owns release evidence confirmation and smoke verification sign-off
- FE / BE: respond only if a release issue is found during execution

## Phase 1: Freeze

- [ ] Freeze the approved Release 1 boundary and stop accepting scope changes
- [ ] Record the intended release timestamp and operator
- [x] Confirm the release environment variables are prepared from [release.env.example](C:/Users/JoeWang/Desktop/MutiData-Nexus/ops/release/release.env.example)
- [x] Confirm Docker daemon access on the target release workstation
- [ ] Confirm the release artifact versions or image tags to deploy

## Phase 2: Preflight

- [x] Re-read [release-gate.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/release-gate.md)
- [x] Re-read [deployment.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/deployment.md)
- [x] Re-read [observability.md](C:/Users/JoeWang/Desktop/MutiData-Nexus/docs/observability.md)
- [x] Confirm target ports, database host, and callback secret values
- [x] Confirm Coze tokens and workflow URLs are set only through environment variables
- [x] Confirm the target PostgreSQL database is reachable

## Phase 3: Release Build

- [x] Run `docker compose -f compose.release.yaml config`
- [x] Run `docker compose -f compose.release.yaml up -d --build`
- [x] Confirm `migrate` exits `0`
- [x] Confirm `postgres`, `controller`, and `web` reach `healthy`
- [x] Capture container status and timestamps for the release record

## Phase 4: Smoke Validation

- [x] Run [smoke.ps1](C:/Users/JoeWang/Desktop/MutiData-Nexus/ops/release/smoke.ps1)
- [x] Confirm controller `/api/v1/ops/healthz`
- [x] Confirm controller `/api/v1/ops/readyz`
- [x] Confirm web `/healthz`
- [x] Confirm web `/readyz`
- [x] Confirm no release-blocking error appears in container logs during the smoke window

## Phase 5: Business Surface Spot Check

Run only boundary checks that map to the verified Release 1 slices:

- [ ] Project page loads
- [ ] Project member management surface loads
- [x] Project catalog surface loads
- [ ] Annotation queue and task detail load
- [ ] Risk dashboard and risk detail load
- [ ] Workflow runs list and detail load

Do not widen this phase into a full regression suite. If any of these checks fail, stop and route the issue back through the Orchestrator.

## Phase 6: Go / Hold Decision

- [ ] If all checks pass, mark release execution as successful
- [x] If any blocking check fails, mark release execution as held
- [x] If held, capture the failure point, impacted surface, and first owner to engage

## Rollback Trigger

Rollback is required if any of the following happens after the release build step:

- A required health or readiness endpoint fails
- The smoke script fails
- A core approved Release 1 surface fails the spot check
- A release-facing document is found to overstate the deployed capability

## Rollback Steps

- [ ] Run [rollback.ps1](C:/Users/JoeWang/Desktop/MutiData-Nexus/ops/release/rollback.ps1)
- [ ] Confirm containers return to the last good state or are cleanly stopped
- [ ] Record the rollback reason and timestamp
- [ ] Re-open the issue through the Orchestrator before any retry

## Exit Criteria

Release execution is complete only when all of the following are true:

- [ ] Release build completed
- [ ] Smoke validation passed
- [ ] Boundary spot checks passed
- [ ] No rollback was required
- [ ] Blackboard state has been updated by the parent thread
- [ ] Release-facing docs still match the deployed boundary

## Evidence To Capture

- Compose config output
- Compose up output
- Container health snapshot
- Smoke script output
- Operator timestamp
- Any hold or rollback note if applicable

## Current Preflight Evidence

- `docker info --format "{{.ServerVersion}}"` returned `29.2.1`.
- `docker compose -f compose.release.yaml config` succeeded after loading the required release environment variables into the release shell.
- Release-process environment coverage is confirmed for callback secret, annotation workflow URL, annotation token, risk workflow URL, risk token, and timeout settings.
- The selected release workstation port set is `POSTGRES_PORT=55432`, `CONTROLLER_PORT=18000`, and `WEB_PORT=13000`.
- The selected release port set is free on the current workstation.
- The release stack provisions PostgreSQL inside Compose for this execution path, so the preflight database check is satisfied by the validated compose configuration and selected port plan.

## Current Build And Smoke Evidence

- `docker compose -f compose.release.yaml up -d --build` completed successfully.
- `docker compose -f compose.release.yaml ps -a` reported:
  - `migrate` exited `0`
  - `postgres` healthy on `55432`
  - `controller` healthy on `18000`
  - `web` healthy on `13000`
- `ops/release/smoke.ps1 -ControllerBaseUrl http://127.0.0.1:18000 -WebBaseUrl http://127.0.0.1:13000` passed.

## Current Spot Check Evidence

- `http://127.0.0.1:13000/projects/proj_atlas` returned `500`.
- `http://127.0.0.1:13000/projects/proj_atlas/catalog` returned `200`.
- `http://127.0.0.1:13000/projects/proj_atlas/annotation/queue` returned `200`, but release logs show server-side controller fetches failing with `401 unauthorized`.
- `http://127.0.0.1:13000/projects/proj_atlas/risk` returned `200`, but release logs show server-side controller fetches failing with `401 unauthorized`.
- `http://127.0.0.1:13000/workflow-runs` returned `500`.
- `mutidata-nexus-web-1` logs show `ControllerApiError: Authorization header is required.`
- `mutidata-nexus-controller-1` logs show `401 Unauthorized` for release-runtime requests such as:
  - `GET /api/v1/projects/proj_atlas`
  - `GET /api/v1/projects/proj_atlas/annotation-tasks`
  - `GET /api/v1/projects/proj_atlas/risk-alerts`
  - `GET /api/v1/projects/proj_atlas/members`
  - `GET /api/v1/workflow-runs`
- After the SSR auth fallback fix was applied and the release web container was rebuilt with `CONTROLLER_API_AUTH_TOKEN`, the web log changed from `Authorization header is required.` to `Authenticated user is not active.` for `/projects/proj_atlas`.
- The release PostgreSQL instance still reports `0` rows in `users`, `project_memberships`, and `projects`.
- `/projects` still renders from `apps/web/src/lib/mock-adapters.ts`, so release navigation can point at project IDs that do not exist in the release controller database.

## Blocking Release Issue

Release-runtime business pages are still not consistently usable, but the blocking cause has moved. The SSR auth-propagation bug is fixed; the current blockers are missing release-runtime seed/bootstrap data and residual mock-backed project navigation.

Impacted surfaces:

- Project overview
- Project member management surface
- Annotation queue and downstream task-detail path
- Risk dashboard and downstream risk-detail path
- Workflow runs list and downstream detail path

Requested next owners:

- `be`
- `fe`
