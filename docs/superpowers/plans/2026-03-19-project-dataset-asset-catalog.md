# Project Dataset & Asset Catalog Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one live, project-scoped dataset and multimodal asset catalog slice that proves Release 1 dataset management and multimodal item management are real backend-owned product surfaces.

**Architecture:** Reuse the approved v1 contract without schema changes. FastAPI exposes dataset list, source-asset list, and source-asset access endpoints over existing `Dataset` and `SourceAsset` tables; Next.js adds one project-scoped catalog page and consumes only controller APIs.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, pytest, Next.js, React, Vitest

---

## Chunk 1: Backend Catalog APIs

### Task 1: Dataset and asset read APIs

**Files:**
- Modify: `services/controller/app/api/router.py`
- Modify: `services/controller/app/api/routes/projects.py`
- Modify: `services/controller/app/api/routes/source_assets.py`
- Create: `services/controller/app/services/datasets.py`
- Modify: `services/controller/app/services/source_assets.py`
- Test: `services/controller/tests/test_project_data_catalog.py`
- Test: `services/controller/tests/conftest.py`

- [ ] Add failing backend tests for `GET /projects/{project_id}/datasets`, `GET /projects/{project_id}/source-assets`, and `POST /source-assets/{asset_id}/access`.
- [ ] Run the new backend tests to confirm they fail for missing routes or behavior.
- [ ] Implement dataset serialization and project-scoped dataset listing with visibility checks.
- [ ] Implement project-scoped source-asset listing with `dataset_id` and `asset_kind` filters.
- [ ] Implement source-asset access response with a thin backend-owned access envelope built from existing asset metadata.
- [ ] Run the targeted backend tests to confirm they pass.

## Chunk 2: Frontend Catalog Page

### Task 2: Project dataset and asset catalog live page

**Files:**
- Modify: `apps/web/src/lib/contracts.ts`
- Modify: `apps/web/src/lib/controller-api.ts`
- Modify: `apps/web/src/lib/controller-api.test.ts`
- Create: `apps/web/src/app/(workspace)/projects/[projectId]/catalog/page.tsx`
- Create: `apps/web/src/app/(workspace)/projects/[projectId]/catalog/loading.tsx`
- Create: `apps/web/src/app/(workspace)/projects/[projectId]/catalog/error.tsx`
- Modify: `apps/web/src/app/(workspace)/projects/[projectId]/page.tsx`
- Test: `apps/web/src/app/(workspace)/projects/[projectId]/catalog/page.test.tsx`

- [ ] Add failing frontend tests for catalog data loading and rendering.
- [ ] Run the targeted frontend tests to confirm they fail.
- [ ] Extend controller client types and request helpers for datasets, source-assets, and access info.
- [ ] Build the live catalog page with project context, dataset summary cards, and asset rows grouped by modality.
- [ ] Add a project overview entry link into the catalog page without broadening unrelated pages.
- [ ] Run the targeted frontend tests to confirm they pass.

## Chunk 3: Slice Verification and Blackboard

### Task 3: QA verification and Orchestrator blackboard update

**Files:**
- Modify: `docs/qa-report.md`
- Modify: `docs/blackboard/state.yaml`

- [ ] Run backend targeted tests for the catalog slice.
- [ ] Run frontend targeted tests for the catalog slice.
- [ ] Run one broader backend regression command and one broader frontend build command.
- [ ] Update `docs/qa-report.md` with slice-specific evidence and conclusion.
- [ ] Update `docs/blackboard/state.yaml` only from the parent thread after QA passes.
