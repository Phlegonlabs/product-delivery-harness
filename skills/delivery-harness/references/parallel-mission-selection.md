# Parallel Mission Selection

Use this reference after the parent-only `System Review And Route` stage and Plan Readiness pass, before any parallel write fan-out. Selection is deterministic analysis. It does not create tasks, branches, worktrees, commits, merges, pushes, or cleanup actions. The system review itself is never selected as a graph node and never creates PLAN/RUN state.

The Project Size Gate and `System Review And Route` (see `execution-state-model.md`) run first. Small work never reaches this selector. Large work uses scheduler fan-out only when at least two dependency-ready, nonconflicting missions make parallel execution useful; otherwise keep the accepted PLAN/RUN graph and execute the derived `managed_sequential` route with its selected runtime driver. A no-agent route uses `sequential_parent` and writes one mission at a time. See `execution-state-model.md`'s `sequential_parent` definition.

This file defines the shared scope/resource conflict rules and deterministic write budget. PLAN v6 and RUN v11 use `scripts/select_ready_nodes.py`. The selector computes the typed graph frontier first, then applies this contract to ready mission nodes. For a managed-sequential route, never run parallel writers in `shared_checkout`; the selected driver and isolated writer remain explicit.

For every execution-authorized managed run, selection is the default post-readiness action, not an optional optimization the parent may skip. Prove the chosen runtime driver before readiness and run the selector before any production task. The selected wave contains every dependency-ready, nonconflicting mission the effective budget allows — it shrinks only when live capacity, isolation, dependencies, conflicts, resources, permissions, or authorization actually require it, never because of an arbitrary starting number. The selector reports `managed_sequential` for fewer than two actually selected safe write missions and `parallel_graph` for two or more; this derived route is separate from `runtime_driver`. A one-mission managed route makes no fan-out claim, requires no tasks view, invents no cross-mission batch gate, and inventories no unused parallel drivers; it keeps the isolated writer, authorization, scope/head, and review gates.

Observe every advertised current driver before dispatch. Unrelated surfaces need no inventory; capability and authorization stay separate.

## Capacity And Dispatch

Before accepting a multi-mission wave, check `observed.runtime.available_worker_slots` and `isolation_capacity` against current host evidence. `new_run.py` seeds both as 1; those placeholders are not a measured one-worker limit. `max_parallel_workers: 4` alone does not override observed capacity. A Git observation does not discover agent slots. Record the actual available capacity through `record-observation --available-worker-slots <n> --isolation-capacity <n> --capacity-evidence <text>`; global `--repo-root` precedes the subcommand. These values must come from current host evidence, never a guessed number. If independent missions remain deferred, report the specific capacity, dependency, scope, resource, or authorization reason.

Launch every selected worker in its own authorized worktree before waiting for any worker to finish. Short launch/lease bookkeeping may be sequential; implementation must overlap when the driver supports it, so dispatch a blocking external CLI asynchronously rather than awaiting it inside a loop. Collect each result as it finishes. Serial task checkpoints stay inside each mission and serial integration stays in the parent; neither serializes independent mission workers.

Host build/test commands do not consume Docker/Podman capacity. Serial host verification within one runner/checkout does not lower the worker budget or prevent other isolated worktrees from executing. Shared ports, databases, credentials and caches still need accurate resource claims.

## Inputs And Output

The selector reads only canonical machine data. For current RUN v11, provider routing comes from `runtime_capabilities.runtime_adapter`:

- Static `harness_plan` JSON from `PLAN.md`.
- Mutable `harness_run` JSON from `RUN.md`.
- Explicit observed-capacity inputs supplied by the parent when they are not already in a fresh RUN snapshot.

It must not parse Markdown tables, inspect UI labels, guess resource ownership, or mutate Git/runtime state.

When routing selects `sequential_parent`, the selector emits at most one mission directive at a time for the existing PLAN `executor: runtime_worker` node, bound per `execution-state-model.md`'s Sequential Parent Route; the route does not require `spawn_subagents` or `create_user_owned_tasks` and is not a delegated launch. Keep the same PLAN/RUN, review, integration, and exact-head gates as delegated execution.

The output is canonical sorted JSON with no timestamps. Its top-level keys are exactly:

```text
plan_id
plan_revision
plan_digest_sha256
graph_revision
execution_route
ready_frontier
dispatchable_nodes
deferred_nodes
conflict_edges
```

`ready_frontier` lists the node IDs that are logically ready before dispatch gating. Serialize each deferred entry as `{ "node_id": ..., "reason_codes": [...] }` and each conflict edge as `{ "left": <node ID>, "right": <node ID>, "reason_codes": [...] }`. Sort IDs and reason codes; never encode a reason only in prose.

