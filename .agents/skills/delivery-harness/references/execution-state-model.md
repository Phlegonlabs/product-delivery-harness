# Execution State Model

Use this reference for long, multi-mission, refined-task, or parallel execution. It defines which artifact owns each kind of state and prevents a worker result from being mistaken for an integrated result.

## System Review And Route

Before any PLAN/RUN artifact, task-specific skill, runtime adapter/model selection, worker preflight, or worker launch, the parent performs one bounded, read-only `System Review And Route`. It reads the user request, repository instructions, current Git state, requested scope, and available upstream product/design inputs, then records a route decision outside managed artifacts:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
```

The stage is parent-only and cannot create or edit `PLAN.md`, `RUN.md`, `tasks.md`, evidence, branches, worktrees, or other managed state; it does not load a task skill, select a worker/model, invoke an external runtime, or spawn a worker. A small route remains direct and creates no PLAN/RUN. A large route creates the current PLAN schema v6 plus RUN schema v11 and only then enters graph readiness. The stage is not a graph node and must not be represented in `graph_state`.

## Sequential Parent Route

When no agent capability is available after routing, write missions in the large route may select `sequential_parent`: the PLAN mission remains `executor: runtime_worker`, while RUN records a parent-owned executor/worker binding solely for lease/state validation (`worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, `completion_channel: agent_result`). This binding is not a delegated or spawned worker and requires no `spawn_subagents`; the parent is the sole mission writer and executes one mission at a time. It cannot satisfy a fresh independent runtime-review node, which remains blocked until an eligible reviewer driver or allowed host exists. A parent-managed worktree is required; if it is unavailable or unauthorized, the route blocks rather than writing in `shared_checkout`.

## Three Authorities

The harness has three distinct authorities. Do not merge them into one table or infer one from another.

| Authority | Owns | Does not own |
|---|---|---|
| `PLAN.md` | Static declarations for one plan revision: requirements, traces, mission/task definitions, dependency DAGs, scopes, resource claims, verifier commands, provider/model policy, priorities, and merge ranks | Worker leases, live phase, current Git head, verifier results, authorization decisions, or selected waves |
| `RUN.md` | Mutable coordination state: readiness, explicit authorization ledger, chosen runtime capabilities, mission/task phases, leases, workers, wave proposals accepted by the parent, integration outcomes, batch/final-gate results, UI artifact metadata, landing state, blockers, and evidence pointers | Repository truth, process truth, or a new plan definition |
| Observed Git/runtime facts | The current checkout, refs, commit ancestry, diffs, worktrees, dirty state, active worker slots, process availability, and completion signals | User authorization or declarative scope |

`PLAN.md` and `RUN.md` each contain one canonical fenced JSON manifest. The exact level-two headings are `## Harness Plan Manifest` and `## Harness Run State`; the first non-empty content after each heading is its single fenced `json` block. Markdown tables — including the optional standalone `tasks.md` (`assets/templates/TASKS.template.md`), an on-demand regenerated mission/task listing view — are non-canonical human views. Tools parse the JSON manifests only; they must not recover state from prose or tables.

The parent is the only writer of `PLAN.md` and `RUN.md`. Workers return reports and evidence. The parent verifies those reports against observed facts before changing canonical state.

New managed work is never authored as compact RUN-only work. Legacy compact RUN-only manifests whose `plan` identity fields are `null` remain readable and validatable for migration and closeout compatibility, but they make no current scheduling claim and cannot authorize new managed execution or enter the PLAN-v6/RUN-v11 graph. When work continues, the parent creates a fresh PLAN schema v6 and RUN schema v11 pair after routing; it does not null the PLAN fields in the current runbook. “Sequential” for a current large run follows the Sequential Parent Route defined above; it does not null the PLAN fields in the current runbook. Require one exact-head read-only review before parent integration; the same sequential parent context cannot supply that independent review, so use a fresh eligible reviewer driver or serialize a same-repository host handoff. Then merge the passing head into the resolved integration branch and run its integration gate.

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
| PLAN-v6 graph run | Every node is succeeded, skipped, or superseded; every edge is terminal; no retained node blocker (a failed node must be routed or superseded before closeout) |
| RUN-v11 gates | Every PLAN batch and final gate has a PASS result bound to the integration head, and every required UI screenshot matrix entry is PASS; when a UI registry is supplied, the PLAN surface matrix also covers its exact responsive set, required states, and route trace/test bindings |
| Gate freshness | A changed integration head invalidates an earlier gate PASS immediately, in every RUN lifecycle state |

