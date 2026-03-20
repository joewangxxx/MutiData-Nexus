# Frontend Stack Decision

Status: `approved`
Owner: `orchestrator`
Last Updated: `2026-03-18`

## Decision

Use `Next.js` with `React` and `TypeScript` as the frontend application stack for the MutiData-Nexus dashboard.

## Selected Shape

- Framework: `Next.js` App Router
- UI runtime: `React`
- Language: `TypeScript`
- Styling direction: design-token-backed CSS variables with a utility-friendly styling layer in the app
- Routing model: file-system routes aligned to `docs/page-list.md`
- Testing baseline: component and route-level tests plus later end-to-end coverage

## Why This Stack

- It matches the repository constraint set by the project brief.
- It supports role-aware dashboards, dense data views, and route-based workspaces well.
- It gives FE a stable path for server-rendered shells and client-side interactive workbench screens.
- It maps cleanly to the existing information architecture, page list, and token system.

## Non-Goals for the First Build

- No direct frontend-to-Coze communication.
- No bespoke frontend state platform before core route and API consumption patterns are working.
- No design-system overbuild before the dashboard shell and workflow views exist.

## Notes for FE

- Consume `docs/design-tokens.md` as the visual source of truth.
- Treat `docs/api-contract.md` as read-only.
- Prefer shared layout primitives and route-aware shells over page-specific styling forks.
