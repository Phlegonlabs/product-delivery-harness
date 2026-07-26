# Parallel Mission Selection

Use this reference after plan readiness passes and before any parallel write fan-out. Selection is deterministic analysis. It does not create tasks, branches, worktrees, commits, merges, pushes, PRs, deployments, or cleanup actions.

The Project Size Gate runs first. Small work never reaches this selector. Large work uses scheduler fan-out only when at least two dependency-ready, nonconflicting missions make parallel execution useful; otherwise keep the accepted plan and execute it with the sequential parent.

This file defines the legacy PLAN-v2/v3 mission-DAG selector. Current PLAN v5 and RUN v10 use `scripts/select_ready_nodes.py`; supported PLAN-v4/RUN-v8-or-v9 typed graphs use it too. It computes the typed graph frontier first, then applies these same scope/resource conflicts and deterministic write budget to ready mission nodes. Never run `scripts/select_parallel_missions.py` against a typed-graph plan.

For every execution-authorized plan-backed multi-mission run, selection is the default post-readiness action, not an optional optimization the parent may skip. Proactively detect runtime capabilities before readiness, set the configured maximum generously high unless the user sets an explicit lower limit, and run the selector before any production task. The selected wave contains every dependency-ready, nonconflicting mission the effective budget allows — it shrinks only when live capacity, isolation, dependencies, conflicts, resources, permissions, or authorization actually require it, never because of an arbitrary starting number.

## Inputs And Output

The selector reads only canonical machine data. In RUN schema v6 and later, provider routing comes from `runtime_capabilities.runtime_adapter`:

- Static `harness_plan` JSON from `PLAN.md`.
- Mutable `harness_run` JSON from `RUN.md`.
- Explicit observed-capacity inputs supplied by the parent when they are not already in a fresh RUN snapshot.

It must not parse Markdown tables, inspect UI labels, guess resource ownership, or mutate Git/Codex state.

The output is canonical sorted JSON with no timestamps. It binds:

```text
plan_id
plan_revision
plan_digest_sha256
batch_base_sha
effective_worker_budget
runtime_route (RUN schema v6+)
ready_frontier
conflict_edges with reason codes
selected_missions
launch_directives
wave_launch (RUN schema v6+ Claude Dynamic Workflow only)
deferred_missions with reason codes
```

Serialize each conflict edge as `{ "left": <lower mission ID>, "right": <higher mission ID>, "reason_codes": [...] }`. Serialize each deferred mission as `{ "mission_id": ..., "reason_codes": [...], "conflicts_with": [...] }`. Sort IDs and reason codes; never encode a reason only in prose.

Each selected mission has one deterministic `launch_directives` entry containing its mission ID, launch kind, runtime provider/driver, runtime/workspace/completion axes, required action keys, worker prompt template, and any route-specific policy. It contains no allocated worker, task, branch, or worktree identity. For Claude Dynamic Workflow, `wave_launch` bundles the selected mission IDs into one flat workflow invocation, supplies the template through `script_path`, and marks the accepted wave as the structured argument source; the per-mission directives remain the source for allocation and validation. The output is a proposal until the parent rechecks observed facts and records it in RUN state.

## Ready Frontier

A mission is in the ready frontier only when all conditions pass:

1. Canonical RUN state has `plan_readiness: "ready"` and `execution_authorized: true`.
2. The mission exists in the current plan revision and its RUN phase is exactly `queued` or `ready`; every other canonical mission phase is excluded.
3. Every declared mission dependency is `integrated` with integration gate `PASS`.
4. Each dependency has an `integrated_sha`, and the parent can confirm it is an ancestor of the current integration head before launch.
5. The wave base is a fixed, committed SHA and matches the integration branch snapshot used by selection.
6. Trace, write-scope, verifier, and resource inventory validation passed.
7. `resource_inventory_complete` is true.
8. The chosen runtime/workspace/completion capability combination supports the mission; a parallel write mission has `worktree_eligible: true` and an isolated workspace.
9. Required action-specific authorizations for the proposed launch path are present. App-task fan-out includes `spawn_subagents` because every non-trivial mission thread is expected to use its bounded read-only child policy. Claude Dynamic Workflow and direct subagent fan-out require `spawn_subagents`; isolated workflow writes also require parent-managed worktree, branch, and commit authorization.
10. The inherited permission boundary is observed and already covers linked-worktree Git metadata, temp/cache, outbound network, local/private bindings, and required sockets.
11. No human approval, secret, service, contract decision, or destructive action remains unresolved.

