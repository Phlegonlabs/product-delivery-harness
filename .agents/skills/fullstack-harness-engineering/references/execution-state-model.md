# Execution State Model

Use this reference for long, multi-mission, refined-task, or parallel execution. It defines which artifact owns each kind of state and prevents a worker result from being mistaken for an integrated result.

## Three Authorities

The harness has three distinct authorities. Do not merge them into one table or infer one from another.

| Authority | Owns | Does not own |
|---|---|---|
| `PLAN.md` | Static declarations for one plan revision: requirements, traces, mission/task definitions, dependency DAGs, scopes, resource claims, verifier commands, priorities, and merge ranks | Worker leases, live phase, current Git head, verifier results, authorization decisions, or selected waves |
| `RUN.md` | Mutable coordination state: readiness, explicit authorization ledger, chosen runtime capabilities, mission/task phases, leases, workers, wave proposals accepted by the parent, integration outcomes, PR landing state, blockers, and evidence pointers | Repository truth, process truth, or a new plan definition |
| Observed Git/runtime facts | The current checkout, refs, commit ancestry, diffs, worktrees, dirty state, active worker slots, process availability, and completion signals | User authorization or declarative scope |

`PLAN.md` and `RUN.md` each contain one canonical fenced JSON manifest. The exact level-two headings are `## Harness Plan Manifest` and `## Harness Run State`; the first non-empty content after each heading is its single fenced `json` block. Markdown tables are non-canonical human views. Tools parse the JSON manifests only; they must not recover state from prose or tables.

The parent is the only writer of `PLAN.md` and `RUN.md`. Workers return reports and evidence. The parent verifies those reports against observed facts before changing canonical state.

Compact RUN-only work is a deliberately sequential exception: its RUN plan identity fields are `null`, it uses `parent` + `shared_checkout` with one writer, and it makes no validated scheduling claim. The parent may set compact `plan_readiness` to `ready` after the applicable human readiness checks pass, then set `status` to `running` only with explicit execution authorization. Before delegation, execution-time task decomposition, worktree use, or parallel selection, create a canonical PLAN, populate the RUN plan identity/digest, and pass validation.

Use exact RUN lifecycle values:

```text
status: draft | ready | running | blocked | complete
plan_readiness: draft | ready | blocked
```

`plan_readiness: ready` is the machine gate. Human verification tables may display `PASS`, but selectors never substitute a table cell for canonical readiness.

## Plan Revisions And Snapshots

