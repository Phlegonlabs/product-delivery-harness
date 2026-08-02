# Execution State Model

Use this reference for long, multi-mission, refined-task, or parallel execution. It defines which artifact owns each kind of state and prevents a worker result from being mistaken for an integrated result.

## System Review And Route

Before any PLAN/RUN artifact, task-specific skill, runtime adapter/model selection, worker preflight, or worker launch, the parent performs one bounded, read-only `System Review And Route`. It reads the user request, repository instructions, current Git state, requested scope, and available upstream product/design inputs, then records a route decision outside managed artifacts:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
```

The stage is parent-only and cannot create or edit `PLAN.md`, `RUN.md`, `tasks.md`, evidence, branches, worktrees, or other managed state; it does not load a task skill, select a worker/model, invoke an external runtime, or spawn a worker. A small route remains direct and creates no PLAN/RUN. A large route creates the current PLAN schema v5 plus RUN schema v10 and only then enters graph readiness. The stage is not a graph node and must not be represented in `graph_state`.

When no agent capability is available after routing, the large route remains plan-backed and selects `sequential_parent`: the PLAN mission remains `executor: runtime_worker`, while RUN records a parent-owned executor/worker binding solely for lease/state validation (`worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, `completion_channel: agent_result`). This binding is not a delegated or spawned worker and requires no `spawn_subagents`; the parent is the sole mission writer and executes one mission at a time. A parent-managed worktree is required; if it is unavailable or unauthorized, the route blocks rather than writing in `shared_checkout`.

## Three Authorities

The harness has three distinct authorities. Do not merge them into one table or infer one from another.

| Authority | Owns | Does not own |
|---|---|---|
| `PLAN.md` | Static declarations for one plan revision: requirements, traces, mission/task definitions, dependency DAGs, scopes, resource claims, verifier commands, provider/model policy, priorities, and merge ranks | Worker leases, live phase, current Git head, verifier results, authorization decisions, or selected waves |
| `RUN.md` | Mutable coordination state: readiness, explicit authorization ledger, chosen runtime capabilities, mission/task phases, leases, workers, wave proposals accepted by the parent, integration outcomes, batch/final-gate results, UI artifact metadata, landing state, blockers, and evidence pointers | Repository truth, process truth, or a new plan definition |
| Observed Git/runtime facts | The current checkout, refs, commit ancestry, diffs, worktrees, dirty state, active worker slots, process availability, and completion signals | User authorization or declarative scope |

`PLAN.md` and `RUN.md` each contain one canonical fenced JSON manifest. The exact level-two headings are `## Harness Plan Manifest` and `## Harness Run State`; the first non-empty content after each heading is its single fenced `json` block. Markdown tables — including the standalone `tasks.md` (`assets/templates/TASKS.template.md`), a regenerated mission/task listing view created alongside `RUN.md` — are non-canonical human views. Tools parse the JSON manifests only; they must not recover state from prose or tables.

The parent is the only writer of `PLAN.md` and `RUN.md`. Workers return reports and evidence. The parent verifies those reports against observed facts before changing canonical state.

New managed work is never authored as compact RUN-only work. Legacy compact RUN-only manifests whose `plan` identity fields are `null` remain readable and validatable for migration and closeout compatibility, but they make no current scheduling claim and cannot authorize new managed execution or enter the PLAN-v5/RUN-v10 graph. When work continues, the parent creates a fresh PLAN schema v5 and RUN schema v10 pair after routing; it does not null the PLAN fields in the current runbook. “Sequential” for a current large run describes the mission cadence: keep the PLAN mission's `executor: runtime_worker`, record the parent-owned executor/worker binding in RUN solely for lease/state validation, and bind it to `worker_runtime: parent`, `parent_managed_worktree`, and `agent_result`. The binding is not a delegated or spawned worker, so no `spawn_subagents` grant is needed; the parent executes one mission at a time. Parent-managed worktrees are required, and an unavailable or unauthorized worktree blocks the route rather than permitting a `shared_checkout` write. Require one exact-head read-only review before parent integration, then merge the passing head into the resolved integration branch and run its integration gate.

Use exact RUN lifecycle values:

```text
status: draft | ready | running | blocked | complete
plan_readiness: draft | ready | blocked
```

`complete` is an execution closeout state, not a label the parent may set independently. Setting `status: complete` requires every applicable condition below to hold:

| Condition | Requirement |
|---|---|
| Execution intent | The run carries execution intent, not plan-only |
| Inputs frozen | Every source input is ready/frozen or accepted |
| Integration head | A `integration_head_sha` is recorded |
| Missions | Every mission is integrated or superseded |
| Tasks | Every live task is `mission_recorded` with a PASS verifier |
| Blockers | No blockers remain |
| Workers | No active or blocked mission or review worker |
| Waves | No proposed or active wave |
| Landing | `landing.continuity` is `preserved` with its `head_sha` equal to the integration head |
| PLAN-v5 graph run | Every node is succeeded, skipped, or superseded; every edge is terminal; no retained node blocker (a failed node must be routed or superseded before closeout) |
| RUN-v10 gates | Every PLAN batch and final gate has a PASS result bound to the integration head, and every required UI screenshot matrix entry is PASS; when a UI registry is supplied, the PLAN surface matrix also covers its exact responsive set, required states, and route trace/test bindings |
| Gate freshness | A changed integration head invalidates an earlier gate PASS immediately, in every RUN lifecycle state |