New runs are authored at RUN v11. The manifest validator still reads older RUN schemas, but graph selection and node-result validation require RUN v11. RUN v9 introduced the gate arrays; v10 adds PLAN-v6 binding, continuity, and append-only verifier history.

`plan_readiness: ready` is the machine gate. Human verification tables may display `PASS`, but selectors never substitute a table cell for canonical readiness.

New PLAN/RUN files are authored at the current schema (PLAN v6, RUN v11). Older files remain validatable as manifests but cannot drive graph selection or node-result validation.

## Generating And Validating State

Author PLAN by hand: its objective, sources and digests, traces, scopes, verifiers, graph, and acceptance rows are the real decisions.

Generate RUN with `scripts/new_run.py --plan <PLAN.md> --run-id <id> --branch <exact ref> --out <RUN.md>`. Everything a new RUN can derive from PLAN it derives: the mirrored graph state, seeded mission and task states, gate result ids, and the plan digest. Everything it cannot derive stays at its safe unset value — authorizations false, `observed` null, `batch_base_sha` unset, `plan_readiness: draft`. Generating a RUN grants nothing, and the command refuses to overwrite an existing file.

Record a returned graph-backed mission payload with one locked call: `scripts/harness_transition.py --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-worker-result --node-result <file> --worker-result <file> --verifier-result <file>`. Repeat the verifier-result flag as needed. The transition observes the bound worker worktree's live branch, head, dirty state, `base..head` diff, and ancestry; reloads and validates the current pair, node result, worker result, and retained verifier executions inside the RUN transaction; then rechecks the worker head and PLAN before replacing RUN. A non-passing mission uses the same command with its node result and no passing worker/verifier payload. When the parent cannot trust or accept the candidate itself, use guarded `reject-worker-result --node-id <id> --worker-id <id> --outcome <retryable_failure|blocked> --reason <text>`. `scripts/validate_result.py` remains the read-only preflight when no state update is requested.

## Plan Revisions And Snapshots

