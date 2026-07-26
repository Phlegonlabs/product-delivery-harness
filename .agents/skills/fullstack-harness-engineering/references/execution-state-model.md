# Execution State Model

Use this reference for long, multi-mission, refined-task, or parallel execution. It defines which artifact owns each kind of state and prevents a worker result from being mistaken for an integrated result.

## Three Authorities

The harness has three distinct authorities. Do not merge them into one table or infer one from another.

| Authority | Owns | Does not own |
|---|---|---|
| `PLAN.md` | Static declarations for one plan revision: requirements, traces, mission/task definitions, dependency DAGs, scopes, resource claims, verifier commands, provider/model policy, priorities, merge ranks, and release targets | Worker leases, live phase, current Git head, verifier results, authorization decisions, deployments, or selected waves |
| `RUN.md` | Mutable coordination state: readiness, explicit authorization ledger, chosen runtime capabilities, mission/task phases, leases, workers, wave proposals accepted by the parent, integration outcomes, batch/final-gate results, UI artifact metadata, PR landing and deployment state, blockers, and evidence pointers | Repository truth, process truth, or a new plan definition |
| Observed Git/runtime facts | The current checkout, refs, commit ancestry, diffs, worktrees, dirty state, active worker slots, process availability, and completion signals | User authorization or declarative scope |

`PLAN.md` and `RUN.md` each contain one canonical fenced JSON manifest. The exact level-two headings are `## Harness Plan Manifest` and `## Harness Run State`; the first non-empty content after each heading is its single fenced `json` block. Markdown tables — including the optional standalone `tasks.md` (`assets/templates/TASKS.template.md`), a regenerated mission/task listing view — are non-canonical human views. Tools parse the JSON manifests only; they must not recover state from prose or tables.

The parent is the only writer of `PLAN.md` and `RUN.md`. Workers return reports and evidence. The parent verifies those reports against observed facts before changing canonical state.

Compact RUN-only work is a deliberately sequential exception: its RUN plan identity fields are `null` and it makes no validated scheduling claim. "Sequential" describes the mission cadence, not the workspace: default it to `subagent` + `parent_managed_worktree`, one mission worktree at a time from the target repository's current `development` SHA. Require one exact-head read-only review before parent integration, then merge the passing head into persistent `development` and run its integration gate. Use `parent` + `shared_checkout` only when worktree creation itself is unavailable or unauthorized. The parent may set compact `plan_readiness` to `ready` after the applicable human readiness checks pass, then set `status` to `running` only with explicit execution authorization.

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
| Pull-request mode | A merged landing preserves current-head checks and review, and `merge_pr` authorization covers every mission plus the exact `pr:<full-PR-URL>` target |
| PLAN-v5 graph run | Every node is succeeded, skipped, or superseded; every edge is terminal; no retained node blocker (a failed node must be routed or superseded before closeout) |
| RUN-v10 gates | Every PLAN batch and final gate has a PASS result bound to the integration head, and every required UI screenshot matrix entry is PASS; when a UI registry is supplied, the PLAN surface matrix also covers its exact responsive set, required states, and route trace/test bindings |
| Gate freshness | A changed integration head invalidates an earlier gate PASS immediately, in every RUN lifecycle state |

Older RUN files remain readable under their recorded schema. RUN v9 introduced the gate arrays; current RUN v10 adds PLAN-v5 binding, provider-neutral targets, continuity, and append-only verifier history.

`plan_readiness: ready` is the machine gate. Human verification tables may display `PASS`, but selectors never substitute a table cell for canonical readiness.

## Schema Upgrade Maintenance

New PLAN/RUN files are authored at the current schema (PLAN v5, RUN v10); older version numbers exist only so the harness can keep reading a file some earlier run instantiated. When the parent encounters an existing `PLAN.md` or `RUN.md` whose `schema_version` is below the current default, it should proactively upgrade it with `scripts/upgrade_harness_schema.py` rather than leave the file on an old schema indefinitely. This is ordinary file maintenance already covered by the parent's sole-writer authority over `PLAN.md`/`RUN.md`: an in-place, reversible, local rewrite of its own canonical files that touches no Git ref, remote, PR, deployment, or other external system, so it needs no new action-ledger entry.

