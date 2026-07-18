---
name: fullstack-harness-engineering
description: "Plan first, then optionally run compact full-stack Codex or Claude Code delivery loops from product ideas, PRDs, wireframes, design systems, architecture notes, or existing apps. Use for complete PRD implementation planning, frontend/backend sequencing, end-to-end implementation, Goal planning, long-running app work, mission decomposition, deterministic parallel mission selection, UI evidence, verification gates, worktree orchestration, or full-stack acceptance. Plan-backed multi-mission runs proactively detect the current runtime and, after Plan Readiness, select up to three dependency-ready nonconflicting missions for isolated parallel execution. Selecting this skill does not authorize implementation or lifecycle actions: each spawn, task, worktree, commit, integration, landing, deploy, archival, or cleanup action requires recorded authorization. Use zero management files for direct work, RUN.md for medium work, and PLAN.md plus RUN.md for long or multi-mission work."
---

# Full-Stack Harness Engineering

## Purpose

Plan the complete delivery path before implementation, then run it only when execution is explicitly authorized. Reuse product and design sources instead of duplicating them. Preserve repository clarity while keeping enough durable state for compaction, resume, handoff, and long-running Goal execution.

Keep `prd-builder` and `design-package-builder` as separate upstream skills. If required product, Builder UX Direction, or visual inputs are missing, route to the matching skill, use user-authorized assumptions, or record the gap as `UNVALIDATED`. Builder direction comes from the named human product/design owner or commissioning team; an implementation agent does not invent it.

For plan-backed orchestration, keep three layers separate:

1. **Task decomposition:** flat immutable task IDs and one bounded execution-time refinement generation.
2. **Parallel analysis:** pure static validation/conflict analysis, followed by a launch-gated ready frontier and deterministic wave proposal.
3. **Execution coordination:** parent-confirmed leases, branches/workspaces/tasks, worker-result validation, serial integration, and next-wave recomputation under action-specific authorization.

## Reference Routing

- Read `references/contract-and-traceability.md` when source handoff, contract freeze, trace IDs, permissions, or file placement matters.
- Read `references/execution-state-model.md` before creating or changing canonical PLAN/RUN manifests, authorization state, phases, runtime capability fields, or integration state.
- Read `references/execution-task-decomposition.md` when defining flat task IDs or handling an execution-time split request.
- Read `references/parallel-mission-selection.md` before proposing any parallel write wave, scope/resource conflict decision, or batch recomputation.
- Read `references/design-input-updates.md` for updated PRDs, wireframes, design systems, screenshots, Figma/page UI references, or page-specific deltas.
- Read `references/platform-archetypes.md` to select only relevant platform contracts and gates.
- Read `references/existing-app-refinement.md` for audits, baselines, ranked improvements, and before/after evidence.
- Read `references/worktree-thread-orchestration.md` only for multiple missions, subagents, nested subagents inside app tasks, worker threads, or worktrees.
- Read `references/orchestration-research-notes.md` before changing orchestration guidance.
- Read `references/verification-gates.md` for task, integration, UI, release, and evidence gates.
- Read `references/cloudflare-deployment-lifecycle.md` when a deployable application targets Cloudflare or the release plan includes development and production Workers.
- Read `references/commit-convention.md` before creating or recording any harness-managed commit.
- Use `assets/templates/HARNESS_PLAN.template.md` as `PLAN.md` and `assets/templates/MISSION_RUNBOOK.template.md` as `RUN.md`. Use other templates only for an explicit optional expansion.
- For a new GitHub repository that will use pull-request landing, inspect its root `AGENTS.md`, PR template, CI workflows, branch rules, and repository auto-merge setting. When durable project setup is in scope, instantiate `assets/templates/PROJECT_AGENTS.template.md`, `PULL_REQUEST.template.md`, and `PROJECT_CI.template.yml`; replace every placeholder with repo-specific values before activating the workflow. For a deployable Cloudflare application, also instantiate `PROJECT_CLOUDFLARE_DEPLOY.template.yml` as an exact-SHA dispatched CD workflow. Enable repository auto-merge or install/change deployment workflows only with `configure_repository` authorization.

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
- A medium `RUN.md` without `PLAN.md` is compact sequential mode: one parent writer in `shared_checkout`, no worker lease, execution-time task split, worktree fan-out, or deterministic wave claim. Promote to `PLAN.md` + `RUN.md` before any of those become necessary.
- Put one canonical, fenced JSON manifest in each harness artifact as specified by its template. Compact RUN-only mode keeps its plan identity fields `null`; plan-backed validation and selection remain unavailable until promotion. JSON keeps the shipped validators Python-stdlib-only. Do not add YAML frontmatter or a second state database for the same fields.
- Treat Markdown tables as human views only. Update the canonical manifest first; scripts must never parse tables as state.
- Use an established repository planning convention instead of adding `docs/goal/` when one exists.
- Split a section only when it becomes difficult to scan or needs separate ownership.

