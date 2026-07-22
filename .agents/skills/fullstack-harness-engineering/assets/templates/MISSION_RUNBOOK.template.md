# Run: <feature or product slice>

Use this template as `docs/goal/RUN.md` only after the Project Size Gate classifies the work as large or the user explicitly requests managed planning. Small direct work does not instantiate this file. Keep mutable authorization, observed runtime facts, mission/task phases, wave selection, worker state, verification, blockers, and closeout here. Keep static plan definitions in `PLAN.md`; version support does not enable Cloudflare release state by itself.

For compact large sequential work that intentionally has no `PLAN.md`, use schema v7, set the three `plan` values to `null`, remove the complete `deployments` and `graph_state` objects, and leave waves/workers empty. Default to `worker_runtime: "subagent"`, `workspace_mode: "parent_managed_worktree"`, `max_parallel_workers: 1`: the parent still processes one mission at a time, but each one gets its own worktree and merges into local `main` only after its integration gate passes, so the primary checkout is never a direct implementation target. Fall back to `worker_runtime: "parent"`, `workspace_mode: "shared_checkout"` only when worktree creation itself is unavailable or unauthorized. That compact mode does not claim static plan or graph validation and cannot delegate writes, accept execution-time task refinement, or use a selector. Create and validate a schema-v4 `PLAN.md`, promote the RUN to schema v9, then fill the plan ID/revision/digest and graph state before crossing any of those boundaries.

For plan-backed multi-mission execution, replace the generic fallback runtime snapshot before the first production edit. Proactively record every observed driver independently from authorization, set the configured write-worker maximum generously high unless an explicit user or runtime limit applies, and run deterministic selection immediately after Plan Readiness. Choose landing from the requested outcome: local branch, commit, or integration work stays `local_only` and does not wait for GitHub. When pull-request landing is explicitly requested, inspect the review and merge path and request every missing launch and landing action in one Plan Readiness checkpoint. Before the PR exists, use `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` for its review and merge targets. Record approvals under separate exact ledger entries, rerun selection after the answer, and continue through authorized review and merge without repeated prompts. Start or observe current-head CI and Codex review concurrently after the final candidate is pushed. Do not hide a capability or silently downgrade because authorization is missing. Never run parallel writers in `shared_checkout`.

## Harness Run State

`deployments.provider` accepts `cloudflare | vercel | aws | self_hosted | other` and must match the PLAN's `release.provider`. The `development`/`production` fields below (including `worker_name`/`url`/`version_id`) apply to any provider, but a `PASS` status only requires a non-empty `worker_name`/`url`/`version_id` when `provider` is `cloudflare`; other providers only require `source_sha` and retained `evidence`.