The upgrade adds only the keys each version introduces, always with neutral "nothing has happened yet" values: `false` for every authorization, `null` for unknown SHAs, revisions, and paths, `not_started`/`planned`/`queued`/`dormant` for status enums, and empty collections. It must never fabricate an authorization, a passed gate, a frozen source provenance, or any evidence; where a required field cannot be established without inventing content (for example a source `content_sha256`/`source_revision` whose content is not a readable file under the repository root), the tool aborts and writes nothing rather than guess. Reaching current RUN v10 requires the paired PLAN to be schema v5, so the same operation upgrades the PLAN first. Older supported PLAN-v4/RUN-v8-or-v9 pairs retain their historical contract. The result must pass the same validators as a from-scratch file before it is written. After an upgrade, the parent reports exactly which fields were added at each step and treats the file as canonical only once it has confirmed those additions.

## Plan Revisions And Snapshots

Every plan manifest has a stable `plan_id`, a positive integer `revision`, and a semantic SHA-256 digest of the `harness_plan` object. Before encoding, the shipped tools recursively canonicalize dictionaries; sort object lists with `id` by ID, resource lists by `(key, access)`, and scalar set-like lists lexically; and preserve `argv` order because command argument order is semantic. Canonical bytes are the UTF-8 encoding of `json.dumps(normalized_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Reordering sources, missions, tasks, release targets, claims, or other set-like fields therefore does not change the digest. Any semantic change to mission/task definitions, dependencies, scopes, resources, verifiers, or the release contract creates a new digest and requires an incremented revision.

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
| `worker_passed -> integrating` | Parent rechecks ancestry, actual diff scope, forbidden files, head stability, integration authorization, and at least one read-only review PASS bound to the exact worktree head |
| `integrating -> integrated` | Changes are on `development`, the integration verifier passed, and `integrated_sha` is recorded |

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

PLAN schema v4 adds typed nodes and explicit dependency/route edges. RUN schema v8 and v9 add one `graph_state` object with the matching plan revision, one state per node, and one state per edge. The graph state is the routing authority; mission state remains the operational lease, Git, worker, and integration detail for mission nodes.

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

Run `select_ready_nodes.py` for v4/v8 or v4/v9. It computes graph readiness before runtime binding, then applies the existing write-conflict and worker-budget rules to ready mission nodes. See `graph-orchestration.md` for the complete routing contract.

## Authorization Action Ledger

Authorization is action-specific. Overall `execution_authorized` also has siblings `execution_authorization_source` and `execution_authorization_scope`; when true, both must match the run, mission, and expiry boundary. Every action entry defaults to `authorized: false` and records an explicit user source before it can become true. A goal, plan, template, skill selection, worker report, or assistant assumption cannot authorize itself.

The schema-v8-and-v9 ledger has 17 actions. Schema v2 remains readable with its original 13 entries; schemas v3 through v7 retain their 16-action ledgers and later landing/runtime/release fields. New graph RUN files use v9:

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

`invoke_external_runtime` is required when the Harness parent starts a different provider process or service. Its target is `runtime:<provider>`. It does not replace `spawn_subagents`, worktree, branch, commit, integration, or lifecycle authorization.

Seven of these entries — `invoke_external_runtime`, `spawn_subagents`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally` — are local and reversible. Per `SKILL.md`'s Execution Authorization Gate, one execution-intent instruction covers all seven together in a single authorization request or checkpoint, recording its `source` under each entry, while the externally-visible or hard-to-reverse entries (`push`, `create_pr`, `manage_pr_review`, `merge_pr`, `deploy`, `configure_repository`, `remove_worktrees`, `delete_branches`) stay independent gates that each need their own authorization moment. Each of the seven still records its own `source`; grouping them only avoids manufacturing separate confirmation pauses — it does not merge or remove any ledger entry.

Each `authorizations` entry has this minimum shape:

```json
{
  "authorized": false,
  "source": null
}
```

