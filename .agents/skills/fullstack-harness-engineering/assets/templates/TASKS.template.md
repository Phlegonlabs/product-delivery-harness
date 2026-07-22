# Tasks: <feature or product slice>

Use this template as `docs/goal/tasks.md` only when `RUN.md` exists (see the Project Size Gate and File Budget in `SKILL.md`). It is a human-readable, non-canonical view of mission ("milestone") and task progress, regenerated from `RUN.md`'s canonical `mission_states`, `task_states`, and `graph_state` (for typed PLAN-v4 graphs) whenever that state changes — never a second source of truth. If this file and `RUN.md` ever disagree, `RUN.md` is right; regenerate this file from it, and never re-derive a phase, transition, or unblock rule here — cite `references/execution-state-model.md`'s "Canonical Mission Phases" and "Canonical Task Phases" instead of restating them, so this view can't silently drift out of sync with the rule it's displaying.

## Mission (Milestone) And Task View

| Mission / task | Trace | Depends on | Phase | Worker gate | Integration gate | Evidence / commit |
|---|---|---|---|---|---|---|
| M1 | REQ-001 | none | queued | planned | planned | |
| M1/T01 | REQ-001 | none | queued | planned | n/a | |

Phase values and the unblock rule are defined in `references/execution-state-model.md`'s "Canonical Mission Phases" and "Canonical Task Phases" — read the current rule there rather than assuming this file's last-regenerated snapshot of it.
