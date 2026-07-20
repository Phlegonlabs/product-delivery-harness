---
name: fullstack-harness-engineering
description: "Classify work as small or large before optionally running Codex or Claude Code full-stack delivery from product ideas, PRDs, wireframes, design systems, architecture notes, or existing apps. Small work stays direct without planner, scheduler, PLAN/RUN, or external-runtime preflight. Large work may use PRD implementation planning, typed graph orchestration, conditional routing, bounded correction loops, frontend/backend sequencing, long-running work, mission decomposition, deterministic parallel selection, mixed-runtime binding, UI evidence, verification gates, worktree orchestration, or acceptance. Selecting this skill grants no implementation or lifecycle permission: external invocation, spawn, task, worktree, commit, integration, landing, deploy, archival, and cleanup actions each require recorded authorization."
---

# Full-Stack Harness Engineering

## Purpose

Plan the complete delivery path before implementation, then run it only when execution is explicitly authorized. Reuse product and design sources instead of duplicating them. Preserve repository clarity while keeping enough durable state for compaction, resume, handoff, and long-running Goal execution.

Keep `prd-builder` and `design-package-builder` as separate upstream skills. If required product, Builder UX Direction, or visual inputs are missing, route to the matching skill, use user-authorized assumptions, or record the gap as `UNVALIDATED`. Builder direction comes from the named human product/design owner or commissioning team; an implementation agent does not invent it.

## Project Size Gate

Before invoking the planner, graph scheduler, worker allocator, external-runtime bridge, or any PLAN/RUN workflow, perform one bounded read-only scope scan and classify the work as `small` or `large`. This is a routing decision, not implementation authorization. An explicit user request to use planning controls the route. A request to skip planning keeps only qualifying small work direct; it cannot override a `large` classification or a required safety or authorization boundary.

Classify the work as `small` only when all of these are true:

- It has one primary outcome in one bounded component or repository area.
- One writer can complete it without parallel missions, durable handoff, or cross-task coordination.
- It has no broad schema migration, multi-environment release, destructive data operation, or independently staged deployment.
- It does not require a frozen multi-surface contract, conditional correction graph, or multiple dependent implementation missions.
- One coherent test and review pass can verify the result.

Classify the work as `large` when any small-work condition fails. Full PRDs, multiple independently writable missions, frontend/backend/data delivery across separate boundaries, long-running handoff, migration or release promotion, conditional routing, or mixed-runtime execution are large. Judge size by coordination scope and blast radius, not changed-line or file count alone.

Route the result as follows:

```text
small -> direct inspect -> implement -> verify -> review -> authorized Git actions
large -> planner -> readiness -> sequential execution or scheduler when parallel work is useful
```

- Small work creates no PLAN/RUN files, performs no scheduler or worker-capability scan, launches no subagent by default, and does not preflight an external runtime. Use the current parent and the smallest relevant verification surface.
- Large work enters Intake And Route and uses the file budget below. Planning does not automatically require parallel execution.
- Enable scheduler fan-out only when the large plan has at least two dependency-ready, nonconflicting missions and the isolation, capacity, permission, and action gates pass. A large plan with one ready execution path stays with the sequential parent.
- Preflight an external provider before ready-node selection only when the user explicitly requests it, a ready node's current PLAN runtime policy prefers or requires it, or the host cannot satisfy a ready node whose declared fallback allows it. A Codex parent uses the Claude bridge preflight. A Claude Code parent uses the `codex:codex-rescue` preflight for Codex. An installed CLI or plugin, an unready node, or an unselected fallback is not enough.
- If small work crosses a large-work condition during execution, stop at a safe checkpoint, preserve completed edits and verification, and plan only the remaining work. Promotion does not restart completed work.

For plan-backed orchestration, keep four layers separate:

