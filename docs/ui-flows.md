# UI Flows

Status: `review_pending`
Owner: `designer`
Last Updated: `2026-03-18`

This document describes the core dashboard flows for annotation, risk review, and workflow status inspection. The flows are written for the future Next.js + React dashboard and focus on user movement, state changes, and recovery paths.

## Shared Flow Rules

- Every flow should keep the user inside the current project unless they explicitly switch context.
- Every important action should show a clear success, failure, or pending state.
- Every long-running action should preserve the current screen state so the user does not lose context.
- Every flow should be recoverable through Inbox, history, or a parent list view.

## Flow 1: Annotation Workbench

### Entry Points

- My Queue
- Project overview
- Inbox item that links to a task
- Dataset detail

### Happy Path

1. The annotator opens a task from the queue.
2. The workbench loads the source item, task instructions, project context, and any linked history.
3. The annotator reviews AI suggestions, existing labels, and any quality notes.
4. The annotator edits the annotation, adds notes if needed, and saves a draft.
5. The annotator submits the task for review or completion.
6. The task leaves the active queue, and the next item becomes available from the queue or a follow-up view.

### Key UI States

- Loading skeleton while the task content is fetched.
- Draft state while changes are being edited or autosaved.
- Blocked state when required source data or instructions are missing.
- Review-needed state when a human approver must confirm the result.
- Completed state with a clear submission timestamp and outcome.

### Exception Paths

- If the task has conflicting instructions, the workbench should surface the conflict inline and provide a route to the project manager or inbox.
- If an AI suggestion is low confidence, the suggestion should be visually subdued and clearly marked as optional.
- If the user loses connection or the request fails, the draft should remain visible with retry and save-later messaging.

### Exit Paths

- Submit and move to the next task.
- Save and return to the queue.
- Escalate a blocker to the inbox or project manager.

## Flow 2: Risk Review

### Entry Points

- Project risk dashboard
- Project overview
- Inbox alert
- Assignment or workflow issue surfaced as a risk signal

### Happy Path

1. The project manager opens a project risk dashboard or a specific risk item.
2. The dashboard shows risk level, recent trend, owner, and related workstreams.
3. The manager opens a risk card to inspect evidence, comments, and linked annotation work.
4. The manager chooses the smallest correct action: acknowledge, assign, request more context, escalate, or resolve.
5. The decision is written back to the project history and visible in the activity timeline.
6. The risk item either clears, remains open with follow-up ownership, or escalates to a higher-severity path.

### Key UI States

- Healthy state when no active risks need attention.
- Watch state for items that are trending worse but are not yet critical.
- Active state for items that need a decision.
- Escalated state for critical blockers or repeated failures.
- Resolved state with an audit trail and resolution note.

### Exception Paths

- If the risk item is tied to an incomplete annotation task, the interface should show that dependency explicitly.
- If the manager lacks permission to close the item, the UI should explain the restriction and offer the correct handoff path.
- If the user dismisses a change with unsaved notes, the interface should confirm the discard.

### Exit Paths

- Update the risk item and return to the dashboard.
- Assign follow-up work and keep the item open.
- Escalate into Inbox for another role.

## Flow 3: Workflow Status Inspection

### Entry Points

- Project overview
- Workflow runs list
- Inbox alert for a failed or stalled run
- Annotation or risk detail when a workflow state needs inspection

### Happy Path

1. The user opens the workflow runs list for the current project or workspace.
2. The list shows run name, related object, current stage, owner, start time, and status.
3. The user filters or searches for the run they need.
4. The user opens run detail to inspect the stage timeline, timestamps, logs, artifacts, and linked objects.
5. The user confirms whether the run is healthy, waiting, blocked, failed, or complete.
6. The user either leaves the run as-is or takes a follow-up action such as reassigning, retrying, or opening the linked object.

### Key UI States

- Queued state before the workflow starts.
- Running state with a visible stage progress indicator.
- Paused or blocked state with reason text and owner information.
- Failed state with an explicit error summary and recovery action.
- Succeeded state with a clear completion summary and linked outputs.

### Exception Paths

- If the run is stalled, the detail page should make the last successful step obvious.
- If the run depends on a missing task or approval, the dependency should appear in the timeline.
- If the user navigates from a linked object into the run, the page should preserve the back path to that object.

### Exit Paths

- Return to the workflow list.
- Open the linked task, dataset, or risk item.
- Escalate the issue to Inbox when the run cannot be recovered locally.

## Cross-Flow Behaviors

- Status chips, icons, and colors should mean the same thing across annotation, risk, and workflow views.
- Any action that changes a state should also update the activity trail.
- The Inbox should always provide a path back to the originating object.
- Detail pages should never trap the user without a way back to a list, project, or parent workflow.

