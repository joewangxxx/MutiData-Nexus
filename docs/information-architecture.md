# Information Architecture

Status: `review_pending`
Owner: `designer`
Last Updated: `2026-03-18`

This document defines the dashboard information architecture for MutiData-Nexus. It describes how annotators, project managers, and shared operational views move through one Next.js + React dashboard shell without feeling like separate products.

## IA Goals

- Make the platform feel like one operating system for project work, not two separate tools.
- Keep the project as the anchor object everywhere.
- Give annotators a fast queue-first path and project managers an exception-first path.
- Treat workflow execution status as a first-class view, not a hidden admin detail.
- Keep linked objects, evidence, and history visible wherever users work.

## Design Principles

- One shell, one language, one object model.
- Role-specific content, shared navigation patterns.
- Summary first, then drill-down, then audit trail.
- Every important state should have a visible status, owner, and next step.
- Cross-links should be explicit so users can move between project, task, risk, and workflow views without losing context.

## Global Shell

The app should use a single global shell with role-aware navigation and a persistent project context.

| Region | Purpose | Notes |
|--------|---------|-------|
| Top bar | Workspace switcher, project switcher, global search, notifications, user menu | Keep search and notifications persistent across all routes. |
| Left rail | Role-specific primary navigation | Shared destinations stay in stable positions so the shell feels consistent. |
| Main canvas | Active page content | This is where dashboards, workbenches, and detail pages live. |
| Right rail or drawer | Context, linked records, activity, and evidence | Use only when it adds context without overwhelming the main canvas. |

## Primary Information Hierarchy

The dashboard should read from broad context to specific action.

1. Workspace or organization
2. Project
3. Workstream, such as annotation or risk monitoring
4. Queue, dataset, task group, alert set, or workflow run
5. Individual task, risk item, annotation, or run step
6. Evidence, comments, history, and audit trail

This hierarchy keeps users oriented while still letting them move quickly into deep work.

## Core Object Model

| Object | Purpose | Typical Entry Points | Typical Next Step |
|--------|---------|----------------------|-------------------|
| Workspace | Top-level organizational context | Workspace switcher | Select a project or role view |
| Project | Container for work, risk, and ownership | Portfolio, project search, alerts | Open project overview or a child workstream |
| Dataset | Source collection for annotation work | Project overview, annotation pages | Open task batches or dataset detail |
| Annotation task | Assignable unit of annotation work | My Queue, project detail, inbox | Complete, save, submit, or route to review |
| Annotation result | Output of human or AI-assisted labeling | Task detail, review history | Compare versions, approve, or revise |
| Risk item | Actionable risk condition | Risk dashboard, inbox, project overview | Acknowledge, assign, escalate, or resolve |
| Workflow run | Status record for a process execution | Project activity, operations view, task detail | Inspect stage status, logs, and linked artifacts |
| Audit event | Immutable history entry | Reports, history, compliance views | Trace who changed what and when |
| Inbox item | One actionable notification or approval | Inbox, notifications drawer | Open the linked object and complete the smallest correct action |

## Route Families

The following route families give the frontend a clear page structure while staying implementation-agnostic.

| Route family | Purpose | Common pages |
|--------------|---------|--------------|
| Dashboard | Role landing and summary surfaces | Annotator home, project manager home |
| Projects | Portfolio browsing and project entry | Project list, project overview |
| Annotation | Work execution and review | Queue, workbench, dataset detail, review history |
| Risk | Project health and exception management | Risk dashboard, risk item detail, assignment balance |
| Workflow runs | Execution status inspection | Run list, run detail, stage timeline |
| Inbox | Cross-role action queue | Approvals, alerts, mentions, system outcomes |
| Search | Cross-object retrieval | Results by project, task, risk, run, report |
| Reports | Summary and export surfaces | Trend views, activity summaries, audit-oriented pages |

## Role-Specific Navigation

### Annotator Navigation

Annotators should see a task-centered navigation model.

- Home
- My Queue
- Projects
- Datasets
- Tasks
- Review History
- Inbox
- Help

### Project Manager Navigation

Project managers should see a portfolio and exception-centered navigation model.

