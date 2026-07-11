---
name: fullstack-harness-engineering
description: "Plan first, then optionally run compact full-stack Codex delivery loops from product ideas, document folders, PRDs, wireframes, design systems, UI references, architecture notes, or existing apps. Use for complete PRD implementation planning, frontend/backend sequencing, end-to-end implementation, Codex /goal planning, long-running app work, mission decomposition, UI evidence, verification gates, refinement, worktree orchestration, or full-stack acceptance. Selecting this skill alone does not authorize code changes: review, plan, audit, and how-to requests remain planning-only; implementation starts only after explicit execution authorization or an active delivery Goal. Preserve repository clarity with zero management files for direct work, one RUN.md for medium work, and PLAN.md plus RUN.md only for long or multi-mission work."
---

# Full-Stack Harness Engineering

## Purpose

Plan the complete delivery path before implementation, then run it only when execution is explicitly authorized. Reuse product and design sources instead of duplicating them. Preserve repository clarity while keeping enough durable state for compaction, resume, handoff, and long-running Goal execution.

Keep `prd-builder` and `design-package-builder` as separate upstream skills. If required product or visual inputs are missing, route to the matching skill, use user-authorized assumptions, or record the gap as `UNVALIDATED`.

## Reference Routing

- Read `references/contract-and-traceability.md` when source handoff, contract freeze, trace IDs, permissions, or file placement matters.
- Read `references/design-input-updates.md` for updated PRDs, wireframes, design systems, screenshots, Figma/page UI references, or page-specific deltas.
- Read `references/platform-archetypes.md` to select only relevant platform contracts and gates.
- Read `references/existing-app-refinement.md` for audits, baselines, ranked improvements, and before/after evidence.
- Read `references/worktree-thread-orchestration.md` only for multiple missions, subagents, worker threads, or worktrees.
- Read `references/orchestration-research-notes.md` before changing orchestration guidance.
- Read `references/verification-gates.md` for task, integration, UI, release, and evidence gates.
- Read `references/commit-convention.md` before creating or recording any harness-managed commit.
- Use `assets/templates/HARNESS_PLAN.template.md` as `PLAN.md` and `assets/templates/MISSION_RUNBOOK.template.md` as `RUN.md`. Use other templates only for an explicit optional expansion.

## File Budget

```text
direct work        -> no management files
medium work        -> docs/goal/RUN.md
long/multi-mission -> docs/goal/PLAN.md + docs/goal/RUN.md
binary UI evidence -> docs/goal/evidence/** only when artifacts exist
worktree workers   -> temporary per-mission reports only while integration needs them
```

- Do not create empty directories, duplicate source documents, or one file per concern.
- Keep Goal text, checkpoint, task state, verification, attempts, evidence links, blockers, and closeout in `RUN.md`.
- Create `PLAN.md` only for contract freeze, complete PRD coverage, multiple missions, dependency ordering, risk, or handoff.
- Put machine-readable status in `RUN.md` YAML frontmatter; do not create a second state database unless the target app already has one.
- Use an established repository planning convention instead of adding `docs/goal/` when one exists.
- Split a section only when it becomes difficult to scan or needs separate ownership.

## Execution Authorization Gate

Selecting or implicitly invoking this skill does not authorize implementation.

Classify the user's intent before any code edit, stateful command, commit, subagent write task, or external write:

```text
plan-only          -> inspect, analyze, and produce the complete plan; stop at ready
plan-then-stop     -> produce PLAN.md/RUN.md and wait for explicit approval
plan-then-execute  -> plan completely, pass readiness, then execute in the same task
execute-ready-plan -> validate an existing ready plan, then continue execution
```

Authorization rules:

- Treat `review`, `plan`, `audit`, `analyze`, `how`, `what first`, `which order`, and similar requests as `plan-only` or `plan-then-stop`.
- Treat `implement`, `build`, `fix`, `execute`, `continue`, `start implementation`, `plan then execute`, and an explicit request to complete delivery as execution authorization.
- An active Goal authorizes execution only when its objective explicitly requires implementation or delivery. A planning/review Goal remains planning-only.
- Creating or starting a native Goal requires explicit `/goal` usage or an explicit request to start one. Drafting a Goal prompt is not the same as starting Goal mode.
- If authorization is ambiguous, complete planning, set `status: ready` and `execution_authorized: false`, then stop before implementation.
- Never infer authorization for destructive actions, production changes, push/PR, paid services, or cleanup from general implementation authorization.

## Workflow

### 1. Intake And Route

```text
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Objective:
Existing inputs:
Existing app state: greenfield | built | deployed | legacy | partial
Product archetype:
Critical surfaces:
Scale: small | medium | multi-mission | program
Contract state: missing | draft | frozen | delta proposed | delta accepted
Design input state: missing | provided | partial | conflicting | frozen | updated
UI Evidence Gate: required | optional | n/a
Orchestration: sequential parent | single-checkout subagents | mission worktrees | app-managed worktrees
Verification surfaces:
Execution authorized: yes | no
Authorization source: explicit prompt | active delivery Goal | approved ready plan | none
File budget: 0 | RUN.md | PLAN.md + RUN.md | optional evidence/
Stop or ask when:
```