Each `dispatchable_nodes` entry carries the node's `node_id`, `kind`, `ref`, and `launch_kind`; runtime-bound nodes also carry the runtime provider/driver/source, the immutable `runtime_binding`, `tool_profile`, `failure_outcome`, required action keys, and the runtime/workspace/completion axes. It contains no allocated worker, task, branch, or worktree identity. The `batch_base_sha`/budget binding and concrete launch arguments are parent-side steps, not selector output: the parent re-observes facts, records the batch base and accepted wave in RUN, and renders launcher arguments from the dispatchable entries. The output is a proposal until the parent rechecks observed facts and records it in RUN state.

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
9. Required action-specific authorizations for the proposed launch path are present. Parent-owned sibling agents require `spawn_subagents`; isolated writes also require parent-managed worktree, branch, and commit authorization.
10. The inherited permission boundary is observed and already covers linked-worktree Git metadata, temp/cache, outbound network, local/private bindings, and required sockets.
11. No human approval, secret, service, contract decision, or destructive action remains unresolved.

An isolated write worker must have an authorized durable branch/ref and `create_local_commits: true`; the portable protocol does not integrate an uncommitted patch from another workspace. When those are unavailable, the mission stays deferred and the parent requests the missing branch/commit authorization; the integration checkout is merge-only and never hosts implementation.

Selection happens before worker/task/branch/worktree identities are allocated. Therefore a launch-path action passes this pre-allocation gate only when the user explicitly authorized that action for the mission scope with `targets: ["*"]`. For a RUN-v11 mission launch that grant must also list exact `mission_ids`, not `"*"`, at every version, because RUN validation checks each launch receipt against exact mission ids; the selector defers such a launch and `lease-worker` refuses it. A current subagent reviewer also needs exact `mission_ids`. A selector must never manufacture `worker:<mission-id>`, `branch:<mission-id>`, or another pseudo-target. After the parent allocates concrete identities, it checks the exact `worker:`, `task:`, `worktree:`, or `branch:` target again immediately before each mutation; the pre-allocation result is not a substitute for that check.

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

Declare only the files or subtrees the mission actually needs. For independent page work, naming one shared tests directory as `/**` in every mission creates a real scope conflict even when the planned test files differ. Use exact paths where known; put genuinely shared helpers or contracts in a foundation dependency. Never narrow a scope merely to bypass a real overlap.

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
- **Integration-stage-only use** (no mission-level claim needed): a shared local dev server or database that only an `integration_verifiers` end-to-end/migration check depends on. Integration already happens one mission at a time, so that resource is serialized where it is used; an exclusive mission-level claim would only block worker-stage parallelism.
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

Unary ineligibility or deferral belongs on the node entry, not on a graph edge. Most deferral codes name their own cause (`action_not_authorized`, `over_budget`, `write_conflict`, `run_paused`); the selector output is authoritative. These deferral codes need a remedy:

- `ui_authoring_skills_missing` — a current Wireframe or HiFi HTML authoring mission lacks `ui-design-builder` or `frontend-design` in `required_skills`; retain historical PLAN validity and repair the current dispatch contract before leasing.
- `authorization_head_stale` — a v10 head-bound lifecycle grant does not cover the current integration head.
- `independent_reviewer_unavailable` — a sequential-parent review node requires an independent reviewer and no role-aware fresh-reviewer driver or other allowed host is available.
- `review_result_dissent` — the node's current review result disagrees with the recorded worker outcome.
- `capability_unprobed` — independent, conflict-free, authorized missions were held back only by a write budget, and `runtime_adapter.detection_source` is still `fallback`. The selector withholds the whole proposal in that state rather than dispatching one mission: `fallback` means the capability was never determined, so a sequential wave there is a guess presented as a decision, and it looks exactly like a deliberate cap. Resolve it by probing the host and recording real capacity (`observed`), or by declaring the sequential route on purpose (`explicit`). A genuine observed capacity of one is a real answer and dispatches normally.
- `pinned_bundle_or_restart_required` — historical `adopted` cannot dispatch in current tools; use its exact pinned bundle or restart.
- `runtime_contract_unobserved` — a required loaded or installed Harness digest is unknown; preserve unknown identity and follow `runtime-upgrades.md`.

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

Set the configured maximum generously high; observed slots, isolation capacity, and conflict capacity do the bounding. Lower it only for a user instruction or a real runtime limit. `shared_checkout` is not an eligible workspace for plan-backed mission writes; direct/read-only inspection remains separately governed.

Then scan candidates in order:

1. Add a candidate when it has no conflict edge to any already-selected mission.
2. Otherwise defer it and record every conflict reason and conflicting selected mission.
3. Stop adding after the effective budget is reached.
4. Record ready-but-over-budget missions separately from conflicting or unsafe missions.