Every plan manifest has a stable `plan_id`, a positive integer `revision`, and a semantic SHA-256 digest of the `harness_plan` object. Before encoding, the shipped tools recursively canonicalize dictionaries; sort object lists with `id` by ID, resource lists by `(key, access)`, and scalar set-like lists lexically; and preserve `argv` order because command argument order is semantic. Canonical bytes are the UTF-8 encoding of `json.dumps(normalized_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Reordering sources, missions, tasks, claims, or other set-like fields therefore does not change the digest. Any semantic change to mission/task definitions, dependencies, scopes, resources, or verifiers creates a new digest and requires an incremented revision.

Verifier declarations are data, not shell prose. Each verifier records at least `id`, repository-relative `cwd`, argument-vector `argv`, and a deterministic `pass_signal`. This keeps validation independent of shell quoting and makes worker and integration gates auditable.

A worker-supplied hash is only a claim, even when it is 64 lowercase hexadecimal characters. The parent retains each `verifier_runtime.py` result, including verifier ID, immutable context, key document, exact head, status, exit result, and execution key. Worker-result validation recomputes the key from the retained key document and requires the reported verifier ID, status, and evidence key to match that parent-retained result exactly. Missing, forged, stale-context, wrong-head, or mismatched results fail closed.

When the CLI is given `--repo-root`, current PLAN-v6 local sources are resolved inside that root and checked against their frozen bytes; a supplied `source_revision` is read from that immutable Git revision. URLs are not fetched and need an immutable revision or a local frozen snapshot. For RUN-v11 UI evidence, the verifier reads the artifact blob from the recorded accepted Git commit/ref, decodes those bytes, and only then compares `artifact_sha256`; RUN-v9 retains working-tree compatibility.

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
| `worker_running -> worker_passed` | `record-worker-result` observed the bound worktree and revalidated its head/diff/ancestry, worker/node payload, and retained verifier evidence under the RUN lock |
| `worker_passed -> integrating` | Parent rechecks ancestry, actual diff scope, forbidden files, head stability, integration authorization, and a terminal `review_workers[]` PASS bound to the exact worktree head; current RUN-v11 workers never use task-local nested review evidence, while v6-v9 records retain their historical compatibility rule |
| `integrating -> integrated` | Changes are on the resolved integration branch, the integration verifier passed, and `integrated_sha` is recorded |

These phase transitions describe one run's lifecycle; when `run.integration.retention` is `"persistent"`, the integration branch itself survives across runs rather than being scoped to a single run.

`worker_passed` is not completion for dependency purposes. It means only that the worker-level gate passed in its workspace. A dependent mission becomes ready only when every dependency is `integrated`, its integration gate is `PASS`, and observed Git ancestry confirms its `integrated_sha` is an ancestor of the current integration head.

`worker_failed` preserves the terminal node evidence recorded by `record-worker-result`; a passing worker payload is required only for `worker_passed`. `integration_failed` preserves the worker-passed state plus the failed integration attempt. Neither unlocks downstream dependencies. Retrying creates a new attempt or lease; it does not overwrite the failed evidence.

## Canonical Task Phases

Tasks are executed sequentially inside one mission worker. Use the same success distinction at task scale:

```text
queued -> ready -> running -> worker_passed -> mission_recorded
blocked | worker_failed | superseded
```

`worker_passed -> mission_recorded` occurs when the parent confirms the passing task's commit/change is reachable from the reported mission head and represented by its `task_results` entry in the accepted worker result/report. The parent may record both observations in one serialized RUN update, but it must preserve the evidence distinction. A blocked/failed mission result names `current_task_id` and preserves earlier task results. `mission_recorded` does not make the mission `integrated`. Refined parent tasks use `superseded`; their replacement tasks carry the executable work.

## Resume Reconciliation Gate

A `running` RUN can be picked up by a different session than the one that last touched it — the same host resuming after an interruption, or a different agent entirely. Before that parent selects or launches any ready node, it must reconcile the observed working tree against canonical `task_states`/`mission_states`, not just trust the last recorded checkpoint. Start with `python .agents/skills/delivery-harness/scripts/inspect_harness_run.py --repo-root <target-root>` — it exits 1 when any mission needs reconciliation, and its summary shows the run lock and control state, so a second parent learns immediately whether another live session holds the run. Before dispatching work that consumes a project-bound skill slot, also verify that binding's pin with `scripts/check_skill_bindings.py`; a mismatch is a review moment, not a silent swap.

Read `observed.git.parent_dirty` and the actual diff live. If the checkout is dirty, map every changed path to the task(s) whose `write_scope` covers it. Any dirty content that falls inside a task still at `queued`, `ready`, or `running` — i.e. not yet `worker_passed` — is drift: real work exists that canonical state does not account for. This is exactly how an interrupted session leaves a large, unverified pile behind: implementation kept going across several tasks without the verify-then-commit checkpoint ever firing in between, so nothing downstream ever learned the work existed.

Drift blocks new work. The parent must resolve it before advancing to the next ready node, by one of:

- Running the covering task's own verifier against the current dirty state. If it passes, commit per `commit-convention.md` and record the task as `worker_passed` (then `mission_recorded` once integration-reachability is confirmed) so canonical state now matches reality.
- If the drift does not pass verification, is partial, or its origin is unclear, stop and ask the user how to proceed (finish and verify it, stash it, or discard it) rather than silently building further work on top of unverified, unrecorded state.

Never treat a dirty checkout as either "safe to ignore" or "safe to build on" without this reconciliation — both let the same gap compound on the next resume.

A resume snapshot is usable only when the parent checkout path, branch, head, and clean/dirty state are all known. Enumerate live linked worktrees before frontier selection and reconcile each one to the current parent, Git's primary checkout, or a recorded worker. The clean primary checkout may remain listed when the integration branch itself runs from a linked worktree. Reconcile every nonterminal worker to its exact worktree path, branch, observed head, and clean state. An unknown or dirty parent/worktree, any other unrecorded linked worktree, a missing worktree for a live write worker, or a branch/head mismatch blocks the whole frontier until the parent records or resolves it. A stale RUN snapshot is not a safe default.

Reconcile the current host and loaded Harness release through `runtime_capabilities.runtime_adapter.version_gate` as a separate observation. Follow `runtime-upgrades.md`. `unobserved`, `upgrade_required`, and `restart_required` defer runtime-worker dispatch. `compatible_old` may finish only the already-active wave and its streaming reviews; it defers the next wave. A runtime update never revives a lease. Preserve terminal exact-bound results, but create a new attempt and lease for unfinished work after restart and fresh capability probing.

Resume also rejects any mission worker or review worker still recorded as `leased` or `worker_running`. After a stopped review fan-out, use `harness_transition.py reconcile-interrupted-reviews` once with every affected review worker ID. The transition records each interrupted attempt as blocked, restores lineage counts from the append-only attempt log, resets the current review nodes, removes incoming edge traversals that have no current or retained source attempt, and persists `control.desired_state: paused`. It does not grant another review attempt or resume dispatch.

## Mid-Run Modification Recording

The drift rules above fire at resume; the same duty applies while the run is live. Un-checkpointed work of an existing task is drift and stays with that task under the rules above; review-driven repair likewise stays inside the mission it repairs, as a new attempt on the same work. Everything else that appears during the run — an extra fix, a follow-up edit, or a change the user reports mid-run — is new content, never folded into a mission that happens to be nearby.

Record each such modification as its own mission: open it through a plan revision before the edits continue (`contract-and-traceability.md`), give it its own tasks and verifier, and run it through the normal lease, worker, and integration phases. Then regenerate `docs/tasks.md` with `scripts/render_tasks_view.py`. The view groups one section per mission, newest mission first, so every extra modification appears as its own mission section — the newest work at the top, M1 at the bottom — with its own task rows.

A mid-run modification is not done when the edit lands; it is done when it is recorded in RUN and visible in the tasks view. `docs/tasks.md` ends the run listing every modification the run made — nothing stays only in the working tree or only in the conversation.

## Typed Graph State

PLAN v6 and RUN v11 carry the typed-graph contract: typed nodes, explicit dependency/route edges, and one `graph_state` object with the matching plan revision, one state per node, and one state per edge. The graph state is the routing authority; mission state remains the operational lease, Git, worker, and integration detail for mission nodes.

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

Run `select_ready_nodes.py` for PLAN v6 with RUN v11. Its strict current-pair entrypoint rejects other schema pairs before compatibility dispatch. It computes graph readiness before runtime binding, then applies the existing write-conflict and worker-budget rules to ready mission nodes. The derived selector-only `execution_route` is `managed_sequential` for fewer than two actually selected safe write missions and `parallel_graph` for two or more; `runtime_driver` remains a separate transport fact. See `graph-orchestration.md` for the complete routing contract.

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

The ordinary execution loop uses only the applicable local entries: `invoke_external_runtime`, the selected worker/worktree actions, `create_local_branches`, `create_local_commits`, and `integrate_locally`. An instruction such as "implement", "build", "fix", or "refactor" records its source under those covered local keys and never implies `push`. A separate explicit remote instruction such as "push" or "publish" must authorize `push` for exactly one resolved integration branch and the current integration head. The outer v10 `app_threads` app-task route excludes `spawn_subagents` because app-task workers never delegate. Parent-dispatched direct sibling workers and reviewers, including Dynamic Workflow agents, retain their top-level `spawn_subagents` requirement. RUN v6-v9 nested policies retain their legacy wildcard-compatible validation behavior but are not a template for new execution. All 12 ledger keys remain present; `archive_worker_tasks`, `remove_worktrees`, `delete_branches`, and any push outside the resolved branch remain independent gates.

For a large `sequential_parent` route, leave `spawn_subagents`, `create_user_owned_tasks`, and `create_app_managed_worktrees` unauthorized and unused. The route's parent-owned worktree/branch/commit/integration actions still require their own matching grants. The binding itself is defined once above.

The current v10 push guard requires explicit remote intent, one exact target equal to the resolved `integration.branch`, and `authorized_head_sha` equal to the current `integration.integration_head_sha`. Literal `main` remains a fail-safe refusal. When optional `observed.git.default_branch` is available, its resolved branch is refused too; when that identity is unknown, the current push fails closed while unrelated local actions remain usable. Legacy RUN validation keeps its historical behavior.

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
    "targets": ["branch:refs/heads/<exact-run-branch>"]
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

A run starts and normally ends in `local_only`: the verified local integration head is recorded without touching the remote. An explicit remote outcome may move it to `integration_push`; the verified integration head is then pushed to the run's own branch, and the run is complete at that push. `pushed_head_sha` must equal `integration.integration_head_sha` — a later local commit would otherwise leave the run claiming a head the remote never received — and the push needs the exact branch/head authorization above. Either way, every mission worktree still passes its exact-head pre-integration review.

Landing that branch on the default branch is the user's own step, done outside this harness. The harness opens no pull request, merges nothing, deploys nothing, and records none of it.

`integration.branch` is the only branch field in RUN. Every push target is built from it, so there is no head/base pair to keep in sync. The optional `observed.git.default_branch` fact is only a push safety observation; it is not required for local execution.

`continuity` records that the run branch survives the run — it is what the user reads and lands:

```text
status: planned | preserved | blocked
```

`planned` and `preserved` require a full local `refs/heads/` ref in `branch_ref`. `preserved` also requires `head_sha`. `blocked` requires a `reason`. Authorized execution requires `planned` or `preserved`; a `complete` run requires `preserved` with `head_sha` equal to the integration head.

## Runtime Capability Axes

Represent orchestration with three independent axes. Do not encode them as a single mode string.

RUN records them together under `runtime_capabilities`, along with `max_parallel_workers`, a `platform_lifecycle` object, and optional backward-compatible `nested_subagents`, `permission_boundary`, and `reviewer_tools` objects. Schema v10 requires `runtime_adapter`. `platform_lifecycle` has `owner` (`parent` or `app`), `automatic_retention_cleanup_possible`, and `durable_branch_required_before_unique_work`.

### Runtime adapter and routing

RUN v11 records observed host capabilities without replacing the three portable axes:

```json
{
  "runtime_adapter": {
    "provider": "claude_code",
    "available_drivers": ["dynamic_workflow", "subagents", "sequential_parent"],
    "detection_source": "observed"
  }
}
```

`provider` is `codex`, `claude_code`, `pi`, or `generic`. `detection_source` is `observed`, `explicit`, or `fallback`, and the three are not interchangeable: `observed` means the host was probed and the recorded capacity is real, `explicit` means the route was chosen on purpose, and `fallback` means the capability was never determined. A multi-mission plan may not run sequentially on `fallback` — the selector withholds the proposal with `capability_unprobed` until the parent probes or declares. How to probe differs per host and belongs to the adapter; whether it happened is checked here, the same way for all three. `available_drivers` contains only capabilities proven in the current surface and always includes `sequential_parent`. The selector applies a fixed route: Codex uses `app_threads`, then `subagents`, then `sequential_parent`; Claude Code uses `dynamic_workflow`, then `subagents`, then `sequential_parent`; Pi and generic use `subagents`, then `sequential_parent`.

RUN v11 adds an optional `runtime_adapter.capability_probe` that is valid only for an observed Codex adapter. A route that may select two writers must complete it before entering `ready` or `running`; a provably sequential route may omit the unrelated surfaces and records only the facts needed to prove its selected driver:

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

Every supplied probe entry has exactly `status` and `evidence`; status is `available`, `unavailable`, or `unobserved`, and evidence is non-empty. A parallel-capable ready/running Codex execution rejects a missing probe or any `unobserved` entry with `capability_snapshot_incomplete`. A sequential route may omit the probe when `sequential_parent` is selected, or provide only the selected driver's required available surfaces; it still cannot claim an app-thread or subagent driver without those facts. When all eight entries are supplied, all six `app_*` entries being available derives `app_threads`; both `direct_*` entries being available derives `subagents`; `sequential_parent` is always derived, and `available_drivers` must equal those derived drivers in Codex priority order. Historical/superseded RUN evidence remains readable, but a resumed parallel route re-probes before launch.

### Reviewer tool capabilities

PLAN review nodes may declare `required_tools`. The supported reviewer tool is currently `chrome_devtools`. Use it for web visual review and any frontend review whose evidence needs the live DOM, console, network, runtime JavaScript, accessibility tree, or rendered interaction. Source-only and backend reviews omit it.

RUN records the selected driver's observation separately from its orchestration capability:

```json
{
  "reviewer_tools": {
    "chrome_devtools": {
      "status": "available",
      "provider": "codex",
      "driver": "subagents",
      "surface": "raw_cdp",
      "probe_scope": "reviewer_session",
      "session_id": "reviewer-probe-01",
      "evidence": "Fresh reviewer attached to the active tab and Runtime.evaluate returned 2 for 1+1"
    }
  }
}
```

`status` is `available`, `unavailable`, or `unobserved`. `provider` must be the active host and an available entry's `driver` must be the selected runtime driver. `surface` is provider-specific: Codex uses `raw_cdp`, Claude Code uses `claude_in_chrome`, Pi uses `pi_chrome_devtools`, and an unobserved generic default uses `none`. An available entry requires `probe_scope: reviewer_session` and a non-empty fresh reviewer session ID. Parent-session access, configuration, a package listing, or a launch flag is supporting evidence only; none proves the child surface. The read-only probe child uses the same provider, driver, role, and extension inheritance as the planned reviewer, requires the matching launch authorization, and cannot submit a review verdict or update review state.

The selector defers a node with `reviewer_tool_unobserved:<tool>` until this probe is completed, or `reviewer_tool_unavailable:<tool>` when the probed child lacks it. The dispatch directive and bounded review packet carry the exact requirement and capability evidence. A required browser tool is not silently replaced by retained screenshots, Playwright in another process, or the parent's browser connection. Those remain valid separate evidence only when PLAN does not require reviewer-side Chrome DevTools.

PLAN v6 runtime-worker nodes may add `provider_options` for any provider in their `allowed_providers`. Each option uses the exact keys `model` and `reasoning_effort`. Model is null or a safe token matching `^[A-Za-z0-9][A-Za-z0-9._-]*$`. Reasoning effort is null or one of `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; selectable effort is supported for Codex, Claude Code, and Pi, while generic providers keep it null. Pi model remains null because the installed role owns primary-model and fallback selection; a non-null Pi effort changes only that run's thinking tier. The selector chooses the provider first, then attaches its options to one immutable runtime binding. A missing Codex option means the destination default; a missing Claude option means `sonnet`; a missing Pi option preserves the installed Pi role/model/effort configuration. The destination host still validates current model and effort support.