An isolated write worker must have an authorized durable branch/ref and `create_local_commits: true`; the portable protocol does not integrate an uncommitted patch from another workspace. When those are unavailable, keep the mission out of fan-out and use sequential parent execution in the integration checkout.

Selection happens before worker/task/branch/worktree identities are allocated. Therefore a launch-path action passes this pre-allocation gate only when the user explicitly authorized that action for the mission scope with `targets: ["*"]`. A selector must never manufacture `worker:<mission-id>`, `branch:<mission-id>`, or another pseudo-target. After the parent allocates concrete identities, it checks the exact `worker:`, `task:`, `worktree:`, or `branch:` target again immediately before each mutation; the pre-allocation result is not a substitute for that check.

Keep capability detection independent from this authorization gate. If the preferred observed route lacks one or more action grants, retain that route in `runtime_adapter`, report `action_not_authorized`, request the complete route bundle once, and rerun selection after the answer. Do not select a lower-priority runtime driver solely because its mutation bundle is easier to satisfy.

`worker_passed` dependencies are not ready dependencies. Dirty shared foundation, an unknown base SHA, missing resource claims, unsupported scope syntax, or a stale plan digest removes a mission from the frontier.

## Supported Write-Scope Grammar

The minimum portable grammar supports only:

```text
path/to/exact-file.ext
path/to/subtree/**
```

Rules:

- Paths are repository-relative POSIX paths.
- Reject absolute paths, empty segments, `.` or `..`, backslashes, negation, braces, character classes, and every wildcard except one terminal `/**`.
- Normalize repeated separators and reject a claim whose normalized spelling differs in a way that could escape or obscure scope.
- Compare directory segments, not string prefixes: `src/a/**` overlaps `src/a/file.ts` but not `src/ab/file.ts`.
- Treat case-only differences conservatively as a conflict unless repository and filesystem case behavior is proven compatible.
- `PLAN.md`, `RUN.md`, and parent-owned evidence/state paths are forbidden worker write scopes. A single parent-assigned temporary mission report path may be worker-owned for `completion_channel: report_file`; declare and validate it separately from production scope.
- `deny_scope` uses the same grammar. A mission is invalid when an allowed write claim overlaps one of its denied claims.
- Unsupported or ambiguous syntax is unsafe. Defer the mission; never interpret it optimistically.

Overlap rules are deterministic:

- Exact versus exact conflicts when normalized paths are equal.
- Exact versus subtree conflicts when the exact path is at or below the subtree boundary.
- Subtree versus subtree conflicts when either boundary is equal to or an ancestor of the other by complete path segments.

The parent validates the worker's actual changed paths with the same grammar before integration. A clean declared graph does not excuse an out-of-scope diff.

## Runtime Resource Claims

Use `serialized_resources` for opaque coordination keys that are always exclusive, such as a single generated-contract stream or repository-wide migration allocator. Normalize keys as exact strings. Two missions with the same serialized key always conflict; an empty inventory is `[]`, never `none`.

Use `runtime_resources` for resources whose access mode matters. Every claim is typed:

```json
{
  "key": "service:test-database",
  "access": "exclusive"
}
```

Supported access values are:

```text
exclusive | shared_read
```

Two missions conflict when they claim the same normalized resource key and at least one access is `exclusive`. Two `shared_read` claims do not conflict. Unknown access values, missing keys, duplicate contradictory claims, or an incomplete inventory are unsafe.

Use exclusive serialized keys or typed runtime keys for migration streams, generated clients, root lock/config surfaces, build caches, dev ports, databases/schemas, test identities, external sandboxes, queues, buckets, webhooks, and other shared state. Do not encode “no resources” as a string such as `none`; use empty arrays and set `resource_inventory_complete: true` only after both inventories were actually checked.

Worktrees isolate repository files only. They do not make runtime resources non-conflicting.

Only declare a mission-level `runtime_resources`/`serialized_resources` claim for a resource concurrent *workers* would actually contend for, not one only `integration_verifiers` touch:

- **Worker-stage contention** (claim it): each worktree's own worker would boot a live dev server on the same fixed port, or write to one shared live database at the same time.
- **Integration-stage-only use** (no mission-level claim needed): a shared local dev server or database that only an `integration_verifiers` end-to-end/migration check depends on. Integration already happens one mission at a time (see Batch Integration And Recompute below), so that resource is naturally serialized where it's actually used — an exclusive mission-level claim here would only block worker-stage worktree parallelism the resource was never contending for, forcing sequential execution even when the missions' file changes don't overlap.
- **Mitigation**: when a mission's own `worker_verifiers` need a live local service, prefer a per-worktree or dynamically assigned port/database path over one fixed shared instance, so the claim can stay `shared_read` or be omitted instead of defaulting to `exclusive`.

