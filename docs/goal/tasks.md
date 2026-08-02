# Tasks: System-first Harness orchestration

This is the non-canonical human view of the mission and task state in `RUN.md`.

## Mission (Milestone) And Task View

| Mission / task | Trace | Depends on | Phase | Worker gate | Integration gate | Evidence / commit |
|---|---|---|---|---|---|---|
| M1 Core contract | REQ-001/002/003/004/005 | none | queued | planned | planned | |
| M1/T01 System-first stage | REQ-001/005 | none | queued | planned | n/a | |
| M1/T02 Shared orchestration contract | REQ-002/003/004/005 | M1/T01 | queued | planned | n/a | |
| M2 Runtime selection | REQ-002/003/005 | none | queued | planned | planned | |
| M2/T01 Sequential parent worktree | REQ-002/005 | none | queued | planned | n/a | |
| M2/T02 Optional nested policy | REQ-003/005 | M2/T01 | queued | planned | n/a | |
| M3 Adapter and README alignment | REQ-001/003/004/005 | none | queued | planned | planned | |
| M3/T01 Adapter contracts | REQ-001/003/004/005 | none | queued | planned | n/a | |
| M3/T02 README alignment | REQ-001/003/004/005 | M3/T01 | queued | planned | n/a | |

Canonical phases and evidence live only in `docs/goal/RUN.md`.
