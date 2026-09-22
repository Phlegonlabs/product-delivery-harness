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
- `app_task` is an independent, user-owned app task with its own conversation in the left sidebar. A generic skill cannot promise an automatic callback to the parent task; use polling, a report file, or user relay unless an App Server integration supplies events.
- `parent` is the sequential route when delegation is unavailable; its plan-backed mission still requires a parent-managed worktree.

If a requested combination is unsupported, downgrade to sequential parent execution and record the reason. Never silently simulate parallel isolation in a shared checkout.

## Runtime Adapter Routing

Use the one general contract in `runtime-adapters.md`. Observe the current host's native tools, effective instructions, permission boundary, completion channel and isolation. Record a lowercase provider identity (or `generic` when unknown), ordered `available_drivers`, and `detection_source`. Drivers are `app_threads`, `subagents`, and `sequential_parent`; provider names never choose a driver.

Every advertised delegated driver needs evidenced capability facts before ready/running dispatch. Record only relevant capabilities; no launch grant is implied. Models and effort remain null unless explicitly selected and supported. Requested independent user-owned tasks cannot be replaced by direct subagents or a parent fallback.

The node is eligible on the current host exactly when its `allowed_providers` includes that host. `preferred_provider` is advisory ordering among allowed hosts and never blocks an otherwise allowed current host. Never probe or launch another runtime as a bridge. Driver bindings must match the recorded workspace and completion axes.

## Default Plan-Backed Wave

After Plan Readiness and execution authorization, run validation and deterministic mission selection before starting any production task. Set the configured maximum generously high, then let live slots, worktree isolation, dependencies, conflicts, runtime resources, permission boundaries, and any explicit user limit determine the effective wave.

If the preferred route's task/worktree/branch/commit bundle is missing, request it once for the run and pause. Retain the observed route while waiting, record the answer, and rerun selection. When it is already authorized, create every selected worker without another confirmation. Fall back to fewer workers or sequential parent execution only after user refusal or concrete runtime evidence requires it.

## Parent And Worker Ownership

The parent/coordinator exclusively owns:

- source intake, contract freeze, and plan revisions;
- canonical `PLAN.md` and `RUN.md` writes;
- authorization checks and runtime capability detection;
- observed native capability mapping and bounded packet construction;
- batch-base selection, wave confirmation, leases, and worker prompts;
- non-runtime node reservations/results and lifecycle evidence receipts;
- branch/worktree creation when authorized;
- worker-result validation, integration order, conflict handling, and E2E verification;
- post-archive candidate publication and manual cleanup actions when separately authorized.

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

### Parent-managed worktree

Default every plan-backed mission write to `parent_managed_worktree`, whether one mission is worked at a time or several run concurrently — `create_local_worktrees` authorization covers this even for a single sequential mission. A no-agent `sequential_parent` route requires this same isolated worktree contract while the parent itself writes the mission and serializes the budget at one; if it cannot be created or authorized, the route blocks. Create each worktree from the recorded `batch_base_sha` on the resolved integration branch. Resolve that exact non-default run branch from repository governance or the user's instruction; if neither source names it, ask before branch creation and never synthesize a fixed prefix or name. Per `branch-promotion-contract.md`, cut both initial-delivery and enhancement run branches from observed remote `main`. The first wave uses that recorded base; later waves re-anchor to the current integration head. The primary integration checkout is a merge target, never a direct implementation surface: each mission worktree receives an exact-head read-only review before it may merge there.

- The parent creates every worktree from the same recorded `batch_base_sha`; portable write handoff also requires `create_local_branches` and `create_local_commits`, because the parent integrates a durable committed head rather than an uncommitted patch.
- The parent records the exact path, branch/ref, lease, ports, databases, fixtures, and external resource claims.
- Workers never synchronize against the base branch. The parent handles any unavoidable mid-run sync at a task boundary and reruns affected verifiers.
- A worktree isolates tracked files, not ports, databases, environment files, caches, queues, buckets, tenants, or third-party sandboxes.

### App-managed worktree

Use `app_managed_worktree` only when the runtime exposes it and `create_app_managed_worktrees` is explicitly authorized. The other required actions depend on who owns the worker:

- A user-owned host app task requires `create_user_owned_tasks` and uses `app_task` + `thread_poll` or another declared task channel.

For user-owned host app tasks:

