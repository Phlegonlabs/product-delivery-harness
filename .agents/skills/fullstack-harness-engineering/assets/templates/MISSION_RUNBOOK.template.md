# Mission Runbook: <feature or product slice>

## Resume Checkpoint

```text
Current mission:
Current task:
Last verified evidence:
Remaining:
Blocked:
Next action:
```

## Run Mode And Caps

```text
Run mode: sequential | parent-orchestrated workers | Codex-managed worktrees
Max parallel workers:
Iteration cap:
No-progress cap:
Failed-mission cap:
Session cap:
Fallback if subagents/worktrees unavailable:
```

## Mission Coordination

| Mission | Depends on | Worker/thread | Worktree | Branch | Resource isolation | Write scope | Verifier | Evidence | Commit | Integration result | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M1 | none | <id/name> | <path> | <branch> | <port/db/services> | <paths> | <cmd> | <path> | <hash> | pending | planned |

## Mission <n>: <objective>

### Read Scope

- <contract paths>

### Write Scope

- <allowed paths>

### Tasks

| Task | Trace | Work | Verifier | Status | Evidence | Commit |
|---|---|---|---|---|---|---|
| T1 | PRD-001 | <work> | <cmd> | planned | | |

### Acceptance

| Gate | Trace | Pass signal | Status | Evidence |
|---|---|---|---|---|
| Task verifier | TEST-001 | <literal pass signal> | planned | |
| UI Evidence Gate | UI-001 or `N/A - UI Evidence Gate not triggered` | required / optional / `N/A - UI Evidence Gate not triggered` | planned | |
| Platform gate | <AUTH/TENANT/SEO/etc or n/a> | <literal pass signal or n/a> | planned | |

### Attempt Log

| Time | Task | Approach | Verification / evidence | Progress (prev -> now) | Result | Next action |
|---|---|---|---|---|---|---|
| <time> | <task> | <approach> | <cmd/path> | <metric> | <result> | <next> |

## Integration Acceptance

| Gate | Pass signal | Status | Evidence |
|---|---|---|---|
| Mission verifier rerun after merge | <cmd exits 0> | planned | |
| E2E journey | <journey passes> | planned | |
| Final git status / diff review | <clean or expected changes only> | planned | |
| Evidence paths exist | <all required files exist> | planned | |
| Release impact | <recorded or n/a> | planned | |