When the parent allocates a PLAN-v6 graph worker in RUN v11, copy a mission binding into `workers[].runtime_binding` or a read-only verifier binding into `review_workers[].runtime_binding`, with provider, driver, source, model, reasoning effort, and option source. A live mission or review attempt must match the current RUN runtime adapter's provider and selected driver. Before any managed review launch, `reserve-review-dispatch` must atomically persist the selected directive as a leased `review_workers[]` binding and a running graph attempt; only the matching receipt may later become a terminal review result. This makes a Pi-hosted attempt stay on Pi's role-aware `subagents` surface; it cannot be rebound to Claude Code or its `dynamic_workflow` driver. A review worker also records node/attempt identity, graph revision, review path, and exact reviewed SHA; it has no mission lease, writable worktree, branch, or commit authority. For Codex app tasks, pass non-null values through task creation. A Claude Code host passes each node's own model and non-null reasoning effort directly into that node's own `agent()` call inside the Workflow script; one wave may freely mix models and reasoning efforts across nodes since selection happens per spawned agent, not per wave. Pi keeps the installed role's resolved model and fallbacks, then applies a non-null binding effort through the per-run thinking suffix. Never silently replace a rejected model or effort; replan the affected node and increment the PLAN revision.

For a managed route that may fan out, capture this adapter before the first production edit or worker launch. A managed-sequential route proves only its selected driver and does not inventory unused parallel driver surfaces. Capability observation and action authorization are separate facts: record a usable driver even when its launch actions remain false. In particular, do not omit `app_threads` because `create_user_owned_tasks` or worktree authorization is missing. Record the capability, request the launch bundle once at Plan Readiness, and rerun selection after the answer.

