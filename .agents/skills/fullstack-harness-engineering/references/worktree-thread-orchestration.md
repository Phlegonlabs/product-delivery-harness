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
- `app_task` is an independent, user-owned Codex task with its own conversation in the left sidebar. A generic skill cannot promise an automatic callback to the parent task; use polling, a report file, or user relay unless an App Server integration supplies events.
- `parent` is the safe fallback when delegation or isolation capabilities are unavailable.

If a requested combination is unsupported, downgrade to sequential parent execution and record the reason. Never silently simulate parallel isolation in a shared checkout.

## Runtime Adapter Routing

Schemas v6 through v9 record the observed host provider separately from the portable axes under `runtime_capabilities.runtime_adapter`:

```text
provider: codex | claude_code | generic
available_drivers: app_threads | dynamic_workflow | subagents | sequential_parent
detection_source: observed | explicit | fallback
```

Always include `sequential_parent` as the safe fallback. Select the first observed driver in this fixed order:

```text
codex: app_threads -> subagents -> sequential_parent
claude_code: dynamic_workflow -> subagents -> sequential_parent
generic: subagents -> sequential_parent
```

The selected driver must match the axes recorded in RUN. `app_threads` maps to `app_task` + `app_managed_worktree` + `thread_poll`. `dynamic_workflow` maps to `subagent` + `parent_managed_worktree` + `agent_result`. Direct `subagents` use a supported shared or parent-managed workspace and result/report channel. `sequential_parent` maps to `parent` + `shared_checkout` + `agent_result`. Do not route from a product label alone; record how the capability was observed and fall back if the selected primitive is missing at launch.

Detect the host that is executing the Harness. Current-session Codex project/thread tools prove `app_threads`; the Claude Code `Workflow` tool and a supported runtime prove `dynamic_workflow`; current-session child-agent tools prove `subagents`. Codex task tools may be lazy-loaded, so use the current tool-discovery surface to search for project listing, top-level task creation, messaging, and thread waiting before declaring `app_threads` missing. Do not select a provider merely because its CLI is installed or its config directory exists. When native host identity is unavailable, use an explicit provider only from a user/config source; otherwise record `generic` fallback.

Perform this detection proactively before the first production edit in every plan-backed multi-mission run. Record all observed drivers even when their action authorizations are false. Missing authorization is a launch gap, not evidence that `app_threads`, `dynamic_workflow`, or `subagents` is unavailable.

A PLAN node is eligible on the current host exactly when its `allowed_providers` includes that host. `preferred_provider` is advisory ordering among allowed hosts and never blocks an otherwise allowed current host. There is no cross-host fallback and no mechanism to invoke the other runtime from this one: a ready node whose allowed providers do not include the current host is not executable here. Report it as blocked on provider mismatch and leave it for a run hosted by an allowed adapter.

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
- landing and manual cleanup actions when separately authorized.

A worker owns one mission lease only:

- its assigned workspace and allowed mission write scope;
- task-level implementation, verification, and authorized task commits;
- bounded read-only child delegation when its recorded nested-subagent policy is enabled and authorized;
- a structured result or `REFINEMENT_REQUEST` returned through the declared completion channel.

Workers never edit the parent-owned `PLAN.md` or `RUN.md`, never expand their own scope, and never pull, rebase, merge, push, create a PR, deploy, or clean up unless that exact action is separately authorized and assigned.

## Mode Selection

### Shared checkout

Reserve `shared_checkout` for genuinely small direct work (see the Project Size Gate) and for parallel read-only analysis. It is a fallback for plan-backed mission writes, not the default — use it there only when worktree creation is unavailable or unauthorized.

- Allow at most one writer at a time, whether that writer is the parent or a subagent.
- Parallel read-only workers may inspect the same checkout if they do not run mutating generators, formatters, services, or tests with shared state.
- Task completion may integrate immediately only after the same worker-result and integration gates are applied.

### Parent-managed worktree

