# Runtime, Worktree, And Thread Orchestration

Use this reference when the harness runs multiple missions, delegates to workers, or needs workspace isolation. Read `execution-state-model.md` and `parallel-mission-selection.md` first.

## System Review And Route Comes First

Before reading this runtime/worktree procedure, the parent completes the read-only `System Review And Route` stage defined in `execution-state-model.md`. Small work never reaches this reference. A large route enters the existing PLAN-v6/RUN-v11 graph; a no-agent large route uses the parent-owned `sequential_parent` path below, one mission at a time.

## Describe Capabilities, Not Product Labels

Record three independent fields for each run or worker:

```text
worker_runtime: parent | subagent | app_task
workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
completion_channel: agent_result | thread_poll | report_file | user_relay
```

These fields are orthogonal. Do not infer workspace isolation, completion notification, or cleanup behavior from the word "worker" or from a product name.

- `subagent` is a parent-managed child. It can return an `agent_result`, but still shares the checkout unless an isolated workspace was deliberately provided.
- `app_task` is an independent, user-owned Codex task with its own conversation in the left sidebar. A generic skill cannot promise an automatic callback to the parent task; use polling, a report file, or user relay unless an App Server integration supplies events.
- `parent` is the sequential route when delegation is unavailable; its plan-backed mission still requires a parent-managed worktree.

If a requested combination is unsupported, downgrade to sequential parent execution and record the reason. Never silently simulate parallel isolation in a shared checkout.

## Runtime Adapter Routing

RUN v11 records the observed host provider separately from the portable axes under `runtime_capabilities.runtime_adapter`:

```text
provider: codex | claude_code | pi | generic
available_drivers: app_threads | dynamic_workflow | subagents | sequential_parent
detection_source: observed | explicit | fallback
```

Always include `sequential_parent` as the safe fallback. Select the first observed driver in this fixed order:

```text
codex: app_threads -> subagents -> sequential_parent
claude_code: dynamic_workflow -> subagents -> sequential_parent
generic: subagents -> sequential_parent
```

The selected driver must match the axes recorded in RUN. `app_threads` maps to `app_task` + `app_managed_worktree` + `thread_poll`. `dynamic_workflow` maps to `subagent` + `parent_managed_worktree` + `agent_result`. Direct `subagents` use a supported shared or parent-managed workspace and result/report channel. `sequential_parent` maps to the existing PLAN `runtime_worker` mission plus a parent-owned RUN binding of `parent` + `parent_managed_worktree` + `agent_result` solely for lease/state validation. It is not a delegated or spawned worker, does not require `spawn_subagents`, and blocks when the required parent-managed worktree is unavailable or unauthorized; `shared_checkout` is not a fallback for this route. Do not route from a product label alone; record how the capability was observed and block if the selected primitive is missing at launch.

Detect the host that is executing the Harness. Current-session Codex project/thread tools prove `app_threads`; the Claude Code `Workflow` tool and a supported runtime prove `dynamic_workflow`; current-session child-agent tools prove `subagents`. In Pi, the installed subagent workflow must also return a terminal child result before `subagents` is recorded. Codex task tools may be lazy-loaded, so use the current tool-discovery surface to search for project listing, top-level task creation, messaging, and thread waiting before declaring `app_threads` missing. Do not select a provider merely because its CLI is installed or its config directory exists. When native host identity is unavailable, use an explicit provider only from a user/config source; otherwise record `generic` fallback.

For a RUN-v11 observed Codex execution that may select two writers, write the full eight-entry `capability_probe` described by `execution-state-model.md`; do not summarize several surfaces into one claim. A provably sequential route may omit unused surfaces, but still records enough available facts to prove a selected app-thread or subagent driver (or records the native `sequential_parent` route). `app_threads` is derived only from available project listing, thread creation/read/message/wait, and app-managed-worktree support. Direct `subagents` is derived separately from spawn and result support. Before a parallel-capable ready/running run validates, every surface must be `available` or `unavailable` with evidence, and `available_drivers` must exactly match the derived Codex priority list. Missing, `unobserved`, under-reported, or over-claimed required snapshots block execution.

