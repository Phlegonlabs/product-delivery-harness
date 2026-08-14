# Claude Code Project Instructions

@AGENTS.md

## Claude Code Runtime Boundary

- Treat `AGENTS.md` as the shared repository governance imported above. Keep Claude Code-only instructions in this file.
- Use the Full-Stack Harness Claude Code adapter for Claude worker roles, model selection, Dynamic Workflow, and Agent Teams behavior. Do not copy Codex or Pi launch mechanics into a Claude worker.
- A Claude mission worker is one bounded writer. It does not delegate, edit parent-owned PLAN/RUN state, integrate, push, or clean up unless the exact Harness action is separately authorized.
- Claude explorers, mission writers, and reviewers are parent-dispatched siblings. Each writer has explicit file ownership and a separate clean exact-base worktree.
- After serial integration, the parent starts fresh reviewers on the unified head and runs one broad final validation only after those reviewers pass.
- Return the exact worktree, branch, head SHA, changed files, verifier evidence, and blocking state through the completion channel supplied by the Harness parent.
