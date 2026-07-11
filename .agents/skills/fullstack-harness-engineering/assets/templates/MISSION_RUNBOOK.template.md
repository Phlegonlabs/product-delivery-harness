---
schema_version: 1
status: draft
intent: plan-only
plan_readiness: draft
execution_authorized: false
authorization_source: null
current_mission: null
current_task: null
last_verified: null
blocked: false
next_action: null
updated_at: null
---

# Run: <feature or product slice>

Use this template as `docs/goal/RUN.md`. Keep it as the single operational dashboard for the Goal prompt, checkpoint, tasks, verification, evidence, blockers, and closeout.

## Goal

```text
/goal Deliver <measurable outcome> using <PLAN.md and canonical source paths> as the source of truth and this RUN.md as the live checkpoint. First read the complete PRD and related sources, map every must-have trace to a dependency-ordered mission, task, verifier, and final E2E gate, and pass the Plan Readiness Gate before changing production code. After readiness, execute only because this Goal explicitly authorizes delivery. Work on one ready task at a time, verify it, record evidence here, and commit only verified work when allowed using the harness atomic commit convention. Stop on unresolved conflicts, unavailable required tools, approval boundaries, or three consecutive no-progress iterations. Complete only when every required gate is PASS and every UNVALIDATED surface is explicitly accepted.
```

## Checkpoint

```text
Objective:
Current mission:
Current task:
Last verified result:
Remaining:
Blocked / waiting approval:
Next action:
```

## Run Controls

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Execution authorized: yes | no
Authorization source: explicit prompt | active delivery Goal | approved ready plan | none
File budget: RUN.md | PLAN.md + RUN.md | optional evidence/
Run mode: sequential parent | single-checkout subagents | mission worktrees | app-managed worktrees
Worker budget: parent + up to 3 child workers
Parallel policy: multi-mission/program planning uses up to 3 independent read-only workers; writes stay sequential unless declared worktrees are isolated
Commit convention: Conventional Commit subject + Task / Trace / Verified trailers
Iteration cap:
No-progress cap: 3
Landing: left local | push/PR after approval
```

## Plan Readiness Gate

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Every in-scope trace is planned, deferred, or out of scope | draft / PASS / BLOCKED | |
| Complete must-have task and verifier coverage | draft / PASS / BLOCKED | |
| Dependency order is explicit and acyclic | draft / PASS / BLOCKED | |
| Frontend/backend/data boundaries are defined | draft / PASS / BLOCKED | |
| Shared foundations and migrations are ordered | draft / PASS / BLOCKED | |
| UI routes, states, breakpoints, and evidence are planned | draft / PASS / BLOCKED / n/a | |
| Mission write scopes and verifiers exist | draft / PASS / BLOCKED | |
| Blocking decisions and approvals are resolved | draft / PASS / BLOCKED | |
| Final E2E, regression, and release gates exist | draft / PASS / BLOCKED | |

Do not set `status: running` until all required rows pass and `execution_authorized: true`.

## Mission And Task Board

| Order | Mission / task | Trace | Work | Depends on | Verifier | Status | Evidence / commit |
|---|---|---|---|---|---|---|---|
| 1 | M1 / T1 | PRD-001 | <work> | none | <command/action> | queued | `<hash>` — `<subject>` — PASS |

Status values: `queued`, `ready`, `in_progress`, `verifying`, `passed`, `blocked`, `skipped`.

Commit each independently verified task with:

```text
<type>(<scope>): <imperative summary>

Task: M<n>/T<n>
Trace: <TRACE-ID>[, <TRACE-ID>]
Verified: <command or action> (<pass signal>)
```

## Verification Dashboard

| Gate | Required | Pass signal | Status | Evidence |
|---|---|---|---|---|
| Build / static health | yes / no | <literal signal> | planned | |
| Focused behavior | yes / no | <literal signal> | planned | |
| API / data / permissions | yes / no | <literal signal> | planned | |
| Primary journey | yes / no | <literal signal> | planned | |
| UI / responsive / states | yes / no | <literal signal> | planned | |
| Console / network | yes / no | <literal signal> | planned | |
| Accessibility | yes / no | <literal signal> | planned | |
| Visual comparison | yes / no | <literal signal> | planned | |
| Performance / release | yes / no | <literal signal> | planned | |

Gate values: `planned`, `PASS`, `FAIL`, `BLOCKED`, `UNVALIDATED`.

## UI Evidence

Include only when UI Evidence Gate is required or optional.

| Route / flow | Viewport | State | Browser result | Console / network | A11y | Visual evidence | Status |
|---|---|---|---|---|---|---|---|
| <route> | <size> | ready / loading / empty / error / disabled / permission / long-running | <result> | <result> | <result> | <path> | planned |

Store only real binary artifacts under `docs/goal/evidence/`. Do not create empty evidence folders.

## Attempt Log

| Time | Mission / task | Action | Verification | Progress | Result / next action |
|---|---|---|---|---|---|
| <time> | M1 / T1 | <action> | <command/path> | <before -> after> | <result> |

## Blockers And Approvals

| Item | Evidence | Required input / approval | Status |
|---|---|---|---|
| <item> | <path/result> | <need> | open / resolved |

## Skipped And Unvalidated

| Surface / gate | Reason | Risk | Accepted by | Status |
|---|---|---|---|---|
| <surface> | <reason> | <risk> | <name/date or pending> | UNVALIDATED |

## Closeout

```text
Final status:
Outcome:
Evidence:
Changed files:
Commits:
Residual risk:
Landing state:
```