Perform this detection proactively before the first production edit in every plan-backed run, using the lightweight selected-driver check for a sequential route. Record all observed drivers even when their action authorizations are false. Missing authorization is a launch gap, not evidence that `app_threads`, `dynamic_workflow`, or `subagents` is unavailable.

A PLAN node is eligible on the current host exactly when its `allowed_providers` includes that host. `preferred_provider` is advisory ordering among allowed hosts and never blocks an otherwise allowed current host. There is no cross-host fallback and no mechanism to invoke the other runtime from this one: a ready node whose allowed providers do not include the current host is not executable here. Report it as deferred with `runtime_unavailable` and leave it for a run hosted by an allowed adapter.

## Default Plan-Backed Wave

After Plan Readiness and execution authorization, run validation and deterministic mission selection before starting any production task. Set the configured maximum generously high, then let live slots, worktree isolation, dependencies, conflicts, runtime resources, permission boundaries, and any explicit user limit determine the effective wave.

If the preferred route's task/worktree/branch/commit bundle is missing, request it once for the run and pause. Retain the observed route while waiting, record the answer, and rerun selection. When it is already authorized, create every selected worker without another confirmation. Fall back to fewer workers or sequential parent execution only after user refusal or concrete runtime evidence requires it.

## Parent And Worker Ownership

The parent/coordinator exclusively owns:

- source intake, contract freeze, and plan revisions;
- canonical `PLAN.md` and `RUN.md` writes;
- authorization checks and runtime capability detection;
- provider/driver routing and Dynamic Workflow argument construction;
- batch-base selection, wave confirmation, leases, and worker prompts;
- branch/worktree creation when authorized;
- worker-result validation, integration order, conflict handling, and E2E verification;
- push and manual cleanup actions when separately authorized.

A worker owns one mission lease only:

- its assigned workspace and allowed mission write scope;
- task-level implementation, verification, and authorized task commits;
- no child delegation; request any independent explorer or reviewer from the parent;
- a structured result or `REFINEMENT_REQUEST` returned through the declared completion channel.

Workers must not edit the parent-owned `PLAN.md` or `RUN.md`, expand their own scope, or pull, rebase, merge, push, or clean up unless that exact action is separately authorized and assigned. Nothing prevents the write at the filesystem level; it is detected on the way back, when `validate_worker_result.py` rejects a parent-owned path in `changed_files` as `parent_owned_file`. That detection depends on the parent passing the real observed diff, not the worker's own claim.

## Mode Selection

### Shared checkout

Reserve `shared_checkout` for genuinely small direct work (see the Project Size Gate) or parallel read-only analysis. It is not an eligible workspace for plan-backed mission writes, including `sequential_parent`.

- Do not assign a plan-backed write lease in this checkout. Read-only inspection may run concurrently when it does not mutate shared state.
- Parallel read-only workers may inspect the same checkout if they do not run mutating generators, formatters, services, or tests with shared state.
- Task completion may integrate immediately only after the same worker-result and integration gates are applied.

### Parent-managed worktree

Default every plan-backed mission write to `parent_managed_worktree`, whether one mission is worked at a time or several run concurrently — `create_local_worktrees` authorization covers this even for a single sequential mission. A no-agent `sequential_parent` route requires this same isolated worktree contract while the parent itself writes the mission and serializes the budget at one; if it cannot be created or authorized, the route blocks. Create each worktree from the recorded `batch_base_sha` on the resolved integration branch. Resolve that exact non-default branch from repository governance or the user's instruction; if neither source names it, ask before branch creation and never synthesize a fixed prefix or name. Cut it from the recorded current default-branch SHA. The first wave's `batch_base_sha` is the default-branch SHA recorded at run start; each later wave re-anchors its batch base to the current integration head. The primary integration checkout is a merge target, never a direct implementation surface: each mission's worktree branch receives an exact-head read-only review before it may merge there.