- Portfolio Home
- Projects
- Risk Dashboard
- Annotation Health
- Assignments
- Workflow Runs
- Reports
- Inbox
- Settings

### Shared Navigation Rules

- `Projects` is always the anchor object and should never feel buried.
- `Inbox` is the shared action surface for approvals, alerts, mentions, and system outcomes.
- `Workflow Runs` should be visible to managers and operators, and available to annotators when run status affects their work.
- Search should work across projects, tasks, datasets, annotations, risks, workflow runs, and reports.
- Navigation labels should stay consistent even when the visible content is role-specific.

## Dashboard Surfaces

### Annotator Surfaces

- Today's queue
- Task progress
- Quality or review feedback
- Recent submissions
- Blockers and instructions
- Quick links to datasets and project context

### Project Manager Surfaces

- Portfolio health
- Project status cards
- Annotation throughput and backlog
- Risk trend summary
- High-priority alerts
- Team workload and assignment balance
- Recent decisions and escalations

### Shared Surfaces

- Global search results
- Inbox and notifications
- Activity timeline
- Audit trail excerpts
- Project-level summary cards
- Workflow execution status

## Project Workspace Structure

Every project should feel like a self-contained workspace with a predictable set of child views.

| Workspace area | What it contains | Why it matters |
|----------------|------------------|----------------|
| Overview | Project summary, key metrics, status, ownership, and recent activity | Gives users a quick read on the project before they drill down. |
| Annotation | Queue, workbench, dataset detail, review feedback, submission state | Lets annotators and managers track production work in one place. |
| Risk | Risk score, risk items, evidence, escalation history, follow-ups | Lets managers inspect project health without leaving the project context. |
| Workflow runs | Run list, step timeline, logs, and outcome state | Makes the execution layer visible and debuggable. |
| Activity | Comments, changes, and audit events | Preserves traceability and decision context. |

## Movement Between Surfaces

Users should rarely jump through unrelated screens. The IA should encourage direct transitions between linked objects.

- From a project, users can move into datasets, tasks, risk summaries, workflow runs, and recent activity.
- From a dataset, annotators can move into task batches, task detail, and annotation history.
- From a task, users can move into the underlying data item, prior annotations, linked risks, and workflow history.
- From a risk item, project managers can move into the affected project, the evidence trail, and the related annotation workstream.
- From a workflow run, users can move into the originating object, the stalled step, and the downstream audit trail.
- From any object, users should be able to open its parent context without losing their current place.

## Shared Versus Role-Specific Surfaces

### Shared Surfaces

These should be visible to both roles, with content tailored by permissions and context.

- Project overview
- Global search
- Inbox
- Activity history
- Reports and exports
- Notifications
- Object details with linked entities
- Workflow execution status

### Role-Specific Surfaces

These should feel distinct in emphasis, not in product identity.

- Annotator surfaces: queue, task execution, review history, annotation detail, dataset work.
- Project manager surfaces: portfolio view, project health, risk monitoring, assignment balancing, workflow status, progress reporting.
- Admin or operator surfaces, if added later, should live outside the main daily workflows and never dominate the primary nav.

## Workflow Status Views

Workflow status should be visible in three places:

1. The project overview, as a compact summary card.
2. The workflow runs page, as a searchable execution list.
3. The workflow run detail page, as a step-by-step inspection view.

Each status view should answer the same three questions:

- What is running?
- Where is it stuck or completed?
- What should happen next?

## Content Rules

- Summary cards should show the minimum decision-making set: status, owner, priority, and last update.
- Dense tables should use compact spacing but never sacrifice readability.
- Evidence panels should surface the smallest relevant slice first, with drill-down on demand.
- Empty states should always tell users what to do next, not only that data is missing.
- Error states should preserve context and keep the user one click away from recovery.

## UX Assumptions

- Users are comfortable starting from projects rather than a generic landing page.
- Annotators need low-friction, high-density task views with minimal navigation overhead.
- Project managers need quick exception scanning and the ability to jump from summary to detail without losing context.
- Shared search and linked-object navigation will reduce the need for duplicate status pages.
- The platform will support multiple projects per workspace, but project boundaries should remain clear.
- Role-based visibility is expected, but the product should still feel coherent if users switch roles or manage both workflows.