Default every plan-backed mission write to `parent_managed_worktree`, whether one mission is worked at a time or several run concurrently — `create_local_worktrees` authorization covers this even for a single sequential mission. Create each worktree from the target repository's recorded current `development` SHA. The primary `development` checkout is a merge target, never a direct implementation surface: each mission's worktree branch receives an exact-head read-only review before it may merge there.

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
- Treat the app task itself as the sole writer in its managed worktree. Direct subagents may assist only under the bounded read-only policy below; a second writer requires a separately planned outer mission and isolated worktree, not an informal nested child.
- Preflight the selected permission mode before task creation. A linked worktree's `.git` file points to metadata in the original repository's Git common directory, which may sit outside the app worktree sandbox; branch creation and commits can therefore prompt even when source edits are inside the worktree. Package caches, system temp, local dev ports, private-network bindings, and Unix sockets are separate surfaces that must also fit the selected boundary.
- Record the effective permission boundary in RUN. Subagents inherit the app task's active mode, and app tasks inherit the parent mode chosen before launch. `Approve for me` changes eligible prompt review but does not widen the sandbox. A later config/composer change does not retroactively update already-running tasks.

The platform controls managed-worktree retention. `remove_worktrees: false` prevents Harness-initiated removal; it cannot override platform lifecycle or automatic retention cleanup. Preserve failed or cancelled worktrees and commits for diagnosis. Never reset or delete them automatically.

True event-driven cross-task completion requires a runtime integration that exposes task/thread events, such as Codex App Server notifications. Otherwise use `thread_poll`, `report_file`, or `user_relay` and state that limitation explicitly.

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

Before its first production edit, a non-trivial app task with this policy evaluates four lanes: codebase exploration, documentation/API research, test/log analysis, and independent review. Run eligible exploration, research, and test-plan/contract review before writing. A child that reviews the proposed diff runs after implementation but before the mission result and must bind its decision to the exact current worktree head. Exploration, research, and test-analysis lanes may be skipped when they add no independent value, but the post-edit reviewer is mandatory for an enabled non-trivial task. If the mission is trivial or no child slot/tool or safe reviewer lane is available, the WORKER_RESULT records that reason and the parent performs an equivalent read-only review before integration. Since this exploration, research, test-analysis, and diff-review work is bounded, read-only discovery, each child takes the fast, inexpensive model tier from `graph-orchestration.md`'s Runtime Binding point 6 — the host's fastest/cheapest model (a delegated Claude Code child set to `haiku`, not `sonnet`) with `low` or `medium` reasoning effort — unless the parent mission's own risk classification (security-sensitive, migration, difficult-correctness, or another point-2-level high-risk surface) keeps its children at the parent's own model tier to match its quality bar for that specific mission.