- The parent creates every worktree from the same recorded `batch_base_sha`; portable write handoff also requires `create_local_branches` and `create_local_commits`, because the parent integrates a durable committed head rather than an uncommitted patch.
- The parent records the exact path, branch/ref, lease, ports, databases, fixtures, and external resource claims.
- Workers never synchronize against the base branch. The parent handles any unavoidable mid-run sync at a task boundary and reruns affected verifiers.
- A worktree isolates tracked files, not ports, databases, environment files, caches, queues, buckets, tenants, or third-party sandboxes.

### App-managed worktree

Use `app_managed_worktree` only when the runtime exposes it and `create_app_managed_worktrees` is explicitly authorized. The other required actions depend on who owns the worker:

- A user-owned Codex app task requires `create_user_owned_tasks` and uses `app_task` + `thread_poll` or another declared task channel.

For user-owned Codex app tasks:

- Record the returned task/thread identity and completion channel. Never invent an identity from the mission ID.
- Use one top-level task/thread with one app-managed worktree per selected Harness mission. It appears as an independent conversation in the Codex left sidebar. Direct subagents of the coordinator do not satisfy this boundary.
- Managed worktrees may begin detached. If durable commits or handoff are required, create an authorized branch or durable ref early; do not leave unique work reachable only from a detached checkout.
- Do not launch app-managed write fan-out unless branch and commit creation are authorized. Otherwise use sequential parent execution; this protocol does not depend on extracting an uncommitted patch from a managed worktree.
- Use the repository's supported ignored-file inclusion mechanism, such as `.worktreeinclude`, only for necessary local files and never to copy tracked files or secrets without permission.
- Treat the app task itself as the sole writer in its managed worktree. Any explorer or reviewer is a separately parent-dispatched read-only sibling; a second writer requires a separately planned mission and isolated worktree.
- Preflight the selected permission mode before task creation. A linked worktree's `.git` file points to metadata in the original repository's Git common directory, which may sit outside the app worktree sandbox; branch creation and commits can therefore prompt even when source edits are inside the worktree. Package caches, system temp, local dev ports, private-network bindings, and Unix sockets are separate surfaces that must also fit the selected boundary.
- Record the effective permission boundary in RUN. Subagents inherit the app task's active mode, and app tasks inherit the parent mode chosen before launch. `Approve for me` changes eligible prompt review but does not widen the sandbox. A later config/composer change does not retroactively update already-running tasks.

The platform controls managed-worktree retention. `remove_worktrees: false` prevents Harness-initiated removal; it cannot override platform lifecycle or automatic retention cleanup. Preserve failed or cancelled worktrees and commits for diagnosis. Never reset or delete them automatically.

Prefer event-driven cross-task completion when the runtime exposes task/thread events, such as Codex App Server notifications, or a cursor-based wait surface. `thread_poll` remains the stable RUN channel label for both cursor waits and its repeated-read fallback. When no event/wait surface exists, use bounded repeated inspection, `report_file`, or `user_relay` and record that limitation and wait time explicitly.

## Flat Parent-Owned Agent Topology

Use one coordination level:

```text
Harness parent -> read-only explorers | mission writers | read-only reviewers
```

Workers and reviewers never spawn or delegate further. RUN-v11 therefore accepts only an omitted or disabled `nested_subagent_policy`. If an app task would benefit from another independent view, it reports that need and waits; the parent may dispatch a bounded read-only sibling under its own authorization and budget.

Every write mission has one worker, one explicit `write_scope` ownership boundary, and one clean exact-base worktree. Before launch, the parent verifies repository identity, branch/ref, HEAD equal to `batch_base_sha`, and empty `git status --porcelain`. Shared API, schema, and type edits are a prerequisite mission: freeze, review, and integrate them before cutting dependent worktrees.

