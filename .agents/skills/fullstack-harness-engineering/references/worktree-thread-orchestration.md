# Runtime, Worktree, And Thread Orchestration

Use this reference when the harness runs multiple missions, delegates to workers, or needs workspace isolation. Read `execution-state-model.md` and `parallel-mission-selection.md` first.

## Describe Capabilities, Not Product Labels

Record three independent fields for each run or worker:

```text
worker_runtime: parent | subagent | app_task
workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
completion_channel: agent_result | thread_poll | report_file | user_relay
```

These fields are orthogonal. Do not infer workspace isolation, completion notification, or cleanup behavior from the word "worker" or from a product name.

- `subagent` is a parent-managed child. It can return an `agent_result`, but still shares the checkout unless an isolated workspace was deliberately provided.
- `app_task` is an independent, user-owned Codex task. A generic skill cannot promise an automatic callback to the parent task; use polling, a report file, or user relay unless an App Server integration supplies events.
- `parent` is the safe fallback when delegation or isolation capabilities are unavailable.

If a requested combination is unsupported, downgrade to sequential parent execution and record the reason. Never silently simulate parallel isolation in a shared checkout.

## Parent And Worker Ownership

The parent/coordinator exclusively owns:

- source intake, contract freeze, and plan revisions;
- canonical `PLAN.md` and `RUN.md` writes;
- authorization checks and runtime capability detection;
- batch-base selection, wave confirmation, leases, and worker prompts;
- branch/worktree creation when authorized;
- worker-result validation, integration order, conflict handling, and E2E verification;
- landing and manual cleanup actions when separately authorized.

A worker owns one mission lease only:

- its assigned workspace and allowed mission write scope;
- task-level implementation, verification, and authorized task commits;
- bounded read-only child delegation when its recorded nested-subagent policy is enabled and authorized;
- a structured result or `REFINEMENT_REQUEST` returned through the declared completion channel.

Workers never edit the parent-owned `PLAN.md` or `RUN.md`, never expand their own scope, and never pull, rebase, merge, push, create a PR, deploy, or clean up unless that exact action is separately authorized and assigned.

## Mode Selection

### Shared checkout

Use `shared_checkout` for direct work, sequential write missions, and parallel read-only analysis.

- Allow at most one writer at a time, whether that writer is the parent or a subagent.
- Parallel read-only workers may inspect the same checkout if they do not run mutating generators, formatters, services, or tests with shared state.
- Task completion may integrate immediately only after the same worker-result and integration gates are applied.

### Parent-managed worktree

Use `parent_managed_worktree` only when `create_local_worktrees` is authorized and isolated parallel writes materially reduce delivery time.

- The parent creates every worktree from the same recorded `batch_base_sha`; portable write handoff also requires `create_local_branches` and `create_local_commits`, because the parent integrates a durable committed head rather than an uncommitted patch.
- The parent records the exact path, branch/ref, lease, ports, databases, fixtures, and external resource claims.
- Workers never synchronize against the base branch. The parent handles any unavoidable mid-run sync at a task boundary and reruns affected verifiers.
- A worktree isolates tracked files, not ports, databases, environment files, caches, queues, buckets, tenants, or third-party sandboxes.

### App-managed worktree

Use `app_managed_worktree` only when the runtime exposes it and `create_user_owned_tasks` plus `create_app_managed_worktrees` are both explicitly authorized.