New runs are authored at RUN v10. The manifest validator still reads older RUN schemas, but graph selection and node-result validation require RUN v10. RUN v9 introduced the gate arrays; v10 adds PLAN-v5 binding, continuity, and append-only verifier history.

`plan_readiness: ready` is the machine gate. Human verification tables may display `PASS`, but selectors never substitute a table cell for canonical readiness.

New PLAN/RUN files are authored at the current schema (PLAN v5, RUN v10). Older files remain validatable as manifests but cannot drive graph selection or node-result validation.

## Plan Revisions And Snapshots

Every plan manifest has a stable `plan_id`, a positive integer `revision`, and a semantic SHA-256 digest of the `harness_plan` object. Before encoding, the shipped tools recursively canonicalize dictionaries; sort object lists with `id` by ID, resource lists by `(key, access)`, and scalar set-like lists lexically; and preserve `argv` order because command argument order is semantic. Canonical bytes are the UTF-8 encoding of `json.dumps(normalized_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Reordering sources, missions, tasks, claims, or other set-like fields therefore does not change the digest. Any semantic change to mission/task definitions, dependencies, scopes, resources, or verifiers creates a new digest and requires an incremented revision.

Verifier declarations are data, not shell prose. Each verifier records at least `id`, repository-relative `cwd`, argument-vector `argv`, and a deterministic `pass_signal`. This keeps validation independent of shell quoting and makes worker and integration gates auditable.

A worker-supplied hash is only a claim, even when it is 64 lowercase hexadecimal characters. The parent retains each `verifier_runtime.py` result, including verifier ID, immutable context, key document, exact head, status, exit result, and execution key. Worker-result validation recomputes the key from the retained key document and requires the reported verifier ID, status, and evidence key to match that parent-retained result exactly. Missing, forged, stale-context, wrong-head, or mismatched results fail closed.

Derived artifacts must bind all three values:

```text
plan_id
plan_revision
plan_digest_sha256
```

A selected wave also binds a committed `batch_base_sha`. A proposal becomes stale when its plan revision, plan digest, or base SHA no longer matches current observed facts. Recompute it; do not edit the old result into apparent validity.

Any script or manual edit that mutates `PLAN.md`/`RUN.md`'s JSON content must pipe its result through `scripts/validate_harness_plan.py` (and `validate_node_result.py`/`validate_worker_result.py` where applicable) before writing back and before the mutation is treated as authoritative. A one-off script that recomputes a digest or bumps a revision without running the shared validator can silently produce an invalid plan — a broken DAG, an unreachable trace, a malformed verifier — that nothing catches until a much later gate, if ever.

Observed facts are read live before every mutating action. `RUN.md` may record a timestamped snapshot under `observed` for auditability, but the snapshot never replaces a fresh check.

The minimum RUN snapshot shape is:

```json
{
  "observed": {
    "captured_at": null,
    "git": {
      "parent_worktree_path": null,
      "parent_branch": null,
      "parent_head_sha": null,
      "parent_dirty": null,
      "worktrees": []
    },
    "runtime": {
      "available_worker_slots": 1,
      "isolation_capacity": 1,
      "completion_channel_available": true
    }
  }
}
```

`null` means “not observed yet,” not “safe” or “not applicable.” A selector that needs a null fact must defer or request a fresh observation.

## Canonical Mission Phases

Mission phases are finite-state values, not free-form progress notes:

```text
queued -> ready -> leased -> worker_running -> worker_passed -> integrating -> integrated
```

Terminal or interrupting phases are:

```text
blocked | worker_failed | integration_failed | superseded
```

| Transition | Required evidence |
|---|---|
| `queued -> ready` | Dependencies are integrated, gates pass, authorization permits the next action, and the mission has no blocker |
| `ready -> leased` | Parent records one worker lease bound to mission, plan revision/digest, and base SHA |
| `leased -> worker_running` | Worker identity and workspace are observable |
| `worker_running -> worker_passed` | Worker verifier passed and a result with head SHA, diff summary, and evidence was returned |
| `worker_passed -> integrating` | Parent rechecks ancestry, actual diff scope, forbidden files, head stability, integration authorization, and at least one retained read-only review PASS bound to the exact worktree head; enabled task-local review uses the worker's canonical `nested_review_evidence`, while a disabled policy or graph-backed direct worker without one requires a terminal covering `review_workers[]` PASS |
| `integrating -> integrated` | Changes are on the resolved integration branch, the integration verifier passed, and `integrated_sha` is recorded |

These phase transitions describe one run's lifecycle; when `run.integration.retention` is `"persistent"`, the integration branch itself survives across runs rather than being scoped to a single run.

`worker_passed` is not completion for dependency purposes. It means only that the worker-level gate passed in its workspace. A dependent mission becomes ready only when every dependency is `integrated`, its integration gate is `PASS`, and observed Git ancestry confirms its `integrated_sha` is an ancestor of the current integration head.

`worker_failed` preserves the worker result and evidence. `integration_failed` preserves the worker-passed state plus the failed integration attempt. Neither unlocks downstream dependencies. Retrying creates a new attempt or lease; it does not overwrite the failed evidence.

## Canonical Task Phases

Tasks are executed sequentially inside one mission worker. Use the same success distinction at task scale:

```text
queued -> ready -> running -> worker_passed -> mission_recorded
blocked | worker_failed | superseded
```

`worker_passed -> mission_recorded` occurs when the parent confirms the passing task's commit/change is reachable from the reported mission head and represented by its `task_results` entry in the accepted worker result/report. The parent may record both observations in one serialized RUN update, but it must preserve the evidence distinction. A blocked/failed mission result names `current_task_id` and preserves earlier task results. `mission_recorded` does not make the mission `integrated`. Refined parent tasks use `superseded`; their replacement tasks carry the executable work.

## Resume Reconciliation Gate

A `running` RUN can be picked up by a different session than the one that last touched it — the same host resuming after an interruption, or a different agent entirely. Before that parent selects or launches any ready node, it must reconcile the observed working tree against canonical `task_states`/`mission_states`, not just trust the last recorded checkpoint.

Read `observed.git.parent_dirty` and the actual diff live. If the checkout is dirty, map every changed path to the task(s) whose `write_scope` covers it. Any dirty content that falls inside a task still at `queued`, `ready`, or `running` — i.e. not yet `worker_passed` — is drift: real work exists that canonical state does not account for. This is exactly how an interrupted session leaves a large, unverified pile behind: implementation kept going across several tasks without the verify-then-commit checkpoint ever firing in between, so nothing downstream ever learned the work existed.

Drift blocks new work. The parent must resolve it before advancing to the next ready node, by one of:

- Running the covering task's own verifier against the current dirty state. If it passes, commit per `commit-convention.md` and record the task as `worker_passed` (then `mission_recorded` once integration-reachability is confirmed) so canonical state now matches reality.
- If the drift does not pass verification, is partial, or its origin is unclear, stop and ask the user how to proceed (finish and verify it, stash it, or discard it) rather than silently building further work on top of unverified, unrecorded state.

Never treat a dirty checkout as either "safe to ignore" or "safe to build on" without this reconciliation — both let the same gap compound on the next resume.

A resume snapshot is usable only when the parent checkout path, branch, head, and clean/dirty state are all known. Enumerate live linked worktrees before frontier selection and reconcile each one to a recorded worker or to the primary checkout. Reconcile every nonterminal worker to its exact worktree path, branch, observed head, and clean state. An unknown or dirty parent/worktree, an unrecorded linked worktree, a missing worktree for a live write worker, or a branch/head mismatch blocks the whole frontier until the parent records or resolves it. A stale RUN snapshot is not a safe default.

## Typed Graph State

PLAN v5 and RUN v10 carry the typed-graph contract: typed nodes, explicit dependency/route edges, and one `graph_state` object with the matching plan revision, one state per node, and one state per edge. The graph state is the routing authority; mission state remains the operational lease, Git, worker, and integration detail for mission nodes.

Use node phases:

```text
dormant | ready | running | succeeded | failed | blocked | skipped | superseded
```

Use declared outcomes only:

```text
pass | fix_required | retryable_failure | blocked | contract_gap
```

Every node state records `attempts`, `last_attempt_id`, `last_outcome`, optional bound worker, and blockers. Every edge state records `status`, traversal count, and source attempt. A terminal node requires an attempt identity and outcome. A mission node may become `succeeded/pass` only when its mission is `integrated` with an integration `PASS`; the validator rejects either side claiming completion without the other.

Dependency edges always consume `pass` and remain acyclic. Route edges activate from declared outcomes. A cyclic route requires a PLAN traversal bound and an exit. A retry or subgraph replay creates new attempts and preserves old evidence; it never revives a lease, action grant, base/head binding, or verifier result.

Run `select_ready_nodes.py` for PLAN v5 with RUN v10. It computes graph readiness before runtime binding, then applies the existing write-conflict and worker-budget rules to ready mission nodes. See `graph-orchestration.md` for the complete routing contract.

## Authorization Action Ledger

Authorization is action-specific. Overall `execution_authorized` also has siblings `execution_authorization_source` and `execution_authorization_scope`; when true, both must match the run, mission, and expiry boundary. Every action entry defaults to `authorized: false` and records an explicit user source before it can become true. A goal, plan, template, skill selection, worker report, or assistant assumption cannot authorize itself.

The ledger has exactly 12 actions:

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
archive_worker_tasks
remove_worktrees
delete_branches
```