The review, integration, and final-validation gates that follow are defined in `verification-gates.md`.

## Launch Preconditions

Before proposing any write wave, the parent confirms:

```text
canonical PLAN and RUN manifests validate
plan revision and digest match
plan readiness and execution authorization are true
the exact spawn/worktree/branch/commit actions are authorized
integration branch/ref and immutable batch_base_sha are observed
parent dirty files are attributed and do not overlap mission scopes
each new mission worktree has the expected repository/branch/base and a clean status
mission/task dependency DAGs are acyclic
shared APIs, schemas, and types are frozen before dependent write fan-out
resource_inventory_complete is true for every candidate
write/deny scopes use the supported grammar
runtime slots and isolation capacity are known
provider, available drivers, and selected route are observed
required environment and verifier tools are available
selected permission boundary and worker inheritance are observed
linked-worktree Git metadata, temp/cache, network, local-binding, and socket requirements fit that boundary
```

Also inspect the current Git status, worktree list, existing branches/refs, and intended integration head. Stop before overwriting, moving, deleting, resetting, or cleaning anything.

Branch and worktree identities are runtime allocations, not static PLAN truth. Derive collision-resistant names from the run, mission, and attempt, then compare the exact proposed branch and path with observed refs/worktrees before creation. For Claude Dynamic Workflow, place parent-managed worktrees under `.claude/worktrees/<run>-<mission>-<attempt>/` so `EnterWorktree` can bind the child without the outside-worktree confirmation added in current Claude Code releases. Never reuse a branch or directory merely because its human alias looks related. Record the final allocation in RUN worker state.

## Select And Confirm A Wave

Run the pure validator and selector before any mutating Git or Codex action. The selector emits a proposal bound to:

```text
plan_id
plan_revision
plan_digest_sha256
graph_revision
ready_frontier
dispatchable_nodes with per-node launch directives
deferred_nodes with reason codes
conflict_edges with reason codes
```

The selector does not emit a batch base, an effective budget, or a bundled wave. The parent binds the committed `batch_base_sha`, confirms the budget it applied, records the accepted wave in `RUN.md`, assigns leases, and only then creates branches, worktrees, subagents, or app tasks. Scripts must not parse human Markdown tables or mutate Git, Codex, PLAN, or RUN.

When no safe set exists, run the next dependency-ready mission sequentially. Parallel execution is an optimization, not a completion requirement.

## Launch Selected Claude Dynamic Workflow

This section is retained schema-v6-through-v9 context for in-flight legacy runs only. The current mechanics live in `../../fullstack-harness-claude-code/SKILL.md`, which routes by wave composition rather than schema version; read the adapter first. Current selection requires PLAN v6/RUN v11, so current tools never produce a v6-v9 wave — nothing below can fire from a newly selected wave.

When the accepted schema-v6-through-v9 wave routes to `claude_code` + `dynamic_workflow`, use one flat workflow for the selected wave:

1. Confirm Dynamic Workflow is available in the current Claude Code runtime. Treat version support and observed command availability as capability evidence, not authorization.
2. Allocate one authorized parent-managed worktree, durable branch, worker ID, and lease per selected mission from the fixed `batch_base_sha`. The parent owns these mutations and records the concrete identities in RUN.
3. Render the workflow arguments from the accepted selector result and `WORKER_GOAL.template.md` handoffs. Each mission receives its lease ID, branch ref, assigned existing worktree path, scope, tasks, resources, verifiers, permission boundary, and frozen plan/base identity. `CLAUDE_DYNAMIC_WORKFLOW.template.js` has no `EnterWorktree` tool or allowlist; its mission prompt instructs the agent in plain English to enter the existing worktree at that exact path before any repository read, write, or shell action, then verify repository root, branch, and batch base. It returns blocked if it cannot bind; it never creates a replacement worktree or writes in the parent checkout. (The typed-graph route in `CLAUDE_GRAPH_WORKFLOW.template.js` instructs the agent the same way, in prompt text; it differs only in carrying `node_kind`, `tool_profile`, and typed review bindings — see `references/graph-orchestration.md`. Neither route applies a tool allowlist.)
The launcher's `args` object is not the selector's output. `select_ready_nodes.py` emits scheduling facts (`execution_route`, `node_id`, `kind`, `ref`, `launch_kind`, `tool_profile`, `runtime_binding`, `required_actions`); the parent has to add the identities it just minted and the rendered prompt. `execution_route` is derived selection output only; `runtime_driver` remains the transport binding. Per node the flat launcher requires `mission_id`, `lease_id`, `branch_ref`, `worktree_path`, `worker_prompt`, and `model`; the typed-graph launcher additionally requires `node_id`, `node_kind`, `attempt_id`, and `failure_outcome`, and for a review node `review_id`, `review_type`, `reviewed_sha`, `review_path`, `review_scope`, and `required_evidence`.