## Conflict Graph

Create an undirected edge between two structurally valid candidate missions for every proven or conservative pairwise conflict. Keep all reason codes, not only the first. Pairwise edge codes are:

```text
scope_overlap
case_scope_collision
serialized_resource_conflict
runtime_resource_conflict
workspace_not_isolated
```

Unary ineligibility or deferral belongs on the mission/proposal, not on a graph edge. Use exact applicable codes from:

```text
plan_not_ready
execution_not_authorized
action_not_authorized
mission_phase_not_ready
dependency_not_integrated
dependency_gate_not_pass
dependency_ancestry_unconfirmed
plan_digest_mismatch
batch_base_missing
batch_base_stale
incomplete_resource_inventory
unsupported_scope
parent_owned_scope
worktree_ineligible
runtime_capacity_unavailable
completion_channel_unavailable
permission_boundary_not_ready
blocker_present
platform_lifecycle_unknown
over_budget
```

Dependency edges determine readiness and topological level; they are not conflict edges among already-ready missions. Unknown facts yield an ineligibility/defer code or a conservative pairwise edge, never an assumed independent pair.

## Deterministic Greedy Selection

Sort ready candidates by this exact tuple:

```text
(topo_level ASC, priority DESC, merge_rank ASC, mission_id ASC)
```

`topo_level` is zero for a root mission and otherwise one plus the maximum level of its dependencies. It is derived from the validated DAG. `priority` and `merge_rank` are explicit plan integers. `mission_id` is the final stable tie-breaker.

Compute the effective write-worker budget as:

```text
configured maximum = min(
  PLAN.harness_plan.max_parallel_workers,
  RUN.harness_run.runtime_capabilities.max_parallel_workers
)

conflict capacity = size of the deterministic greedy nonconflicting set
                    when scanned without a numeric cap

min(
  configured maximum,
  observed runtime worker slots,
  observed workspace isolation capacity,
  conflict capacity
)
```

There is no default numeric ceiling on the configured maximum; set it generously high and let observed worker slots, isolation capacity, and conflict capacity do the actual bounding. Set it lower only when the user or a real runtime limit requires that. `shared_checkout` has workspace isolation capacity one for writes.

Then scan candidates in order:

1. Add a candidate when it has no conflict edge to any already-selected mission.
2. Otherwise defer it and record every conflict reason and conflicting selected mission.
3. Stop adding after the effective budget is reached.
4. Record ready-but-over-budget missions separately from conflicting or unsafe missions.

Given semantically identical canonical inputs, selection must be byte-for-byte stable regardless of source list order, hash seed, locale, or invocation time.

## Parent Launch Gate

Before using a proposal, the parent re-observes:

- Plan revision and digest.
- Integration branch and committed `batch_base_sha`.
- Dirty state and uncommitted shared foundation.
- Available worker slots and isolation capacity.
- Observed provider, available runtime drivers, and the selected deterministic route.
- Existing branch/worktree names and paths.
- Each selected mission's required authorizations and completion channel.
- The selected parent permission mode/profile, worker inheritance, and every required filesystem/network/local surface.

If anything differs, discard the proposal and rerun selection. Launch workers with leases bound to the accepted plan revision/digest and base SHA.

When the proposal is empty only because launch actions are unauthorized, request the preferred route's exact bundle once with run-wide mission scope and pre-allocation `targets: ["*"]`, then pause. After the answer is recorded, rerun validation and selection. Use sequential fallback only after the user declines or a non-authorization capability, isolation, permission, dependency, conflict, or resource gate prevents the wave.

For `launch_kind: "create_thread"`, the parent must consume the directive after accepting the wave instead of merely reporting `selected_missions`:

1. Search the current Codex tool surface when project/thread tools were not loaded initially, then resolve the current Codex project once through the available project-listing surface.
2. Allocate a worker/lease and exact durable branch target. For task/worktree identities assigned only by creation, recheck the explicit pre-allocation `*` grant; recheck every already-known target exactly.
3. Create one top-level app-managed worktree thread for the mission. It is a separate conversation in the Codex left sidebar; a direct subagent of the coordinator is not equivalent. Use the complete `WORKER_GOAL.template.md` handoff as the initial prompt and start from the recorded integration branch/ref that points at `batch_base_sha`.
4. Record the returned thread ID or queued client-thread ID in the RUN worker record, bind later actions to that concrete identity, and move the mission to `worker_running` only when the task/workspace is observable.
5. If the directive says `capability_handshake`, prohibit production edits until the thread reports direct child-tool/result availability. Update RUN and send the enabled or disabled nested policy through the thread-message surface.
6. Poll through the available read-thread/status surface with backoff. Treat the terminal task output as a worker result candidate and validate it normally.

