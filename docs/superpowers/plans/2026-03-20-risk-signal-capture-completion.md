# Risk Signal Capture Completion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a thin live risk-input surface with two explicit actions: create a risk signal only, or create a risk signal and immediately trigger the unified risk workflow.

**Architecture:** Reuse the frozen risk contract. Backend must enforce the semantic split between `POST /projects/{project_id}/risk-signals` and `POST /projects/{project_id}/risk-generate`; frontend adds one shared form with two submit paths on the project risk page. No new workflow family, no new pages, no direct Coze calls from the browser.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js App Router, React, Vitest, pytest

---

## Chunk 1: Backend Signal-Only vs Signal-And-Analyze Semantics

### Task 1: Make `risk-signals` create only a signal

**Files:**
- Modify: `services/controller/app/services/risk_monitoring.py`
- Modify: `services/controller/tests/test_risk_monitoring.py`

- [ ] **Step 1: Write or update failing tests for signal-only creation**

Add assertions that `POST /api/v1/projects/{project_id}/risk-signals`:
- persists a `RiskSignal`
- does **not** create a workflow run or Coze run
- returns a signal-centric payload only

- [ ] **Step 2: Run the targeted backend test to verify it fails**

Run: `python -m pytest services/controller/tests/test_risk_monitoring.py -q`

- [ ] **Step 3: Implement the minimal backend change**

Update `create_risk_signal_with_workflow()` so it becomes signal-only creation with idempotent replay, audit persistence, and no workflow dispatch.

- [ ] **Step 4: Keep `risk-generate` on the existing workflow path**

Confirm `dispatch_project_risk_analysis()` still:
- creates the signal
- creates workflow/coze runs
- persists analysis and strategies

- [ ] **Step 5: Re-run targeted and full backend tests**

Run:
- `python -m pytest services/controller/tests/test_risk_monitoring.py -q`
- `python -m pytest services/controller/tests -q`

### Task 2: Keep backend responses stable for the frontend slice

**Files:**
- Modify: `services/controller/tests/test_risk_monitoring.py`
- Modify: `services/controller/tests/test_risk_coze_gateway.py` (only if needed)

- [ ] **Step 1: Add regression tests for the dual-entry behavior**

Cover:
- `risk-signals` returns signal-only success
- `risk-generate` returns signal + workflow/coze/ai/alert/strategies
- idempotency replay still works on both endpoints

- [ ] **Step 2: Run the targeted tests**

Run: `python -m pytest services/controller/tests/test_risk_monitoring.py services/controller/tests/test_risk_coze_gateway.py -q`

- [ ] **Step 3: Commit or hand off clean backend diff**

Summarize exact payload semantics for the FE owner.

---

## Chunk 2: Frontend Dual-Action Risk Capture Form

### Task 3: Add shared risk capture form with two actions

**Files:**
- Modify: `apps/web/src/app/(workspace)/projects/[projectId]/risk/page.tsx`
- Create or Modify: `apps/web/src/components/risk/project-risk-capture-form.tsx`
- Modify: `apps/web/src/lib/controller-api.ts`
- Modify: `apps/web/src/lib/contracts.ts` (only if existing types are insufficient)

- [ ] **Step 1: Write failing frontend tests for the new form**

Cover:
- one form renders required fields
- “仅保存 Signal” posts to the platform route for `risk-signals`
- “保存并分析” posts to the platform route for `risk-generate`
- success path refreshes the page

- [ ] **Step 2: Run the targeted FE tests to verify failure**

Run: `cmd /c npm exec vitest run <targeted test files>`

- [ ] **Step 3: Implement the thin shared form**

Requirements:
- one shared input form
- two submit buttons
- no new page family
- no browser-to-Coze calls

- [ ] **Step 4: Wire the risk page to show the live form plus existing live alerts/signals**

Keep the page thin and project-scoped.

- [ ] **Step 5: Re-run targeted FE tests**

Run the same Vitest command and confirm green.

### Task 4: Add Next.js platform routes for both actions

**Files:**
- Create or Modify: `apps/web/src/app/api/projects/[projectId]/risk-signals/route.ts`
- Create or Modify: `apps/web/src/app/api/projects/[projectId]/risk-generate/route.ts`
- Create tests beside those routes

- [ ] **Step 1: Write failing route tests**

Verify:
- each route forwards to the correct controller endpoint
- `Idempotency-Key` is generated when absent
- error envelopes are proxied correctly

- [ ] **Step 2: Run route tests to verify failure**

- [ ] **Step 3: Implement the minimal route handlers**

- [ ] **Step 4: Re-run route tests, lint, and build**

Run:
- `cmd /c npm exec vitest run <route test files>`
- `cmd /c npm run lint`
- `cmd /c npm run build`

---

## Chunk 3: QA Slice Validation

### Task 5: Slice QA for Risk Signal Capture Completion

**Files:**
- Modify: `docs/qa-report.md`

- [ ] **Step 1: Validate only this slice**

Scope:
- project risk page form
- `risk-signals` create path
- `risk-generate` path
- backend-owned workflow dispatch
- no direct Coze calls from FE

- [ ] **Step 2: Record findings or explicit none**

- [ ] **Step 3: Recommend pass/fail**

---

Plan complete and saved to `docs/superpowers/plans/2026-03-20-risk-signal-capture-completion.md`. Ready to execute.
