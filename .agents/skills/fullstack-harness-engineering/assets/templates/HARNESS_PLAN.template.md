# Plan: <feature or product slice>

Use this template as `docs/goal/PLAN.md` only for long, multi-mission, high-risk, or handoff-heavy work. Omit sections that do not apply.

## Objective

<One measurable outcome and stopping condition.>

## Source Map

| Source | Path / URL | Status | Role / notes |
|---|---|---|---|
| Product requirements | <path> | draft / frozen / missing / n/a | <notes> |
| Architecture / API / data | <path> | draft / frozen / missing / n/a | <notes> |
| Wireframe / flow | <path> | draft / frozen / missing / n/a | <notes> |
| Design system / page UI | <path or URL> | draft / frozen / missing / n/a | <notes> |
| Existing app baseline | <path or URL> | captured / missing / n/a | <notes> |

## Delivery Context

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Execution authorized: yes | no
Authorization source: explicit prompt | active delivery Goal | approved ready plan | none
Product archetype:
Existing app state:
Audience / primary journey:
Critical surfaces:
Release target:
UI Evidence Gate: required | optional | n/a
Orchestration: sequential parent | single-checkout subagents | mission worktrees | app-managed worktrees
```

## Scope

### Must Have

- `<TRACE-ID>` <requirement>

### Should / Could / Deferred

- `<TRACE-ID>` <requirement> — planned / deferred with rationale

### Non-Goals

- <explicitly out of scope>

### Assumptions And Open Decisions

- <assumption or decision>

## Contract Freeze

| Surface | Canonical source | Status | Decision / gap |
|---|---|---|---|
| Product behavior | <path/section> | frozen / draft / missing | <decision> |
| Architecture / data / API | <path/section> | frozen / draft / missing / n/a | <decision> |
| Identity / permissions | <path/section> | frozen / draft / missing / n/a | <decision> |
| UI flow and states | <path/section> | frozen / draft / missing / n/a | <decision> |
| Visual design | <path/section> | frozen / draft / missing / n/a | <decision> |
| Verification | RUN.md | ready / partial | <decision> |

## Traceability

| Trace | Requirement | Mission / task | Pass signal |
|---|---|---|---|
| PRD-001 | <requirement> | M1 / T1 | <literal signal> |

## Accepted Input Deltas

| Delta | Source | Change | Affected traces / surfaces | Status |
|---|---|---|---|---|
| DELTA-001 | <source> | <change> | <traces/routes/components> | accepted / blocked |

## UI Surface Matrix

Include only when UI Evidence Gate is required or optional.

| Route / screen | Source | Breakpoints | Required states | Evidence |
|---|---|---|---|---|
| <route> | <source> | <sizes> | ready/loading/empty/error/... | <screenshot/trace/test> |

## Delivery Dependency Strategy

```text
Shared foundations:
Backend prerequisites:
Frontend prerequisites:
Mocked / contract-first work allowed:
First end-to-end vertical slice:
Serialized surfaces:
Chosen order and rationale:
```

Use dependency evidence rather than a generic backend-first or frontend-first rule. Freeze shared contracts first, implement the minimum prerequisite path, validate one vertical slice, then scale the remaining missions.

## Mission Map

| Order | Mission | Objective | Traces | Depends on | Write scope | Exit verifier | Status |
|---|---|---|---|---|---|---|---|
| 1 | M1 | <objective> | <trace IDs> | none | <paths> | <command/action> | queued |

## Plan Readiness Gate

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Every in-scope trace is planned, deferred, or out of scope | draft / PASS / BLOCKED | <note> |
| Every must-have trace maps to task and verifier | draft / PASS / BLOCKED | <note> |
| Mission dependency graph is explicit and acyclic | draft / PASS / BLOCKED | <note> |
| Frontend/backend/data integration points are defined | draft / PASS / BLOCKED | <note> |
| Shared foundations and migrations are ordered | draft / PASS / BLOCKED | <note> |
| UI routes, breakpoints, states, and evidence are planned | draft / PASS / BLOCKED / n/a | <note> |
| Write scopes and deterministic verifiers exist | draft / PASS / BLOCKED | <note> |
| Blocking decisions and approvals are resolved | draft / PASS / BLOCKED | <note> |
| Final E2E, regression, and release gates exist | draft / PASS / BLOCKED | <note> |

Implementation may start only when every required row is `PASS`, `plan_readiness` is `ready`, and execution is explicitly authorized.

## Orchestration Exceptions

Default is sequential work in one checkout. Complete this section only when using worktrees or parallel workers.

| Mission | Worker / worktree | Resource isolation | Merge order | Temporary report |
|---|---|---|---|---|
| M1 | <id/path> | <port/db/services> | 1 | docs/goal/evidence/M1/REPORT.md |

## Stop / Ask Conditions

- <condition>

## Open Risks

| Risk | Impact | Mitigation / owner |
|---|---|---|
| <risk> | <impact> | <mitigation> |