Provider means the host session running the Harness, not every CLI installed on the machine. Observe current-session native tools first: Codex project/thread creation and polling for `app_threads`, Claude Code's `Workflow` tool and supported runtime for `dynamic_workflow`, and current-session child-agent tools for `subagents`. In Pi, the installed subagent workflow plus a terminal child result proves `subagents`; Pi agent files or package settings alone do not. Use `explicit` only when the host surface is opaque; otherwise use `generic` + `fallback`. A binary or plugin version may confirm feature compatibility after provider detection, but it does not select the provider or authorize a launch.

The chosen host driver must match the portable host axes. `app_threads` requires `app_task` + `app_managed_worktree` + `thread_poll`. `dynamic_workflow` requires `subagent` + `parent_managed_worktree` + `agent_result`. Direct `subagents` use `subagent` with a supported shared or parent-managed workspace and direct result/report channel. `sequential_parent` requires `parent` + `parent_managed_worktree` + `agent_result`; parent-managed worktree creation is mandatory and an unavailable or unauthorized worktree blocks the route. It never implies a delegated or spawned worker.

For a plan-backed graph, every mission node remains a write mission with PLAN `executor: runtime_worker` and must bind to `parent_managed_worktree` or `app_managed_worktree`. A `sequential_parent` mission runs one mission at a time under the binding defined above. The selector never rewrites that node into a deterministic parent action or a shared-checkout write. If the required parent-managed worktree and its worktree/branch/commit authorizations cannot be obtained, the route remains deferred or blocked rather than downgrading.