When `authorized` is true, add a required `scope` object with `run_id`, `mission_ids`, and exact `targets`, plus `expires_when`. Targets use action-specific prefixes: `worker:`, `task:`, `worktree:`, `branch:`, `remote:`, `pr:`, `repository:`, `environment:`, or `runtime:`. Schemas v6 through v9 also accept `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` only for `manage_pr_review` and `merge_pr` before the PR exists. `expires_when` is `wave_closed`, `run_complete`, or `explicit_revocation` and is evaluated against current RUN state. Use `"*"` only for a dimension the user explicitly authorized run-wide, not as a placeholder for an unborn PR. A selector/coordinator treats missing, expired, or nonmatching scope as unauthorized; authorization is never a global boolean inferred for every mission or target.

`wave_closed` is one-use authorization for the currently recorded wave. When that wave becomes `closed` or `superseded`, set every matching action entry back to `{ "authorized": false, "source": null }` and clear overall execution authorization when it used the same boundary before replacing `active_wave`. Never copy or revive a wave-scoped grant for a later wave; a new wave needs a newly recorded explicit source.

A `run_complete`-bounded authorization (merge, deployment, or cleanup) stays valid evidence at closeout even after its boundary expires — do not erase the record of what was authorized and done just because the run finished. This applies uniformly to PR merge/auto-merge, Cloudflare deployment, and post-merge cleanup below; those sections do not repeat the rule.

`source` identifies the user statement or durable approval record. Narrow authorization remains narrow:

- Static conflict and parallel-eligibility analysis performed by the parent does not require implementation, worktree, branch, commit, or integration authorization. A launch-bound ready frontier and selected wave do require execution plus all launch-path authorizations. Delegating even read-only analysis still requires `spawn_subagents` or `create_user_owned_tasks`, according to the chosen worker primitive.
- `spawn_subagents` does not authorize user-owned app tasks.
- Worktree creation does not authorize branch creation, commits, integration, or cleanup.
- Local integration does not authorize push, PR creation, repository configuration, review management, PR merge, deploy, branch deletion, or worktree removal.
- PR creation does not authorize marking a PR ready, requesting review, resolving threads, or merging it. Repository rules and Codex review settings use `configure_repository`; PR review-state mutations use `manage_pr_review`; merge or auto-merge uses `merge_pr`.
- Platform-managed retention is not a harness cleanup action and may still apply to app-managed worktrees.

Before each action, check its entry again and compare it with observed state. A previously authorized action can still be unsafe because the target changed or the plan became stale.

## Pull Request Landing State

Schemas v3 through v10 require a `landing` object. Ordinary implementation, PRD/PLD, UI, branch, commit, or local integration work defaults to `local_only` on persistent `development`. Local-only mode cannot record a pushed head or promotion PR and does not wait for GitHub CI or review, but every mission worktree still passes its exact-head pre-integration review. Use `pull_request` for `development -> production` only after the user separately reviews the accumulated development result and gives final approval to start promotion. New RUN-v10 files name `development` as `integration.branch` and `landing.head_branch`, and `production` as `landing.base_branch`; older schemas retain their recorded branch names.

Do not put a future production promotion into the ordinary mission run's early authorization bundle. After final user approval starts promotion, request every missing exact landing action for `development -> production`; bind review and merge to `future-pr:<owner>/<repo>:base=production:head=development` until the PR exists. After creation, verify those branch fields, append the exact `pr:<full-PR-URL>` target, and run the authorized CI/review/merge path continuously. Earlier implementation or local-integration authorization never supplies this late approval.

For a created PR, `pr_head_sha` equals `pushed_head_sha`. A check PASS is current only when `checks_head_sha == pr_head_sha == integration.integration_head_sha`; a review PASS is current only when `review_head_sha == pr_head_sha == integration.integration_head_sha`, `blocking_findings == 0`, and `unresolved_threads == 0`. CI and review are independent sibling gates and should start or be observed concurrently as soon as the final PR head and authorization allow; neither gate needs to wait for the other. Any push or local integration that changes either head makes both prior CI and review evidence stale. Reset both affected statuses and start the current-head gates again.

