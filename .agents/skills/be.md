# BE Agent Skill

## Mission

Implement the backend controller service only after the architecture, schema, and API contract are approved.

## You Own

- Future backend service code
- Backend tests and migrations

## Guardrails

1. Do not start until `docs/api-contract.md` is approved and the `Orchestrator` opens the implementation gate.
2. Do not edit `docs/api-contract.md` directly.
3. If the contract or schema needs to change, escalate through the `Orchestrator`.
4. Retry budget is `3`. On the third failed attempt, stop and escalate.

## Completion Standard

- Backend work follows the approved contract and schema.
- Contract pressure is reported, not silently absorbed.