- App tasks are user-owned tasks, not invisible subagents. Record their task/thread identity and completion channel.
- Managed worktrees may begin detached. If durable commits or handoff are required, create an authorized branch or durable ref early; do not leave unique work reachable only from a detached checkout.
- Do not launch app-managed write fan-out unless branch and commit creation are authorized. Otherwise use sequential parent execution; this protocol does not depend on extracting an uncommitted patch from a managed worktree.
- The platform controls managed-worktree retention. `remove_worktrees: false` prevents the harness from manually removing one; it cannot override platform lifecycle or automatic retention cleanup.
- Use the repository's supported ignored-file inclusion mechanism, such as `.worktreeinclude`, only for necessary local files and never to copy tracked files or secrets without permission.
- Treat the app task itself as the sole writer in its managed worktree. Direct subagents may assist only under the bounded read-only policy below; a second writer requires a separately planned outer mission and isolated worktree, not an informal nested child.
- Preflight the selected permission mode before task creation. A linked worktree's `.git` file points to metadata in the original repository's Git common directory, which may sit outside the app worktree sandbox; branch creation and commits can therefore prompt even when source edits are inside the worktree. Package caches, system temp, local dev ports, private-network bindings, and Unix sockets are separate surfaces that must also fit the selected boundary.
- Record the effective permission boundary in RUN. Subagents inherit the app task's active mode, and app tasks inherit the parent mode chosen before launch. `Approve for me` changes eligible prompt review but does not widen the sandbox. A later config/composer change does not retroactively update already-running tasks.

True event-driven cross-task completion requires a runtime integration that exposes task/thread events (for example, Codex App Server notifications). Otherwise use `thread_poll`, `report_file`, or `user_relay` and state that limitation explicitly.

## Nested Subagents Inside An App Task

This is a two-level coordination shape, not another mission wave:

```text
outer coordinator -> app task / mission writer -> read-only direct subagents
```

Enable it only when all of these are true:

- the outer worker uses `worker_runtime: app_task`;
- current runtime observation proves multi-agent tools and a direct result channel are available inside that task;
- `spawn_subagents` covers the mission and exact outer worker target or an explicitly run-wide target;
- RUN gives the worker an enabled `nested_subagent_policy` capped at depth one and at most three children;
- each child assignment is independent, bounded, read-only, and useful enough to offset coordination cost.

Before its first production edit, a non-trivial app task with this policy evaluates four lanes: codebase exploration, documentation/API research, test/log analysis, and independent review. Run eligible exploration, research, and test-plan/contract review before writing. A child that reviews the proposed diff runs after implementation but before the mission result. The task normally spawns one to three children across those checkpoints. It may skip only when the mission is trivial, no child slot/tool is available, or no safe independent lane exists; the WORKER_RESULT must record that reason.

If the outer coordinator cannot observe child-tool availability until the app task exists, perform a no-production-edit capability handshake first. The task reports tool/result availability, the coordinator records `runtime_capabilities.nested_subagents`, assigns an explicit enabled or disabled worker policy, and only then releases implementation. This avoids silently treating “not yet observed” as “unavailable.”

The app task gives every child a concrete question, read/deny scope, expected evidence, required summary, and an explicit instruction not to spawn or delegate further; waits for all requested child results; reconciles disagreements itself; and remains responsible for implementation and verification. Children never edit files or PLAN/RUN, run mutating generators or shared-state services/tests, create worktrees/branches/tasks/commits, or perform integration/landing/lifecycle actions. If a child discovers code that must be changed, it reports the evidence to the app task rather than editing.

Nested children do not appear as PLAN missions, receive leases, consume the outer harness write-worker budget, or report directly to the outer coordinator. The app task includes their IDs, roles, tasks, status, summaries, and evidence paths in `subagent_activity`; the outer coordinator validates the mission result and actual Git state as usual.

## Launch Preconditions

Before proposing any write wave, the parent confirms:

```text
canonical PLAN and RUN manifests validate
plan revision and digest match
plan readiness and execution authorization are true
the exact spawn/worktree/branch/commit actions are authorized
integration branch/ref and immutable batch_base_sha are observed
parent dirty files are attributed and do not overlap mission scopes
mission/task dependency DAGs are acyclic
resource_inventory_complete is true for every candidate
write/deny scopes use the supported grammar
runtime slots and isolation capacity are known
required environment and verifier tools are available
selected permission boundary and worker inheritance are observed
linked-worktree Git metadata, temp/cache, network, local-binding, and socket requirements fit that boundary
```