A current PLAN-v6 typed node's `allowed_providers` must include the current host's provider for the node to be selectable at all; there is no other-host adapter to fall back into. A node whose `allowed_providers` excludes the current host provider is deferred with `runtime_unavailable` and reported as needing a run hosted by the matching adapter.

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
- `thread_poll`: the stable schema label for a separately running task completion channel. Prefer a status subscription or cursor-based thread wait; use repeated inspection only as a recorded fallback.
- `report_file`: a durable report is the handoff channel; the parent still verifies it against Git/runtime facts.
- `user_relay`: the user reports completion when no programmatic channel exists.

Do not promise an automatic callback from a generic skill. True event-driven task completion requires an App Server client that subscribes to completion/status notifications. Without that integration, use an available poll/result/report channel or fall back to sequential execution.

### Flat parent-owned delegation

An app task is a root task in its own app-managed worktree and is the sole writer for one mission. It never coordinates child agents. The parent may still record the observed host capability under `runtime_capabilities.nested_subagents`, but capability does not change the RUN-v11 prohibition:

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

`available` is an observed capability, not authorization. Outer app-task selection and creation does not require or preauthorize `spawn_subagents`. RUN v11 accepts only an omitted `nested_subagent_policy` or one with `enabled: false`; enabled policy is invalid even when the host exposes child tools. The worker reports `subagent_activity.status: "not_applicable"`, no children, and a concrete flat-topology reason.