Two mappings are easy to miss: the selector's `kind` is the launcher's `node_kind`, its `ref` is the launcher's `mission_id`, and `model` must be hoisted out of `runtime_binding` to the top level of the node. `worker_prompt` is the rendered `WORKER_GOAL.template.md` text for that mission — the launcher throws before starting any agent when it is absent.

4. Invoke the Claude Code `Workflow` tool with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and the accepted wave supplied as structured `args`. Its `pipeline()` starts sibling mission agents and returns one complete `WORKER_RESULT` or `REFINEMENT_REQUEST` object per mission through `agent_result`. Save a reusable rendered copy under `.claude/workflows/` only when that project file write is planned and authorized.
5. Do not ask for user input inside the workflow. A mission that needs a contract decision or refined tasks returns a blocked/refinement result; the parent updates PLAN/RUN and starts a later workflow after the decision.
6. Validate every result against live worktree, branch, head, scope, and verifier facts. Integrate accepted mission heads serially and recompute the next wave.

Claude Code currently supports nested subagents, but this schema-v6-through-v9 route intentionally has no nested worker layer and omits `nested_subagents`. The workflow script coordinates sibling mission agents; each remains the sole writer for its lease and is instructed not to delegate. The script does not directly read files, run shell commands, edit PLAN/RUN, integrate, or push. If Dynamic Workflow is unavailable, use the recorded fallback route; do not simulate it with an untracked ad hoc fan-out.

## Launch Selected Codex App Threads

When the accepted wave uses `app_task` + `app_managed_worktree` + `thread_poll`, `../../fullstack-harness-codex/SKILL.md` owns the current launch procedure: project resolution, grant rechecks, prompt construction, task creation, event/cursor waiting, the read-only review, and the correction loop. Read the adapter for those mechanics. This section keeps only the topology rules the procedure must preserve, which do not change with schema version.

- A non-empty selector result is an instruction for the parent to act, not a final report. Never leave a `dispatchable_nodes` entry unlaunched without a recorded reason.
- Use one top-level worktree task/thread per mission, created from the recorded integration branch/ref. Each task owns its own app-managed worktree and appears as an independent conversation in the Codex left sidebar. Coordinator-owned subagents do not satisfy this boundary. Record the returned thread ID or the queued client-thread ID; never invent an identity from the mission ID.
- Read-only explorers and reviewers are parent-dispatched siblings, never children of a mission task. A missing current-head review is an integration blocker.
- Only a mission's own direct pre-integration review may bind to that mission's worktree head. A review covering several missions is a batch review and must bind to an integrated head.
- If the app lacks any required project, thread-create, thread-read, thread-message, or worktree capability, leave the affected directive unlaunched and record the exact capability gap. Fall back to the sequential parent only when the user did not explicitly require independent left-sidebar tasks. When that outer topology was requested, stop and report the missing capability instead of substituting coordinator-owned subagents or sequential execution. Never claim that writing a worker record created a real task.

## Worker Handoff