`invoke_external_runtime` is required when the Harness parent starts a different provider process or service. Its target is `runtime:<provider>`. It does not replace `spawn_subagents`, worktree, branch, commit, integration, or lifecycle authorization.

Nine possible entries — `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, and `push` restricted to the resolved integration branch — carry the ordinary development loop. Per `SKILL.md`'s Execution Authorization Gate, one execution-intent instruction covers only the subset that the selected route actually uses, recording its `source` under each covered entry in a single authorization request or checkpoint. The outer v10 `app_threads` app-task route excludes `spawn_subagents` from that pre-allocation subset; an enabled nested policy may request an exact `worker:<id>` grant only after worker allocation, while an omitted or disabled policy launches no nested children. Direct subagent and Dynamic Workflow routes retain their existing `spawn_subagents` requirements, and RUN v6-v9 nested policies retain their mandatory wildcard-compatible legacy behavior. The remaining three (`archive_worker_tasks`, `remove_worktrees`, `delete_branches`) and any `push` aimed outside that scope stay independent gates that each need their own authorization moment. Each covered loop action still records its own `source`, and `push` still carries exact targets; grouping only avoids manufacturing separate confirmation pauses.

For a large `sequential_parent` route, the parent executes the PLAN mission through its `executor: runtime_worker` node, not a delegated worker launcher: leave `spawn_subagents`, `create_user_owned_tasks`, and `create_app_managed_worktrees` unauthorized and unused. RUN records the parent-owned executor/worker binding solely for lease/state validation, with `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result`; it is not a spawned worker. The route's parent-owned worktree/branch/commit/integration actions still require their own matching grants, and an unavailable or unauthorized parent-managed worktree blocks rather than downgrades to `shared_checkout`.

One branch guard applies to `push`, and it is the whole guard: the push is refused when the requested target resolves to `main`, or when the run's own `integration.branch` resolves to `main`. It reads only those two values — no evidence field, no contract marker, no repository lookup.

Each `authorizations` entry has this minimum shape:

```json
{
  "authorized": false,
  "source": null
}
```

When `authorized` is true, add a required `scope` object with `run_id`, `mission_ids`, and exact `targets`, plus `expires_when`. Schema v10 additionally requires `plan_revision` and `plan_digest_sha256` in that scope, and both must equal `run.plan.revision` and `run.plan.digest_sha256`:

```json
{
  "authorized": true,
  "source": "<exact user statement>",
  "scope": {
    "run_id": "<run id>",
    "plan_revision": 3,
    "plan_digest_sha256": "<64-hex>",
    "mission_ids": ["M1"],
    "targets": ["branch:refs/heads/codex/<short-name>"]
  },
  "expires_when": "run_complete"
}
```

That pair is what makes `SKILL.md`'s rule real: when the plan revision or digest changes, the scope stops matching and the grant stops covering anything, instead of silently carrying forward. Below v10 the scope has no plan binding, so nothing compares one — the invalidation rule is inert there and a v7-v9 grant survives a plan change untouched.

Targets use action-specific prefixes, and there are only five: `worker:`, `task:`, `worktree:`, `branch:`, and `runtime:`. The kind is part of the action's type, so every action accepts only its own kinds and this is always enforced — there is no per-artifact opt-in. `expires_when` is `wave_closed`, `run_complete`, or `explicit_revocation` and is evaluated against current RUN state. Use `"*"` only for a dimension the user explicitly authorized run-wide. A selector/coordinator treats missing, expired, or nonmatching scope as unauthorized; authorization is never a global boolean inferred for every mission or target.

`wave_closed` is one-use authorization for the currently recorded wave. Its scope must add the immutable `wave_id` and `batch_base_sha`, and both values must equal the current `active_wave` while that wave is `proposed` or `active`. When that wave becomes `closed` or `superseded`, append its `{ "wave_id", "batch_base_sha" }` pair to the v10 RUN's durable `closed_waves` list before replacing or re-proposing `active_wave`. Every matching action entry then returns to `{ "authorized": false, "source": null }`, and overall execution authorization is cleared when it used the same boundary. Never copy or revive a wave-scoped grant for a pair already in `closed_waves`; a new wave needs a newly recorded explicit source and a new identity/base pair. Legacy RUN schemas remain readable without this v10 history field.

A `run_complete`-bounded authorization stays valid evidence at closeout even after its boundary expires — do not erase the record of what was authorized and done just because the run finished.

`source` identifies the user statement or durable approval record. Narrow authorization remains narrow:

- Static conflict and parallel-eligibility analysis performed by the parent does not require implementation, worktree, branch, commit, or integration authorization. A launch-bound ready frontier and selected wave do require execution plus all launch-path authorizations. Delegating even read-only analysis still requires `spawn_subagents` or `create_user_owned_tasks`, according to the chosen worker primitive.
- `spawn_subagents` does not authorize user-owned app tasks.
- Worktree creation does not authorize branch creation, commits, integration, or cleanup.
- Local integration does not authorize branch deletion, worktree removal, or any `push` outside the integration-branch scope named above.
- Platform-managed retention is not a harness cleanup action and may still apply to app-managed worktrees.

Before each action, check its entry again and compare it with observed state. A previously authorized action can still be unsafe because the target changed or the plan became stale.

## Landing State

Schema v10 requires a `landing` object with exactly four keys:

```text
mode: local_only | integration_push
remote
pushed_head_sha
continuity: { status, branch_ref, head_sha, reason }
```

A run ends in one of the two modes. `integration_push` is the ordinary end: the verified integration head is pushed to the run's own branch, and the run is complete at that push. `pushed_head_sha` must equal `integration.integration_head_sha` — a later local commit would otherwise leave the run claiming a head the remote never received — and the push needs an authorization covering the integration branch. `local_only` is for a run that must not touch the remote at all; it cannot record a pushed head. Either way, every mission worktree still passes its exact-head pre-integration review.

Landing that branch on the default branch is the user's own step, done outside this harness. The harness opens no pull request, merges nothing, deploys nothing, and records none of it.

`integration.branch` is the only branch field in RUN. Every push target is built from it, so there is no head/base pair to keep in sync.

`continuity` records that the run branch survives the run — it is what the user reads and lands:

```text
status: planned | preserved | blocked
```

`planned` and `preserved` require a full local `refs/heads/` ref in `branch_ref`. `preserved` also requires `head_sha`. `blocked` requires a `reason`. Authorized execution requires `planned` or `preserved`; a `complete` run requires `preserved` with `head_sha` equal to the integration head.

## Runtime Capability Axes

Represent orchestration with three independent axes. Do not encode them as a single mode string.

RUN records them together under `runtime_capabilities`, along with `max_parallel_workers`, a `platform_lifecycle` object, and optional backward-compatible `nested_subagents` and `permission_boundary` objects. Schema v10 requires `runtime_adapter`. `platform_lifecycle` has `owner` (`parent` or `app`), `automatic_retention_cleanup_possible`, and `durable_branch_required_before_unique_work`.

### Runtime adapter and routing

RUN v10 records observed host capabilities without replacing the three portable axes:

```json
{
  "runtime_adapter": {
    "provider": "claude_code",
    "available_drivers": ["dynamic_workflow", "subagents", "sequential_parent"],
    "detection_source": "observed"
  }
}
```

`provider` is `codex`, `claude_code`, or `generic`. `detection_source` is `observed`, `explicit`, or `fallback`. `available_drivers` contains only capabilities proven in the current surface and always includes `sequential_parent`. The selector applies a fixed route: Codex uses `app_threads`, then `subagents`, then `sequential_parent`; Claude Code uses `dynamic_workflow`, then `subagents`, then `sequential_parent`; generic uses `subagents`, then `sequential_parent`.

RUN v10 adds an optional `runtime_adapter.capability_probe` that is valid only for an observed Codex adapter. It becomes required before such a run enters `ready` or `running`, even if another stale or malformed field still claims readiness is blocked:

```json
{
  "capability_probe": {
    "app_project_list": {"status": "available", "evidence": "tool:codex_app__list_projects"},
    "app_thread_create": {"status": "available", "evidence": "tool:codex_app__create_thread"},
    "app_thread_read": {"status": "available", "evidence": "tool:codex_app__read_thread"},
    "app_thread_message": {"status": "available", "evidence": "tool:codex_app__send_message_to_thread"},
    "app_thread_wait": {"status": "available", "evidence": "tool:codex_app__wait_threads"},
    "app_managed_worktree": {"status": "available", "evidence": "create_thread supports a worktree target"},
    "direct_subagent_spawn": {"status": "available", "evidence": "tool:spawn_agent"},
    "direct_agent_result": {"status": "available", "evidence": "direct agent-result channel"}
  }
}
```

Every probe entry has exactly `status` and `evidence`; status is `available`, `unavailable`, or `unobserved`, and evidence is non-empty. Ready/running observed Codex execution rejects a missing probe or any `unobserved` entry with `capability_snapshot_incomplete`. All six `app_*` entries being available derives `app_threads`; both `direct_*` entries being available derives `subagents`; `sequential_parent` is always derived. `available_drivers` must equal those derived drivers in Codex priority order. Thus a parent cannot prove the app task/thread surface and then silently record only direct subagents or sequential execution. Blocked historical RUNs may remain readable without the probe, but they must re-probe before resuming.

PLAN v5 runtime-worker nodes may add `provider_options` for any provider in their `allowed_providers`. Each option uses the exact keys `model` and `reasoning_effort`. Model is null or a safe token matching `^[A-Za-z0-9][A-Za-z0-9._-]*$`. Reasoning effort is null or one of `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; selectable effort is supported for Codex and Claude Code, while generic providers keep it null. The selector chooses the provider first, then attaches its options to one immutable runtime binding. A missing Codex option means the destination default; a missing Claude option means `sonnet`. The destination host still validates current model and effort support.