- Use Direct Work only when the task is bounded and execution is explicit.
- Use `RUN.md` for several verified steps or work likely to cross compaction.
- Add `PLAN.md` for a full PRD, multiple missions, frontend/backend sequencing, high risk, or durable handoff.
- For unclear existing-app improvement, audit first and record ranked candidates in `RUN.md`.

### 2. Plan The Complete PRD Before Execution

For a PRD-backed build, read all canonical requirements before changing production code. Plan every must-have requirement, not only the first feature.

Build the plan in this order:

1. Register PRD, architecture, wireframe, design-system, page UI, and current-code sources.
2. Extract every in-scope requirement, preserve its priority, and assign stable trace IDs; explicitly mark optional or deferred requirements instead of dropping them.
3. Identify shared foundations: environment, schema, auth, permissions, design tokens, app shell, API clients, fixtures, and test harness.
4. Draw the dependency order between backend, frontend, data, integrations, UI states, and release work.
5. Decompose the complete scope into vertical missions and independently verifiable tasks.
6. Define write scope, pass signal, evidence, risks, and stop conditions for every mission.
7. Populate the entire mission/task board in `RUN.md`; leave only execution-time discoveries to later refinement.

Do not always force backend-first or frontend-first. Use dependency evidence:

- Start with contract and schema foundations when both sides depend on them.
- Build the minimum backend capability first when the frontend requires real auth, permissions, persistence, or side effects.
- Allow frontend shell, design-system, and mocked-state work after UI/data contracts are frozen, even if backend implementation is incomplete.
- Prefer the first end-to-end vertical slice as soon as the minimum frontend and backend path exists; use it to validate integration before scaling either side.
- Serialize shared schemas, generated clients, migrations, global config, and design tokens.
- Record the chosen order and rationale in `PLAN.md`; do not rely on a generic backend-first rule.

### 3. Pass The Plan Readiness Gate

Set `plan_readiness: ready` only when:

- Every in-scope PRD/UI/architecture/design trace is planned, deferred with rationale, or out of scope; every must-have trace maps to at least one task and pass signal.
- Mission dependencies are explicit and acyclic.
- Frontend/backend/data boundaries and their integration points are defined.
- Shared foundations and migration order are identified.
- Required UI routes, breakpoints, states, and visual evidence are planned.
- Each mission has an allowed write scope and deterministic verifier, or an explicit `UNVALIDATED` risk.
- Blocking requirements conflicts and approval needs are resolved or clearly surfaced.
- Final E2E, regression, release, and residual-risk gates are present.

At the gate:

- `plan-only` or `plan-then-stop`: set run status to `ready`, keep `execution_authorized: false`, report the proposed first mission and stop.
- `plan-then-execute`: record the explicit authorization, set run status to `running`, and begin the first ready task.
- `execute-ready-plan`: verify that the plan is still current, record approval, then set run status to `running`.

### 4. Execute The Ready Plan

Prefer thin vertical missions connecting behavior, UI/data, and verification. Execute one ready write task at a time:

```text
observe -> confirm plan/authorization -> choose smallest ready task -> implement -> verify -> record evidence -> atomic commit if allowed -> update RUN.md -> continue or stop
```

- Never start a task whose dependencies are not `passed`.
- Commit only after task-specific verification passes, and follow `references/commit-convention.md` for the atomic boundary, subject, trailers, and `RUN.md` recording format.
- Keep one coherent verified task outcome per commit. Split an oversized task before committing instead of mixing independent outcomes.
- Do not retry the same failed approach more than twice.
- After three consecutive no-progress iterations, record the exact blocker and required input.
- Define a missing verifier before high-risk implementation; otherwise mark the surface `UNVALIDATED`.
- Update `RUN.md` after every verified task, blocker change, approval boundary, or mission transition.
- Replan only affected downstream tasks when implementation reveals new evidence; preserve completed trace coverage.

### 5. Orchestrate Only When Needed

Keep one parent-owned `RUN.md`; workers never edit it concurrently.

- Default to parent execution or one sequential write mission at a time in one checkout.
- Fan out read-only audits, reviews, and verification lenses only when delegation is allowed.
- Worktree workers write temporary reports under `docs/goal/evidence/M<n>/REPORT.md`; the parent verifies and folds durable results into `RUN.md`.
- Remove empty or duplicate worker artifacts only with required approval.
- If subagents are unavailable, run the same dependency-ordered plan sequentially.

### 6. Verify UI And Close

For UI-bearing work, record in `RUN.md`:

- Primary journey and target routes.
- Required breakpoints.
- Ready, loading, empty, error, disabled, permission, and long-running states that apply.
- Browser interaction, console/page/network health, accessibility, and design comparison.
- Clickable screenshot, trace, or report paths only when artifacts exist.

Final completion requires:

- Every must-have trace has implementation and verification coverage.
- Every required gate is `PASS`.
- Skipped or `UNVALIDATED` gates include reason, risk, and acceptance status.
- Primary journey and relevant platform gates pass.
- `RUN.md` records final status, evidence, changed files, commits, residual risk, and landing state.

## Output Shape

```text
Intent and execution authorization:
Route and file budget:
Complete mission order and rationale:
Plan readiness:
Current checkpoint or proposed first mission:
Verification and evidence:
Blockers / unvalidated surfaces:
Next action:
```