Also inspect the current Git status, worktree list, existing branches/refs, and intended integration head. Stop before overwriting, moving, deleting, resetting, or cleaning anything.

Branch and worktree identities are runtime allocations, not static PLAN truth. Derive collision-resistant names from the plan/run plus immutable mission ID, for example `codex/<plan-slug>-m1`, then compare the exact proposed branch and path with observed refs/worktrees before creation. Never reuse a branch or directory merely because its human alias looks related. Record the final allocation in RUN worker state.

## Select And Confirm A Wave

Run the pure validator and selector before any mutating Git or Codex action. The selector emits a proposal bound to:

```text
plan_revision
plan_digest_sha256
batch_base_sha
candidate order and conflict reasons
effective worker budget
selected mission IDs
```

The parent reviews live Git/runtime facts, confirms the proposal, records it in `RUN.md`, assigns leases, and only then creates branches, worktrees, subagents, or app tasks. Scripts must not parse human Markdown tables or mutate Git, Codex, PLAN, or RUN.

When no safe set exists, run the next dependency-ready mission sequentially. Parallel execution is an optimization, not a completion requirement.

## Worker Handoff

Use `assets/templates/WORKER_GOAL.template.md`. A complete handoff binds the worker to:

```text
plan revision and digest
mission ID and lease ID
batch base SHA and assigned branch/ref
worker_runtime, workspace_mode, completion_channel
enabled nested-subagent policy or an explicit disabled policy
allowed and denied paths
declared serialized/runtime resources
task order and verifier argv/cwd
forbidden parent-owned artifacts
result/refinement schema and stop conditions
```

Prefer structured result data returned directly to the parent. Use temporary `docs/goal/evidence/<mission>/REPORT.md` only when the completion channel or durable handoff requires it; the file contains the exact `## Worker Result Manifest` heading and fenced JSON from the worker template. Record that one path as worker-owned handoff scope; every other PLAN/RUN/evidence state path remains parent-owned. The parent validates claims against observed workspace and Git facts before integration.

## Batch Integration

Integrate selected missions serially in declared `merge_rank` and mission-ID order:

1. Receive the worker result through the declared completion channel.
2. Confirm the lease, plan revision/digest, batch base, and observed worker head.
3. Validate ancestry, actual changed paths, denied paths, parent-owned files, resource claims, commits, and worker verifiers.
4. Transition `worker_passed -> integrating` only after result validation succeeds.
5. Integrate onto the current integration head when `integrate_locally` is authorized.
6. Rerun the mission integration verifier on the new head.
7. Record `integrated_sha` and `integration_gate: PASS`, then transition to `integrated`; otherwise record `integration_failed` and stop dependent work.
8. After all selected missions integrate, run the PLAN-level batch verifiers; stop the next wave if any fail.
9. Reobserve the integration head and recompute the ready frontier/conflict graph before launching another wave.

Never treat a completed task/thread, a worker `PASS`, or a commit on a mission branch as dependency satisfaction. Only the integrated state described in `verification-gates.md` unblocks downstream missions.

## Landing And Lifecycle

Push, PR creation, deploy, task archival, worktree removal, and branch deletion are independent authorization actions. Passing verification does not authorize any of them.

- Review the final diff and rerun final gates before any outward-facing landing action.
- Preserve user-owned dirty work and unrelated branches/worktrees.
- For manual worktrees, remove only the exact recorded path after integration and only when `remove_worktrees` is true; never force-remove unmerged work.
- Delete only the exact recorded, fully integrated branch when `delete_branches` is true.
- Archive only worker tasks explicitly covered by `archive_worker_tasks`.
- Record manual cleanup as complete, deferred, or not authorized. Record app-managed lifecycle separately because platform retention remains outside the harness's control.
