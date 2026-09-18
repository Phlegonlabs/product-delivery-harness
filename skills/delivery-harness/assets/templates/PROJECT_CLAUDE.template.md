# Claude Code Project Instructions

@AGENTS.md

## Claude Code Runtime Boundary

- On each skill invocation, follow the shared document-sync and bounded-enhancement rules in `AGENTS.md`; keep runtime-specific instructions here. Preserve existing owner text when an authorized pointer correction is needed, and never copy one runtime's instructions over another's.

- Treat `AGENTS.md` as the shared repository governance imported above. Keep Claude Code-only instructions in this file.
- Use the Product Delivery Harness runtime adapter reference (Claude Code section) for Claude worker roles, model selection, native workflow orchestration, and Agent Teams behavior. Do not copy Codex or Pi launch mechanics into a Claude worker.

The rules below apply only when this Claude session is executing a managed Product Delivery Harness PLAN/RUN mission. Direct Claude Code work follows `AGENTS.md` and the user's request without creating Harness state or worker topology.

## Managed Harness Missions

- A Claude mission worker is one bounded writer. It never delegates, edits parent-owned PLAN/RUN state, integrates, pushes, or cleans up. Authorization for those actions remains with the Harness parent and does not transfer to the worker.
- Claude explorers, mission writers, and reviewers are parent-dispatched siblings. Each writer has explicit file ownership and a separate clean exact-base worktree.
- After serial integration, the parent starts fresh reviewers on the unified head, including the required read-only `code-security-review` sibling, and runs one broad final validation only after those reviewers pass.
- Harness 0.38 RUNs close locally. Only the parent may later archive candidate C, commit and reverify archive-only A, and—under separate action-time authorization—publish A through the checkout-external request/attempt/receipt protocol. No Claude worker receives that authority.
- Return the exact worktree, branch, head SHA, changed files, verifier evidence, and blocking state through the completion channel supplied by the Harness parent.
