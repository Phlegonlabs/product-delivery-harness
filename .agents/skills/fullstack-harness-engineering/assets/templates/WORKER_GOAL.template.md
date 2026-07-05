# Worker Goal: Mission <n> - <objective>

```text
/goal Complete Mission <n> (<objective>) only, using <contract paths> as frozen source of truth and the Mission <n> section of <runbook path> as the task list.
Worktree: <path>. Branch: <branch>. Resource isolation: <port / db / services>.
Write only: <mission write scope>. Do not edit shared harness docs, frozen contracts, or unrelated files.
Each iteration: choose one ready task, implement it, run its verifier, record evidence under <evidence dir>, and commit only verified work.
Do not pull, rebase, merge, push, or otherwise sync against <base branch>; the parent thread owns upstream sync, integration, and landing.
When the mission is done or blocked, write the report to <evidence dir>/REPORT.md and stop.
Guardrails: one task per iteration; stop after 3 no-progress iterations; do not retry the same failed approach more than twice; stop and ask if the write scope is insufficient, requirements conflict, verification cannot run, or a destructive action is needed.
```

## Report Contract

Write the final report to `<evidence dir>/REPORT.md`. The parent reads this file; do not edit shared harness docs.

```text
Mission:
Status: done | blocked | partial
Changed files:
Commands and exit codes:
Evidence paths:
Commits (hash + message):
Blockers:
Residual risk:
Notes for integration:
```

## Launch Checklist

- [ ] Worktree and branch exist and match the mission coordination table.
- [ ] Resource isolation (port / DB / services) matches the runbook.
- [ ] Contract files and this mission's runbook section are readable from the worktree.
- [ ] Evidence directory exists: `<evidence dir>`.
- [ ] Base branch and sync policy are recorded: workers never sync upstream.