The parent owns every launch. It may dispatch independent read-only explorers before writing, one writer per mission/worktree, exact-head pre-integration reviewers, and fresh reviewers after serial integration. These are sibling PLAN nodes or parent-owned runtime attempts; none is a child of a worker or reviewer. RUN v6 through v9 retain their legacy nested-policy compatibility for validation only. Never copy that legacy shape into a new RUN.

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
| Flat worker result | Current RUN-v11 workers report `subagent_activity: not_applicable` with a concrete reason and empty `children`; legacy v6-v9 nested-policy evidence is compatibility-only |

If any capability, isolation, permission, or completion row is unknown, do not fan out. Observe it first; if it remains unavailable, select the real `sequential_parent` route defined above and apply the same verification gates. Missing launch authorization is not an unknown capability: request the exact run-wide launch bundle once and pause rather than rewriting the runtime adapter or silently downgrading.

For plan-backed multi-mission execution, the configured write-worker maximum has no default numeric ceiling; per `SKILL.md`'s Default Runtime And Wave Policy the parent sets `max_parallel_workers` generously high and lets observed worker slots, isolation capacity, and the dependency-ready conflict-free frontier size do the real bounding. Deterministic mission selection is the default immediately after Plan Readiness and execution authorization; run validation and selection before any production task. The effective wave remains the minimum of that configured maximum, live worker slots, isolated workspaces, dependency-ready nonconflicting missions, and every capability and permission gate above.

## Run Lock And Watchdog

Durable execution for one RUN has two machine guards; both are `harness_transition.py` subcommands.

- **Run lock**: before dispatching, the parent records `run.run_lock` (`session_id`, `acquired_at`, `heartbeat_at`) with `--session-id <id> acquire-run-lock` (the flag goes before the subcommand) and refreshes it with `--session-id <id> heartbeat-run-lock`; any successful transition by the holding session also refreshes the heartbeat. Every mutating transition refuses a lock held by another session — fresh, stale, or with an unparseable heartbeat — so two parents cannot dispatch against the same state; a stale or unparseable foreign lock is taken over only through the explicit `watchdog --reclaim` or `acquire-run-lock` path. The seven dispatch commands (`accept-wave`, `lease-worker`, `record-worker-result`, `reject-worker-result`, `reserve-review-dispatch`, `record-integration`, `close-wave`) additionally require the calling session to already hold the durable lock. Separately, every `harness_transition.py` process takes a short operating-system lock keyed to the RUN path across its exact-text PLAN/RUN load, validation, mutation, and atomic replace. This serializes two commands from the same session as well as competing lock acquisitions. Final PLAN and RUN comparisons refuse a non-cooperating writer that changed either file before replacement. Release the durable lock with `release-run-lock` when the session ends.
- **Watchdog**: `watchdog [--stale-after-minutes N]` reports read-only whether the lock is live or stale and lists `running` nodes that lost their parent heartbeat as interrupted-work candidates; `--reclaim` clears a stale lock so the reconcile transitions can run.

RUN coordination paths also protect `docs/goal/DECISIONS.md`, the parent-owned mid-run decision log: one row per owner decision (decision id, question, decision, source turn, date), created on the run's first owner decision and never written by a worker. A decision recorded there binds later waves exactly like a PLAN revision note; `review_lineages.owner_decisions` remains the review-attempt view of the same decisions.

## Serialized Same-Repository Host Handoff