Given semantically identical canonical inputs, selection must be byte-for-byte stable regardless of source list order, hash seed, locale, or invocation time.

## Parent Launch Gate

Before using a proposal, the parent re-observes the list below. This is one batched turn, not one turn per bullet: run `scripts/harness_step.py --plan <PLAN.md> --run <RUN.md> --repo-root <root>` to derive every manifest- and Git-derivable fact and the ready frontier in a single read-only call, then observe the host-only facts it names under `still_observe_yourself`. The contract fixes the order of mutating actions, never the number of parent turns spent reading.

The facts:

- Plan revision and digest.
- Integration branch and committed `batch_base_sha`.
- Dirty state and uncommitted shared foundation.
- Available worker slots and isolation capacity.
- Observed provider, available runtime drivers, and the selected deterministic route.
- Existing branch/worktree names and paths.
- Each selected mission's required authorizations and completion channel.
- The selected parent permission mode/profile, worker inheritance, and every required filesystem/network/local surface.

If anything differs, discard the proposal and rerun selection. Launch workers with leases bound to the accepted plan revision/digest and base SHA.

Recording the accepted wave and batch base, minting worker/branch/worktree identities, and re-checking each exact target immediately before its own mutation stay parent actions. `harness_step.py` is read-only and records nothing.

When the proposal is empty only because launch actions are unauthorized, request the preferred route's exact bundle once with run-wide mission scope and pre-allocation `targets: ["*"]`, then pause. After the answer is recorded, rerun validation and selection. If the System Review And Route selected no-agent execution, use `sequential_parent` directly and do not request `spawn_subagents` or report a delegated launch. For an agent-capable route, use sequential fallback only after the user declines or a non-authorization capability, isolation, permission, dependency, conflict, or resource gate prevents the wave.

Current dispatch supports subagents and sequential-parent work only.
If the owner explicitly requests user-owned app tasks, report the unsupported route and stop that dispatch.
Never replace those tasks silently or fabricate an app-task identity.
Historical app/task bindings use their [exact pinned bundle](legacy-pins.md#finishing-a-run-on-its-pinned-bundle).

## Batch Integration And Recompute

One wave lifecycle has a fixed mutation order. Worker-result validation accepts a result only while its wave is active. The selector blocks new writer waves and lifecycle mutations while `run.active_wave.status` is `active`. Under `review_policy: per_mission` it may also stream a dependency-ready, read-only pre-integration review for a selected mission at `worker_passed`, and integrate a finished mission once that review passes. So:

1. Launch all selected workers before waiting for completion; each uses its own authorized worktree.
2. Record each selected mission through `record-worker-result` against the still-active wave. Under `per_mission`, as each mission reaches `worker_passed`, re-run selection and dispatch its ready review while sibling workers continue.
3. Close the wave once all selected missions' worker results are recorded. Under `per_mission`, a mission whose exact-head review has PASSed may integrate before this transition, one at a time. Batch gates wait for wave close.
4. Re-run selection and dispatch any remaining review nodes per `verification-gates.md#review-topology`; repairs follow `gen-verify-correct.md#loop`.
5. Integrate the passing missions serially in declared merge order (steps below).
6. Run the batch gates, then recompute.

The integration procedure itself is defined once, in `worktree-thread-orchestration.md`'s Batch Integration section. Under `per_mission`, one selector-specific rule applies on top of it: the review PASS bound to the exact current worktree head may come from the streamed active-wave review or a post-close selector pass, and a terminal covering `review_workers[]` PASS on that SHA must be recorded before the mission transitions to `integrating`.

Selection then continues: refresh RUN observations, recompute the ready frontier and conflict graph, and repeat until the frontier is empty and no mission remains `queued`, `ready`, `leased`, `worker_running`, or blocked pending a retry. A failed mission may retry only after `retryable_failure`. A blocked mission may retry only when its latest mission attempt is an `interrupted_worker_reconciliation` with result `blocked`; `contract_gap` stays blocked for PLAN refinement. `lease-worker` enforces the same rule as the selector. Only then proceed to the final/current-head gate on the resolved integration branch; do not treat any single wave's completion as the run's finish line while missions remain outside a terminal phase.

Never reuse the prior wave's independence result. Each merge changes the integration head and may change dependencies, generated artifacts, or resource availability. Push, task archival, worktree removal, and branch deletion remain separate authorization-gated actions.

## Conservative Fallback

When the selector, runtime, workspace isolation, completion channel, or observed facts are unavailable, keep the same PLAN/RUN graph and gates but execute one mission at a time as the parent when no agent route is available. Lack of parallel capability is not a reason to bypass verification, author compact RUN-only state, or invent a worker spawn.
