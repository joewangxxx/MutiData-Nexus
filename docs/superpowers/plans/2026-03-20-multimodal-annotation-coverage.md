# Multimodal Annotation Coverage Completion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove Release 1 annotation coverage across image, audio, and video by adding a unified workbench media preview and validating the existing AI-generate, submit, review, and workflow drilldown loop for all three modalities.

**Architecture:** Keep the existing annotation queue, task detail, submission, review, and workflow detail contract unchanged. Extend the task-detail read composition to include source-asset access information for rendering, add a unified modality-aware preview component in the existing workbench, and strengthen backend plus frontend tests so the three modalities are verifiably covered without introducing modality-specific annotators.

**Tech Stack:** Next.js + React, FastAPI, SQLAlchemy, Vitest, Pytest

---

## Chunk 1: Backend Multimodal Coverage Proof

### Task 1: Expand backend seeded data for audio and video annotation tasks

**Files:**
- Modify: `services/controller/tests/conftest.py`
- Test: `services/controller/tests/test_annotation_submission.py`
- Test: `services/controller/tests/test_annotation_reviews.py`

- [ ] **Step 1: Write failing backend assertions for audio and video task coverage**

- [ ] **Step 2: Run targeted pytest to verify the new assertions fail**

Run: `python -m pytest services/controller/tests/test_annotation_submission.py services/controller/tests/test_annotation_reviews.py -q`
Expected: FAIL because the fixtures only provide image-based seeded coverage.

- [ ] **Step 3: Extend seeded test data with one audio asset/task and one video asset/task**

Implementation notes:
- Keep all new assets project-scoped under the existing seeded project.
- Use the existing annotation task model and current contract; do not introduce new fields.
- Preserve the current image fixtures.

- [ ] **Step 4: Add modality-agnostic backend tests for the existing annotation loop**

Coverage notes:
- AI generate can dispatch for image, audio, and video tasks.
- Submission can persist revisions for all three modalities.
- Review flow can operate on all three modalities without branching behavior.
- Source-asset access remains available for all three modalities.

- [ ] **Step 5: Re-run targeted backend tests**

Run: `python -m pytest services/controller/tests/test_annotation_submission.py services/controller/tests/test_annotation_reviews.py -q`
Expected: PASS

- [ ] **Step 6: Run wider backend regression for confidence**

Run: `python -m pytest services/controller/tests -q`
Expected: PASS

## Chunk 2: Frontend Unified Multimodal Preview

### Task 2: Add a modality-aware source preview to the existing annotation workbench

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/controller-api.ts`
- Create: `apps/web/src/components/annotation/annotation-source-asset-preview.tsx`
- Create: `apps/web/src/components/annotation/annotation-source-asset-preview.test.tsx`
- Modify: `apps/web/src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.tsx`
- Test: `apps/web/src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.test.tsx`

- [ ] **Step 1: Write failing frontend tests for image/audio/video preview rendering**

Coverage notes:
- Image task renders an image preview.
- Audio task renders an audio player.
- Video task renders a video player.
- Transcript and metadata remain visible where available.

- [ ] **Step 2: Run targeted vitest to verify the preview tests fail**

Run: `cmd /c npm exec vitest run src/components/annotation/annotation-source-asset-preview.test.tsx "src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.test.tsx"`
Expected: FAIL because no unified preview component exists yet.

- [ ] **Step 3: Extend the workbench data composition with source-asset access**

Implementation notes:
- Reuse the existing controller access endpoint and helper; do not add a new backend contract.
- Keep the browser unaware of controller credentials.

- [ ] **Step 4: Implement a unified modality-aware preview component**

Implementation notes:
- Render `<img>` for image.
- Render `<audio controls>` for audio.
- Render `<video controls>` for video.
- Reuse the same section card in the current workbench.
- Do not introduce a modality-specific editor or page split.

- [ ] **Step 5: Re-run targeted frontend tests**

Run: `cmd /c npm exec vitest run src/components/annotation/annotation-source-asset-preview.test.tsx "src/app/(workspace)/projects/[projectId]/annotation/tasks/[taskId]/page.test.tsx"`
Expected: PASS

- [ ] **Step 6: Run broader frontend regression**

Run: `cmd /c npm run test`
Expected: PASS

- [ ] **Step 7: Run lint and build**

Run: `cmd /c npm run lint`
Expected: PASS

Run: `cmd /c npm run build`
Expected: PASS

## Chunk 3: Slice QA

### Task 3: Validate multimodal annotation coverage as one slice

**Files:**
- Modify: `docs/qa-report.md`

- [ ] **Step 1: Verify the live workbench covers image, audio, and video**

Acceptance notes:
- Queue to task detail remains unchanged.
- Task detail shows the correct preview for each asset kind.
- AI-generate, submit, review, and workflow detail stay consistent across all three modalities.

- [ ] **Step 2: Confirm no scope drift**

Guardrails:
- No modality-specific annotator introduced.
- No contract drift.
- No risk-domain changes.

- [ ] **Step 3: Record QA result in `docs/qa-report.md`**

Expected result:
- Either `Passed` with residual risks, or findings ordered by severity.