## Pure Validation Tools

- `scripts/validate_harness_plan.py --plan <PLAN.md> [--run <RUN.md>]` validates manifests, trace/DAG/refinement structure, scopes/resources, authorization shape, and plan/run digest consistency.
- `scripts/select_parallel_missions.py --plan <PLAN.md> --run <RUN.md>` computes a deterministic launch-gated frontier, static conflict graph, wave proposal, and one tool-agnostic launch directive per selected mission.
- `scripts/validate_worker_result.py --plan <PLAN.md> --run <RUN.md> --result <REPORT.md> --observed-head-sha <sha> --observed-changed-file <path>... --ancestry-confirmed` checks a worker integration candidate against parent-observed facts.

All three are Python-stdlib-only and read-only. Their output is sorted JSON with no timestamps. They never create or modify Git refs, worktrees, Codex tasks, PLAN, or RUN. The parent observes live facts and performs authorized mutations only after reviewing their output.

## Default Runtime And Wave Policy

Apply this policy to every plan-backed multi-mission execution unless the user explicitly requests a lower worker budget:

1. Before the first production edit or worker launch, proactively inspect the current-session native tool surface, permission boundary, worker slots, worktree isolation, completion channel, Git state, and runtime resources. Do not wait until delegation appears useful.
2. Record every observed driver independently of authorization. In Codex, usable project lookup plus thread create/read/message surfaces prove `app_threads`; child-agent tools prove `subagents`. Missing authorization must never make an available driver disappear from `runtime_adapter.available_drivers`.
3. Use three as the configured plan-backed write-worker maximum. The effective wave may contain fewer missions because it is still capped by observed slots, isolation capacity, dependency readiness, conflicts, permission boundaries, and the user's lower explicit limit.
4. Immediately after `plan_readiness: ready`, validate PLAN/RUN and compute the dependency-ready conflict graph. For execution-authorized work, run `select_parallel_missions.py` before starting a production task and select up to three nonconflicting missions in deterministic order.
5. For execution-intent work in a shared repository, default `landing.mode` to `pull_request` unless the user explicitly requests local-only delivery. At Plan Readiness, inspect the remote, branch rules, required checks, Codex review availability, and repository auto-merge setting, then request every missing launch and landing action in one authorization checkpoint. Before a PR exists, scope `manage_pr_review` and `merge_pr` to `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` in RUN schema v6 or v7; do not use `*` merely because the PR URL is not known. Record each approved action separately in the ledger; the bundled request is not blanket permission.
6. The normal landing bundle is `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `create_pr`, `manage_pr_review`, and `merge_pr`, plus the selected route's worker/worktree actions. Include `configure_repository` in the same checkpoint only when the observed repository needs an exact configuration change for the requested flow. When full deployed Cloudflare delivery is requested and PLAN declares both targets, use the same one-time checkpoint to ask separately for `deploy` on `environment:development` and `environment:production`; recording them in the same answer does not merge deploy into push or merge authorization. Keep archival, worktree removal, and branch deletion outside this bundle.
7. When the selected launch route and landing path are already authorized, accept the wave, consume every launch directive, and continue through review and merge without another confirmation. When either exact bundle is missing, request the complete missing-action set once, pause at that boundary, record the answer, and rerun selection. Do not silently downgrade merely because authorization is missing.
8. Fall back to fewer workers, sequential parent execution, or local-only closeout only when the user declines the relevant bundle or live capability, isolation, permission, dependency, conflict, resource, or repository evidence requires it. Record the exact reason.
9. Never run more than one write-capable parent or subagent in `shared_checkout`. Parallel writes require isolated worktrees and durable authorized branch/commit handoff.

## Execution Authorization Gate

Selecting or implicitly invoking this skill does not authorize implementation.

Classify the user's intent before any code edit, stateful command, worker launch, commit, integration, external write, or cleanup:

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

General execution authorization and action authorization are separate. Keep these exact ledger keys in `RUN.md`, all `false` by default:

```text
spawn_subagents
create_user_owned_tasks
create_local_worktrees
create_app_managed_worktrees
create_local_branches
create_local_commits
integrate_locally
push
create_pr
configure_repository
manage_pr_review
merge_pr
deploy
archive_worker_tasks
remove_worktrees
delete_branches
```

Only an explicit user instruction recorded with its source may set overall execution or an action to `true`. Every true action also records run/mission/target scope and an expiry boundary; nonmatching or expired authorization is false for the proposed action. A generated Goal prompt, PLAN, RUN, worker prompt, inferred best practice, successful verification, or platform capability cannot self-authorize it. When an unauthorized action is optional, use a safe sequential/local fallback; when it is required, stop at that boundary.

PR creation, repository review configuration, review management, and merge are separate boundaries. `create_pr` does not authorize marking a PR ready, requesting or resolving review, enabling branch rules, or merging. A read-only local or GitHub diff inspection does not need mutation authorization, but any review-state change uses `manage_pr_review`.

A single explicit user instruction may authorize several exact actions together. Record that one source separately under every covered ledger key; do not collapse the entries into a new blanket permission. For plan-backed execution that will land through a pull request, proactively request the complete landing bundle once at Plan Readiness: normally `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `create_pr`, `manage_pr_review`, and `merge_pr`, together with run/mission/target scope. When the PR does not exist yet, use the bounded schema-v6+ `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` target for its review and merge actions. After creation, verify that repository, base, and head match, append the exact `pr:<full-PR-URL>` target without replacing the future binding or user source, and require that exact target before either action. If a branch, commit, or integration already exists, require only the actions that will actually mutate state. For full deployed Cloudflare delivery, ask in that same checkpoint for the exact `deploy` targets declared by PLAN while preserving deploy as its own ledger entry. This request does not grant them. `configure_repository` remains its own ledger action even when an observed setup gap causes it to be included in the same readiness checkpoint; keep archival, worktree removal, and branch deletion separate.

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
Builder UX Direction state: missing | selected | provisional | assumed | conflicting | updated
UI Evidence Gate: required | optional | n/a
UX Validation Gate: required | optional | n/a
Worker runtime: parent | subagent | app_task
Workspace mode: shared_checkout | parent_managed_worktree | app_managed_worktree
Completion channel: agent_result | thread_poll | report_file | user_relay
Runtime provider: codex | claude_code | generic
Available runtime drivers: app_threads | dynamic_workflow | subagents | sequential_parent
Selected runtime driver: <deterministic route from observed capabilities>
Nested subagents: unavailable | available-not-authorized | enabled-read-only
Automatic mission threads: not-needed | pending-authorization | enabled | unavailable
Automatic PR landing: local-only | pending-authorization | enabled | blocked
Deployment platform: cloudflare | other | n/a
Release targets: development PR head -> production merged main | custom | n/a
Automatic environment promotion: pending-authorization | enabled | blocked | n/a
Permission boundary: unknown | ready | may-prompt | blocked
Selected permission mode/profile and source:
Required filesystem/network/local-binding surfaces:
Configured worker budget:
Observed runtime/isolation capacity:
Verification surfaces:
Execution authorized: yes | no
Authorization source: explicit prompt | active delivery Goal | approved ready plan | none
File budget: 0 | RUN.md | PLAN.md + RUN.md | optional evidence/
Stop or ask when:
```

- Use Direct Work only when the task is bounded and execution is explicit.
- Use `RUN.md` for several verified sequential steps or work likely to cross compaction.
- Add `PLAN.md` for a full PRD, multiple missions, frontend/backend sequencing, high risk, or durable handoff.
- Promote RUN-only work before delegating a write mission, accepting execution-time refinement, or selecting parallel work.
- For unclear existing-app improvement, audit first and record ranked candidates in `RUN.md`.
- For plan-backed multi-mission execution, set the configured worker budget to three by default, then reduce it only from observed capacity, conflicts, dependencies, permissions, or an explicit user limit.

### 2. Plan The Complete PRD Before Execution

For a PRD-backed build, read all canonical requirements before changing production code. Plan every must-have requirement, not only the first feature.

Build the plan in this order:

1. Register PRD, Builder UX Direction, architecture, wireframe, design-system, page UI, user-research/usability evidence when it exists, and current-code sources.
2. Extract every in-scope requirement, preserve its priority, and assign stable trace IDs, including `UX-*` traces for critical user tasks, interaction/recovery expectations, and required validation; explicitly mark optional or deferred requirements instead of dropping them.
3. Identify shared foundations: environment, schema, auth, permissions, design tokens, app shell, API clients, fixtures, and test harness.
4. Draw the dependency order between backend, frontend, data, integrations, UI states, and release work. For Cloudflare delivery, define isolated development and production Workers, bindings, auth/payment modes, migration order, exact source SHAs, and deployed-environment verification.
5. Decompose the complete scope into vertical missions and independently verifiable tasks.
6. Give missions and tasks opaque immutable IDs; keep tasks flat, and express hierarchy only through refinement lineage.
7. Define exact/subtree write scope, deny scope, complete serialized/runtime resource claims, pass signal, evidence, risks, and stop conditions for every mission. The mission is always the parallel write unit.
8. Define task/worker, mission-integration, batch, and final verifiers as structured `cwd` plus `argv`, never shell prose that requires interpretation.
9. Populate the complete static definitions in `PLAN.md` and initialize their live phases in `RUN.md`; leave only execution-time discoveries to bounded refinement.

For UI-bearing work, translate the Builder UX Direction into task and acceptance consequences. Builder approval can prove direction conformance, but it cannot prove usability. When a critical or unfamiliar flow has a required validation depth, order its wireframe/prototype and usability evaluation before irreversible or broad production implementation. When representative-user evidence is unavailable, keep the relevant UX gate `UNVALIDATED` or obtain explicit residual-risk acceptance; do not promote agent judgment, screenshots, or automated E2E into user-validation evidence.

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
- Every UI-bearing plan records the human Builder UX Direction owner, each controlling decision and its `selected` / `provisional` / `assumed` status, and any conflict with user evidence, product requirements, platform conventions, or accessibility.
- Every must-have `UX-*` trace names its critical task, intended success/failure signal, validation depth, downstream task, and evidence gate. Builder approval alone never satisfies a required usability gate.
- Canonical sources, trace priorities/dispositions, UI surfaces, risks, and mission stop conditions are complete; human tables do not contain execution-driving fields absent from the manifest.
- Mission dependencies are explicit and acyclic.
- Task dependencies and refinement lineage are explicit, acyclic, and valid; accepted child tasks are at most refinement generation 1.
- Frontend/backend/data boundaries and their integration points are defined.
- Shared foundations and migration order are identified.
- Required UI routes, breakpoints, states, and visual evidence are planned.
- Each mission has an allowed write scope and deterministic verifier, or an explicit `UNVALIDATED` risk.
- Every mission eligible for fan-out declares `resource_inventory_complete: true`, supported write-scope claims, and all serialized/runtime resources it may mutate.
- Blocking requirements conflicts and approval needs are resolved or clearly surfaced.
- Final E2E, regression, release, and residual-risk gates are present. When a primary journey exists, name its automated E2E command, current-head CI check, target environment, retained evidence, and manual-smoke disposition.
- For a deployable Cloudflare application, PLAN schema v3 declares both release targets and RUN schema v7 initializes both deployment states. Development binds to the current PR head after CI; production depends on development PASS and binds to merged `main`. Exact deploy targets and any repository workflow change are surfaced as separate authorization needs.
- The shipped plan validator passes; the canonical RUN plan ID, revision, and digest match PLAN.

At the gate:

- `plan-only` or `plan-then-stop`: set run status to `ready`, keep `execution_authorized: false`, report the proposed first mission and stop.
- `plan-then-execute`: make one Plan Readiness authorization checkpoint for the exact execution, launch, and pull-request landing actions; record the explicit decision, set run status to `running` only when the next actions are authorized, then apply the Default Runtime And Wave Policy before beginning any production task.
- `execute-ready-plan`: verify that the plan is still current, make the same one-time missing-action checkpoint, record the explicit decision, set run status to `running` only when the next actions are authorized, then apply the Default Runtime And Wave Policy before beginning any production task.

### 4. Execute The Ready Plan

Prefer thin vertical missions connecting behavior, UI/data, and verification. Keep tasks sequential inside each mission. For plan-backed multi-mission work, launch the selected isolated wave first; use sequential parent execution only as the recorded fallback. Execute one ready task at a time within each leased mission:

```text
observe -> confirm plan/digest/authorization -> lease ready mission -> choose smallest ready task -> implement -> verify -> report worker result -> integrate if authorized -> verify integration -> update RUN -> recompute
```

- Never start a mission whose dependencies are not `integrated` with a PASS integration gate on the current integration lineage. `worker_passed` is not dependency satisfaction.
- Commit only after task-specific verification passes and `create_local_commits` is authorized; follow `references/commit-convention.md` for the atomic boundary, subject, trailers, and `RUN.md` recording format.
- Keep one coherent verified task outcome per commit. Split an oversized task before committing instead of mixing independent outcomes.
- Do not retry the same failed approach more than twice.
- After three consecutive no-progress iterations, record the exact blocker and required input.
- Define a missing verifier before high-risk implementation; otherwise mark the surface `UNVALIDATED`.
- Only the parent updates `RUN.md`, after every verified task result, blocker change, approval boundary, lease, mission phase transition, integration result, or wave recomputation.
- If a task needs decomposition, the worker emits `REFINEMENT_REQUEST` and stops. The parent accepts or rejects it, increments the plan revision when accepted, validates trace/DAG/conflict state, and invalidates stale wave proposals. Generation-1 tasks cannot split again; stop for mission-level replanning instead.
- Replan only affected downstream work when implementation reveals new evidence; preserve completed trace coverage and immutable IDs.

### 5. Orchestrate Only When Needed

Keep one parent-owned `PLAN.md` and `RUN.md`; workers never edit either.

- Fan out read-only planning only when `spawn_subagents` is authorized. Keep mutating generators and shared-state tests serialized even when their intended source edits are read-only.
- Before choosing a launch primitive, proactively detect the host session and record a schema-v6-or-v7 `runtime_adapter` capability snapshot before the first production edit. Use native surfaces in the session that is actually running the Harness: Codex app project/thread tools prove `app_threads`; the Claude Code `Workflow` tool plus its supported runtime prove `dynamic_workflow`; the current session's child-agent tools prove `subagents`. An installed `codex` or `claude` binary, directory name, prompt wording, model name, or missing action authorization does not identify or remove a runtime capability. Use an explicit provider only when the host surface is opaque, otherwise record `generic` fallback. Codex routes in this order: `app_threads`, `subagents`, `sequential_parent`. Claude Code routes in this order: `dynamic_workflow`, `subagents`, `sequential_parent`. A generic or unknown runtime uses `subagents` when observed and otherwise `sequential_parent`. Capability detection never grants authorization.
- Default plan-backed multi-mission execution to a configured maximum of three isolated write workers. `worker_runtime: parent`, `workspace_mode: shared_checkout`, and one writer remain the compact or evidence-forced fallback. For authorized multi-mission or program execution in the Codex app, prefer `app_task` + `app_managed_worktree` + `thread_poll` when current thread tools, isolation, and completion polling are available.
- For parallel writes, first validate PLAN/RUN, compute the ready frontier and conflict graph with `scripts/select_parallel_missions.py`, then bind a proposed wave to the current plan revision, digest, and fixed batch base SHA.
- Do not stop after printing a non-empty app-task wave. After the parent rechecks live facts, records the accepted wave, allocates leases, and verifies the explicit pre-allocation `*` grant for app-assigned task/worktree identities plus every concrete target already known, consume every `launch_directives` entry: resolve the current Codex project once, create one worktree thread per selected mission with the complete `WORKER_GOAL.template.md` handoff as its initial prompt, and record the returned thread/client identity in the RUN worker record. A selector directive is not authorization and never creates the thread itself.
- App-task fan-out requires `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `spawn_subagents` to cover the selected mission and allocated targets. Request this bundle once at readiness with explicit run/mission/target scope when it is missing; pause and rerun selection after the answer instead of silently choosing a lower runtime driver. Do not repeatedly ask for each worker when an unexpired run-wide grant already matches. Keep integration, push, PR, merge, deploy, archival, and cleanup permissions separate.
- Every launched app-task mission receives an explicit depth-one, read-only nested-subagent policy. When capability is already observed, the worker must start at least one useful child for a non-trivial mission and may use up to three across exploration, documentation/API research, test/log analysis, and proposed-diff review. When capability is unknown, launch a no-production-edit handshake, poll the task, record the result, then send an enabled or disabled policy before implementation. If the required capability is unavailable, do not silently run the promised multi-agent shape; record the downgrade and use the sequential parent fallback.
- Poll app-task threads through the available read-thread/status surface with backoff, preserve blockers and partial results, and send follow-up instructions through the available thread-message surface. Never claim an automatic callback when only polling exists. A terminal thread is still only a worker result; validate its reported head, actual diff, scope, ancestry, and verifiers before integration.
- For a Claude Code `dynamic_workflow` route, use `subagent` + `parent_managed_worktree` + `agent_result`. Allocate one authorized worktree, branch, and lease per selected mission, then invoke the Claude Code `Workflow` tool once with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and the accepted wave supplied as structured `args`. Include the frozen plan identity, batch base, complete worker prompts, and allocated worktree paths. The workflow script coordinates sibling mission agents; this schema-v6-or-v7 adapter deliberately forbids further delegation inside those mission agents even when the platform supports nesting.
- Claude Dynamic Workflow has no mid-run user-input channel. A mission that needs contract sign-off, new authorization, a secret, destructive action, or scope refinement returns `REFINEMENT_REQUEST`; the workflow stops that mission and the parent closes or supersedes the wave before any follow-up run. Completed workflow output is still only a set of worker-result candidates and must pass the same Git, scope, ancestry, verifier, and serial-integration gates.
- Dynamic Workflow availability must be observed, including feature enablement and usable agent/result surfaces; a version string alone is insufficient. Its runtime concurrency is an observed capacity, not permission to exceed the harness's three-writer policy. Read-only analysis may use a separately recorded larger provider budget, but write missions remain bounded by the selector's effective worker budget.
- Effective concurrency is the minimum of configured budget, observed worker slots, isolation capacity, and ready nonconflicting missions. Never exceed three write workers unless the user explicitly changes this skill's default and the runtime safely supports it.
- The parent confirms current Git/runtime facts and records the wave before any mutating launch action. Unsupported scopes, incomplete resource inventory, unknown capabilities, stale bases, or missing action authorization force sequential fallback or a stop.
- Before launching subagents or app tasks, observe the permission mode selected for the parent and record the effective approval, filesystem, network, local-binding, and inheritance facts. Child agents inherit the parent task's active permission mode; selecting `Approve for me` changes who reviews eligible prompts, not the sandbox boundary.
- Preflight every worker against the surfaces its commands actually need: the app worktree, the repository Git common directory used by linked worktrees, system temp, package-manager caches, outbound domains, local/private bindings, and any required Unix sockets. Mark the permission boundary `ready` only when those surfaces are already inside the selected boundary. Treat `may-prompt`, `blocked`, or `unknown` as a launch blocker for unattended write fan-out.
- Config or composer changes apply at the task/session boundary and do not retroactively widen already-running app tasks. Select the intended mode before the parent turn creates workers; recreate or explicitly restart affected tasks when the mode changes.
- Never present nested delegation as an approval bypass. If the user explicitly chooses non-interactive full access, the effective Codex setting is `danger-full-access` with approval policy `never`; otherwise prefer a named least-privilege profile that covers the required surfaces. This skill records and verifies the choice but never self-authorizes or silently widens it.
- Isolated write fan-out requires authorized durable branch and commit creation; the portable coordinator does not integrate uncommitted patches from worker workspaces.
- Integrate a wave serially in deterministic order. Validate actual diffs and worker results, rerun integration verifiers, mark only successful heads `integrated`, then recompute the next frontier.
- App-managed tasks are user-owned independent tasks; do not promise automatic parent callbacks. Use the declared completion channel. Platform-managed retention remains outside manual cleanup authorization.
- An `app_task` mission worker may use bounded direct subagents only when `spawn_subagents` covers that worker and RUN records an enabled nested-subagent policy. The app task remains the sole mission writer; nested children are read-only explorers, researchers, test analysts, or reviewers and never edit PLAN/RUN, create refs/worktrees/tasks, commit, integrate, push, deploy, or clean up.
- For a non-trivial app task with an enabled policy, explicitly evaluate independent read-only lanes before the first production edit. Run eligible exploration, documentation/API verification, and test-plan/contract review lanes before writing; run a proposed-diff review after implementation but before the mission result. Normally spawn one to three direct children across those checkpoints; skip only for trivial work, missing slots/runtime, or no safe independent lane, and report the reason. Wait for requested children and synthesize their results before returning the mission result.
- Nested children are task-local assistants, not new harness missions. They receive no mission lease, do not change the outer wave budget or dependency graph, and return only to their app-task parent through `agent_result`; the outer coordinator continues to observe the app task through its declared completion channel.
- If dynamic workflows, subagents, app tasks, worktrees, callbacks, or slots are unavailable, run the same dependency-ordered plan sequentially.