If project/thread creation, worktree isolation, follow-up messaging, or polling is unavailable, do not mark the directive launched. Record the capability failure. Use sequential parent execution only when the user did not explicitly require independent left-sidebar tasks; otherwise stop at the missing-capability boundary.

For app-managed worktrees, record that they may begin detached and are governed by platform retention. `platform_lifecycle` is an object with `owner` (`parent` or `app`), `automatic_retention_cleanup_possible`, and `durable_branch_required_before_unique_work`. Create a durable authorized branch/ref early when unique work must survive task/worktree lifecycle. `remove_worktrees: false` prevents the harness from removing one; it cannot disable platform-managed retention.

For `launch_kind: "run_dynamic_workflow"`, the parent consumes the whole accepted wave through one flat Claude Dynamic Workflow invocation:

1. Confirm the observed provider is `claude_code`, the selected driver is `dynamic_workflow`, and the installed Claude Code version/runtime exposes Dynamic Workflow.
2. Allocate one authorized durable branch, parent-managed worktree, worker ID, and lease per selected mission from the same `batch_base_sha` before starting the workflow.
3. Build the workflow arguments from the accepted selector result and frozen worker handoffs. Pass each mission's lease ID, branch ref, existing worktree path, task data, verifiers, and plan/base identity. The agent must enter that exact worktree before any repository action and return blocked if it cannot bind; do not let the workflow discover or mutate canonical PLAN/RUN state or create replacement worktrees.
4. Invoke the Claude Code `Workflow` tool with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and pass the accepted wave as structured `args`. The script launches sibling mission agents through `pipeline()` and returns complete `WORKER_RESULT` or `REFINEMENT_REQUEST` objects through `agent_result`. If the team chooses to save a reusable project command, place a rendered copy under `.claude/workflows/` only when that file write is planned and authorized.
5. Validate every returned result against the allocated lease and live Git facts, then integrate passing missions serially. A workflow-level exception or missing mission result leaves the affected mission blocked or failed; it is not a silent sequential success.
6. When a mission needs human sign-off or task refinement, preserve its result as blocked or `REFINEMENT_REQUEST`, return control to the parent, update canonical state there, and start a later workflow. Dynamic Workflow does not support mid-run user input.

Current Claude Code can support nested subagents, but RUN schema v6 and later deliberately keep Dynamic Workflow flat: the workflow is the single wave coordinator, every mission agent is a sibling and sole mission writer, and the adapter omits `nested_subagents`. This keeps the Harness worker budget, lease ownership, and result validation explicit. If Dynamic Workflow is unavailable, reroute deterministically to direct `subagents` when observed, otherwise to `sequential_parent`; never claim the workflow launched.

## Batch Integration And Recompute

The parent integrates one worker-passed mission at a time in declared merge order:

1. Confirm worker base/head ancestry and head stability.
2. Recompute actual changed paths and reject scope escape or parent-owned files.
3. Require at least one read-only review PASS bound to the exact current worktree head. Repair findings in that worktree and review the changed head again.
4. Integrate into persistent `development` only when `integrate_locally` is authorized.
5. Run the affected mission's integration verifiers after its integration.
6. Mark it `integrated` only after the gate passes and record `integrated_sha`.
7. Stop the batch on worker failure, review failure, integration failure, unexpected conflict, stale base, or contract gap.
8. Run cross-mission/batch verification after all selected missions integrate.
9. Refresh RUN observations and recompute the next ready frontier and conflict graph.
10. Repeat steps 1-9 with the recomputed frontier until the ready frontier is empty and no mission remains `queued`, `ready`, `leased`, `worker_running`, or blocked pending a retry. Only then proceed to the final/current-head gate on `development`; do not treat any single wave's completion as the run's finish line while missions remain outside a terminal phase.

Never reuse the prior wave's independence result. Each merge changes the integration head and may change dependencies, generated artifacts, or resource availability. Push, PR, deploy, task archival, worktree removal, and branch deletion remain separate authorization-gated actions.

## Conservative Fallback

When the selector, runtime, workspace isolation, completion channel, or observed facts are unavailable, keep the same plan and gates but execute one mission at a time. Lack of parallel capability is not a reason to bypass verification or invent state.