When the parent allocates a PLAN-v5 graph worker in RUN v10, copy a mission binding into `workers[].runtime_binding` or a read-only verifier binding into `review_workers[].runtime_binding`, with provider, driver, source, model, reasoning effort, and option source. A review worker also records node/attempt identity, graph revision, review path, and exact reviewed SHA; it has no mission lease, writable worktree, branch, or commit authority. For Codex app tasks, pass non-null values through task creation. A Claude Code host passes each node's own model and non-null reasoning effort directly into that node's own `agent()` call inside the Workflow script; one wave may freely mix models and reasoning efforts across nodes since selection happens per spawned agent, not per wave. Never silently replace a rejected model or effort; replan the affected node and increment the PLAN revision.

For every plan-backed multi-mission run, capture this adapter before the first production edit or worker launch. Capability observation and action authorization are separate facts: record a usable driver even when its launch actions remain false. In particular, do not omit `app_threads` because `create_user_owned_tasks` or worktree authorization is missing. Record the capability, request the launch bundle once at Plan Readiness, and rerun selection after the answer.

Provider means the host session running the Harness, not every CLI installed on the machine. Observe current-session native tools first: Codex project/thread creation and polling for `app_threads`, Claude Code's `Workflow` tool and supported runtime for `dynamic_workflow`, and current-session child-agent tools for `subagents`. Use `explicit` only when the host surface is opaque; otherwise use `generic` + `fallback`. A binary or plugin version may confirm feature compatibility after provider detection, but it does not select the provider or authorize a launch.

