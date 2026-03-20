# Shared Agent Policy

Apply these rules before following any role-specific instructions:

1. Read `AGENTS.md`, `.codex/config.toml`, your `.codex/agents/<role>.toml`, and `docs/blackboard/state.yaml`.
2. Treat `docs/blackboard/state.yaml` as read-only unless you are the parent-thread `Orchestrator`.
3. Respect ownership boundaries. Do not edit another role's source-of-truth doc unless the `Orchestrator` explicitly reassigns ownership.
4. Do not implement product features during this scaffold phase unless the `Orchestrator` explicitly switches the repository into implementation mode.
5. Record assumptions, decisions, and blockers in the doc you own or in your handoff message.
6. If your work reveals a cross-role conflict, stop and escalate with evidence instead of making a silent change.
7. `fe` and `be` must never change `docs/api-contract.md` directly. They propose contract changes to the `Orchestrator`.