- Record the returned task/thread identity and completion channel, then pass the real ID to `lease-worker --task-thread-id` for an `app_task`. Never invent an identity from the mission ID or pass a task ID to another worker runtime.
- Include run, PLAN revision/digest, wave, and mission identity in the task packet. If task creation returns no usable identity, inspect existing app tasks/worktrees and bind only one exact packet/base match; otherwise block. Never create a duplicate automatically or delete the uncertain task.
- Use one top-level task/thread with one app-managed worktree per selected Harness mission. It appears as an independent conversation in the host task list. Direct subagents of the coordinator do not satisfy this boundary.
- Managed worktrees may begin detached. If durable commits or handoff are required, create an authorized branch or durable ref early; do not leave unique work reachable only from a detached checkout.
- Do not launch app-managed write fan-out unless branch and commit creation are authorized. Otherwise use sequential parent execution; this protocol does not depend on extracting an uncommitted patch from a managed worktree.
- Use the repository's supported ignored-file inclusion mechanism, such as `.worktreeinclude`, only for necessary local files and never to copy tracked files or secrets without permission.
- Treat the app task itself as the sole writer in its managed worktree. Any explorer or reviewer is a separately parent-dispatched read-only sibling; a second writer requires a separately planned mission and isolated worktree.
- Preflight the selected permission mode before task creation. A linked worktree's `.git` file points to metadata in the original repository's Git common directory, which may sit outside the app worktree sandbox; branch creation and commits can therefore prompt even when source edits are inside the worktree. Package caches, system temp, local dev ports, private-network bindings, and Unix sockets are separate surfaces that must also fit the selected boundary.
- Record the effective permission boundary in RUN. Subagents inherit the app task's active mode, and app tasks inherit the parent mode chosen before launch. `Approve for me` changes eligible prompt review but does not widen the sandbox. A later config/composer change does not retroactively update already-running tasks.

The platform controls managed-worktree retention. `remove_worktrees: false` prevents Harness-initiated removal; it cannot override platform lifecycle or automatic retention cleanup. Preserve failed or cancelled worktrees and commits for diagnosis. Never reset or delete them automatically.

Prefer event-driven cross-task completion when the runtime exposes task/thread events, such as native status notifications, or a cursor-based wait surface. `thread_poll` remains the stable RUN channel label for both cursor waits and its repeated-read fallback. When no event/wait surface exists, use bounded repeated inspection, `report_file`, or `user_relay` and record that limitation and wait time explicitly.

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

Branch and worktree identities are runtime allocations, not static PLAN truth. Derive collision-resistant names from the run, mission, and attempt, then compare the exact proposed branch and path with observed refs/worktrees before creation. Choose a parent-managed worktree location compatible with the observed host permissions; verify the child can bind that exact path before repository access. Never reuse a branch or directory merely because its human alias looks related. Record the final allocation in RUN worker state.

## Select And Confirm A Wave

Run the pure validator and selector before any mutating Git or runtime action. The selector emits a proposal bound to:

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

The selector does not emit a batch base, an effective budget, or a bundled wave. The parent binds the committed `batch_base_sha` (the observed parent head), confirms the budget it applied, and records the accepted wave in `RUN.md`. Parent-managed routes then allocate their authorized worktree/branch before `lease-worker`; an app-task route creates the task/worktree first and immediately leases the returned exact identities. The scripted write path uses `harness_transition.py record-observation` (live-Git snapshot), `accept-wave` (reruns selection and accepts the current mission frontier), `lease-worker` (derives and records the complete worker binding and exact identities), `reserve-node-attempt` (reserves approval, external-wait, lifecycle, or deterministic batch/final-verifier work), `record-node-result` (records the matching outcome/evidence and traverses routes), `record-worker-result`, `reject-worker-result`, `record-integration`, and `close-wave`. A selected `worker_passed` mission may close under a surviving `run_complete` grant and integrate afterward; a `wave_closed` grant must first resolve every selected mission. Hand-editing the RUN JSON for these steps is the path the transitions replaced and remains forbidden. Selector and validator scripts do not mutate Git, PLAN, or RUN; `harness_transition.py` is the sole scripted RUN writer. Lifecycle actions execute outside the transition lock and lifecycle targets must already be exact.

When no safe set exists, run the next dependency-ready mission sequentially. Parallel execution is an optimization, not a completion requirement.

## Launch Selected Native Workers

`runtime-adapters.md` owns the observed native launch mapping. The parent accepts the frontier, rechecks exact grants, supplies bounded fresh-context packets, binds real worker identities and assigned checkouts, and validates terminal results. It never substitutes a guessed tool name, model, script or task ID.