The chosen host driver must match the portable host axes. `app_threads` requires `app_task` + `app_managed_worktree` + `thread_poll`. `dynamic_workflow` requires `subagent` + `parent_managed_worktree` + `agent_result`. Direct `subagents` use `subagent` with a supported shared or parent-managed workspace and direct result/report channel. `sequential_parent` requires `parent` + `parent_managed_worktree` + `agent_result`; parent-managed worktree creation is mandatory and an unavailable or unauthorized worktree blocks the route. It never implies a delegated or spawned worker.

For a plan-backed graph, every mission node remains a write mission with PLAN `executor: runtime_worker` and must bind to `parent_managed_worktree` or `app_managed_worktree`. A `sequential_parent` mission binds the parent-owned RUN executor/worker record to one mission at a time with `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result` solely for lease/state validation; it is not a delegated or spawned worker and needs no `spawn_subagents`. The selector never rewrites that node into a deterministic parent action or a shared-checkout write. If the required parent-managed worktree and its worktree/branch/commit authorizations cannot be obtained, the route remains deferred or blocked rather than downgrading.

A current PLAN-v5 typed node's `allowed_providers` must include the current host's provider for the node to be selectable at all; there is no other-host adapter to fall back into. A node whose `allowed_providers` excludes the current host provider is deferred with `runtime_unavailable` and reported as needing a run hosted by the matching adapter.