`merge_status: ready` requires `pr_state: open`, `pr_head_sha == integration.integration_head_sha`, plus current-head PASS checks and review. A later local integration therefore invalidates readiness even before the next push. `merge_status: merged` preserves those same head/check/review gates and additionally requires `pr_state: merged` plus a recorded merged SHA. These are state facts, not authorization: `merge_pr` must still cover the exact PR before merge or auto-merge.

In schemas v4 through v9, `auto_merge_requested: true` records that GitHub auto-merge was successfully enabled for the exact `auto_merge_head_sha`. At request time it is valid only when `merge_status` is `ready`, the mode is `pull_request`, `auto_merge_head_sha == pr_head_sha == integration.integration_head_sha`, and an unexpired `merge_pr` authorization covers every run mission plus the exact `pr:<full-PR-URL>` target (or an explicitly run-wide `*`). A schema-v6-through-v9 authorization that began with `future-pr:` must retain that binding, and the exact PR must match its repository, base, and head. Enable it only after current-head checks and the configured repository review pass and all blocking findings and unresolved threads are zero. Use an exact-head guard such as `gh pr merge --auto --squash --match-head-commit <sha>`. A new push, local integration, canceled request, or changed head resets `auto_merge_requested` to false and `auto_merge_head_sha` to null until fresh gates pass. Repository-level auto-merge configuration uses `configure_repository`; enabling it on a PR uses `merge_pr`.

## Cloudflare Deployment State

Current PLAN schema v5 uses provider-neutral `release.targets`; Cloudflare identity is not encoded as extra target keys. Each target has the exact v5 field set and declares source, stage, artifact/channel/data mode, trigger, migration classification, commands, prerequisites, and smoke verifiers. A null migration classification is unresolved and blocks target execution. Worker names, Wrangler config/environment, isolated binding IDs, account identity, and URLs live in project deployment documentation, prerequisites, and retained evidence. Older PLAN v3/v4 provider-shaped release contracts remain readable under their historical schema.

Current RUN schema v10 uses `targets` keyed exactly by PLAN target IDs. Each target retains exact source and authorized-head SHAs, artifact/build/version/signing proof, channel/promotion/availability proof, migration and verification status, destructive-migration confirmation when applicable, and hashed evidence references. Older RUN v7-v9 `deployments` objects remain readable but are not the current authoring shape.

Development PASS binds the target's declared `pr_head` or `integration_head` source to the deployed artifact, requires migration `PASS` or `not_required`, deployed-environment verification PASS, retained evidence, and exact `deploy` authorization for `release:<target-id>`. A manual remote workflow additionally requires `trigger_remote_ci` for `workflow:<identity>`; provisioning requires `provision_cloud_resources` for `cloud-resource:<provider>:<environment>:<kind>:<logical-name>`.

Production PASS requires the applicable prerequisite targets, merged landing state, `run.targets[target-id].source_sha == landing.merged_sha`, migration `PASS` or `not_required`, smoke PASS, retained evidence, and exact deploy authorization. The authorized candidate head and the resulting merged source SHA are separate values, especially after squash merge.

For a native merge-triggered publication, `merge_pr` and `deploy` are independent exact grants bound to the same PLAN revision/digest, candidate head, missions, and `release:<target-id>`. Neither grant implies the other. The merge is the publication trigger; after it completes, retain the resulting merged source SHA separately. See `cloudflare-deployment-lifecycle.md` for provider setup and evidence rules.

A PR closed without merge uses the exact terminal pair `pr_state: closed` and `merge_status: closed_unmerged`, with no `merged_sha`. No state other than `merged` may record `merged_sha`. This prevents review or merge automation from treating the closed PR as merely not ready.

## Post-Merge Cleanup State

Schema v5 adds `post_merge_cleanup`; schemas v6 through v9 preserve it. It closes only local lifecycle state and never changes the GitHub merge result. Valid v2 through v4 RUN files remain readable without it.