User-owned app tasks each receive one clean exact-base app-managed worktree. Direct workers use parent-managed isolation for writes. Resolve ambiguous task creation against existing identities before retrying; never create a duplicate automatically. Every explorer, writer and reviewer remains a parent-dispatched sibling.

Launch all selected siblings before waiting. Prefer terminal events or cursor-based waits, then bounded polling. A result starts validation; it does not prove a PASS. Native resume must first reconcile canonical PLAN/RUN, authorizations, live Git and retained evidence.

## Worker Handoff

Use `assets/templates/WORKER_GOAL.template.md`. A complete handoff binds the worker to:

```text
plan revision and digest
mission ID and lease ID
batch base SHA and assigned branch/ref
worker_runtime, workspace_mode, completion_channel
runtime provider and selected driver
selector-derived model and reasoning effort, plus worker runtime/workspace/completion axes
real app task/thread identity when `worker_runtime: app_task`
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
2. Run `record-worker-result` with the node result, worker result, and retained verifier results. It reads the bound worktree and verifies its branch, head, dirty state, ancestry, changed files, denied and parent-owned paths, resource claims, commits, and verifier evidence before one atomic RUN update.
3. If the candidate itself is stale or cannot be trusted enough to enter that validation path, record the current attempt with guarded `reject-worker-result`; never rewrite RUN by hand.
4. Transition `worker_passed -> integrating` only after `record-worker-result` succeeds.
5. Integrate onto the current integration head when `integrate_locally` is authorized. Keep the integration commit atomic per `commit-convention.md`'s Run-Wide Atomicity rule — reviewed mission heads and coordination state only, never an unrelated fix.
6. Rerun the mission integration verifier on the new head.
7. Record `integrated_sha` and `integration_gate: PASS`, then transition to `integrated`; otherwise record `integration_failed` and stop dependent work.
8. After the wave closes and every selected mission has integrated, run the PLAN-level batch verifiers; stop the next wave if any fail.
9. Reobserve the integration head and recompute the ready frontier/conflict graph before launching another wave.

Never treat a completed task/thread, a worker `PASS`, or a commit on a mission branch as dependency satisfaction. Only the integrated state described in `verification-gates.md` unblocks downstream missions.

## Push And Lifecycle

Push, task archival, worktree removal, and branch deletion are independent authorization actions. Passing verification does not authorize any of them.

- Integrate only exact-head review-passing worker results serially into the exact resolved integration branch. Worker branches and worktrees do not push.
- Review the final diff locally and rerun final gates before pushing. Use an observed read-only review surface for uncommitted changes or a branch diff.
- Harness 0.38 RUNs complete `local_only` at C and cannot reserve or execute a RUN push. Archival writes a receipt-bound immutable anchor outside the checkout. After committing A, prepare its publication handoff only through `push_archived_candidate.py` with that same anchor, a new authorization, and external request/attempt/receipt/evidence. The request binds the exact canonical URL plus observed trust-policy and absolute verifier hashes; a trusted host independently revalidates and signs the exact no-force execution, local tooling never invokes `git push`, and recovery verifies the evidence before reading back A. Pre-0.38 RUNs retain the old path only for recovery.
- `integration.branch` names the exact non-protected run branch cut from observed remote `main`. The archive-candidate protocol derives that branch and C from the archived RUN, verifies a clean direct C-to-A archive commit, refuses `main` and `development`, checks the configured remote pre-state, emits a no-force trusted-host argv, and reads back exact A only through recovery.
- Start later PRD, UI, and feature enhancements from a fresh run branch cut from the current observed remote `main` head after the prior promotion state is resolved. Never implement directly on `main` or recreate `development`.
- Every `main` promotion requires another action-time authorization naming the remote branch and exact A. Neither the archived RUN nor the run-branch receipt authorizes it. Never force-push or continue after remote drift, failed ancestry, non-fast-forward state, or candidate-test failure.
- Preserve user-owned dirty work and unrelated branches/worktrees.
- For manual worktrees, remove only the exact recorded path after integration and only when `remove_worktrees` is true; never force-remove unmerged work.
- Delete only the exact recorded, fully integrated branch when `delete_branches` is true, unless `run.integration.retention == "persistent"`, in which case the branch is preserved rather than deleted.
- Archive only worker tasks explicitly covered by `archive_worker_tasks`.
- Record manual cleanup as complete, deferred, or not authorized. Record app-managed lifecycle separately because platform retention remains outside the harness's control.

For parent execution, follow the Sequential Parent Route in `execution-state-model.md`; it performs one mission at a time and cannot supply independent review.
