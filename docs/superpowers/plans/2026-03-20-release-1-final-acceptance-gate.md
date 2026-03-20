# Release 1 Final Acceptance Gate Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile Release 1 scope, QA evidence, and release-facing documentation so the Orchestrator can make an evidence-based final GO/NO-GO decision without adding product code.

**Architecture:** This is a documentation and gate-control slice only. `pm` updates the Release 1 product boundary, `qa` updates the final acceptance view and real blockers, `general` aligns release-facing documents, and the parent thread alone updates `docs/blackboard/state.yaml`.

**Tech Stack:** Markdown docs, repository blackboard, agent handoff workflow

---

## Chunk 1: Product Boundary Reconciliation

### Task 1: PM reconciles must-have gates against verified slices

**Files:**
- Modify: `docs/mvp-scope.md`

- [ ] **Step 1: Re-read the current verified slice inventory**

Use:
- `docs/blackboard/state.yaml`
- `docs/qa-report.md`
- `docs/release-gate.md`

- [ ] **Step 2: Update must-have gate evidence**

For each Release 1 must-have gate, make it explicit whether it is:
- satisfied by verified slices
- partially satisfied
- still blocked

- [ ] **Step 3: Remove stale blockers**

Clear blockers that are no longer true after the latest verified slices, especially:
- workflow-runs live list
- project member management
- dataset and multimodal item management where already verified
- multimodal annotation coverage if already verified
- risk signal capture if already verified

- [ ] **Step 4: Keep only real remaining blockers**

Do not claim `GO` here; only tighten the boundary.

---

## Chunk 2: QA Final Acceptance View

### Task 2: QA updates final Release 1 acceptance framing

**Files:**
- Modify: `docs/qa-report.md`

- [ ] **Step 1: Reframe QA as final acceptance evidence**

Summarize:
- verified slices that count toward Release 1
- residual non-blocking risks
- true blocking items, if any

- [ ] **Step 2: Remove stale blocker language**

Do not keep old “not yet implemented” statements that are already disproven by later verified slices.

- [ ] **Step 3: Record a final recommendation**

Recommendation must be one of:
- release-ready
- not release-ready
- release-ready pending specific external validation

---

## Chunk 3: Release-Facing Document Alignment

### Task 3: General aligns release docs to the same decision boundary

**Files:**
- Modify: `docs/release-gate.md`
- Modify: `docs/release.md`
- Modify: `docs/handoff.md`
- Optionally modify: `README.md` if release summary is stale

- [ ] **Step 1: Update verified capability inventory**

Make sure release-facing docs cite the same verified slices as PM and QA.

- [ ] **Step 2: Update blocking gaps**

Keep only real blockers. Remove outdated ones.

- [ ] **Step 3: Keep GO/NO-GO wording aligned**

Every release-facing document must tell the same truth.

---

## Chunk 4: Orchestrator Final Decision

### Task 4: Parent thread updates the blackboard

**Files:**
- Modify: `docs/blackboard/state.yaml`

- [ ] **Step 1: Review pm, qa, and general handoffs**

- [ ] **Step 2: Decide final gate outcome**

Update only if supported by evidence:
- `workflow.phase`
- `workflow.status`
- `gates.implementation_complete`
- `gates.release_ready`
- relevant agent/document statuses

- [ ] **Step 3: Record the reason in workflow notes**

State clearly whether Release 1 is:
- GO
- NO-GO
- GO pending external validation

---

Plan complete and saved to `docs/superpowers/plans/2026-03-20-release-1-final-acceptance-gate.md`. Ready to execute.