Cleanup may become `ready` only after the landing state is `merged`, every mission is integrated, the merged SHA is freshly confirmed reachable from the base branch, and the exact local feature branch still points to `landing.pr_head_sha`. When the primary checkout is on that feature branch, its observed `parent_head_sha` must supply the same proof. This exact-head rule matters for squash merge: the feature commit is not normally an ancestor of the squash commit, so ordinary `git branch -d` may reject it even though GitHub merged the PR. A forced local ref deletion is safe only after the merged-PR/current-head proof and exact `delete_branches` authorization pass.

For a parent-managed linked worktree, record its absolute path, branch ref, head SHA, clean state, and `managed_by: parent`. Schemas v5 through v9 also record `observed.git.parent_worktree_path`; the cleanup target must differ so the primary checkout cannot be removed. `ready` requires the same clean parent-managed linked worktree in the current observed snapshot plus `remove_worktrees` authorization for `worktree:<absolute-path>`. `not_applicable` requires no matching linked worktree; an app-managed match must use deferred platform lifecycle state instead. Remove a parent-managed worktree without force, refresh the worktree observation, switch the primary checkout to the base branch, and only then delete `branch:refs/heads/<head-branch>`. `complete` requires the worktree to be absent, the primary checkout to be clean on the base branch, the local branch to be recorded `deleted`, and verification evidence to be present — except when `run.integration.retention == "persistent"`, in which case `complete` instead requires the local branch to be recorded `preserved`, not deleted, since the branch survives across runs as the next run's starting base; only its temporary worktree directory, a separate concern, may still be removed normally.

Use `deferred` with a reason when either cleanup action is not authorized, observed state is dirty or changed, or platform-managed retention owns the worktree. Use `not_applicable` for local-only/uncreated/closed-unmerged landing only when a fresh terminal observation contains no matching linked worktree. Never remove the primary checkout. App-managed automatic cleanup and snapshot restoration remain platform lifecycle facts, not `remove_worktrees` execution.

## Runtime Capability Axes

Represent orchestration with three independent axes. Do not encode them as a single mode string.

RUN records them together under `runtime_capabilities`, along with `max_parallel_workers`, a `platform_lifecycle` object, and optional backward-compatible `nested_subagents` and `permission_boundary` objects. Schemas v6 through v9 require `runtime_adapter`. `platform_lifecycle` has `owner` (`parent` or `app`), `automatic_retention_cleanup_possible`, and `durable_branch_required_before_unique_work`.

### Runtime adapter and routing

Schemas v6 through v9 record observed host capabilities without replacing the three portable axes:

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

