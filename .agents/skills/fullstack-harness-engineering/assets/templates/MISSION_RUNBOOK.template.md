# Run: <feature or product slice>

Use this template as `docs/goal/RUN.md`. Keep mutable authorization, observed runtime facts, mission/task phases, wave selection, worker state, verification, blockers, and closeout here. Keep static plan definitions in `PLAN.md`.

For compact medium work that intentionally has no `PLAN.md`, set the three `plan` values to `null`, keep `worker_runtime: "parent"`, `workspace_mode: "shared_checkout"`, `max_parallel_workers: 1`, and leave waves/workers empty. That compact mode does not claim static plan validation and cannot delegate writes, accept execution-time task refinement, or use the selector. Create and validate `PLAN.md`, then fill the plan ID/revision/digest before crossing any of those boundaries.

## Harness Run State

```json
{
  "harness_run": {
    "schema_version": 4,
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
    "landing": {
      "mode": "pull_request",
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
    "attempt_log": []
  }
}
```

The exact fenced JSON block above is the canonical run state. Scripts read this block only; Markdown tables later in this document are non-canonical human views. Update the JSON first, keep it valid, and never infer authorization from plan readiness, a template, or a Goal prompt.

The action ledger has 16 independent entries. Keep every entry false unless an explicit user instruction authorizes that exact action; put a concise evidence reference in its `source`. When `execution_authorized` is true, `execution_authorization_source` must identify the explicit user source and `execution_authorization_scope` must be `{ "run_id": ..., "mission_ids": [...], "expires_when": ... }` matching the current operation. `execution_authorized` is an overall implementation gate, not a substitute for action-specific authorization. Repository configuration, push, PR creation, PR review management, PR merge, deploy, archive, worktree removal, and branch deletion remain false unless separately authorized.

`landing` is required in schemas v3 and v4. Schema v4 adds the auto-merge fields shown above; schema v3 remains readable without them. Use `mode: "pull_request"` for the default shared-repository flow and `local_only` only when the user explicitly wants no remote landing; local-only mode cannot record a pushed head or created PR. A created PR records its current remote head in both `pushed_head_sha` and `pr_head_sha`. `checks_status: "PASS"` and `review_status: "PASS"` are valid only when their recorded head SHA and `integration.integration_head_sha` match that current PR head. Any new push or local integration makes the old landing result stale; reset the affected status, push the current integration head, request review again, and do not set `merge_status: "ready"` until the PR head equals the integration head, current-head checks and review pass, and blocking findings and unresolved threads are zero. Preserve those same gates when recording `merge_status: "merged"`, then also record `pr_state: "merged"` and `merged_sha`.

Set `auto_merge_requested: true` only after GitHub accepts a squash auto-merge request for the exact current PR head, and record that SHA in `auto_merge_head_sha`. At request time this requires `merge_status: "ready"`, current-head CI and Codex review PASS, zero blocking findings and unresolved threads, repository auto-merge enabled under `configure_repository`, and unexpired `merge_pr` authorization whose mission scope covers the run and whose target is `pr:<full-PR-URL>` (or an explicitly run-wide `*`). Use `gh pr merge --auto --squash --match-head-commit <sha>` or an equivalent exact-head operation. After the PR reaches `merge_status: "merged"`, preserve the matching authorization evidence even when its `run_complete` boundary expires during final closeout. Any new push, changed integration head, canceled request, or closed-unmerged PR resets the fields to `false` and `null`.

A PR closed without merge records `pr_state: "closed"`, `merge_status: "closed_unmerged"`, and `merged_sha: null`. Do not leave a closed PR at `not_ready`, because terminal automation must stop or explicitly reopen it.

Create the final integration branch and PR from the parent checkout. In pull-request mode, record that same branch in both `integration.branch` and `landing.head_branch`; it must differ from `landing.base_branch`. Worker branches and worker worktrees do not push or open their own PRs unless the plan explicitly defines a separate landing target. The normal order is local verification and read-only diff review, push final branch, create Draft PR, pass CI, mark Ready, obtain GitHub review, resolve blocking threads, then enable SHA-bound auto-merge only with separate `merge_pr` authorization. Never push the base branch directly in pull-request mode.

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

When an action is authorized, scope is required and must cover the current run, mission, and target; use `"*"` only when the user's approval is explicitly run-wide. Encode exact targets as `worker:<id>`, `task:<id>`, `worktree:<absolute-path>`, `branch:<full-ref>`, `remote:<remote/ref>`, `pr:<full-PR-URL>`, or `environment:<name>` as appropriate. `expires_when` is exactly `wave_closed`, `run_complete`, or `explicit_revocation`; the coordinator evaluates that boundary against current RUN state. Treat an expired or nonmatching entry as unauthorized.

Treat `wave_closed` as a one-use grant. On `closed` or `superseded`, reset matching action entries to unauthorized and clear an overall wave-scoped execution grant before replacing `active_wave`; never carry that source into the next wave.