Hosts may hand off a large plan-backed run only as a serialized, same-repository operation. Host A must close the active wave: `RUN.active_wave.status` is neither `active` nor `proposed`. The `active_wave` object remains part of RUN; an absent object is not proof that handoff is safe. The handoff never transfers a live lease, hides a worker, or starts a second writer. Preserve the canonical PLAN/RUN and graph state, mission/task evidence, and current exact head SHA. Do not invent a new schema field or identity from the handoff.

Host B must validate the preserved PLAN/RUN and exact SHA, then re-probe its own runtime version, loaded Harness version, permission, isolation, and completion capabilities. Replace the old `runtime_adapter`/observed capability snapshot with Host B's fresh snapshot before selecting work or running the next read-only review; do not merge Host A's capability claims into Host B's. Terminal worker and review records remain historical evidence with Host A's original bindings. Any live or newly allocated attempt must instead match Host B's provider and selected driver. Host B uses the same graph and exact-head review gates and may proceed only from a clean, reconciled state.

If Host B's review returns `fix_required`, route the findings back to Host A's original mission/worktree for repair. The old review is invalid; any new head invalidates the prior review and requires a fresh verifier and exact-head review before integration or another handoff. This is a serialized file/repository handoff, not an in-session bridge or automatic cross-host invocation. Cross-machine handoff is unsupported until a future schema defines a portable workspace identity and evidence transport; do not claim that a shared repository path alone provides that bridge.

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

RUN schema v11 also carries an append-only `closed_waves` list of
`{ wave_id, batch_base_sha }` pairs. Append a pair before closing or
superseding that wave; a proposed or active wave may not reuse a pair already
listed there. A `wave_closed` grant is valid only when its scope matches the
current pair and that pair is absent from `closed_waves`. Older RUN schemas do
not require this field and remain readable.

Each mission lease and worker record repeats the lease ID, plan revision/digest, and batch base so stale results can be rejected without inference. The run-level `runtime_adapter` records provider/driver routing. Worker records name runtime/workspace/completion axes, the selected runtime binding when graph-backed, task/thread identity when applicable, worktree path, branch/ref, optional nested-subagent policy, optional report path, phase, and observed head SHA.

Worker status, head SHA, integration result, and evidence are live RUN state. A wave stays `active` while its selected workers run, and `record-worker-result` accepts a result only against that active wave and the current bound attempt. During the active wave the selector blocks new writers and lifecycle mutations, but dispatches any dependency-ready read-only node: a pre-integration review for a selected mission already at `worker_passed`, an approval, or an external wait. Read-only nodes hold no lease, produce no commit, and move no head, so they cannot perturb a live writer. The parent records terminal worker results as they arrive and re-runs selection so review overlaps remaining workers. A mission whose exact-head pre-integration review has PASSed may integrate before the wave closes; integration stays strictly serial, so at most one mission is `integrating` at a time. The wave closes as soon as every selected mission's worker result is recorded. Batch gates always follow wave close. Any worker failure, integration failure, dependency change, or plan revision also closes the wave and forces a recompute from current state. A plan revision supersedes every active old-revision lease: quiesce those workers at safe boundaries and issue new leases only after validating their preserved heads against the new plan. Never carry forward an old result, conflict, or readiness assumption.

Closing a wave is a guarded transition, never a hand edit: `harness_transition.py ... close-wave --source <text>` refuses while any worker or review worker is still live (reconcile them first) and while any selected mission is still queued or running. A `worker_passed` mission may close with the wave — its worker result was recorded by `record-worker-result` and its integration may complete after the close — but only while overall execution authorization survives the boundary: a `run_complete`-bounded grant does, while a `wave_closed`-bounded grant dies at close and therefore requires those missions to integrate, fail, or reconcile first. The command appends the `{ wave_id, batch_base_sha }` tombstone, flips the wave to `closed`, resets every `wave_closed`-bounded action grant to `{ "authorized": false, "source": null }`, and clears overall execution authorization when it used the same boundary; `run_complete`-bounded grants survive as closeout evidence. The next `accept-wave` must name a fresh wave identity and base pair. The write-path guards are likewise enforced by the tooling: `accept-wave` requires a live clean product tree on the observed non-default integration branch and head; `lease-worker` binds the mission's own graph node and refuses conflicting concurrent missions; `record-worker-result` observes the bound worktree and atomically records accepted or validator-rejected terminal state; `reject-worker-result` records a parent-rejected current candidate; and `record-integration` proves the integrated head against live Git. Each command fails closed on stale state.