Use `assets/templates/WORKER_GOAL.template.md`. A complete handoff binds the worker to:

```text
plan revision and digest
mission ID and lease ID
batch base SHA and assigned branch/ref
worker_runtime, workspace_mode, completion_channel
runtime provider and selected driver
required_skills (the mission's skill list, verbatim, or "none")
omitted or explicitly disabled nested-subagent policy; RUN-v11 never enables it
allowed and denied paths
declared serialized/runtime resources
task order and verifier argv/cwd
forbidden parent-owned artifacts
result/refinement schema and stop conditions
```

Prefer structured result data returned directly to the parent. Use temporary `docs/goal/evidence/<mission>/REPORT.md` only when the completion channel or durable handoff requires it; the file contains the exact `## Worker Result Manifest` heading and fenced JSON from the worker template. Record that one path as worker-owned handoff scope; every other PLAN/RUN/evidence state path remains parent-owned. The parent validates claims against observed workspace and Git facts before integration.

## Batch Integration

Integrate selected missions serially, one at a time. A mission integrates as soon as its exact-head review PASSes; it does not wait for the rest of the wave. `merge_rank` and mission-ID order break ties between missions that become ready at the same moment — it is not a queue a finished mission waits in behind a slower one.

1. Receive the worker result through the declared completion channel.
2. Confirm the lease, plan revision/digest, batch base, and observed worker head.
3. Validate ancestry, actual changed paths, denied paths, parent-owned files, resource claims, commits, and worker verifiers.
4. Transition `worker_passed -> integrating` only after result validation succeeds.
5. Integrate onto the current integration head when `integrate_locally` is authorized.
6. Rerun the mission integration verifier on the new head.
7. Record `integrated_sha` and `integration_gate: PASS`, then transition to `integrated`; otherwise record `integration_failed` and stop dependent work.
8. After the wave closes and every selected mission has integrated, run the PLAN-level batch verifiers; stop the next wave if any fail.
9. Reobserve the integration head and recompute the ready frontier/conflict graph before launching another wave.

Never treat a completed task/thread, a worker `PASS`, or a commit on a mission branch as dependency satisfaction. Only the integrated state described in `verification-gates.md` unblocks downstream missions.

## Push And Lifecycle

Push, task archival, worktree removal, and branch deletion are independent authorization actions. Passing verification does not authorize any of them.

- Integrate only exact-head review-passing worker results serially into the exact resolved integration branch. Worker branches and worktrees do not push.
- Review the final diff locally and rerun final gates before pushing. Codex `/review` is a read-only option for uncommitted changes or a branch diff.
- Local-only delivery is the default: it stops after its authorized local branch, commit, integration, and final verification outcome without touching the remote. An explicit remote outcome may use `integration_push`, where the verified integration head is pushed to the run's own branch and the run is complete there. Landing that branch on the default branch is the user's own step, outside this harness.
- `integration.branch` is the only branch field in RUN. It names the exact non-default branch resolved from repository governance or the user's instruction and cut from the current default branch. Refuse a current v10 `push` without explicit remote intent, an exact branch/head grant, or known default-branch identity; also refuse when the target or integration branch equals the observed default branch, and retain the literal `main` fail-safe.
- Start later PRD, UI, and feature work from a fresh, explicitly resolved non-default branch cut from the then-current default branch. Never invent a fixed prefix, make those edits directly on the default branch, or integrate a mission worktree into it locally.
- Preserve user-owned dirty work and unrelated branches/worktrees.
- For manual worktrees, remove only the exact recorded path after integration and only when `remove_worktrees` is true; never force-remove unmerged work.
- Delete only the exact recorded, fully integrated branch when `delete_branches` is true, unless `run.integration.retention == "persistent"`, in which case the branch is preserved rather than deleted.
- Archive only worker tasks explicitly covered by `archive_worker_tasks`.
- Record manual cleanup as complete, deferred, or not authorized. Record app-managed lifecycle separately because platform retention remains outside the harness's control.
