# Claude Code Project Instructions

@AGENTS.md

## Claude Code Runtime Boundary

- Treat `AGENTS.md` as the shared repository governance imported above. Keep Claude Code-only instructions in this file.
- Use the Full-Stack Harness Claude Code adapter for Claude worker roles, model selection, Dynamic Workflow, and Agent Teams behavior. Do not copy Codex or Pi launch mechanics into a Claude worker.

The rules below apply only when this Claude session is executing a managed Full-Stack Harness PLAN/RUN mission. Direct Claude Code work follows `AGENTS.md` and the user's request without creating Harness state or worker topology.

## Managed Harness Missions

- A Claude mission worker is one bounded writer. It never delegates, edits parent-owned PLAN/RUN state, integrates, pushes, or cleans up. Authorization for those actions remains with the Harness parent and does not transfer to the worker.
- Claude explorers, mission writers, and reviewers are parent-dispatched siblings. Each writer has explicit file ownership and a separate clean exact-base worktree.
- After serial integration, the parent starts fresh reviewers on the unified head and runs one broad final validation only after those reviewers pass.
- Return the exact worktree, branch, head SHA, changed files, verifier evidence, and blocking state through the completion channel supplied by the Harness parent.
