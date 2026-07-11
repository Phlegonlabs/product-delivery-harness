# Optional Goal Prompt

Normally keep the Goal prompt inside `docs/goal/RUN.md`. Use this standalone snippet only when the target workflow explicitly needs a copy-ready prompt without creating RUN.md.

```text
/goal Deliver <measurable outcome> using <complete PRD, canonical sources, and optional PLAN.md> as the source of truth. Before changing production code, map every must-have requirement to dependency-ordered frontend/backend/data missions, independently verifiable tasks, UI evidence when applicable, and final E2E gates; record the complete plan in PLAN.md and RUN.md and pass the Plan Readiness Gate. This Goal explicitly authorizes execution after readiness. Then work on one ready write task at a time, run its verifier, record evidence, and commit only verified work when allowed using the harness atomic commit convention. Use subagents only when applicable instructions allow delegation, keep writes sequential in one checkout by default, and use worktrees only for declared isolation or parallel-write needs. Stop on requirements conflicts, unavailable required tools, approval boundaries, or three consecutive no-progress iterations. Complete only when every required gate is PASS and every UNVALIDATED surface is explicitly accepted.
```

## Minimal Pre-Launch Check

- [ ] One objective and one stopping condition are explicit.
- [ ] Canonical sources are linked, not duplicated.
- [ ] Intent and execution authorization are recorded.
- [ ] Every must-have PRD trace is mapped across the complete mission plan.
- [ ] Frontend/backend ordering has a dependency rationale and first vertical slice.
- [ ] Plan Readiness Gate passes before implementation begins.
- [ ] File budget is `0`, `RUN.md`, or `PLAN.md + RUN.md` with optional real evidence.
- [ ] Required verifiers have literal pass signals.
- [ ] UI Evidence Gate is decided when user-facing UI changes.
- [ ] Destructive actions, external writes, push/PR, and cleanup have approval boundaries.