Claude Dynamic Workflow is a wave-level flat script, not a nested mission worker. The parent preallocates one worktree, branch, and lease per selected write mission. The workflow coordinates sibling agents and returns structured result candidates. Omit `nested_subagents` for this flat route. If a workflow stage needs human sign-off, return a refinement/blocker result and run a later workflow after the parent updates canonical state; never let a workflow script or agent edit PLAN/RUN directly.

RUN may record the outer Claude Workflow task/run identity, script digest, node group, options, and status in `workflow_runs`. A retry creates a new graph attempt.

### Worker runtime

```text
parent | subagent | app_task
```

- `parent`: the parent executes the mission loop itself.
- `subagent`: a child agent is owned and coordinated by the parent thread.
- `app_task`: a user-owned Codex app task runs independently of the parent task.

### Workspace mode

```text
shared_checkout | parent_managed_worktree | app_managed_worktree
```

- `shared_checkout`: one checkout; all writes are serialized.
- `parent_managed_worktree`: the parent creates and records a Git worktree and branch when separately authorized.
- `app_managed_worktree`: the Codex app owns worktree creation and retention; the harness records, but does not control, that lifecycle.

### Completion channel

```text
agent_result | thread_poll | report_file | user_relay
```

- `agent_result`: the direct or subagent result returns to the parent execution flow.
- `thread_poll`: the parent can inspect a separately running task through an available thread tool.
- `report_file`: a durable report is the handoff channel; the parent still verifies it against Git/runtime facts.
- `user_relay`: the user reports completion when no programmatic channel exists.

Do not promise an automatic callback from a generic skill. True event-driven task completion requires an App Server client that subscribes to completion/status notifications. Without that integration, use an available poll/result/report channel or fall back to sequential execution.

### Nested subagents inside app tasks

An app task is a root task in its own app-managed worktree and may coordinate direct child subagents when the current runtime exposes multi-agent tools. Record the task-local policy under `runtime_capabilities.nested_subagents`:

```json
{
  "available": true,
  "max_depth": 1,
  "max_children_per_worker": 3,
  "allowed_roles": ["explorer", "researcher", "reviewer", "tester"],
  "write_policy": "read_only",
  "completion_channel": "agent_result"
}
```

`available` is an observed capability, not authorization. Outer app-task selection and creation does not require or preauthorize `spawn_subagents`. In RUN v10, `nested_subagent_policy` is optional: an omitted policy or `enabled: false` means no nested launch. Only after the parent allocates the app-task worker and observes its child-tool/result capability may it enable the policy, and then `spawn_subagents` must carry the exact `worker:<id>` target; a run-wide `*` target is not valid for a v10 nested launch. The harness caps the task-local shape at direct children only and three children per app task even if Codex is configured for more.

When capability cannot be proven before an app task exists, omit the nested policy and launch or continue the outer task without nested children or production edits. After the worker is allocated, ask it to report whether multi-agent tools/direct results are present, record that observation in RUN, then assign an explicit enabled or disabled policy; enabling also requires the exact `worker:<id>` grant described above. Do not preauthorize nested spawning at outer selection, and do not treat an omitted or disabled policy as permission to launch children.

The outer app task remains the mission lease holder and sole writer in its worktree. Children may inspect code, research documentation, analyze tests/logs, or review a proposed diff. They do not receive mission leases, alter the outer wave budget, edit PLAN/RUN, mutate repository or shared runtime state, create tasks/worktrees/branches/commits, integrate, push, or clean up. Their direct `agent_result` is internal to the app task; the outer parent still observes only the app task through `thread_poll`, `report_file`, or `user_relay`.

Each new app-task worker under a RUN that records `runtime_capabilities.nested_subagents` may carry an explicit `nested_subagent_policy` with `enabled`, `max_children`, allowed roles, read-only write policy, and `agent_result` completion. An omitted policy or `enabled: false` means no nested launch and routes the exact-head review to the parent. An enabled v10 policy is valid only after worker allocation with an exact `spawn_subagents` grant targeting that `worker:<id>`; it must include the `reviewer` role and its WORKER_RESULT records `subagent_activity`: completed child summaries, partial/failure evidence, or a concrete reason that eligible delegation was skipped or unavailable. An enabled integration candidate must include a completed exact-head PASS reviewer even when other child activity is partial; `unavailable` or reviewer-failed activity blocks the result. If the post-allocation capability handshake cannot supply that reviewer, record a disabled policy and route the exact-head review to the parent before integration. This report is worker-supplied evidence, not a substitute for parent-observed Git/runtime facts. Older schema-v2 records that omit both optional nested fields remain backward-compatible.

The optional-v10 policy, exact `worker:<id>` grant, mandatory reviewer role when enabled, retained `nested_review_evidence`, and pre-integration review transition gate are RUN-v10 rules. RUN v6 through v9 retain their legacy mandatory nested policy and matching wildcard-compatible spawn authorization and worker-result contract; do not apply that legacy wildcard to v10.

### Permission boundary

Record the permission state that applies before a worker is launched:

```json
{
  "selected_mode": "ask_for_approval",
  "profile_name": null,
  "approval_policy": "on-request",
  "filesystem_scope": "workspace",
  "network_scope": "filtered",
  "local_binding": "blocked",
  "worker_inheritance": "inherited",
  "status": "may_prompt"
}
```

| Field | Allowed values |
|---|---|
| `selected_mode` | `ask_for_approval`, `approve_for_me`, `full_access`, `named_profile`, or `unknown` (`profile_name` is required only for `named_profile`) |
| `approval_policy` | `untrusted`, `on-request`, `never`, `granular`, or `unknown` |
| `filesystem_scope` | `read_only`, `workspace`, `custom`, `unrestricted`, or `unknown` |
| `network_scope` | `disabled`, `filtered`, `open`, or `unknown` |
| `local_binding` | `allowed`, `blocked`, or `unknown` |
| `worker_inheritance` | `inherited`, `not_inherited`, or `unknown` |
| `status` | `ready`, `may_prompt`, `blocked`, or `unknown` |

`status: ready` means the current boundary already covers the concrete worker surfaces, including linked-worktree Git metadata, temp/cache paths, outbound destinations, local bindings, and sockets required by its verifiers. It does not authorize an action. `approve_for_me` may automate review but does not widen filesystem or network access. `full_access` means unrestricted filesystem/network access with approval policy `never`; use it only when the user intentionally selected that boundary. Permission changes do not retroactively update already-running app tasks, so re-observe the boundary when creating or restarting workers.

## Capability Gate

Before leasing or fanning out a mission, the parent must prove all applicable rows:

