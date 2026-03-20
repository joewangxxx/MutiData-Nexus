# Page List

Status: `review_pending`
Owner: `designer`
Last Updated: `2026-03-18`

This page list turns the information architecture into a concrete dashboard surface map. Route patterns are expressed in a Next.js-friendly style for future frontend planning, but the list remains implementation-agnostic.

## Page Families

| Family | Purpose |
|--------|---------|
| Dashboard | Role landing and summary surfaces |
| Projects | Portfolio browsing and project entry |
| Annotation | Queue, workbench, dataset, and review views |
| Risk | Project health and risk investigation |
| Workflow runs | Execution status inspection and debugging |
| Inbox | Shared approvals, alerts, and action items |
| Search | Cross-object lookup and filtered results |
| Reports | Trend summaries and exports |

## Core Pages

| Route pattern | Page | Primary user | Purpose | Key regions |
|---------------|------|--------------|---------|-------------|
| `/dashboard` | Role dashboard | Annotator, project manager | Landing view tailored to the current role | Summary cards, priority items, recent activity, shortcuts |
| `/projects` | Project list / portfolio | Both | Browse, filter, and switch projects | Portfolio cards, filters, search, status counts |
| `/projects/[projectId]` | Project overview | Both | Shared home for a specific project | Project summary, workstream cards, activity, linked objects |
| `/projects/[projectId]/annotation/queue` | My Queue | Annotator | Show prioritized annotation tasks | Task list, filters, urgency, blockers, due dates |
| `/projects/[projectId]/annotation/tasks/[taskId]` | Annotation workbench | Annotator | Execute, review, and submit a single item | Source viewer, instructions, label editor, AI suggestions, notes, submit controls |
| `/projects/[projectId]/annotation/datasets/[datasetId]` | Dataset detail | Annotator, project manager | Show source coverage and task batches | Dataset summary, batches, progress, quality signals |
| `/projects/[projectId]/annotation/review-history` | Review history | Annotator, reviewer | Inspect past submissions and feedback | Timeline, outcome filters, comparison views |
| `/projects/[projectId]/risk` | Project risk dashboard | Project manager | Read project health and current risks | Health score, risk trends, risk cards, owner balance, alerts |
| `/projects/[projectId]/risk/[riskId]` | Risk item detail | Project manager | Investigate a specific risk or blocker | Evidence, timeline, linked work, decision actions, comments |
| `/projects/[projectId]/assignments` | Assignment balance | Project manager | See workload and reassign work | Workload charts, assignee table, bottleneck markers |
| `/workflow-runs` | Workflow run list | Project manager, operator, annotator when relevant | Search all workflow executions | Filters, status table, run summaries, failure counts |
| `/workflow-runs/[runId]` | Workflow run detail | Project manager, operator | Inspect a run step by step | Run summary, stage timeline, logs, artifacts, linked objects |
| `/inbox` | Inbox | Both | Handle approvals, alerts, mentions, and system outcomes | Action list, triage filters, linked object preview |
| `/search` | Global search results | Both | Search projects, tasks, datasets, risks, runs, and reports | Query summary, result groups, filters, saved searches |
| `/reports` | Reports | Project manager, operator | View summaries and export-ready reporting | Trend cards, tables, charts, export actions |
| `/settings` | Settings | Project manager, operator | Manage personal or project preferences | Role-specific settings, notifications, preferences |

## Shared Page Behavior

- Every page should show the current project context when a project is selected.
- Every detail page should expose a clear back path to the parent list or workspace.
- Every object page should surface related items rather than forcing a separate search.
- Every page should preserve filters, sort order, and selected tabs when moving between list and detail views.

## Page Priority

### Tier 1

These pages are essential for the MVP dashboard experience.

- `/dashboard`
- `/projects`
- `/projects/[projectId]`
- `/projects/[projectId]/annotation/queue`
- `/projects/[projectId]/annotation/tasks/[taskId]`
- `/projects/[projectId]/risk`
- `/workflow-runs`
- `/workflow-runs/[runId]`
- `/inbox`

### Tier 2

These pages are highly useful and should follow closely after the core experience.

- `/projects/[projectId]/annotation/datasets/[datasetId]`
- `/projects/[projectId]/annotation/review-history`
- `/projects/[projectId]/risk/[riskId]`
- `/projects/[projectId]/assignments`
- `/search`
- `/reports`

### Tier 3

These pages are useful for broader operations and polish, but can follow after the core flows are stable.

- `/settings`

## Empty and State Screens

The product should also define reusable state screens, even when they are not full pages.

- Empty project state
- Empty queue state
- No risk items state
- No workflow runs found state
- Permission denied state
- Loading skeleton state
- Error and retry state

These states should use the same typography, spacing, and action hierarchy as the rest of the dashboard.