1. **Task decomposition:** flat immutable task IDs and one bounded execution-time refinement generation.
2. **Graph scheduling:** typed nodes, acyclic dependencies, bounded conditional routes, persistent node/edge state, and a deterministic ready frontier.
3. **Parallel analysis:** pure static validation/conflict analysis over ready write missions, followed by a launch-gated wave proposal.
4. **Execution coordination:** runtime-neutral directives, parent-confirmed attempts, leases, branches/workspaces/tasks, node/worker-result validation, serial integration, and next-frontier recomputation under action-specific authorization.

## Reference Routing

- Read `references/contract-and-traceability.md` when source handoff, contract freeze, trace IDs, permissions, or file placement matters.
- Read `references/execution-state-model.md` before creating or changing canonical PLAN/RUN manifests, authorization state, phases, runtime capability fields, or integration state.
- Read `references/graph-orchestration.md` for PLAN schema v4, RUN schema v8 or v9, typed nodes, conditional routes, mixed Codex/Claude execution, node retry, or subgraph replay.
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
small direct work      -> no management files
large sequential work -> docs/goal/RUN.md
large multi-mission   -> docs/goal/PLAN.md + docs/goal/RUN.md
binary UI evidence    -> docs/goal/evidence/** only when artifacts exist
worktree workers      -> temporary per-mission reports only while integration needs them
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

- `scripts/validate_harness_plan.py --plan <PLAN.md> [--run <RUN.md>] [--repo-root <repo-root>]` validates manifests, trace/DAG/refinement structure, scopes/resources, authorization shape, plan/run digest consistency, complete-run closeout, and schema-v9 screenshot file/hash evidence.
- `scripts/select_parallel_missions.py --plan <PLAN.md> --run <RUN.md>` computes a deterministic launch-gated frontier, static conflict graph, wave proposal, and one tool-agnostic launch directive per selected mission.
- `scripts/select_ready_nodes.py --plan <PLAN.md> --run <RUN.md>` computes the typed-graph frontier, per-node runtime bindings, write conflicts, and runtime-neutral directives for PLAN v4/RUN v8 or v9.
- `scripts/validate_worker_result.py --plan <PLAN.md> --run <RUN.md> --result <REPORT.md> --observed-head-sha <sha> --observed-changed-file <path>... --ancestry-confirmed` checks a worker integration candidate against parent-observed facts. For `external_codex_agent`, also pass `--observed-worktree-path`, `--observed-branch-ref`, and `--git-common-dir-confirmed` after independently checking the retained allocation.
- `scripts/select_verifiers.py --plan <PLAN.md> --mission-id <id> --changed-file <path>... [--head-sha <sha>]` applies task/worker `changed_files` selection to parent-observed paths and emits deterministic selected and not-applicable verifier IDs. It never weakens integration, batch, final, release, migration, or smoke gates.
- `scripts/verifier_runtime.py --request <request.json>` runs one local verifier and may reuse a session-only exact PASS when the verifier opts into `session_exact`, the checkout is clean, the parent marks the command cache-safe, and every immutable execution-key input matches. The explicit cache root must be outside the checkout.
- `scripts/validate_node_result.py --plan <PLAN.md> --run <RUN.md> --result <RESULT.json>` validates graph/attempt identity and the declared node outcome before worker integration validation.
- `scripts/claude_runtime_bridge.py preflight` proves a Codex parent can invoke the Claude Code Workflow tool without repository edits. `run-wave --plan <PLAN.md> --run <RUN.md> --request <wave.json>` reloads and validates canonical PLAN/RUN state before consuming an authorized immutable graph-wave request after worktrees and leases are allocated.
- `scripts/validate_codex_wave.py --mode preflight` reloads canonical PLAN v4/RUN v9, requires exact `runtime:codex` and `worker:preallocation` authorization plus run-wide worktree/branch allocation grants, and converts an observed `unknown` cc-codex plugin record into the complete arguments for `assets/templates/CLAUDE_CODEX_PREFLIGHT.template.js`. The template runs the read-only foreground probe in an isolated Agent worktree. Only a successful marker allows the parent to record the runtime as available. Wave mode requires a pending worker allocation with null worktree/branch fields and derives mission-only arguments from canonical state. `assets/templates/CLAUDE_CODEX_GRAPH_WORKFLOW.template.js` launches one fresh cc-codex Agent per guarded write mission and returns marked result candidates. The parent verifies and records the runtime-assigned path/ref after the result. External Codex reviews are disabled in v1; select another allowed provider or defer.

These validators, selectors, and bridge helpers are Python-stdlib-only. The validation and selection paths are read-only and emit sorted JSON without timestamps; the bridge invokes the separately authorized external runtime but never creates or modifies Git refs, worktrees, Codex tasks, PLAN, or RUN. The cc-codex templates depend on the installed `codex:codex-rescue` agent and its foreground stdout contract; they do not add an App Server client or expose an inner Codex thread ID. The parent observes live facts and performs authorized mutations only after reviewing their output.

## Default Runtime And Wave Policy

Apply this policy only after the Project Size Gate classifies the work as large and the accepted plan contains multiple missions, unless the user explicitly requests a lower worker budget:

1. Before the first production edit or worker launch, proactively inspect the current-session native tool surface, permission boundary, worker slots, worktree isolation, completion channel, Git state, and runtime resources. Do not wait until delegation appears useful.
2. Record every observed host driver under `runtime_adapter` independently of authorization. In Codex, usable project lookup plus thread create/read/message surfaces prove `app_threads`; child-agent tools prove `subagents`. Do not probe an external runtime merely because it may be available. In schema v8 or v9, preflight only the provider required by the user request or current ready frontier. When a ready node's PLAN runtime policy calls for external Claude, run the bridge preflight before ready-node selection; a Codex parent records Claude Code only after that preflight. For cc-codex, first record observed plugin metadata with status `unknown`, then run `validate_codex_wave.py --mode preflight`; it requires exact external-runtime and preallocation subagent authorization plus run-wide worktree/branch allocation grants and emits the complete arguments for `CLAUDE_CODEX_PREFLIGHT.template.js`. A Claude Code parent records Codex as available only after that template invokes `codex:codex-rescue` with `--wait --fresh` in an isolated Agent worktree and validates the marker contract. A CLI path, plugin file, or version alone is not proof. Missing authorization must never make an available driver disappear.
3. Use three as the configured plan-backed write-worker maximum. The effective wave may contain fewer missions because it is still capped by observed slots, isolation capacity, dependency readiness, conflicts, permission boundaries, and the user's lower explicit limit.
4. For new PLAN-v4 runtime-worker nodes, prefer Codex `gpt-5.6-terra` with `xhigh` reasoning for general-purpose nodes and backend implementation; keep Claude Code `sonnet` as the availability fallback. For frontend/UI implementation, use the pinned Claude model `claude-fable-5` with `high` reasoning and Codex `gpt-5.6-sol` with `xhigh` reasoning as the availability fallback. Choose review effort by risk instead of assigning every review `xhigh`: routine deterministic `backend_code` review uses Codex `gpt-5.6-terra` with `medium`, routine `frontend_code` review uses `claude-fable-5` with `medium`, and routine visual review uses `claude-fable-5` with `medium`. Raise review effort to `high` or `xhigh` only for security, migration, difficult correctness, broad architecture, or genuinely ambiguous visual judgment. Preserve any explicit user choice and let Plan Mode replace these defaults per node when mission complexity, risk, latency, or cost calls for a different observed option.
5. Immediately after `plan_readiness: ready`, validate PLAN/RUN and compute the dependency-ready conflict graph. For PLAN v4/RUN v8 or v9, run `select_ready_nodes.py`; for older readable plans, run `select_parallel_missions.py`. Select up to three nonconflicting write missions in deterministic order before starting a production task.
6. For execution-intent work in a shared repository, default `landing.mode` to `pull_request` unless the user explicitly requests local-only delivery. At Plan Readiness, inspect the remote, branch rules, required checks, Codex review availability, and repository auto-merge setting, then request every missing launch and landing action in one authorization checkpoint. Before a PR exists, scope `manage_pr_review` and `merge_pr` to `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` in RUN schema v6 or newer; do not use `*` merely because the PR URL is not known. Record each approved action separately in the ledger; the bundled request is not blanket permission.
7. The normal landing bundle is `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `create_pr`, `manage_pr_review`, and `merge_pr`, plus the selected route's worker/worktree actions. Include `configure_repository` in the same checkpoint only when the observed repository needs an exact configuration change for the requested flow. When full deployed Cloudflare delivery is requested and PLAN declares both targets, use the same one-time checkpoint to ask separately for `deploy` on `environment:development` and `environment:production`; recording them in the same answer does not merge deploy into push or merge authorization. Keep archival, worktree removal, and branch deletion outside this bundle.
8. When the selected launch route and landing path are already authorized, accept the wave, consume every launch directive, and continue through review and merge without another confirmation. When either exact bundle is missing, request the complete missing-action set once, pause at that boundary, record the answer, and rerun selection. Do not silently downgrade merely because authorization is missing.
9. Fall back to fewer workers, sequential parent execution, or local-only closeout only when the user declines the relevant bundle or live capability, isolation, permission, dependency, conflict, resource, or repository evidence requires it. Record the exact reason.
10. Never run more than one write-capable parent or subagent in `shared_checkout`. Parallel writes require isolated worktrees and durable authorized branch/commit handoff.

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

General execution authorization and action authorization are separate. Schema v8 adds `invoke_external_runtime`; keep these exact ledger keys in a new graph RUN, all `false` by default:

```text
invoke_external_runtime
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

`invoke_external_runtime` requires an exact `runtime:<provider>` target and does not replace `spawn_subagents`, workspace, branch, commit, integration, or lifecycle authorization. Use it when a Codex parent calls Claude Code, when a Claude Code parent calls Codex through cc-codex, or when another provider crosses a separate cost, data, or permission boundary. A write-capable `external_codex_agent` also requires `spawn_subagents`, `create_app_managed_worktrees`, `create_local_branches`, and `create_local_commits`, but not `create_user_owned_tasks`; it is a child Agent, not a user-owned Codex app task. Older readable RUN schemas retain their original ledger.

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
Project size: small | large
Size-gate evidence:
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

- Use Direct Work for small work when execution is explicit.
- Use `RUN.md` for large work with several verified sequential steps or work likely to cross compaction.
- Add `PLAN.md` for large work with a full PRD, multiple missions, frontend/backend sequencing, high risk, or durable handoff.
- Promote RUN-only work before delegating a write mission, accepting execution-time refinement, or selecting parallel work.
- For unclear existing-app improvement, audit first and record ranked candidates in `RUN.md`.
- For plan-backed multi-mission execution, set the configured worker budget to three by default, then reduce it only from observed capacity, conflicts, dependencies, permissions, or an explicit user limit.

### 2. Plan The Complete PRD Before Execution

For a PRD-backed build, read all canonical requirements before changing production code. Plan every must-have requirement, not only the first feature.

Build the plan in this order:

1. Register PRD, Builder UX Direction, architecture, wireframe, design-system, page UI, user-research/usability evidence when it exists, and current-code sources.
2. Extract every in-scope requirement, preserve its priority, and assign stable trace IDs, including `UX-*` traces for critical user tasks, interaction/recovery expectations, and required validation; explicitly mark optional or deferred requirements instead of dropping them.
3. Identify shared foundations: environment, schema, auth, permissions, design tokens, app shell, API clients, fixtures, and test harness.
4. Draw the typed execution graph between backend, frontend, data, integrations, UI states, verification, approval, and release work. Keep dependency edges acyclic; express correction paths as bounded outcome routes with an exit. When frontend and backend are both in scope, plan separate implementation missions and separate `frontend_code` and `backend_code` runtime review nodes; for UI work, add a `visual` review after integration or preview. Combine reviews only with an explicit single-surface rationale. Every runtime review is read-only, names its mission IDs and repository scope, binds one exact reviewed SHA in `review_workers[]`, and routes `fix_required` to a bounded repair path. For every runtime-worker node, Plan Mode chooses allowed/preferred providers and may set provider-specific model options and reasoning effort for Codex or Claude Code. Treat a user model choice as controlling; otherwise choose for mission complexity and latency/cost, while leaving current model support to destination-host validation. For Cloudflare delivery, define isolated development and production Workers, bindings, auth/payment modes, migration order, exact source SHAs, and deployed-environment verification.
5. Decompose the complete scope into vertical missions and independently verifiable tasks.
6. Give missions and tasks opaque immutable IDs; keep tasks flat, and express hierarchy only through refinement lineage.
7. Freeze every source with a content SHA-256, an immutable upstream revision, or both. Define exact/subtree write scope, deny scope, complete serialized/runtime resource claims, pass signal, evidence, risks, and stop conditions for every mission. The mission is always the parallel write unit.
8. Define task/worker, mission-integration, batch, and final verifiers as structured `cwd` plus `argv`, never shell prose that requires interpretation.
9. Populate the complete static definitions and graph in `PLAN.md`, then initialize every node/edge, mission, and task state in `RUN.md`; leave only execution-time bindings and discoveries to bounded refinement.

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
- Typed graph nodes cover every mission and required verifier/approval/external/lifecycle step. Dependency edges are explicit and acyclic; every route cycle is bounded and has an exit.
- Task dependencies and refinement lineage are explicit, acyclic, and valid; accepted child tasks are at most refinement generation 1.
- Frontend/backend/data boundaries and their integration points are defined.
- Shared foundations and migration order are identified.
- Required UI routes, breakpoints, states, and visual evidence are planned.
- Each mission has an allowed write scope and deterministic verifier, or an explicit `UNVALIDATED` risk.
- Every mission eligible for fan-out declares `resource_inventory_complete: true`, supported write-scope claims, and all serialized/runtime resources it may mutate.
- Blocking requirements conflicts and approval needs are resolved or clearly surfaced.
- Final E2E, regression, release, and residual-risk gates are present. When a primary journey exists, name its automated E2E command, current-head CI check, target environment, retained evidence, and manual-smoke disposition.
- For a deployable Cloudflare application, PLAN schema v4 declares both release targets and RUN schema v9 initializes both deployment states. Development binds to the current PR head after CI; production depends on development PASS and binds to merged `main`. Exact deploy targets and any repository workflow change are surfaced as separate authorization needs.
- The shipped plan validator passes; the canonical RUN plan ID, revision, and digest match PLAN.

At the gate:

- `plan-only` or `plan-then-stop`: set run status to `ready`, keep `execution_authorized: false`, report the proposed first mission and stop.
- `plan-then-execute`: make one Plan Readiness authorization checkpoint for the exact execution, launch, and pull-request landing actions; record the explicit decision, set run status to `running` only when the next actions are authorized, then apply the Default Runtime And Wave Policy before beginning any production task.
- `execute-ready-plan`: verify that the plan is still current, make the same one-time missing-action checkpoint, record the explicit decision, set run status to `running` only when the next actions are authorized, then apply the Default Runtime And Wave Policy before beginning any production task.

### 4. Execute The Ready Plan

Prefer thin vertical missions connecting behavior, UI/data, and verification. Keep tasks sequential inside each mission. For PLAN v4, execute only nodes emitted by the current graph frontier; pass ready write missions through the existing conflict gate before launch. Use sequential parent execution only as the recorded fallback. Execute one ready task at a time within each leased mission:

```text
observe -> confirm plan/graph/digest/authorization -> allocate node attempt -> lease ready mission -> choose smallest ready task -> implement -> verify -> report node and worker result -> integrate if authorized -> verify integration -> update RUN -> traverse outcome edge -> recompute
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
- A graph retry creates a new attempt ID and preserves the prior result. A route edge never revives an expired lease, authorization, verifier result, or head binding. Stop when the node or traversal bound is exhausted.
- At task and worker level, run only focused verifiers selected from the parent-observed changed files when they declare `selection.mode: "changed_files"`. Omitted selection metadata means `always`; a worker claim never decides applicability.
- After serial integration, run that mission's integration surface. Keep PLAN batch verifiers for real cross-mission behavior, not repeated task suites. Run broad regression, browser E2E, visual/UI evidence, and release gates only on the final current head.
- A deterministic local verifier may opt into `cache.mode: "session_exact"` only with literal `pass_signal: "exit 0"`. Reuse one execution only when run, PLAN/digest, graph revision, base, exact head, changed files, trust domain, checkout role, cwd, ordered argv, executable identity, platform, and selected environment values all match. A dirty checkout, malformed entry, failure, timeout, or changed input runs fresh.

### 5. Orchestrate Only When Needed

Keep one parent-owned `PLAN.md` and `RUN.md`; workers never edit either. Treat the stable planner/worker/reviewer/approval/integrator/lifecycle responsibilities as the org graph and the current PLAN/RUN nodes, edges, attempts, and evidence as the temporary work graph. Do not create a second scheduler or graph store.

- Fan out read-only planning only when `spawn_subagents` is authorized. Keep mutating generators and shared-state tests serialized even when their intended source edits are read-only.
- Before choosing a launch primitive for large work, proactively detect the host session and record a runtime adapter capability snapshot before the first production edit. Native Codex project/thread tools prove `app_threads`; the Workflow tool in a Claude Code host proves `dynamic_workflow`; current-session child-agent tools prove `subagents`. In schema v8 or v9, a Codex parent runs the no-edit Claude bridge preflight before ready-node selection and records Claude under `external_runtimes` only when the user request or a ready node's PLAN runtime policy calls for external Claude. Pass one explicit repository-external `--session-cache-root` for that harness session so an unchanged Claude executable/version and exact successful preflight are reused. A failed `preflight --force-refresh` revokes stale disk reuse for that capability scope; a later fresh PASS replaces the stale entry and restores exact disk reuse. An installed binary, version, directory name, model name, cached preflight, or missing authorization never proves or removes launch authorization. Capability detection never grants authorization, and `run-wave` still reloads current PLAN/RUN and validates the exact attempt, base, runtime binding, permission boundary, and actions before every launch.
- Default plan-backed multi-mission execution to a configured maximum of three isolated write workers. `worker_runtime: parent`, `workspace_mode: shared_checkout`, and one writer remain the compact or evidence-forced fallback. For authorized multi-mission or program execution in the Codex app, prefer `app_task` + `app_managed_worktree` + `thread_poll` when current thread tools, isolation, and completion polling are available.
- For parallel writes, first validate PLAN/RUN. Use `scripts/select_ready_nodes.py` for PLAN v4/RUN v8 or v9 and `scripts/select_parallel_missions.py` for older readable schemas, then bind the proposed wave to the current plan/graph revision, digest, and fixed batch base SHA.
- For PLAN-v4 graph workers, consume the selector's complete runtime binding. Copy mission bindings to `workers[]` and read-only verifier bindings to `review_workers[]`. Pass non-null Codex model/reasoning values to task creation as `model`/`thinking`, pass non-null Claude effort as `--effort`, and group external Claude nodes into separate immutable waves by selected model, effort, and derived tool profile. Mission and review profiles require `EnterWorktree` so every worker enters its exact assigned checkout before repository reads. Review profiles still omit `Edit`, `Write`, `NotebookEdit`, and `Bash`. Do not silently substitute a model, effort, or wider tool profile rejected by the destination host; revise the affected policy and reselect.
- Do not stop after printing a non-empty app-task wave. After the parent rechecks live facts, records the accepted wave, allocates leases, and verifies the explicit pre-allocation `*` grant for app-assigned task/worktree identities plus every concrete target already known, consume every `launch_directives` entry: resolve the current Codex project once, create one worktree thread per selected mission with the complete `WORKER_GOAL.template.md` handoff as its initial prompt, and record the returned thread/client identity in the RUN worker record. A selector directive is not authorization and never creates the thread itself.
- App-task fan-out requires `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `spawn_subagents` to cover the selected mission and allocated targets. Request this bundle once at readiness with explicit run/mission/target scope when it is missing; pause and rerun selection after the answer instead of silently choosing a lower runtime driver. Do not repeatedly ask for each worker when an unexpired run-wide grant already matches. Keep integration, push, PR, merge, deploy, archival, and cleanup permissions separate.
- Every launched app-task mission receives an explicit depth-one, read-only nested-subagent policy. When capability is already observed, the worker must start at least one useful child for a non-trivial mission and may use up to three across exploration, documentation/API research, test/log analysis, and proposed-diff review. When capability is unknown, launch a no-production-edit handshake, poll the task, record the result, then send an enabled or disabled policy before implementation. If the required capability is unavailable, do not silently run the promised multi-agent shape; record the downgrade and use the sequential parent fallback.
- Poll app-task threads through the available read-thread/status surface with backoff, preserve blockers and partial results, and send follow-up instructions through the available thread-message surface. Never claim an automatic callback when only polling exists. A terminal thread is still only a worker result; validate its reported head, actual diff, scope, ancestry, and verifiers before integration.
- For an older Claude Code-hosted `dynamic_workflow` route, use `subagent` + `parent_managed_worktree` + `agent_result`, allocate one authorized worktree/branch/lease per mission under `.claude/worktrees/<run>-<mission>-<attempt>/`, and invoke `CLAUDE_DYNAMIC_WORKFLOW.template.js` once for the accepted wave. Include `EnterWorktree`; require each mission to enter and verify its assigned existing worktree before any repository action. Keep that adapter flat and forbid mission-agent delegation.
- For a Claude Code host `dynamic_workflow` route, keep the existing flat schema-v6-or-v7 adapter. For a PLAN-v4 graph wave, use `CLAUDE_GRAPH_WORKFLOW.template.js`; include run, plan, graph, batch-base, node, and attempt identity in every result, and retain a missing agent result as an explicit failure candidate.
- For a Codex parent selecting an observed external Claude runtime, require `invoke_external_runtime` for `runtime:claude_code` plus `spawn_subagents` and the parent-managed worktree/branch/commit actions. Run `claude_runtime_bridge.py preflight` before recording availability. After the parent allocates graph attempts, leases, branches, and worktrees, pass one immutable accepted wave to `run-wave`. Record the Workflow run/task ID only after the bridge matches the final wrapper to the raw Workflow tool result from Claude's verbose event stream. The outer Claude session must emit exactly one `Workflow` call and no other tool calls; the matching result and final wrapper must follow it in order. Also record the script digest, graph/base binding, node-to-attempt bindings, model/effort, tool profile, status, and available metrics in optional RUN `workflow_runs`; never invent runtime IDs. The bridge and Claude workflow never edit PLAN/RUN or integrate; the Codex parent validates every node wrapper, worker result, and live Git fact before serial integration.
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

Converge local deterministic checks and exact-SHA runtime code review before starting the expensive final browser/UI matrix. If review requires a repair, integrate it, bind reviews to the new head, and rerun only the invalidated layers. Start broad regression, browser E2E, screenshot capture, and visual review only after code-review repair loops are closed. Any later head change still invalidates current-head CI, review, E2E, and UI evidence and requires fresh proof.

For UI-bearing work, record in `RUN.md`:

- Builder UX Direction source, owner, decision status, and unresolved validation needs.
- Primary journey and target routes.
- Required breakpoints.
- Ready, loading, empty, error, disabled, permission, and long-running states that apply.
- Browser interaction, console/page/network health, accessibility, and design comparison.
- Direction conformance separately from usability evidence; when usability validation is required, record the method, representative participant/source, task scenario, target, actual result, and redacted evidence.
- For every required UI surface, retain one real screenshot for each planned route-by-breakpoint-by-state combination. Record its repo-relative path, SHA-256, exact integration head SHA, and PASS status in canonical schema-v9 `ui_evidence`. A trace, log, or prose review is supplemental and does not replace the screenshot.
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

For a PLAN schema-v4 Cloudflare release, use the PR head and merged base as two explicit release sources:

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
- Schema-v9 `batch_gate_results` and `final_gate_results` IDs exactly match their PLAN verifier groups; every entry is PASS on `integration_head_sha` with non-empty evidence. A changed integration head invalidates an earlier PASS immediately, even before closeout.
- Skipped or `UNVALIDATED` gates include reason, risk, and acceptance status.
- Primary journey and relevant platform gates pass.
- Every `evidence_gate: required` UI surface has PASS screenshot coverage for its full planned breakpoint-by-state matrix, and each file exists under `docs/goal/evidence/` with the recorded SHA-256.
- A complete pull-request run is merged with current-head CI and review evidence, and its `merge_pr` authorization covers every mission plus the exact `pr:<full-PR-URL>` target; a complete PLAN-v4 graph run has only succeeded, skipped, or superseded nodes, terminal edges, no retained node blocker, and no active or blocked review worker.
- Required automated E2E is PASS on the current integration or PR head. Any duplicate manual smoke it replaces is recorded as `not required - covered by current-head E2E`; uncovered or environment-specific smoke still passes separately.
- `RUN.md` records final status, evidence, changed files, commits, residual risk, and landing state.
- In pull-request mode, the final branch was reviewed locally before push, and current-head CI plus GitHub review are recorded separately. A new push invalidates any earlier PASS tied to another SHA.
- Only the parent integration branch lands by default. In pull-request mode, `integration.branch` must be the PR head branch and must differ from the base branch. Worker branches remain local and do not open their own PRs unless the plan gives them a separate landing target.
- `merge_status: ready` and `merged` both preserve the same current-head gate: the PR head matches the integration head, check and review PASS records match that PR head, and no blocking finding or unresolved thread remains. Schemas v4 through v9 may set `auto_merge_requested: true` only after that gate passes, with `auto_merge_head_sha` equal to the current PR head. Enable squash auto-merge with an exact head-SHA match only when `merge_pr` covers the exact `pr:<full-PR-URL>` and any retained `future-pr:` target matches its repository, base, and head; any new push resets the request and requires fresh CI and review. `merged` additionally records the merged PR state and merge SHA. Merge and deploy still require their own authorization.
- When PLAN declares a Cloudflare release, both development and production deployment states are PASS with exact SHA, Worker, URL, version, migration, verification, evidence, and matching deploy authorization. A successful upload without deployed-environment verification is not PASS.
- New plan-backed files use PLAN schema v4 and RUN schema v9. Schema versions expose fields but do not enable unrelated release behavior: omit `release` and `deployments` together for non-Cloudflare or non-deployable work. When PLAN declares a Cloudflare `release`, RUN must include matching `deployments`. Valid PLAN schemas v2 and v3 and RUN schemas v2 through v8 remain readable. A complete run requires execution intent, ready/frozen inputs, integrated or superseded missions, mission-recorded or superseded tasks, no blockers or open wave, and an integration head. After merge, bind `post_merge_cleanup` to the exact merged PR head and a freshly observed base branch. Remove only an exact clean parent-managed linked worktree under `remove_worktrees`, then switch the primary checkout to the base and delete only the exact local feature branch under `delete_branches`. Record cleanup as complete, deferred, or not applicable; `not_applicable` requires no matching linked worktree, never remove the primary checkout, and keep app-managed retention separate.

## Output Shape

```text
Intent and execution authorization:
Project size and size-gate evidence:
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
