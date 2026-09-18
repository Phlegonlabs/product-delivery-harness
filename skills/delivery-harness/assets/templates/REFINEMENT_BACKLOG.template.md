# Optional Expanded Refinement Backlog: <app or product slice>

Keep refinement candidates in `RUN.md` by default. Use this standalone expansion only when the backlog becomes materially difficult to scan, and link it from `RUN.md`.

This template is for product/app improvement candidates discovered during an audit. It is not the execution task-decomposition protocol and must not be used to mint child task IDs; use `references/execution-task-decomposition.md` for that.

## Baseline Summary

```text
App state:
Routes / journeys checked:
Commands run:
Browser evidence:
Known blockers:
Unvalidated surfaces:
```

## Ranked Candidates

| ID | Lens | Finding | Evidence | Impact | Effort | Risk | Proposed verifier | Status |
|---|---|---|---|---|---|---|---|---|
| REF-001 | <UX/perf/a11y/etc> | <finding> | <path/metric> | high / med / low | S / M / L | low / med / high | <cmd/threshold> | proposed |

## Accepted Refinements

| ID | Mission | Write scope | Verifier | Before evidence | After evidence | Commit |
|---|---|---|---|---|---|---|
| REF-001 | M1 | <paths> | <cmd> | <path> | <path> | <hash> |

## Declined Or Deferred

For next-round delivery gaps, retain original PRD/TEST IDs, platform, failure and reproduction, exact SHA/build/environment, evidence paths, spent repair attempts, blocked dependents, smallest next action, unchanged acceptance condition, and fixture cleanup disposition. Record verified work separately. A deferred required failure is not PASS, does not satisfy a dependency, and never creates or launches a new task automatically.

| ID | Decision | Reason |
|---|---|---|
| <id> | declined / deferred | <reason> |
