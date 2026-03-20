# Roles and Permissions

Status: `draft`  
Owner: `pm`  
Last Updated: `2026-03-18`

## Purpose

This document defines the product-level personas, approval boundaries, and business-state responsibilities for MutiData-Nexus. It clarifies who may create and manage projects, who may work on data items, who may approve outcomes, and which actions remain outside human control because the backend owns the authoritative state.

## State Ownership Rule

- The backend owns all business state, including projects, members, datasets, data items, annotation tasks, workflow runs, risk snapshots, risk events, and strategy suggestions.
- The frontend requests actions and displays state, but it is never the source of truth.
- Coze may generate workflow outputs and recommendations, but it cannot directly own or override product state.

## Personas

### Project Manager / Project Owner

Primary responsibility:

- Create projects, manage project membership, assign work, and oversee delivery and risk.

Allowed actions:

- Create and configure projects within their authority
- Add, remove, and update project members
- Create and organize datasets within a project
- Assign, reassign, pause, and reprioritize annotation work
- Review project risk state, strategy suggestions, and resolution progress
- Approve project-level workflow transitions and closure decisions
- Review workflow execution history for their projects

Not allowed:

- Change platform-wide access policy
- Change system-wide roles or permissions
- Override reviewer approval for task-level quality decisions
- Modify backend-owned business state outside the product workflow path

Approval boundaries:

- Approves project-level membership changes and project workflow transitions within their authority.
- Approves risk response direction for their project when a human sign-off is required.

### Annotator

Primary responsibility:

- Complete assigned multimodal annotation tasks accurately and on time.

Allowed actions:

- View assigned tasks and task details
- Open audio, image, or video data items assigned to them
- Review AI suggestions for their tasks
- Apply labels, notes, or quality feedback
- Submit completed work for review
- Flag unclear or blocked items

Not allowed:

- Create or manage projects
- Manage project members
- Change dataset ownership or structure
- Approve project-level decisions
- Approve final task outcomes when reviewer approval is required

Approval boundaries:

- Confirms their own submission, but does not finalize work that requires review.

### Reviewer / Approver

Primary responsibility:

- Validate submitted annotation work before it is finalized when human review is required.

Allowed actions:

- Review submitted annotation tasks
- Accept, reject, or request revision
- Add quality notes and decision comments
- Confirm task-level completion when review is required

Not allowed:

- Create projects or manage project members
- Reassign work unless explicitly delegated by the project manager
- Change project risk state or project-level closure decisions
- Modify platform access policy

Approval boundaries:

- Approves task-level quality outcomes only.
- Does not approve project membership, platform access, or business-state changes outside the annotation workflow.

### Platform Operator

Primary responsibility:

- Keep the platform accessible, governed, and operationally safe.

Allowed actions:

- Manage user access requests and platform role assignments
- Review operational health and workflow blockers
- Support incident triage and access audits
- Coordinate operational readiness and policy enforcement

Not allowed:

- Make product scope decisions on behalf of the PM
- Change project content, project membership, or task outcomes for business reasons
- Override approval rules for product workflows

Approval boundaries:

- Approves platform access and operational readiness.
- Does not approve project-level or task-level business outcomes.

## Permission Matrix

| Action | Annotator | Reviewer / Approver | Project Manager / Project Owner | Platform Operator |
|--------|-----------|---------------------|---------------------------------|------------------|
| Create project | No | No | Yes | No |
| Manage project members | No | No | Yes | No |
| Create or organize datasets | No | No | Yes | No |
| View assigned work | Yes | Yes | Yes | Limited |
| Edit assigned annotation | Yes | No | No | No |
| Review and approve submitted work | No | Yes | Yes, when delegated | No |
| Reassign work | No | No | Yes | No |
| Change project priority | No | No | Yes | No |
| View workflow execution history | Yes, own work | Yes | Yes | Yes, limited |
| Review risk snapshots and strategy suggestions | No | No | Yes | Yes, limited |
| Approve project-level workflow transitions | No | No | Yes | No |
| Manage access and roles | No | No | No | Yes |
| Override approval policy | No | No | No | No |
| View audit history | Yes, own work | Yes | Yes | Yes |

## Operational Responsibilities

- Annotators keep task execution accurate, timely, and well documented.
- Reviewers keep quality decisions consistent and timely.
- Project managers keep project membership, work queues, and risk visibility current.
- Platform operators keep access, readiness, and service health under control.

## Escalation Rules

- Annotators escalate ambiguous or blocked items to a reviewer or project manager.
- Project managers escalate unresolved risks, repeated quality failures, or scope conflicts through the governance path established by the orchestrator.
- Platform operators escalate access issues, policy exceptions, and operational incidents through the governance path established by the orchestrator.

## Approval Boundaries

- No role can silently bypass review if the workflow requires it.
- Human approval is required for final closure where the workflow marks a step as approvable.
- Permission changes are operational actions, not product-scope changes.
- Requests that change approval policy, role scope, or release policy must be treated as product decisions, not routine operational updates.
- Coze outputs are not approvals; they remain workflow results until the backend persists them into business state.