```json
{
  "harness_run": {
    "schema_version": 9,
    "run_id": "RUN-<stable-id>",
    "plan": {
      "id": "PLAN-<stable-id>",
      "revision": 1,
      "digest_sha256": null
    },
    "status": "draft",
    "intent": "plan-only",
    "plan_readiness": "draft",
    "execution_authorized": false,
    "execution_authorization_source": null,
    "execution_authorization_scope": null,
    "authorizations": {
      "invoke_external_runtime": {
        "authorized": false,
        "source": null
      },
      "spawn_subagents": {
        "authorized": false,
        "source": null
      },
      "create_user_owned_tasks": {
        "authorized": false,
        "source": null
      },
      "create_local_worktrees": {
        "authorized": false,
        "source": null
      },
      "create_app_managed_worktrees": {
        "authorized": false,
        "source": null
      },
      "create_local_branches": {
        "authorized": false,
        "source": null
      },
      "create_local_commits": {
        "authorized": false,
        "source": null
      },
      "integrate_locally": {
        "authorized": false,
        "source": null
      },
      "push": {
        "authorized": false,
        "source": null
      },
      "create_pr": {
        "authorized": false,
        "source": null
      },
      "configure_repository": {
        "authorized": false,
        "source": null
      },
      "manage_pr_review": {
        "authorized": false,
        "source": null
      },
      "merge_pr": {
        "authorized": false,
        "source": null
      },
      "deploy": {
        "authorized": false,
        "source": null
      },
      "archive_worker_tasks": {
        "authorized": false,
        "source": null
      },
      "remove_worktrees": {
        "authorized": false,
        "source": null
      },
      "delete_branches": {
        "authorized": false,
        "source": null
      }
    },
    "runtime_capabilities": {
      "worker_runtime": "parent",
      "workspace_mode": "shared_checkout",
      "completion_channel": "agent_result",
      "max_parallel_workers": 1,
      "runtime_adapter": {
        "provider": "generic",
        "available_drivers": [
          "sequential_parent"
        ],
        "detection_source": "fallback"
      },
      "permission_boundary": {
        "selected_mode": "unknown",
        "profile_name": null,
        "approval_policy": "unknown",
        "filesystem_scope": "unknown",
        "network_scope": "unknown",
        "local_binding": "unknown",
        "worker_inheritance": "unknown",
        "status": "unknown"
      },
      "nested_subagents": {
        "available": false,
        "max_depth": 1,
        "max_children_per_worker": 3,
        "allowed_roles": [
          "explorer",
          "researcher",
          "reviewer",
          "tester"
        ],
        "write_policy": "read_only",
        "completion_channel": "agent_result"
      },
      "platform_lifecycle": {
        "owner": "parent",
        "automatic_retention_cleanup_possible": false,
        "durable_branch_required_before_unique_work": true
      }
    },
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
    },
    "integration": {
      "branch": null,
      "batch_base_sha": null,
      "integration_head_sha": null
    },
    "batch_gate_results": [
      {
        "id": "batch-cross-mission",
        "status": "planned",
        "head_sha": null,
        "evidence": []
      }
    ],
    "final_gate_results": [
      {
        "id": "e2e-primary-journey",
        "status": "planned",
        "head_sha": null,
        "evidence": []
      }
    ],
    "ui_evidence": [],
    "landing": {
      "mode": "local_only",
      "remote": "origin",
      "head_branch": null,
      "base_branch": "main",
      "pushed_head_sha": null,
      "pr_number": null,
      "pr_url": null,
      "pr_state": "not_created",
      "pr_head_sha": null,
      "checks_status": "not_started",
      "checks_head_sha": null,
      "review_status": "not_requested",
      "review_head_sha": null,
      "blocking_findings": null,
      "unresolved_threads": null,
      "merge_status": "not_ready",
      "merged_sha": null,
      "auto_merge_requested": false,
      "auto_merge_head_sha": null
    },
    "deployments": {
      "provider": "cloudflare",
      "development": {
        "status": "not_started",
        "source_sha": null,
        "worker_name": null,
        "url": null,
        "version_id": null,
        "migration_status": "not_started",
        "verification_status": "not_started",
        "rollback_version": null,
        "evidence": []
      },
      "production": {
        "status": "not_started",
        "source_sha": null,
        "worker_name": null,
        "url": null,
        "version_id": null,
        "migration_status": "not_started",
        "verification_status": "not_started",
        "rollback_version": null,
        "evidence": []
      }
    },
    "post_merge_cleanup": {
      "status": "not_started",
      "base": {
        "branch": "main",
        "head_sha": null,
        "merged_sha_reachable": null
      },
      "worktree": {
        "path": null,
        "branch_ref": null,
        "head_sha": null,
        "dirty": null,
        "managed_by": null,
        "status": "not_applicable"
      },
      "local_branch": {
        "ref": null,
        "head_sha": null,
        "status": "pending"
      },
      "evidence": [],
      "deferred_reason": null
    },
    "graph_state": {
      "graph_revision": 1,
      "node_states": {
        "N-M1": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        }
      },
      "edge_states": {}
    },
    "mission_states": {
      "M1": {
        "phase": "queued",
        "lease_id": null,
        "lease_plan_revision": null,
        "lease_plan_digest_sha256": null,
        "worker_id": null,
        "base_sha": null,
        "head_sha": null,
        "integration_gate": "planned",
        "integrated_sha": null,
        "blockers": [],
        "report_path": null
      }
    },
    "task_states": {
      "M1/T01": {
        "phase": "queued",
        "attempts": 0,
        "commit_sha": null,
        "verifier_status": "planned",
        "blockers": [],
        "refinement_request": null
      }
    },
    "active_wave": {
      "wave_id": null,
      "status": "idle",
      "plan_revision": 1,
      "plan_digest_sha256": null,
      "batch_base_sha": null,
      "selected_missions": [],
      "deferred_missions": [],
      "conflict_edges": []
    },
    "workers": [],
    "review_workers": [],
    "workflow_runs": [],
    "attempt_log": []
  }
}
```

The exact fenced JSON block above is the canonical run state. Scripts read this block only; Markdown tables later in this document are non-canonical human views. Update the JSON first, keep it valid, and never infer authorization from plan readiness, a template, or a Goal prompt.

### RUN Schema Version History

