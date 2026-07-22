# Tasks: <feature or product slice>

Use this template as `docs/goal/tasks.md` only when `RUN.md` exists (see the Project Size Gate and File Budget in `SKILL.md`). It is a human-readable, non-canonical view of mission ("milestone") and task progress, regenerated from `RUN.md`'s canonical JSON whenever that state changes. It never replaces `RUN.md`: leases, worker bindings, active-wave state, authorization, landing, and deployment stay there.

The canonical source for every row here is `RUN.md`'s `mission_states`, `task_states`, and `graph_state` (for typed PLAN-v4 graphs). If this file and `RUN.md` ever disagree, `RUN.md` is right; regenerate this file from it.

## Mission (Milestone) And Task View

| Mission / task | Trace | Depends on | Phase | Worker gate | Integration gate | Evidence / commit |
|---|---|---|---|---|---|---|
| M1 | REQ-001 | none | queued | planned | planned | |
| M1/T01 | REQ-001 | none | queued | planned | n/a | |

Use mission phases `queued`, `ready`, `leased`, `worker_running`, `worker_passed`, `integrating`, and `integrated`; mission failure states are `blocked`, `worker_failed`, `integration_failed`, and `superseded`. Use task phases `queued`, `ready`, `running`, `worker_passed`, and `mission_recorded`; task failure states are `blocked`, `worker_failed`, and `superseded`. See `references/execution-state-model.md`'s "Canonical Mission Phases" and "Canonical Task Phases" for the full transition rules and required evidence per transition.

`worker_passed` does not satisfy downstream dependencies. A mission only unblocks dependents once it is `integrated` with an integration gate of `PASS`.