If the outer coordinator cannot observe child-tool availability until the app task exists, perform a no-production-edit capability handshake first. The task reports tool/result availability, the coordinator records `runtime_capabilities.nested_subagents`, assigns an explicit enabled or disabled worker policy, and only then releases implementation. This avoids silently treating “not yet observed” as “unavailable.” Once enabled, the worker cannot pass without a completed exact-head PASS reviewer; a later `partial` or `unavailable` activity record is blocking rather than a fallback. A disabled policy instead routes the exact-head review to the parent before integration.

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
plan_revision
plan_digest_sha256
batch_base_sha
candidate order and conflict reasons
effective worker budget
selected mission IDs
runtime provider and selected driver
```

The parent reviews live Git/runtime facts, confirms the proposal, records it in `RUN.md`, assigns leases, and only then creates branches, worktrees, subagents, or app tasks. Scripts must not parse human Markdown tables or mutate Git, Codex, PLAN, or RUN.

When no safe set exists, run the next dependency-ready mission sequentially. Parallel execution is an optimization, not a completion requirement.

## Launch Selected Claude Dynamic Workflow

When the accepted schema-v6-through-v9 wave routes to `claude_code` + `dynamic_workflow`, use one flat workflow for the selected wave:

1. Confirm Dynamic Workflow is available in the current Claude Code runtime. Treat version support and observed command availability as capability evidence, not authorization.
2. Allocate one authorized parent-managed worktree, durable branch, worker ID, and lease per selected mission from the fixed `batch_base_sha`. The parent owns these mutations and records the concrete identities in RUN.
3. Render the workflow arguments from the accepted selector result and `WORKER_GOAL.template.md` handoffs. Each mission receives its lease ID, branch ref, assigned existing worktree path, scope, tasks, resources, verifiers, permission boundary, and frozen plan/base identity. `CLAUDE_DYNAMIC_WORKFLOW.template.js` has no `EnterWorktree` tool or allowlist; its mission prompt instructs the agent in plain English to enter the existing worktree at that exact path before any repository read, write, or shell action, then verify repository root, branch, and batch base. It returns blocked if it cannot bind; it never creates a replacement worktree or writes in the parent checkout. (The typed-graph route in `CLAUDE_GRAPH_WORKFLOW.template.js` uses the actual `EnterWorktree` tool instead — see `references/graph-orchestration.md`.)
4. Invoke the Claude Code `Workflow` tool with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and the accepted wave supplied as structured `args`. Its `pipeline()` starts sibling mission agents and returns one complete `WORKER_RESULT` or `REFINEMENT_REQUEST` object per mission through `agent_result`. Save a reusable rendered copy under `.claude/workflows/` only when that project file write is planned and authorized.
5. Do not ask for user input inside the workflow. A mission that needs a contract decision or refined tasks returns a blocked/refinement result; the parent updates PLAN/RUN and starts a later workflow after the decision.
6. Validate every result against live worktree, branch, head, scope, and verifier facts. Integrate accepted mission heads serially and recompute the next wave.

Claude Code currently supports nested subagents, but this schema-v6-through-v9 route intentionally has no nested worker layer and omits `nested_subagents`. The workflow script coordinates sibling mission agents; each remains the sole writer for its lease and is instructed not to delegate. The script does not directly read files, run shell commands, edit PLAN/RUN, integrate, push, or land a PR. If Dynamic Workflow is unavailable, use the recorded fallback route; do not simulate it with an untracked ad hoc fan-out.

## Launch Selected Codex App Threads

When the accepted wave uses `app_task` + `app_managed_worktree` + `thread_poll`, a non-empty selector result is an instruction for the parent to act, not a final report. Use the current Codex project/thread tools when they are available:

1. Search the current Codex tool surface for project listing, top-level task/thread creation, follow-up messaging, and bounded thread waiting when those tools were not loaded initially. Resolve the repository's saved project once.
2. For each selected mission in deterministic order, allocate its worker ID, lease ID, and branch/ref. Recheck `create_user_owned_tasks` and `create_app_managed_worktrees` against the explicit pre-allocation `*` grant because the app assigns their concrete identities; recheck `create_local_branches`, `create_local_commits`, and `spawn_subagents` against every already-known target.
3. Build the initial prompt from `WORKER_GOAL.template.md`, including the frozen plan identity, fixed base, mission/task scope, verifiers, permission boundary, nested policy, and the mission's `required_skills` list. Tell the app task directly to use its authorized multi-agent policy.
4. Create one top-level worktree task/thread per mission from the recorded integration branch/ref. Each task must have its own app-managed worktree and appear as an independent conversation in the Codex left sidebar. Record either the returned thread ID or the queued client-thread ID; never invent an identity from the mission ID and never substitute coordinator-owned subagents.
5. When nested capability is unobserved, keep the task in a no-production-edit handshake. Poll its capability result, update RUN, and send the explicit enabled or disabled policy before releasing implementation. Enable it only when `reviewer` is among the allowed roles; otherwise use the disabled parent-review path.
6. Poll running threads with backoff, route necessary follow-up through the thread-message tool, and preserve terminal, blocked, interrupted, and partial results. Do not rely on the user to relay completion when programmatic polling is available.
7. Validate every result against live Git facts. Require the task's own post-edit read-only reviewer to PASS on the exact returned worktree head. For a disabled task-local policy, run an equivalent parent-owned review first and record its terminal exact-head PASS in the covering PLAN review node's `review_workers[]` entry; validation rejects the result without that canonical record.
8. Route findings back to the same worktree and review the changed head again. Integrate passing heads serially into `development`.

For a non-trivial worker with an enabled nested policy, at least one direct child must run and the final useful child lane must be a post-edit proposed-diff review. The worker may use up to three read-only children across pre-edit exploration/research/test analysis and that required review, waits for them, and reports `subagent_activity`. These children belong to that top-level task only; each sibling task runs its own independent Multi-agent set. A missing current-head review is an integration blocker, not a successful single-agent downgrade.

If the app lacks any required project, thread-create, thread-read, thread-message, worktree, or nested-agent capability, leave the affected directive unlaunched and record the exact capability gap. Fall back to the sequential parent only when the user did not explicitly require independent left-sidebar tasks. When that outer topology was requested, stop and report the missing capability instead of substituting coordinator-owned subagents or sequential execution. Never claim that writing a worker record created a real task.

## Worker Handoff

Use `assets/templates/WORKER_GOAL.template.md`. A complete handoff binds the worker to:

```text
plan revision and digest
mission ID and lease ID
batch base SHA and assigned branch/ref
worker_runtime, workspace_mode, completion_channel
runtime provider and selected driver
required_skills (the mission's skill list, verbatim, or "none")
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

Repository configuration, push, PR creation, PR review management, PR merge, deploy, task archival, worktree removal, and branch deletion are independent authorization actions. Passing verification does not authorize any of them.

- Integrate only exact-head review-passing worker results serially into the target repository's persistent `development` branch. Worker branches and worktrees do not push or open PRs.
- Review the final diff locally and rerun final gates before any outward-facing landing action. Codex `/review` is a read-only option for uncommitted changes or a branch diff.
- Local-only delivery stops after its authorized local branch, commit, integration, and final verification outcome; it does not load remote landing or wait for GitHub.
- In local-only mission work, `integration.branch` and `landing.head_branch` name persistent `development`, while `landing.base_branch` names protected `production`. A pull-request promotion is always `development -> production`, starts only after explicit final user approval, and then runs current-head CI and Codex review concurrently.
- When the repository allows auto-merge and `merge_pr` covers the exact PR, wait for current-head CI and Codex review PASS plus zero blocking findings and unresolved threads, then enable squash auto-merge with an exact head-SHA match. Record the request in current RUN v10 (older RUN v4 through v9 retain their historical fields) and reset it after any new push or changed integration head.
- Enable repository rules or Codex Automatic reviews only with `configure_repository` authorization. If Automatic reviews are unavailable, use the repository's documented manual review trigger.
- Bind the PR, CI, and review results to the exact current integration head SHA. After every new local integration or push, treat earlier check/review PASS state as stale and restart both remote gates for the new head.
- Do not merge or enable auto-merge without `merge_pr` authorization, even when every gate passes. Repository-level auto-merge configuration separately requires `configure_repository`.
- After a production promotion, start later PRD/PLD, UI, and feature work from `development` again. Never use `production` as an implementation base.
- Preserve user-owned dirty work and unrelated branches/worktrees.
- For manual worktrees, remove only the exact recorded path after integration and only when `remove_worktrees` is true; never force-remove unmerged work.
- Delete only the exact recorded, fully integrated branch when `delete_branches` is true, unless `run.integration.retention == "persistent"`, in which case the branch is preserved rather than deleted (see `execution-state-model.md`'s Post-Merge Cleanup State).
- Archive only worker tasks explicitly covered by `archive_worker_tasks`.
- Record manual cleanup as complete, deferred, or not authorized. Record app-managed lifecycle separately because platform retention remains outside the harness's control.

For schema v5 through v9 post-merge cleanup, perform this serialized closeout only after GitHub reports the final PR merged: fetch the base, confirm the merged SHA is reachable, confirm the local feature branch still equals the recorded PR head, and refresh `git worktree list --porcelain`. Stop on any dirty, moved, missing, or mismatched target. If the feature branch is attached to an authorized parent-managed linked worktree, remove that exact clean path without force and re-observe it as absent. Switch the primary checkout to the refreshed base branch, then delete only the exact authorized local feature branch. Squash merge may require forced local branch deletion because the original feature commit is not an ancestor of the squash commit; the merged PR and exact-head checks are the safety proof. Never force-remove a worktree, never remove the primary checkout, and never manually clean an app-managed worktree under the platform's retention control.