| Check | PASS condition |
|---|---|
| Runtime available | Chosen `worker_runtime` exists in this session and its authorization entry passes |
| Workspace available | Chosen `workspace_mode` can be created or observed without overwriting existing work |
| Write isolation | Every plan-backed write mission uses an eligible isolated worktree; `shared_checkout` is direct/read-only only and cannot satisfy `sequential_parent` |
| Completion observable | Chosen `completion_channel` can return a terminal result, blocker, or failure to the parent |
| Integration observable | Parent can obtain base SHA, worker head SHA, actual changed paths, and verifier evidence |
| Resource isolation | File scopes and every runtime resource have complete, supported claims |
| Lifecycle understood | Branch/ref durability and app-managed retention behavior are recorded |
| Permission boundary | Parent mode/profile and inheritance are observed; every required filesystem, Git metadata, temp/cache, network, local-binding, and socket surface is covered without an unresolved prompt |
| Runtime route | Provider and available drivers are observed; the deterministic selected driver matches the declared runtime/workspace/completion axes |
| Nested delegation bounded | Any enabled app-task child policy is covered by `spawn_subagents`, stays at depth one, uses at most three read-only children, and returns results to the app-task parent |

If any capability, isolation, permission, or completion row is unknown, do not fan out. Observe it first; if it remains unavailable, select the real `sequential_parent` route with `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result`, then apply the same verification gates. Parent-managed worktree creation is required for this route; if it is unavailable or unauthorized, block the route rather than writing in `shared_checkout`. Missing launch authorization is not an unknown capability: request the exact run-wide launch bundle once and pause rather than rewriting the runtime adapter or silently downgrading.

For plan-backed multi-mission execution, the configured write-worker maximum has no default numeric ceiling; per `SKILL.md`'s Default Runtime And Wave Policy the parent sets `max_parallel_workers` generously high and lets observed worker slots, isolation capacity, and the dependency-ready conflict-free frontier size do the real bounding. Deterministic mission selection is the default immediately after Plan Readiness and execution authorization; run validation and selection before any production task. The effective wave remains the minimum of that configured maximum, live worker slots, isolated workspaces, dependency-ready nonconflicting missions, and every capability and permission gate above.

## Serialized Same-Repository Host Handoff

Hosts may hand off a large plan-backed run only as a serialized, same-repository operation. The handoff is permitted only when `active_wave` is not `active` (close or supersede the wave first); it never transfers a live lease, hides a worker, or starts a second writer. Preserve the existing PLAN/RUN files, PLAN revision/digest, graph state, mission/task evidence, and exact integration/worktree head SHA. Do not invent a new schema field or a new identity from the handoff.

Host B must validate the preserved PLAN/RUN and exact SHA, then re-probe its own runtime, permission, isolation, and completion capabilities. Replace the old `runtime_adapter`/observed capability snapshot with Host B's fresh snapshot before selecting work or running the next read-only review; do not merge Host A's capability claims into Host B's. Host B uses the same graph and exact-head review gates and may proceed only from a clean, reconciled state.

If Host B's review returns `fix_required`, route the findings back to Host A's original mission/worktree for repair. Any new head invalidates the prior review and requires a fresh verifier and exact-head review before integration or another handoff. This is a serialized file/repository handoff, not an in-session bridge or automatic cross-host invocation. Cross-machine handoff remains unsupported until a future schema defines a portable workspace identity and evidence transport; do not claim that a shared repository path alone provides that bridge.

## Parent-Owned Wave State

The selector produces a pure proposal. Only the parent may accept it into `RUN.md` as `active_wave`. The accepted wave records at least:

```text
wave_id
status: idle | proposed | active | closed | superseded
plan_revision
plan_digest_sha256
batch_base_sha
selected_missions
deferred_missions and reason codes
```

RUN schema v10 also carries an append-only `closed_waves` list of
`{ wave_id, batch_base_sha }` pairs. Append a pair before closing or
superseding that wave; a proposed or active wave may not reuse a pair already
listed there. A `wave_closed` grant is valid only when its scope matches the
current pair and that pair is absent from `closed_waves`. Older RUN schemas do
not require this field and remain readable.

Each mission lease and worker record repeats the lease ID, plan revision/digest, and batch base so stale results can be rejected without inference. The run-level `runtime_adapter` records provider/driver routing. Worker records name runtime/workspace/completion axes, the selected runtime binding when graph-backed, task/thread identity when applicable, worktree path, branch/ref, optional nested-subagent policy, optional report path, phase, and observed head SHA.

Worker status, head SHA, integration result, and evidence are live RUN state. A wave stays `active` while its selected workers run — worker-result validation accepts a result only against the active wave — and the selector dispatches no node while a wave is active. The wave therefore closes as soon as every selected mission's worker result is validated, before any review node can dispatch. The parent then re-runs selection to dispatch the review nodes; review PASS, serial integration, and batch gates all follow the wave close, never precede it. Any worker failure, integration failure, dependency change, or plan revision also closes the wave and forces a recompute from current state. A plan revision supersedes every active old-revision lease: quiesce those workers at safe boundaries and issue new leases only after validating their preserved heads against the new plan. Never carry forward an old result, conflict, or readiness assumption.