New RUN files always use v9 (see `SKILL.md`'s Default Runtime And Wave Policy). Older schemas below exist only so a parent can keep reading a RUN.md written before this history table existed; nothing here changes what a new file must contain.

| Schema | Added | Still readable |
|---|---|---|
| v2 | Baseline: 13-action ledger, no landing/deployment/graph state | yes |
| v3 | 16-action ledger (`configure_repository`, `manage_pr_review`, `merge_pr`), `landing` object | yes |
| v4 | `auto_merge_requested` / `auto_merge_head_sha` on `landing` | yes |
| v5 | `post_merge_cleanup` | yes |
| v6 | `runtime_adapter`, `future-pr:` authorization targets | yes |
| v7 | Cloudflare `deployments` (required only when PLAN declares `release`) | yes |
| v8 | `graph_state` for PLAN-v4 typed nodes/edges, 17-action ledger (+`invoke_external_runtime`) | yes |
| v9 (current default) | `batch_gate_results`, `final_gate_results`, `ui_evidence`; `workflow_runs` when also paired with a PLAN-v4 graph run | current |

The rest of this document states rules as the current v9 shape. Where a rule differs for an older, still-readable file, that file's own recorded `schema_version` decides which fields apply — do not backfill v9-only fields into an older valid file just because this history table lists them.

The schema-v9 action ledger has 17 independent entries. Keep every entry false unless an explicit user instruction authorizes that exact action; put a concise evidence reference in its `source`. `invoke_external_runtime` is separate from `spawn_subagents` and uses an exact `runtime:<provider>` target because it can cross a data, cost, and permission boundary. When `execution_authorized` is true, `execution_authorization_source` must identify the explicit user source and `execution_authorization_scope` must be `{ "run_id": ..., "mission_ids": [...], "expires_when": ... }` matching the current operation. `execution_authorized` is an overall implementation gate, not a substitute for action-specific authorization. At Plan Readiness, one prompt may request all missing execution, launch, branch, commit, integration, push, PR creation, review-management, and merge actions for exact targets, but every action remains a separate ledger entry. Use the schema-v6-through-v9 `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` target for review and merge only until that PR is created. Repository configuration may join that checkpoint only for an observed exact setup change. Deploy, archive, worktree removal, and branch deletion remain outside the landing bundle.

`graph_state` is the canonical routing record for PLAN-v4 nodes and edges. Initialize one state for every declared node and edge. A mission node reaches `succeeded` with outcome `pass` only when its matching mission state is `integrated` with an integration `PASS`; keep mission state for lease/Git/integration details and graph state for attempt/outcome/routing details. Every retry uses a new `last_attempt_id`, increments `attempts`, preserves the prior attempt evidence in `attempt_log`, and rechecks authorization. Edge `traversals` never exceeds the PLAN bound. Run `select_ready_nodes.py` after every terminal node result, integration, graph revision, or changed external state.

`landing` is required in schemas v3 through v9. Schemas v4 through v9 include the auto-merge fields shown above; v3 remains readable without them. Schemas v5 through v9 include `post_merge_cleanup`. Schemas v7 through v9 support Cloudflare `deployments` state, but the field is required only when the matching PLAN declares `release` and must be omitted otherwise. Valid older RUN schemas remain readable. New RUN files default to `mode: "local_only"`; switch to `pull_request` only when the user explicitly requests remote landing. Local-only mode cannot record a pushed head or created PR. A created PR records its current remote head in both `pushed_head_sha` and `pr_head_sha`. `checks_status: "PASS"` and `review_status: "PASS"` are valid only when their recorded head SHA and `integration.integration_head_sha` match that current PR head. Any new push or local integration makes the old landing result stale; reset the affected status, push the current integration head, request review again, and do not set `merge_status: "ready"` until the PR head equals the integration head, current-head checks and review pass, and blocking findings and unresolved threads are zero. Preserve those same gates when recording `merge_status: "merged"`, then also record `pr_state: "merged"` and `merged_sha`.

When schema v7 through v9 carries `deployments`, deploy the current PR head to the development Worker only after current-head CI passes. Record its exact SHA, Worker, URL, Cloudflare version ID, migration result, deployed-environment verification, and evidence. Production may reach `PASS` only after development is `PASS`, the PR is merged, and the production source SHA equals `landing.merged_sha`. A complete Cloudflare run requires both targets to pass. Before either mutation, the `deploy` ledger must cover every run mission and the exact `environment:development` or `environment:production` target. One explicit readiness statement may authorize both targets, but deployment stays a separate ledger action from push, merge, and repository configuration.

See `references/execution-state-model.md`'s closeout condition table for the full `status: complete` requirement. Every applicable condition there must hold, with non-empty evidence for each schema-v9 batch, final gate, and required UI screenshot bound to the current integration head.

Set `auto_merge_requested: true` only after GitHub accepts a squash auto-merge request for the exact current PR head, and record that SHA in `auto_merge_head_sha`. At request time this requires `merge_status: "ready"`, current-head CI and Codex review PASS, zero blocking findings and unresolved threads, repository auto-merge enabled under `configure_repository`, and unexpired `merge_pr` authorization whose mission scope covers the run and whose target is `pr:<full-PR-URL>` (or an explicitly run-wide `*`). If that entry began with `future-pr:`, retain it and verify that the exact PR has the same repository, base, and head before appending the exact target. Use `gh pr merge --auto --squash --match-head-commit <sha>` or an equivalent exact-head operation. After the PR reaches `merge_status: "merged"`, preserve the matching authorization evidence even when its `run_complete` boundary expires during final closeout. Any new push, changed integration head, canceled request, or closed-unmerged PR resets the fields to `false` and `null`.

A PR closed without merge records `pr_state: "closed"`, `merge_status: "closed_unmerged"`, and `merged_sha: null`. Do not leave a closed PR at `not_ready`, because terminal automation must stop or explicitly reopen it.

Schemas v5 through v9 use `post_merge_cleanup` only after a pull request reaches `merged`. Before setting cleanup to `ready`, every precondition below must hold:

| Precondition | Requirement |
|---|---|
| Landing merged | The PR has reached `merged` |
| Base fetched | The base branch is freshly fetched |
| Merge reachable | `landing.merged_sha` is reachable from that base |
| Clean checkout | A re-observed checkout is clean |
| Worktree recorded | `observed.git.parent_worktree_path` is recorded |
| Feature branch head | The local feature branch still points to `landing.pr_head_sha`; when the primary checkout is on that branch, its observed `parent_head_sha` must match too |

Manual worktree removal additionally requires a different exact clean linked path, branch ref, head SHA, and `managed_by: "parent"` to match the current observation. Terminal `not_applicable` requires a fresh observation with no matching linked worktree; app-managed worktrees use deferred platform lifecycle state instead. `delete_branches` must cover `branch:refs/heads/<head-branch>` for every run mission; `remove_worktrees` must separately cover `worktree:<absolute-path>` when a parent-managed linked worktree exists. Remove that worktree without force, refresh `git worktree list --porcelain`, switch the primary checkout to the base branch, then delete the exact local feature branch. A squash-merged branch may require forced local ref deletion because its commit is not a Git ancestor of the squash commit; use it only after these merged-PR and exact-head gates pass. Record `complete` with refreshed evidence, or `deferred` with a reason when cleanup is not authorized or the worktree is platform-managed. Never remove the primary checkout or treat app retention as a harness cleanup action.

Create the final integration branch and PR from the parent checkout. In pull-request mode, record that same branch in both `integration.branch` and `landing.head_branch`; it must differ from `landing.base_branch`. In `local_only` mode there is no separate long-lived integration branch: `integration.branch` is `landing.base_branch` itself (local `main`), and each mission's worktree branch merges directly into it once that mission's integration gate passes — that merge is the local dev-test point, run its integration verifiers against the updated `main` immediately after. Worker branches and worker worktrees do not push or open their own PRs unless the plan explicitly defines a separate landing target. Converge focused checks, mission integration, batch checks, and exact-SHA runtime code-review repairs before the expensive final broad regression, browser E2E, screenshot, and visual-review matrix. Any repair that changes the head invalidates affected current-head evidence. The normal landing order is final local verification and read-only diff review, push final branch, create Draft PR, pass CI, mark Ready, obtain GitHub review, resolve blocking threads, then enable SHA-bound auto-merge only with separate `merge_pr` authorization. Never push the base branch directly in pull-request mode.

When every state mutation that remains in the landing path has matching unexpired authorization for the run and exact targets—normally `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `create_pr`, `manage_pr_review`, and `merge_pr` for a new delivery—treat that order as one continuous parent-owned landing loop. Request the complete missing set once at Plan Readiness rather than discovering ordinary landing approvals stage by stage. For unborn PR review and merge entries, use `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>`; after creation, verify those fields and append `pr:<full-PR-URL>` while keeping the future target and source. Do not pause merely because a Draft PR was created, CI is pending, or review was requested. Poll each gate, record its result against the current PR head, repair only authorized in-scope failures, and restart CI/review after every new push. Request Codex review with the observed repository mechanism; when Automatic reviews are not proven, use `@codex review` and wait for the completed review rather than its acknowledgement. Enable squash auto-merge with an exact head-SHA match only after checks and review PASS with zero blocking findings and unresolved threads, then wait until GitHub reports the PR merged and record the merge SHA. Missing repository configuration still requires separate `configure_repository` authorization, though an observed need may be included in the same readiness checkpoint; deploy and cleanup remain outside this loop.

An authorized action may add `scope` and `expires_when` beside `authorized`/`source`:

```json
{
  "authorized": true,
  "source": "<explicit user statement reference>",
  "scope": {
    "run_id": "RUN-<stable-id>",
    "mission_ids": [
      "M1"
    ],
    "targets": [
      "<exact branch, worktree, task, environment, or * when explicitly run-wide>"
    ]
  },
  "expires_when": "run_complete"
}
```

When an action is authorized, scope is required and must cover the current run, mission, and target; use `"*"` only when the user's approval is explicitly run-wide. Encode exact targets as `worker:<id>`, `task:<id>`, `worktree:<absolute-path>`, `branch:<full-ref>`, `remote:<remote/ref>`, `pr:<full-PR-URL>`, `environment:<name>`, or `runtime:<provider>` as appropriate. Schemas v6 through v9 additionally permit `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>` only for `manage_pr_review` and `merge_pr`; it must resolve to and retain the matching exact PR target before either mutation. `expires_when` is exactly `wave_closed`, `run_complete`, or `explicit_revocation`; the coordinator evaluates that boundary against current RUN state. Treat an expired or nonmatching entry as unauthorized.

Treat `wave_closed` as a one-use grant. On `closed` or `superseded`, reset matching action entries to unauthorized and clear an overall wave-scoped execution grant before replacing `active_wave`; never carry that source into the next wave.

The parent may inspect state, validate manifests, and compute static conflict/parallel-eligibility analysis without implementation authorization. A launch-bound ready frontier or selected wave additionally requires canonical readiness, execution authorization, and every action needed by the launch path. Delegating even read-only analysis still requires the matching `spawn_subagents` or `create_user_owned_tasks` authorization.

For automatic app-task fan-out, the selector emits one `launch_directives` entry per selected mission. After accepting the wave, the parent allocates workers, leases, and branches/refs; verifies the explicit pre-allocation `*` grant for app-assigned task/worktree identities and every already-known target under `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, and `create_local_commits`; creates one real Codex worktree thread per directive; and writes the returned thread/client identity into `workers[].task_thread_id`. The directive itself is neither authorization nor proof of launch. If project lookup, thread creation, worktree setup, follow-up messaging, polling, or nested-agent capability is unavailable, leave the worker unlaunched and use the sequential parent fallback.

For graph workers, copy the selector's complete `runtime_binding` into the allocated mission `workers[]` record or read-only verifier `review_workers[]` record. A review worker also binds node ID, attempt ID, graph revision, review path, and exact current integrated or PR-head SHA; it has no mission lease, writable worktree, branch, or commit authority. For Codex app tasks, pass non-null `model` and `reasoning_effort` as task creation `model` and `thinking`; omit null values so the host default remains explicit. For Claude Code, pass each node's own `model` (and non-null `reasoning_effort` as `effort`) into that node's own `agent()` call inside the Dynamic Workflow script; a single wave may mix models and reasoning efforts freely since each node's call carries its own. The destination host validates the exact pair at launch.

Use these exact coordination enums:

- `worker_runtime`: `parent`, `subagent`, or `app_task`
- `workspace_mode`: `shared_checkout`, `parent_managed_worktree`, or `app_managed_worktree`
- `completion_channel`: `agent_result`, `thread_poll`, `report_file`, or `user_relay`

Schemas v6 through v9 require `runtime_capabilities.runtime_adapter`. The parent detects actual host capabilities before selection and records `provider` as `codex`, `claude_code`, or `generic`; `detection_source` as `observed`, `explicit`, or `fallback`; and every actually available host driver in `available_drivers`. Always include `sequential_parent`. Capability detection is not authorization.

When the selected driver is `dynamic_workflow`, use `subagent` + `parent_managed_worktree` + `agent_result`, omit `nested_subagents`, and treat the accepted wave as one flat workflow run. The parent allocates one worktree/branch/lease per mission, then invokes the Claude Code `Workflow` tool with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and the accepted directives supplied as structured `args`. Launch only after `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, and `create_local_commits` cover the selected missions and allocated targets. A workflow cannot wait for human sign-off mid-run; return a refinement request and close the wave when a contract or authorization decision is needed.

`CLAUDE_DYNAMIC_WORKFLOW.template.js` only launches flat mission workers: it has no `node_kind`, no `tool_profile` validation, and no `EnterWorktree` call per node. A wave that mixes mission and review graph nodes, enforces a `tool_profile` (`mission_write`, `code_review_readonly`, `visual_review_readonly`), or requires each node to call `EnterWorktree` before its own reads/writes must instead use `assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js`, passing `tool_profile` and the typed `nodes[]` array (each with `node_kind: "mission"` or `"review"`) as structured `args`. Use the flat script only for single-role, all-mission waves with no read-only review nodes.

A graph node's `allowed_providers` must include the current host's provider before the parent may bind it to a worker at all. There is no cross-host route: a Codex-hosted parent never binds a node to Claude Code, and a Claude-Code-hosted parent never binds a node to Codex. A ready node whose allowed/preferred providers exclude the current host is recorded blocked on provider mismatch and left for a run hosted by the matching adapter.

`runtime_capabilities.permission_boundary` records the effective parent mode before workers launch. Use `selected_mode` values `ask_for_approval`, `approve_for_me`, `full_access`, `named_profile`, or `unknown`; a non-empty `profile_name` is required only for `named_profile`. Record approval, filesystem, network, local-binding, and worker-inheritance facts, then set `status` to `ready` only after linked-worktree Git metadata, temp/cache, outbound network, local/private bindings, and required sockets fit inside the boundary. `may_prompt`, `blocked`, or `unknown` blocks unattended fan-out. Existing schema-v2 RUN files may omit this optional object.

`runtime_capabilities.nested_subagents.available` records whether direct child tools/results were observed inside app tasks; it does not grant permission. The harness policy always caps nesting at depth one, children per app task at three, child work to the listed functional roles, writes to `read_only`, and child completion to `agent_result`. Set a worker's nested policy to enabled only when `spawn_subagents` covers its mission and `worker:<id>` target (or an explicitly run-wide `*`).

Use mission phases `queued`, `ready`, `leased`, `worker_running`, `worker_passed`, `integrating`, and `integrated`; mission failure states are `blocked`, `worker_failed`, `integration_failed`, and `superseded`. Use task phases `queued`, `ready`, `running`, `worker_passed`, and `mission_recorded`; task failure states are `blocked`, `worker_failed`, and `superseded`. `worker_passed` does not satisfy downstream mission dependencies. Only a mission at `integrated` with `integration_gate: "PASS"` and an integrated SHA verified as an ancestor of the current integration head does.

Every non-null mission lease binds `lease_id`, `lease_plan_revision`, `lease_plan_digest_sha256`, `base_sha`, and `worker_id`. Each `workers` entry uses this exact shape:

```json
{
  "worker_id": "W1",
  "mission_id": "M1",
  "lease_id": "<lease-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<sha256>",
  "batch_base_sha": "<full SHA>",
  "worker_runtime": "subagent",
  "workspace_mode": "parent_managed_worktree",
  "completion_channel": "agent_result",
  "runtime_binding": {
    "provider": "claude_code",
    "driver": "dynamic_workflow",
    "source": "host",
    "model": "sonnet",
    "reasoning_effort": "high",
    "option_source": "plan_provider_options"
  },
  "nested_subagent_policy": {
    "enabled": false,
    "max_children": 0,
    "allowed_roles": [],
    "write_policy": "read_only",
    "completion_channel": "agent_result"
  },
  "task_thread_id": null,
  "worktree_path": "<path or null>",
  "branch_ref": "<branch/ref or null>",
  "report_path": null,
  "phase": "leased",
  "worker_head_sha": null
}
```

Leave model and effort null unless the user explicitly selected them in the PLAN provider options. During allocation, `worktree_path` and `branch_ref` may be null. Fill them only after the runtime returns and the parent independently verifies them. `worker_head_sha` stays null until the parent verifies the reported commit.

Worker phases are `leased`, `worker_running`, `worker_passed`, `blocked`, `worker_failed`, and `superseded`. An `attempt_log` entry records `attempt_id`, `mission_id`, nullable `task_id` and `lease_id`, `kind`, `result`, and an `evidence` array. Keep observations such as timestamps inside RUN for audit only; selection output remains timestamp-free.

Each `review_workers` entry uses this exact read-only shape:

```json
{
  "worker_id": "RW1",
  "node_id": "N-FRONTEND-REVIEW",
  "attempt_id": "ATT-REVIEW-1",
  "plan_revision": 1,
  "plan_digest_sha256": "<sha256>",
  "graph_revision": 1,
  "reviewed_sha": "<current integrated or PR-head SHA>",
  "review_path": "<absolute read-only path or immutable snapshot>",
  "worker_runtime": "subagent",
  "completion_channel": "agent_result",
  "runtime_binding": {
    "provider": "claude_code",
    "driver": "dynamic_workflow",
    "source": "host",
    "model": "sonnet",
    "reasoning_effort": "medium",
    "option_source": "plan_provider_options"
  },
  "task_thread_id": null,
  "report_path": null,
  "phase": "worker_running"
}
```

The matching successful node result puts exactly `reviewed_sha`, `findings`, and `evidence_summary` inside `worker_result`. The reviewed SHA must match the active review worker.

Graph RUN schemas v8 and v9 may include `workflow_runs` to bind canonical node attempts to actual outer Claude Code Workflow executions. Invoke the Claude Code `Workflow` tool with the canonical PLAN, RUN, and immutable wave request; the parent revalidates current state, authorization, worker bindings, and checkout HEAD before launch. Add an entry only when the runtime returns a real non-empty workflow run ID; never invent one. Running entries bind every node ID to its active attempt ID and must match the current plan, graph, runtime policy, and batch base. One entry may cover node IDs with different resolved models and reasoning efforts; each node's own `model`/`reasoning_effort` still lives on its `workers[]`/`review_workers[]` `runtime_binding`, not on the `workflow_runs` entry. Completed historical entries remain as evidence after later graph revisions and do not require their superseded nodes to remain in the current PLAN.

```json
{
  "workflow_run_id": "wf_<runtime-id>",
  "workflow_task_id": "<background task id or null>",
  "resume_from_run_id": null,
  "script_path": "<resolved workflow script path>",
  "script_sha256": "<sha256>",
  "run_id": "RUN-<stable-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<sha256>",
  "graph_revision": 1,
  "batch_base_sha": "<full SHA>",
  "node_ids": ["N-M1"],
  "attempt_ids": {
    "N-M1": "ATT-N-M1-1"
  },
  "provider": "claude_code",
  "driver": "dynamic_workflow",
  "tool_profile": "mission_write",
  "status": "running",
  "result_evidence": [],
  "metrics": {
    "duration_ms": null,
    "token_count": null
  }
}
```

Tool profiles are `mission_write`, `code_review_readonly`, and `visual_review_readonly`. These profiles, and per-node `EnterWorktree` enforcement, are implemented only by `assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js` (see above), not by the flat `CLAUDE_DYNAMIC_WORKFLOW.template.js`. Group Claude Graph Workflow nodes by tool profile only; model and reasoning effort travel with each node's own `agent()` call, so one wave may mix them freely. Mission and review waves require `EnterWorktree` so each worker enters its exact assigned checkout before repository reads. Both review profiles remain read-only. Visual review consumes retained screenshots or other existing evidence until a new read-only browser tool is explicitly vetted and added to the profile implementation.

For an enabled app-task nested policy, use `max_children` from 1 to 3 and a non-empty subset of the runtime `allowed_roles`. The app task stays the only writer. A non-trivial mission launches at least one eligible read-only lane and records the resulting child activity in WORKER_RESULT; a skip is valid only for a trivial mission, unavailable runtime/slots, or no safe independent lane. When capability is initially unknown, keep the task at a no-production-edit handshake, record its tool/result observation, and then assign the explicit enabled or disabled policy. Older schema-v2 RUN files may omit both optional nested fields; once a RUN includes `runtime_capabilities.nested_subagents`, every app-task worker must include `nested_subagent_policy` and matching `subagent_activity`.

Use active-wave statuses `idle`, `proposed`, `active`, `closed`, and `superseded`. Any accepted plan revision supersedes the active wave and every old-revision lease; quiesce those workers and issue new leases after revalidation rather than accepting stale results.

Use these exact array entry shapes:

```json
{
  "deferred_mission": {
    "mission_id": "M2",
    "reason_codes": [
      "dependency_not_integrated"
    ],
    "conflicts_with": []
  },
  "conflict_edge": {
    "left": "M2",
    "right": "M3",
    "reason_codes": [
      "serialized_resource_conflict"
    ]
  },
  "observed_worktree": {
    "path": "<absolute path>",
    "branch_ref": "<full ref or null>",
    "head_sha": "<full SHA>",
    "managed_by": "parent",
    "dirty": false
  }
}
```

`managed_by` is `parent` or `app`. Sort selected/deferred IDs and conflict-edge endpoints deterministically before recording a parent-confirmed wave.

## Goal And Checkpoint

```text
Objective:
Canonical PLAN path:
Current mission / task:
Last verified integrated result:
Remaining:
Blocked / waiting authorization:
Next action:
```

If Goal mode is used, its prompt may record expected coordination and request authorizations, but it does not grant them. Copy explicit user decisions into the canonical ledger before any corresponding action.

## Plan Readiness View

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Canonical PLAN JSON validates and digest matches | draft / PASS / BLOCKED | |
| Every in-scope trace maps to a task and verifier | draft / PASS / BLOCKED | |
| Mission and task DAGs are explicit and acyclic | draft / PASS / BLOCKED | |
| Frontend/backend/data boundaries are defined | draft / PASS / BLOCKED | |
| Scopes and typed resource inventories are complete | draft / PASS / BLOCKED | |
| UI routes, states, breakpoints, and evidence are planned | draft / PASS / BLOCKED / n/a | |
| Builder UX Direction owner/status and required UX validation are explicit | draft / PASS / BLOCKED / n/a | |
| Worker, mission-integration, batch, final E2E, and release gates exist; E2E command, current-head check, evidence, environment, and smoke disposition are named | draft / PASS / BLOCKED | |
| Every mission's write scope is covered by a review-type node (`backend_code`/`frontend_code`/`visual`), independent of `landing.mode` | draft / PASS / BLOCKED / n/a | |
| Required user decisions and authorization gaps are surfaced | draft / PASS / BLOCKED | |

For plan-backed work, do not set the run to `running` until all required readiness rows pass, the plan revision/digest is current, `execution_authorized` is true, and every next action has its own authorization. In compact RUN-only mode, the parent may set `plan_readiness: "ready"` and `status: "running"` after the applicable sequential readiness checks pass and execution is explicitly authorized; keep plan identity null and do not claim plan validation, delegation, refinement, or wave selection.

## Mission And Task View

The mission ("milestone") and task listing view moved to `docs/goal/tasks.md` (`assets/templates/TASKS.template.md`). It is a non-canonical human view derived from this file's `mission_states`, `task_states`, and `graph_state`; regenerate it from here, never treat it as a second source of truth.

## Active Wave View

| Wave | Fixed base | Selected missions | Deferred missions | Plan revision / digest |
|---|---|---|---|---|
| <wave> | <SHA> | <IDs> | <IDs + reason codes> | <revision / digest> |

The parent selects a ready, non-conflicting wave from validated canonical state, confirms the fixed base SHA, then records the proposal here. For app-task directives, it must create and record the real mission threads before claiming the wave is running. After each integration batch, observe the new head and recompute readiness and conflicts; do not reuse a stale proposal.

## Worker View

| Worker | Mission | Runtime | Model / effort | Workspace | Completion | Nested helpers | Base / head | Phase | Result source |
|---|---|---|---|---|---|---|---|---|---|
| <id> | M1 | parent / subagent / app_task | <model / effort> | <mode> | <channel> | disabled / 1-3 read-only | <SHAs> | <phase> | <result/report/thread> |

For `app_task`, create one real task/thread for each selected mission and record its returned thread or queued client-thread identity. Automatic cross-task callbacks are not guaranteed, so use `thread_poll` when programmatic polling is available and reserve `user_relay` for runtimes without it. Send the complete worker handoff as the initial prompt and use the thread-message surface for the post-handshake policy or later steering. For `app_managed_worktree`, record platform retention behavior and create a durable branch or ref before unique work when authorized; cleanup controls cannot override platform-managed retention.

## Verification Dashboard

Run verification in this order:

| Layer | Intended scope | Head binding |
|---|---|---|
| Task / worker | focused checks selected from parent-observed changed files | worker head |
| Mission integration | that mission's integration surface after serial integration | integration head |
| Batch | true cross-mission and shared-contract checks | post-wave integration head |
| Final / current-head | broad regression, browser E2E, UI evidence, and release gates after review repairs converge | exact accepted integration or PR head |

For any `session_exact` verifier execution, record the execution/evidence key, `executed` or `reused`, duration, and miss/bypass reason in evidence. Reuse is valid only for an opted-in deterministic local `exit 0` command with a clean checkout, repository-external session cache, and exact immutable inputs. Parent-observed files decide verifier applicability; worker claims do not.

| Layer | Considered | Selected | Executed | Reused | Not applicable | Duration / notes |
|---|---:|---:|---:|---:|---:|---|
| Task / worker | 0 | 0 | 0 | 0 | 0 | |
| Mission integration | 0 | 0 | 0 | 0 | 0 | |
| Batch | 0 | 0 | 0 | 0 | 0 | |
| Final / current-head | 0 | 0 | 0 | 0 | 0 | |

| Gate | Required | Pass signal | Status | Evidence |
|---|---|---|---|---|
| Build / static health | yes / no | <literal signal> | planned | |
| Focused behavior | yes / no | <literal signal> | planned | |
| API / data / permissions | yes / no | <literal signal> | planned | |
| Primary journey | yes / no | <literal signal> | planned | |
| Builder UX direction conformance | yes / no | <literal signal> | planned | |
| Usability / task success | yes / no | <literal signal or required human evidence> | planned | |
| UI / responsive / states | yes / no | <literal signal> | planned | |
| Console / network | yes / no | <literal signal> | planned | |
| Accessibility | yes / no | <literal signal> | planned | |
| Visual comparison | yes / no | <literal signal> | planned | |
| Performance / release | yes / no | <literal signal> | planned | |

Gate values: `planned`, `PASS`, `FAIL`, `BLOCKED`, `UNVALIDATED`.

### Automated E2E And Smoke Reuse

| E2E command | CI check | Environment | Covered journeys | Head SHA | Retained evidence | Status |
|---|---|---|---|---|---|---|
| `<e2e-command>` | `<check-name>` | <local / preview / staging / deployed> | <journey IDs> | <SHA> | <artifact / trace / CI log> | planned |

| Proposed manual smoke | Same journey and equivalent environment covered | Disposition | Reason / uncovered risk |
|---|---|---|---|
| <smoke> | yes / no | `required` / `not required - covered by current-head E2E` | <reason> |

Use the replacement disposition only after the automated E2E passes on the exact current head. Deployment smoke, visual checks, or external-integration smoke remains required when its environment or assertions are not equivalent.

## UI Evidence

Include only when UI evidence is required or optional. Use one column set, chosen by the resolved platform. See `references/verification-gates.md`'s "Capture Mechanism By Platform" for how each row is captured.

For a web mission (browser-rendered), use the web columns:

| Route / flow | Viewport | State | Browser result | Console / network | A11y | Visual evidence | Status |
|---|---|---|---|---|---|---|---|
| <route> | <size> | ready / loading / empty / error / disabled / permission / long-running | <result> | <result> | <result> | <path> | planned |

For a native iOS/Android/Flutter/macOS/Windows mission, use the native columns (same shape, capture mechanism differs — Simulator/Emulator/device screenshot from the platform's UI-test tooling, not a browser):

| Screen / flow | Device / OS version | State | Native test result | Crash / log | A11y | Visual evidence | Status |
|---|---|---|---|---|---|---|---|
| <screen> | <device + OS/SDK version> | ready / loading / empty / error / disabled / permission / long-running | <result> | <result> | <result> | <path> | planned |

Record every screenshot in canonical `ui_evidence` before updating this human view. Each entry binds one PLAN surface, route, breakpoint, and state to a repo-relative `.png`, `.jpg`, `.jpeg`, or `.webp` path under `docs/goal/evidence/`, its lowercase SHA-256, the exact integration head SHA, and a gate status. For `evidence_gate: "required"`, `complete` requires the full breakpoint-by-state matrix to PASS. A trace, console log, or written review does not replace the screenshot.

Store only real binary artifacts under `docs/goal/evidence/`. Do not create empty evidence folders. Run `scripts/validate_harness_plan.py --plan <PLAN.md> --run <RUN.md> --repo-root <repo-root>` to verify that each recorded file exists and matches its SHA-256.

## UX Evidence

Include when Builder UX Direction or a `UX-*` trace exists. Builder approval proves direction conformance only; screenshots, agent review, and automated E2E do not by themselves prove representative-user usability.

| UX trace | Critical task / scenario | Direction source and status | Validation method | Representative participant / source | Target | Actual result | Redacted evidence | Status |
|---|---|---|---|---|---|---|---|---|
| UX-001 | <task and context> | <owner/source; selected/provisional/assumed> | <prototype review / likely-user test / benchmark / other> | <segment or approved source> | <success/failure signal> | <result> | <path/report/decision> | planned / PASS / FAIL / BLOCKED / UNVALIDATED |

Do not store participant personal data, raw recordings, or unredacted transcripts in the repository without explicit approval.

## Attempt Log View

| Observation | Mission / task | Action | Verification | Progress | Result / next action |
|---|---|---|---|---|---|
| <sequence or time> | M1/T01 | <action> | <command/path> | <before -> after> | <result> |

## Blockers, Approvals, And Refinement

| Item | Evidence | Required input / authorization | Status |
|---|---|---|---|
| <item> | <path/result> | <need> | open / resolved |

A worker never edits PLAN or RUN. When it returns `REFINEMENT_REQUEST`, the parent either rejects it, replaces the generation-0 task with bounded generation-1 children and increments the plan revision, or stops for a mission-level replan. Re-run plan, trace, DAG, scope, resource, and conflict validation after any accepted change.

## Closeout

```text
Final status:
Outcome:
Integrated head and verified ancestry:
Evidence:
Changed files:
Commits:
Residual risk:
Landing state:
Development deployment state:
Production deployment state:
Post-merge cleanup state:
```