### 6. Verify, Land, And Close

For UI-bearing work, record in `RUN.md`:

- Builder UX Direction source, owner, decision status, and unresolved validation needs.
- Primary journey and target routes.
- Required breakpoints.
- Ready, loading, empty, error, disabled, permission, and long-running states that apply.
- Browser interaction, console/page/network health, accessibility, and design comparison.
- Direction conformance separately from usability evidence; when usability validation is required, record the method, representative participant/source, task scenario, target, actual result, and redacted evidence.
- Clickable screenshot, trace, or report paths only when artifacts exist.

Run deterministic automated E2E for every primary journey on the final integration head. A PASS may replace a duplicate manual smoke only when the test covers the same journey and equivalent environment, is bound to the current head SHA, and retains a deterministic log, trace, or artifact. Record that disposition as `not required - covered by current-head E2E`, not as a skipped gate. Keep manual smoke for missing, failed, flaky, narrower, visual-only, external-integration, or materially different deployed-environment coverage; deployment smoke remains separate when the live release was not the E2E target. Follow `references/verification-gates.md` for the full equivalence test and `references/cloudflare-deployment-lifecycle.md` for Cloudflare promotion.

#### Authorized Automatic Pull-Request Landing

For execution-intent work in a shared repository, `pull_request` is the default landing mode. Inspect the review and merge path and request the full missing landing bundle once at Plan Readiness, not after implementation. Use `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` for unborn review and merge targets, then resolve it to the matching exact `pr:<full-PR-URL>` after creation. This remains an authorization request: the skill, plan, and default mode cannot approve any action.