The parent may inspect state, validate manifests, and compute static conflict/parallel-eligibility analysis without implementation authorization. A launch-bound ready frontier or selected wave additionally requires canonical readiness, execution authorization, and every action needed by the launch path. Delegating even read-only analysis still requires the matching `spawn_subagents` or `create_user_owned_tasks` authorization.

Use these exact coordination enums:

- `worker_runtime`: `parent`, `subagent`, or `app_task`
- `workspace_mode`: `shared_checkout`, `parent_managed_worktree`, or `app_managed_worktree`
- `completion_channel`: `agent_result`, `thread_poll`, `report_file`, or `user_relay`

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

Worker phases are `leased`, `worker_running`, `worker_passed`, `blocked`, `worker_failed`, and `superseded`. An `attempt_log` entry records `attempt_id`, `mission_id`, nullable `task_id` and `lease_id`, `kind`, `result`, and an `evidence` array. Keep observations such as timestamps inside RUN for audit only; selection output remains timestamp-free.

For an enabled app-task nested policy, use `max_children` from 1 to 3 and a non-empty subset of the runtime `allowed_roles`. The app task stays the only writer. It normally launches eligible read-only lanes and records the resulting child activity—or an exact skip/unavailable reason—in WORKER_RESULT. When capability is initially unknown, keep the task at a no-production-edit handshake, record its tool/result observation, and then assign the explicit enabled or disabled policy. Older schema-v2 RUN files may omit both optional nested fields; once a RUN includes `runtime_capabilities.nested_subagents`, every app-task worker must include `nested_subagent_policy` and matching `subagent_activity`.

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
| Worker, mission-integration, batch, final E2E, and release gates exist | draft / PASS / BLOCKED | |
| Required user decisions and authorization gaps are surfaced | draft / PASS / BLOCKED | |

For plan-backed work, do not set the run to `running` until all required readiness rows pass, the plan revision/digest is current, `execution_authorized` is true, and every next action has its own authorization. In compact RUN-only mode, the parent may set `plan_readiness: "ready"` and `status: "running"` after the applicable sequential readiness checks pass and execution is explicitly authorized; keep plan identity null and do not claim plan validation, delegation, refinement, or wave selection.

## Mission And Task View

| Mission / task | Trace | Depends on | Phase | Worker gate | Integration gate | Evidence / commit |
|---|---|---|---|---|---|---|
| M1 | REQ-001 | none | queued | planned | planned | |
| M1/T01 | REQ-001 | none | queued | planned | n/a | |

## Active Wave View

| Wave | Fixed base | Selected missions | Deferred missions | Plan revision / digest |
|---|---|---|---|---|
| <wave> | <SHA> | <IDs> | <IDs + reason codes> | <revision / digest> |

The parent selects a ready, non-conflicting wave from validated canonical state, confirms the fixed base SHA, then records the proposal here. After each integration batch, observe the new head and recompute readiness and conflicts; do not reuse a stale proposal.

## Worker View

| Worker | Mission | Runtime | Workspace | Completion | Nested helpers | Base / head | Phase | Result source |
|---|---|---|---|---|---|---|---|---|
| <id> | M1 | parent / subagent / app_task | <mode> | <channel> | disabled / 1-3 read-only | <SHAs> | <phase> | <result/report/thread> |

For `app_task`, remember that the task is user-owned and automatic cross-task callbacks are not guaranteed. Use `thread_poll` or `user_relay` unless an event-capable integration is actually available. For `app_managed_worktree`, record platform retention behavior and create a durable branch or ref before unique work when authorized; cleanup controls cannot override platform-managed retention.

## Verification Dashboard

| Gate | Required | Pass signal | Status | Evidence |
|---|---|---|---|---|
| Build / static health | yes / no | <literal signal> | planned | |
| Focused behavior | yes / no | <literal signal> | planned | |
| API / data / permissions | yes / no | <literal signal> | planned | |
| Primary journey | yes / no | <literal signal> | planned | |
| UI / responsive / states | yes / no | <literal signal> | planned | |
| Console / network | yes / no | <literal signal> | planned | |
| Accessibility | yes / no | <literal signal> | planned | |
| Visual comparison | yes / no | <literal signal> | planned | |
| Performance / release | yes / no | <literal signal> | planned | |

Gate values: `planned`, `PASS`, `FAIL`, `BLOCKED`, `UNVALIDATED`.

## UI Evidence

Include only when UI evidence is required or optional.

| Route / flow | Viewport | State | Browser result | Console / network | A11y | Visual evidence | Status |
|---|---|---|---|---|---|---|---|
| <route> | <size> | ready / loading / empty / error / disabled / permission / long-running | <result> | <result> | <result> | <path> | planned |

Store only real binary artifacts under `docs/goal/evidence/`. Do not create empty evidence folders.

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
```