Every plan manifest has a stable `plan_id`, a positive integer `revision`, and a semantic SHA-256 digest of the `harness_plan` object. Before encoding, the shipped tools recursively canonicalize dictionaries; sort object lists with `id` by ID, resource lists by `(key, access)`, and scalar set-like lists lexically; and preserve `argv` order because command argument order is semantic. Canonical bytes are the UTF-8 encoding of `json.dumps(normalized_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Reordering sources, missions, tasks, claims, or other set-like fields therefore does not change the digest. Any semantic change to mission/task definitions, dependencies, scopes, resources, or verifiers creates a new digest and requires an incremented revision.

Verifier declarations are data, not shell prose. Each verifier records at least `id`, repository-relative `cwd`, argument-vector `argv`, and a deterministic `pass_signal`. This keeps validation independent of shell quoting and makes worker and integration gates auditable.

Derived artifacts must bind all three values:

```text
plan_id
plan_revision
plan_digest_sha256
```

A selected wave also binds a committed `batch_base_sha`. A proposal becomes stale when its plan revision, plan digest, or base SHA no longer matches current observed facts. Recompute it; do not edit the old result into apparent validity.

Observed facts are read live before every mutating action. `RUN.md` may record a timestamped snapshot under `observed` for auditability, but the snapshot never replaces a fresh check.

The minimum RUN snapshot shape is:

```json
{
  "observed": {
    "captured_at": null,
    "git": {
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
| `worker_passed -> integrating` | Parent rechecks ancestry, actual diff scope, forbidden files, head stability, and integration authorization |
| `integrating -> integrated` | Changes are on the integration branch, integration verifier passed, and `integrated_sha` is recorded |

`worker_passed` is not completion for dependency purposes. It means only that the worker-level gate passed in its workspace. A dependent mission becomes ready only when every dependency is `integrated`, its integration gate is `PASS`, and observed Git ancestry confirms its `integrated_sha` is an ancestor of the current integration head.

`worker_failed` preserves the worker result and evidence. `integration_failed` preserves the worker-passed state plus the failed integration attempt. Neither unlocks downstream dependencies. Retrying creates a new attempt or lease; it does not overwrite the failed evidence.

## Canonical Task Phases

Tasks are executed sequentially inside one mission worker. Use the same success distinction at task scale:

```text
queued -> ready -> running -> worker_passed -> mission_recorded
blocked | worker_failed | superseded
```

`worker_passed -> mission_recorded` occurs when the parent confirms the passing task's commit/change is reachable from the reported mission head and represented by its `task_results` entry in the accepted worker result/report. The parent may record both observations in one serialized RUN update, but it must preserve the evidence distinction. A blocked/failed mission result names `current_task_id` and preserves earlier task results. `mission_recorded` does not make the mission `integrated`. Refined parent tasks use `superseded`; their replacement tasks carry the executable work.

## Authorization Action Ledger

Authorization is action-specific. Overall `execution_authorized` also has siblings `execution_authorization_source` and `execution_authorization_scope`; when true, both must match the run, mission, and expiry boundary. Every action entry defaults to `authorized: false` and records an explicit user source before it can become true. A goal, plan, template, skill selection, worker report, or assistant assumption cannot authorize itself.

The exact schema-v3 ledger has 16 actions. Schema v2 remains readable with its original 13 entries, but new RUN files use v3:

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

Each `authorizations` entry has this minimum shape:

```json
{
  "authorized": false,
  "source": null
}
```

When `authorized` is true, add a required `scope` object with `run_id`, `mission_ids`, and exact `targets`, plus `expires_when`. Targets use action-specific prefixes: `worker:`, `task:`, `worktree:`, `branch:`, `remote:`, `pr:`, `repository:`, or `environment:`. `expires_when` is `wave_closed`, `run_complete`, or `explicit_revocation` and is evaluated against current RUN state. Use `"*"` only for a dimension the user explicitly authorized run-wide. A selector/coordinator treats missing, expired, or nonmatching scope as unauthorized; authorization is never a global boolean inferred for every mission or target.

`wave_closed` is one-use authorization for the currently recorded wave. When that wave becomes `closed` or `superseded`, set every matching action entry back to `{ "authorized": false, "source": null }` and clear overall execution authorization when it used the same boundary before replacing `active_wave`. Never copy or revive a wave-scoped grant for a later wave; a new wave needs a newly recorded explicit source.

`source` identifies the user statement or durable approval record. Narrow authorization remains narrow:

- Static conflict and parallel-eligibility analysis performed by the parent does not require implementation, worktree, branch, commit, or integration authorization. A launch-bound ready frontier and selected wave do require execution plus all launch-path authorizations. Delegating even read-only analysis still requires `spawn_subagents` or `create_user_owned_tasks`, according to the chosen worker primitive.
- `spawn_subagents` does not authorize user-owned app tasks.
- Worktree creation does not authorize branch creation, commits, integration, or cleanup.
- Local integration does not authorize push, PR creation, repository configuration, review management, PR merge, deploy, branch deletion, or worktree removal.
- PR creation does not authorize marking a PR ready, requesting review, resolving threads, or merging it. Repository rules and Codex review settings use `configure_repository`; PR review-state mutations use `manage_pr_review`; merge or auto-merge uses `merge_pr`.
- Platform-managed retention is not a harness cleanup action and may still apply to app-managed worktrees.

Before each action, check its entry again and compare it with observed state. A previously authorized action can still be unsafe because the target changed or the plan became stale.

## Pull Request Landing State

Schema v3 requires a `landing` object. `mode` is `local_only` or `pull_request`; shared repositories default to `pull_request`. The parent records the remote, final head branch, base branch, pushed head, PR identity/state, CI state, review state, finding/thread counts, and merge state. Worker branches do not land independently unless the PLAN explicitly assigns them a separate landing target.

For a created PR, `pr_head_sha` equals `pushed_head_sha`. A check PASS is current only when `checks_head_sha == pr_head_sha == integration.integration_head_sha`; a review PASS is current only when `review_head_sha == pr_head_sha == integration.integration_head_sha`, `blocking_findings == 0`, and `unresolved_threads == 0`. Any push or local integration that changes either head makes prior CI or review evidence stale. Reset the affected status and request current-head review again.

`merge_status: ready` requires `pr_state: open`, `pr_head_sha == integration.integration_head_sha`, plus current-head PASS checks and review. A later local integration therefore invalidates readiness even before the next push. `merge_status: merged` preserves those same head/check/review gates and additionally requires `pr_state: merged` plus a recorded merged SHA. These are state facts, not authorization: `merge_pr` must still cover the exact PR before merge or auto-merge.

A PR closed without merge uses the exact terminal pair `pr_state: closed` and `merge_status: closed_unmerged`, with no `merged_sha`. No state other than `merged` may record `merged_sha`. This prevents review or merge automation from treating the closed PR as merely not ready.

## Runtime Capability Axes

Represent orchestration with three independent axes. Do not encode them as a single mode string.

RUN records them together under `runtime_capabilities`, along with `max_parallel_workers`, a `platform_lifecycle` object, and optional backward-compatible `nested_subagents` and `permission_boundary` objects. `platform_lifecycle` has `owner` (`parent` or `app`), `automatic_retention_cleanup_possible`, and `durable_branch_required_before_unique_work`.

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

`available` is an observed capability, not authorization. A worker may enable this policy only when `spawn_subagents` covers its mission and exact `worker:<id>` target (or an explicitly run-wide `*` target). The harness caps the task-local shape at direct children only and three children per app task even if Codex is configured for more.

When capability cannot be proven before an app task exists, use a two-stage handshake: launch or continue the task without production edits, ask it to report whether multi-agent tools/direct results are present, record that observation in RUN, then send the explicit enabled or disabled worker policy. Do not leave a known-capable task implicitly disabled merely because capability was unknown at initial allocation.

The outer app task remains the mission lease holder and sole writer in its worktree. Children may inspect code, research documentation, analyze tests/logs, or review a proposed diff. They do not receive mission leases, alter the outer wave budget, edit PLAN/RUN, mutate repository or shared runtime state, create tasks/worktrees/branches/commits, integrate, land, deploy, or clean up. Their direct `agent_result` is internal to the app task; the outer parent still observes only the app task through `thread_poll`, `report_file`, or `user_relay`.

Each new app-task worker under a RUN that records `runtime_capabilities.nested_subagents` must carry an explicit `nested_subagent_policy` with `enabled`, `max_children`, allowed roles, read-only write policy, and `agent_result` completion. Its WORKER_RESULT records `subagent_activity`: completed child summaries, partial/failure evidence, or a concrete reason that eligible delegation was skipped or unavailable. This report is worker-supplied evidence, not a substitute for parent-observed Git/runtime facts. Older schema-v2 records that omit both optional nested fields remain backward-compatible.

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

Use `selected_mode` values `ask_for_approval`, `approve_for_me`, `full_access`, `named_profile`, or `unknown`. `profile_name` is required only for `named_profile`. Use approval values `untrusted`, `on-request`, `never`, `granular`, or `unknown`; filesystem values `read_only`, `workspace`, `custom`, `unrestricted`, or `unknown`; network values `disabled`, `filtered`, `open`, or `unknown`; local-binding values `allowed`, `blocked`, or `unknown`; inheritance values `inherited`, `not_inherited`, or `unknown`; and status values `ready`, `may_prompt`, `blocked`, or `unknown`.

`status: ready` means the current boundary already covers the concrete worker surfaces, including linked-worktree Git metadata, temp/cache paths, outbound destinations, local bindings, and sockets required by its verifiers. It does not authorize an action. `approve_for_me` may automate review but does not widen filesystem or network access. `full_access` means unrestricted filesystem/network access with approval policy `never`; use it only when the user intentionally selected that boundary. Permission changes do not retroactively update already-running app tasks, so re-observe the boundary when creating or restarting workers.

## Capability Gate

Before leasing or fanning out a mission, the parent must prove all applicable rows:

| Check | PASS condition |
|---|---|
| Runtime available | Chosen `worker_runtime` exists in this session and its authorization entry passes |
| Workspace available | Chosen `workspace_mode` can be created or observed without overwriting existing work |
| Write isolation | More than one write mission uses separate eligible worktrees; `shared_checkout` has a write budget of one |
| Completion observable | Chosen `completion_channel` can return a terminal result, blocker, or failure to the parent |
| Integration observable | Parent can obtain base SHA, worker head SHA, actual changed paths, and verifier evidence |
| Resource isolation | File scopes and every runtime resource have complete, supported claims |
| Lifecycle understood | Branch/ref durability and app-managed retention behavior are recorded |
| Permission boundary | Parent mode/profile and inheritance are observed; every required filesystem, Git metadata, temp/cache, network, local-binding, and socket surface is covered without an unresolved prompt |
| Nested delegation bounded | Any enabled app-task child policy is covered by `spawn_subagents`, stays at depth one, uses at most three read-only children, and returns results to the app-task parent |

If any row is unknown, do not fan out. Select a supported sequential combination, normally `parent` or `subagent` with `shared_checkout`, and apply the same verification gates.

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

Each mission lease and worker record repeats the lease ID, plan revision/digest, and batch base so stale results can be rejected without inference. Worker records also name runtime/workspace/completion axes, task/thread identity when applicable, worktree path, branch/ref, optional nested-subagent policy, optional report path, phase, and observed head SHA.

Worker status, head SHA, integration result, and evidence are live RUN state. After any worker failure, integration failure, dependency change, plan revision, or completed batch, close the wave and recompute from current state. A plan revision supersedes every active old-revision lease: quiesce those workers at safe boundaries and issue new leases only after validating their preserved heads against the new plan. Never carry forward an old result, conflict, or readiness assumption.