When `landing.mode` is `pull_request` and every action that remains necessary in the landing path has exact authorization—normally `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `create_pr`, `manage_pr_review`, and `merge_pr` for a new delivery—do not stop after local verification, push, Draft PR creation, CI, or review request. The parent owns this continuous landing loop:

```text
review final diff -> verify -> commit -> push feature head -> create Draft PR
-> poll current-head CI, including required E2E -> authorized development deploy and deployed E2E when required
-> mark Ready -> request Codex review
-> poll review and threads -> repair authorized in-scope findings if needed
-> reset stale gates after every push -> exact-head squash auto-merge
-> wait until GitHub reports merged -> record merged SHA
```

- Recheck the matching authorization and live target immediately before every mutation. One bundled user statement avoids repeated pauses; it does not weaken the separate ledger entries.
- Bind CI, required E2E, and Codex review to the current PR head. A new commit or push resets those results, requires fresh CI and E2E, and requires another review of that SHA.
- Trigger review with the repository's documented mechanism. When Automatic reviews are not observed, use `@codex review` under `manage_pr_review` and poll the PR; do not treat the bot's acknowledgement as PASS.
- If CI or review finds an in-scope defect, fix it only under the existing execution, commit, and push authorization; rerun local gates, push the new head, and restart the current-head loop. Stop for a scope/contract decision, missing authorization, or three consecutive no-progress attempts.
- Enable squash auto-merge only after current-head CI and Codex review PASS with zero blocking findings and unresolved threads. Use an exact-head guard and wait for GitHub to report `merged` before declaring landing complete.
- If repository auto-merge or Codex review configuration is unavailable, do not change repository settings without `configure_repository`. When the gap was observable at Plan Readiness, include that exact action in the one-time checkpoint; otherwise report the newly discovered boundary. Deploy and post-merge cleanup remain separate even when landing is automatic.

#### Authorized Cloudflare Development And Production Promotion

For a PLAN schema-v3 Cloudflare release, use the PR head and merged base as two explicit release sources:

```text
current PR head + current-head CI PASS
-> authorized deploy to environment:development
-> development migration and deployed-environment E2E PASS
-> current-head review and exact-head merge
-> GitHub merged state with merged main SHA
-> authorized deploy to environment:production
-> production migration and smoke PASS
```

- Use one codebase and two isolated Workers. Development uses non-production data, sandbox payment configuration, development auth and host scope; production uses live configuration and production data. Never use production customer data as the development backing store.
- Trigger `PROJECT_CLOUDFLARE_DEPLOY.template.yml` with the exact target and SHA only after rechecking the `deploy` ledger. Do not make an arbitrary branch push or `main` push an unconditional deploy path.
- Development PASS binds `deployments.development.source_sha` to the current `landing.pr_head_sha` and requires current-head checks plus deployed-environment verification. Any new push invalidates it.
- Production PASS requires development PASS, `landing.merge_status: merged`, a source SHA equal to `landing.merged_sha`, and production smoke evidence. Preserve the distinct PR-head and squash-merge SHAs.
- If full deployed delivery and both exact environments are already authorized, continue from development through merge and production without another prompt. Stop only for a failed gate, stale head, changed target, missing secret/resource, or authorization gap.

Final completion requires:

- Every must-have trace has implementation and verification coverage.
- Every required mission is `integrated` with a PASS integration gate, and its recorded integration SHA is on the current integration lineage.
- Every required gate is `PASS`.
- Skipped or `UNVALIDATED` gates include reason, risk, and acceptance status.
- Primary journey and relevant platform gates pass.
- Required automated E2E is PASS on the current integration or PR head. Any duplicate manual smoke it replaces is recorded as `not required - covered by current-head E2E`; uncovered or environment-specific smoke still passes separately.
- `RUN.md` records final status, evidence, changed files, commits, residual risk, and landing state.
- In pull-request mode, the final branch was reviewed locally before push, and current-head CI plus GitHub review are recorded separately. A new push invalidates any earlier PASS tied to another SHA.
- Only the parent integration branch lands by default. In pull-request mode, `integration.branch` must be the PR head branch and must differ from the base branch. Worker branches remain local and do not open their own PRs unless the plan gives them a separate landing target.
- `merge_status: ready` and `merged` both preserve the same current-head gate: the PR head matches the integration head, check and review PASS records match that PR head, and no blocking finding or unresolved thread remains. Schemas v4 through v7 may set `auto_merge_requested: true` only after that gate passes, with `auto_merge_head_sha` equal to the current PR head. Enable squash auto-merge with an exact head-SHA match only when `merge_pr` covers the exact `pr:<full-PR-URL>` and any retained `future-pr:` target matches its repository, base, and head; any new push resets the request and requires fresh CI and review. `merged` additionally records the merged PR state and merge SHA. Merge and deploy still require their own authorization.
- When PLAN declares a Cloudflare release, both development and production deployment states are PASS with exact SHA, Worker, URL, version, migration, verification, evidence, and matching deploy authorization. A successful upload without deployed-environment verification is not PASS.
- New PLAN files use schema v3 and new RUN files use schema v7. Schema versions expose fields but do not enable unrelated release behavior: omit `release` and `deployments` together for non-Cloudflare or non-deployable work. When PLAN declares a Cloudflare `release`, RUN must include matching `deployments`. Valid PLAN schema v2 and RUN schemas v2 through v6 remain readable. After merge, bind `post_merge_cleanup` to the exact merged PR head and a freshly observed base branch. Remove only an exact clean parent-managed linked worktree under `remove_worktrees`, then switch the primary checkout to the base and delete only the exact local feature branch under `delete_branches`. Record cleanup as complete, deferred, or not applicable; `not_applicable` requires no matching linked worktree, never remove the primary checkout, and keep app-managed retention separate.

## Output Shape

```text
Intent and execution authorization:
Action authorization gaps:
Route and file budget:
Complete mission order and rationale:
Plan ID / revision / digest and observed base:
Plan readiness:
Current checkpoint or proposed first mission:
Worker allocation and integration plan:
Permission boundary and inheritance:
Verification and evidence:
Blockers / unvalidated surfaces:
Next action:
```
