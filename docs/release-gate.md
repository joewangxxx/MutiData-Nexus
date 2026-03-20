# Release Gate

Status: `go`
Owner: `general`
Last Updated: `2026-03-20`

This document is the authoritative release hardening gate for Release 1. It records the verified capability inventory, the release-facing evidence that supports GO, the items that may slip, and the conditions that would force Release 1 back to NO-GO.

## Current Verified Capabilities

These slices are verified and may be cited as release evidence:

- Project foundation behavior: project creation, project detail, project updates, member creation, and audit writes for project changes.
- Project member management completion: live member list, project-scoped role/status updates, soft-delete deactivation, idempotency enforcement, active-project-manager guardrails, and audit persistence.
- Project dataset and asset catalog surfaces: live datasets and source-assets catalog APIs, access envelopes, and project overview navigation.
- Project dataset and multimodal item management: project-scoped dataset create/update, optional dataset linkage for source assets, and audit-backed idempotent metadata mutations.
- AI-Assisted Annotation Submission: queue, task detail, AI generate action, callback persistence, revision submission, submitted-state transition, workflow detail drilldown, source asset read path, and audit writes.
- Annotation task management completion: live task create, claim, and patch paths with idempotency and audit behavior.
- Multimodal annotation coverage completion: unified workbench for image, audio, and video previews, plus queue-to-detail, ai-generate, submission, review, and workflow detail coverage.
- Annotation review flow: approve, reject, and revise actions on submitted revisions; task and workflow status transitions; closed-task resubmission guardrails; and audit persistence.
- Annotation Coze integration: backend-owned gateway, runtime-based Coze configuration, synchronous AI result persistence, callback reuse, and contract-safe error mapping.
- Risk signal capture completion: shared project risk capture form with signal-only and analyze actions, live controller-backed persistence, and explicit no-workflow path for the signal-only action.
- Project risk monitoring E2E: live project risk posture, risk alert detail, workflow detail linkage, risk signal persistence, risk alert persistence, and risk strategy persistence.
- Risk workflow backend integration: backend-triggered project-scoped dispatch, accepted-then-callback completion support, runtime-based Coze configuration, and contract-safe error mapping.
- Unified risk workflow output and strategy suggestions: risk analysis and strategy suggestions persist through one shared backend completion path.
- Risk strategy approve/reject: proposed-only decision actions, idempotent replay behavior, conflict handling, and audit persistence.
- Risk alert operations completion: patch and acknowledge actions, idempotency propagation, and audit persistence.
- Workflow runs live list: live-backed list, summary metrics, and drilldown links.
- Release hardening track: controller and web release health checks, Docker images, compose stack, smoke and rollback helpers, and observability notes.

## Release Hardening Artifacts

These release-facing artifacts are available and may be cited as release operations evidence:

- Controller health and readiness endpoints at `/api/v1/ops/healthz` and `/api/v1/ops/readyz`
- Web health and readiness endpoints at `/healthz` and `/readyz`
- Controller Docker image in `services/controller/Dockerfile`
- Web Docker image in `apps/web/Dockerfile`
- Release compose stack in `compose.release.yaml`
- Release smoke and rollback scripts in `ops/release`
- Release environment example in `ops/release/release.env.example`
- Observability guide in `docs/observability.md`

## Release 1 Blocking Gaps

No unresolved blocker remains inside the approved Release 1 boundary. The items below must stay out of scope for the Release 1 claim unless they are later verified explicitly:

- Any product area outside the verified slice inventory must remain out of the Release 1 claim.
- Any future scope increase must not be treated as Release 1 complete until it is verified explicitly.
- Release hardening evidence must continue to reflect the actual runtime package and must not drift away from the verified implementation.

## Allowed Deferrals

These items may be deferred beyond Release 1 without blocking the current gate:

- Broader organization hierarchy beyond project membership.
- Advanced analytics, executive reporting, and predictive scoring.
- Additional workflow families beyond annotation and risk monitoring.
- More configurable approval policies and workflow orchestration options.
- Large-scale enterprise governance features that are not needed for the pilot.
- Mobile-native and offline-first experiences.
- Deep external system integration beyond the core product boundary.
- Warehouse-style reporting or cross-project portfolio analysis.

## Deployment / Ops / Doc Gaps

The following items remain open, but they do not block the current Release 1 gate:

- No production CI/CD pipeline has been defined.
- No cloud-target-specific deployment manifest has been standardized.
- No paging or alert routing policy has been standardized.
- No centralized log aggregation or metrics backend has been wired in.
- Runtime setup guidance is still local-first rather than production-platform-specific.

## Release Decision Status

Decision: **GO**

Reason:

- Verified slices now cover every must-have gate listed in `docs/mvp-scope.md`.
- The release hardening package is verified, including a real Docker compose rehearsal and smoke pass.
- Release-facing docs can now speak about the same narrow Release 1 boundary without claiming unverified surfaces.
- Deferred or broader surfaces remain outside Release 1 rather than blocking it.

## Go / No-Go Checklist

Release remains GO only while all of the following stay true:

- Every Release 1 must-have gate in `docs/mvp-scope.md` is satisfied by verified slices.
- Dataset management and multimodal item management continue to count as complete at the Release 1 boundary.
- Live FE to BE integration remains proven across the approved Release 1 surface represented by the verified slices.
- Backend-owned state and workflow outcomes are consistent across the release surface.
- Deployment packaging exists for the target runtime.
- Rollout and rollback procedures are documented.
- Operational monitoring and alerting expectations are documented.
- Release-facing docs agree on the same release boundary and do not claim unverified capabilities.

Release remains NO-GO if any of the following are true:

- Any must-have gate remains unverified.
- Any critical workflow still depends on mock-only behavior outside a verified slice.
- Any deployment or rollback path is undefined.
- Any release-facing document overstates verified capability.

## Release Package Check

The current release package now satisfies the release-hardening minimums:

- Buildable backend and web container images exist.
- Controller and web release health checks exist.
- Release smoke and rollback helpers exist.
- The release compose stack ties the runtime pieces together for local release rehearsal.
- Observability guidance is documented for the release surface.

That package is now part of the positive Release 1 evidence set. It supports the release claim for the approved boundary, but it must not be used to overstate unverified future scope.

## Cross-References

- `docs/mvp-scope.md`
- `docs/qa-report.md`
- `docs/release.md`
- `docs/handoff.md`
- `docs/deployment.md`
- `docs/observability.md`