PLAN v4 runtime-worker nodes may add `provider_options` for any provider in their `allowed_providers`. Each option uses the exact keys `model` and `reasoning_effort`. Model is null or a safe token matching `^[A-Za-z0-9][A-Za-z0-9._-]*$`. Reasoning effort is null or one of `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, and `ultra`; selectable effort is supported for Codex and Claude Code, while generic providers keep it null. The selector chooses the provider first, then attaches its options to one immutable runtime binding. A missing Codex option means the destination default; a missing Claude option means `sonnet`. The destination host still validates current model and effort support.

When the parent allocates a PLAN-v4 graph worker in RUN v8 or v9, copy a mission binding into `workers[].runtime_binding` or a read-only verifier binding into `review_workers[].runtime_binding`, with provider, driver, source, model, reasoning effort, and option source. A review worker also records node/attempt identity, graph revision, review path, and exact reviewed SHA; it has no mission lease, writable worktree, branch, or commit authority. For Codex app tasks, pass non-null values through task creation. A Claude Code host passes each node's own model and non-null reasoning effort directly into that node's own `agent()` call inside the Workflow script; one wave may freely mix models and reasoning efforts across nodes since selection happens per spawned agent, not per wave. Never silently replace a rejected model or effort; replan the affected node and increment the PLAN revision.

For every plan-backed multi-mission run, capture this adapter before the first production edit or worker launch. Capability observation and action authorization are separate facts: record a usable driver even when its launch actions remain false. In particular, do not omit `app_threads` because `create_user_owned_tasks` or worktree authorization is missing. Record the capability, request the launch bundle once at Plan Readiness, and rerun selection after the answer.

Provider means the host session running the Harness, not every CLI installed on the machine. Observe current-session native tools first: Codex project/thread creation and polling for `app_threads`, Claude Code's `Workflow` tool and supported runtime for `dynamic_workflow`, and current-session child-agent tools for `subagents`. Use `explicit` only when the host surface is opaque; otherwise use `generic` + `fallback`. A binary or plugin version may confirm feature compatibility after provider detection, but it does not select the provider or authorize a launch.

The chosen host driver must match the portable host axes. `app_threads` requires `app_task` + `app_managed_worktree` + `thread_poll`. `dynamic_workflow` requires `subagent` + `parent_managed_worktree` + `agent_result`. Direct `subagents` use `subagent` with a supported shared or parent-managed workspace and direct result/report channel. `sequential_parent` requires `parent` + `shared_checkout` + `agent_result`.

For a plan-backed graph, every mission node is a write mission and must bind to `parent_managed_worktree` or `app_managed_worktree`; the selector never rewrites `harness_parent` into a shared-checkout write with no required actions. `shared_checkout` is available only to explicitly read-only graph work such as verifier/review nodes. If a write node cannot obtain an eligible isolated worktree and its worktree/branch/commit authorizations, it remains deferred rather than silently downgrading.

A current PLAN-v5 typed node's `allowed_providers` must include the current host's provider for the node to be selectable at all; there is no other-host adapter to fall back into. A node whose `allowed_providers` excludes the current host provider is recorded `runtime_unavailable` and reported blocked on provider mismatch, to be picked up by a run hosted by the matching adapter.

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
| Write isolation | More than one write mission uses separate eligible worktrees; `shared_checkout` has a write budget of one |
| Completion observable | Chosen `completion_channel` can return a terminal result, blocker, or failure to the parent |
| Integration observable | Parent can obtain base SHA, worker head SHA, actual changed paths, and verifier evidence |
| Resource isolation | File scopes and every runtime resource have complete, supported claims |
| Lifecycle understood | Branch/ref durability and app-managed retention behavior are recorded |
| Permission boundary | Parent mode/profile and inheritance are observed; every required filesystem, Git metadata, temp/cache, network, local-binding, and socket surface is covered without an unresolved prompt |
| Runtime route | Provider and available drivers are observed; the deterministic selected driver matches the declared runtime/workspace/completion axes |
| Nested delegation bounded | Any enabled app-task child policy is covered by `spawn_subagents`, stays at depth one, uses at most three read-only children, and returns results to the app-task parent |

If any capability, isolation, permission, or completion row is unknown, do not fan out. Observe it first; if it remains unavailable, select a supported sequential combination, normally `parent` or `subagent` with `shared_checkout`, and apply the same verification gates. Missing launch authorization is not an unknown capability: request the exact run-wide launch bundle once and pause rather than rewriting the runtime adapter or silently downgrading.

For plan-backed multi-mission execution, the configured write-worker maximum has no default numeric ceiling; per `SKILL.md`'s Default Runtime And Wave Policy the parent sets `max_parallel_workers` generously high and lets observed worker slots, isolation capacity, and the dependency-ready conflict-free frontier size do the real bounding. Deterministic mission selection is the default immediately after Plan Readiness and execution authorization; run validation and selection before any production task. The effective wave remains the minimum of that configured maximum, live worker slots, isolated workspaces, dependency-ready nonconflicting missions, and every capability and permission gate above.

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

Each mission lease and worker record repeats the lease ID, plan revision/digest, and batch base so stale results can be rejected without inference. The run-level `runtime_adapter` records provider/driver routing. Worker records name runtime/workspace/completion axes, the selected runtime binding when graph-backed, task/thread identity when applicable, worktree path, branch/ref, optional nested-subagent policy, optional report path, phase, and observed head SHA.

Worker status, head SHA, integration result, and evidence are live RUN state. After any worker failure, integration failure, dependency change, plan revision, or completed batch, close the wave and recompute from current state. A plan revision supersedes every active old-revision lease: quiesce those workers at safe boundaries and issue new leases only after validating their preserved heads against the new plan. Never carry forward an old result, conflict, or readiness assumption.
