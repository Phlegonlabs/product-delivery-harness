# Run: <feature or product slice>

Use this template as `docs/goal/RUN.md` only after the parent-only, read-only `System Review And Route` classifies the work as large and routes it into the managed graph (or the user explicitly requests managed planning after that route). Small direct work does not instantiate this file. Keep mutable authorization, observed runtime facts, mission/task phases, wave selection, worker state, verification, blockers, and closeout here. Keep static plan definitions in `PLAN.md`.

All new managed work uses PLAN schema v5 plus RUN schema v10; do not author a compact RUN-only replacement or copy this manifest while nulling its PLAN fields. Legacy compact RUN-only files remain readable and validatable through the shared compatibility path for migration and closeout, but they cannot authorize new managed execution, enter the current graph, or be extended from this template. A large no-agent route is still PLAN/RUN-backed: its PLAN mission remains `executor: runtime_worker`, and RUN records a parent-owned executor/worker binding solely for lease/state validation with `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result`. This is not a delegated or spawned worker, requires no `spawn_subagents`, and blocks if the required parent-managed worktree is unavailable or unauthorized.

The System Review And Route stage completes before this file exists. It is parent-only and read-only: no task-specific skill, adapter/model selection, worker preflight, PLAN/RUN creation, external runtime, or worker launch occurs during that stage.

**Before the first selection, fill in what this template ships as `null`.** `observed.captured_at`, the four required `observed.git` fields, the optional `observed.git.default_branch` safety fact when available, and `integration.batch_base_sha` must come from a live `git status` / `git rev-parse` on the resolved integration branch. The validator does not require them — a RUN that leaves them null still reports `PASS` — but `select_ready_nodes.py` will then return empty `dispatchable_nodes`, with every mission node in `deferred_nodes` under `parent_state_unreconciled` or `batch_base_missing`. Check those two keys, not `ready_frontier`: these are dispatch-time reasons, so the frontier can still list the nodes while none of them is launchable. Once `status` is `running`, the Resume Reconciliation Gate defers every node and `ready_frontier` empties as well. A green validator next to empty `dispatchable_nodes` is what an unfilled snapshot looks like, not a planning error.

Set `max_parallel_workers`, `available_worker_slots`, and `isolation_capacity` from what you actually observed. The values shipped here are a starting point, not a limit to copy: leaving them at `1` serializes a genuinely parallel frontier and the deferral reads only as `over_budget`.

For plan-backed multi-mission execution, replace the generic fallback runtime snapshot before the first production edit. Proactively record every observed driver independently from authorization, set the configured write-worker maximum generously high unless an explicit user or runtime limit applies, and run deterministic selection immediately after Plan Readiness. Resolve the target repository's branch model from its instructions before filling this template. Preserve those branches when defined; otherwise use the template's main-only defaults, where `main` is the default branch and the run's own ephemeral `codex/<short-name>` branch, cut from `main`, is its integration branch. Set `integration.retention` to `persistent` only when repository instructions define a genuine long-lived integration branch. Create mission worktrees from the resolved current integration SHA, require one exact-head read-only review before each integration, and merge passing heads serially into the resolved integration branch. Ordinary PRD, UI, and feature work starts `local_only` and remains local unless the user explicitly requests a remote outcome. With that separate remote intent and an exact branch/head grant, it may move to `integration_push` once the verified integration head is pushed to the integration branch, recording that head in `landing.pushed_head_sha`. Landing that branch on the default branch is the user's own step, done outside this harness. Do not hide a capability or silently downgrade because authorization is missing. Never run parallel writers in `shared_checkout`.

When replacing the fallback with an observed Codex adapter, also add the complete eight-entry `runtime_adapter.capability_probe` defined in `references/execution-state-model.md`. Do not move the run to `ready` or `running` while a probe entry is missing or `unobserved`. The validator derives `app_threads` and `subagents` from that probe and requires the declared driver list to match, so proven App Threads cannot be silently replaced by direct subagents.

## Harness Run State

```json
{
  "harness_run": {
    "schema_version": 10,
    "run_id": "RUN-<stable-id>",
    "plan": {
      "id": "PLAN-<stable-id>",
      "revision": 1,
      "digest_sha256": "f23ffd77a9abbb4bf8c89ae654823c00cfcf4cee755bca64daea938b06a7aaeb"
    },
    "status": "draft",
    "intent": "plan-only",
    "plan_readiness": "draft",
    "execution_authorized": false,
    "execution_authorization_source": null,
    "execution_authorization_scope": null,
    "authorizations": {
      "invoke_external_runtime": {"authorized": false, "source": null},
      "spawn_subagents": {"authorized": false, "source": null},
      "create_user_owned_tasks": {"authorized": false, "source": null},
      "create_local_worktrees": {"authorized": false, "source": null},
      "create_app_managed_worktrees": {"authorized": false, "source": null},
      "create_local_branches": {"authorized": false, "source": null},
      "create_local_commits": {"authorized": false, "source": null},
      "integrate_locally": {"authorized": false, "source": null},
      "push": {"authorized": false, "source": null},
      "archive_worker_tasks": {"authorized": false, "source": null},
      "remove_worktrees": {"authorized": false, "source": null},
      "delete_branches": {"authorized": false, "source": null}
    },
    "runtime_capabilities": {
      "worker_runtime": "parent",
      "workspace_mode": "parent_managed_worktree",
      "completion_channel": "agent_result",
      "max_parallel_workers": 8,
      "runtime_adapter": {
        "provider": "generic",
        "available_drivers": ["sequential_parent"],
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
        "default_branch": null,
        "worktrees": []
      },
      "runtime": {
        "available_worker_slots": 8,
        "isolation_capacity": 8,
        "completion_channel_available": true
      }
    },
    "integration": {
      "branch": "refs/heads/codex/<short-name>",
      "retention": "ephemeral",
      "batch_base_sha": null,
      "integration_head_sha": null,
      "prior_head_shas": []
    },
    "batch_gate_results": [{"id": "batch-cross-mission", "status": "planned", "head_sha": null, "evidence": []}],
    "final_gate_results": [
      {"id": "e2e-primary-journey", "status": "planned", "head_sha": null, "evidence": []},
      {"id": "final-closeout", "status": "planned", "head_sha": null, "evidence": []}
    ],
    "ui_evidence": [],
    "landing": {
      "mode": "local_only",
      "remote": "origin",
      "pushed_head_sha": null,
      "continuity": {
        "status": "planned",
        "branch_ref": "refs/heads/codex/<short-name>",
        "head_sha": null,
        "reason": "Keep the reviewed run branch so the user can read it and land it"
      }
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
        },
        "N-FRONTEND-REVIEW": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        },
        "N-FINAL-GATE": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        },
        "N-VISUAL-REVIEW": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        },
        "N-VISUAL-REPAIR": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        },
        "N-VISUAL-REPAIR-CODE-REVIEW": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        },
        "N-CLOSEOUT-GATE": {
          "phase": "dormant",
          "attempts": 0,
          "last_attempt_id": null,
          "last_outcome": null,
          "bound_worker_id": null,
          "blockers": []
        }
      },
      "edge_states": {
        "E-M1-FRONTEND-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-FRONTEND-VISUAL-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M1-VISUAL-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-REVIEW-REPAIR": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-REPAIR-CODE-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-REPAIR-REREVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-FINAL-GATE": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-FINAL-CLOSEOUT": {"status": "dormant", "traversals": 0, "source_attempt_id": null}
      }
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
        "prior_head_shas": [],
        "integration_gate": "planned",
        "integrated_sha": null,
        "blockers": [],
        "report_path": null
      },
      "M3": {
        "phase": "queued",
        "lease_id": null,
        "lease_plan_revision": null,
        "lease_plan_digest_sha256": null,
        "worker_id": null,
        "base_sha": null,
        "head_sha": null,
        "prior_head_shas": [],
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
      },
      "M3/T01": {
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
    "closed_waves": [],
    "workers": [],
    "review_workers": [],
    "workflow_runs": [],
    "verifier_executions": [],
    "attempt_log": []
  }
}
```

The exact fenced JSON block above is the canonical run state. Scripts read this block only; Markdown tables later in this document are non-canonical human views. Update the JSON first, keep it valid, and never infer authorization from plan readiness, a template, or a Goal prompt.

### RUN Schema Version

New RUN files always use RUN schema v10 (see `SKILL.md`'s Default Runtime And Wave Policy). Older RUN schemas remain readable; their own recorded `schema_version` decides which fields apply.

RUN schema v10 has 12 independent action entries. Keep every entry false unless an explicit user instruction authorizes that exact action. Every authorized execution scope and action scope binds `run_id`, current `plan_revision`, current `plan_digest_sha256`, mission IDs, and the lifecycle boundary; action scopes also bind exact targets. A `wave_closed` scope additionally binds the current `active_wave.wave_id` and `active_wave.batch_base_sha`; those values must be renewed for every wave. Append each closed or superseded pair to the durable `closed_waves` list before re-proposing anything, and never reuse a pair already listed there. A PLAN revision or digest change invalidates the grant. Each action accepts one target kind: `runtime:` for `invoke_external_runtime`, `worker:` for `spawn_subagents`, `task:` for `create_user_owned_tasks` and `archive_worker_tasks`, `worktree:` for the two worktree-creation actions and `remove_worktrees`, and `branch:` for `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, and `delete_branches`. `push` also records `authorized_head_sha` and cannot use a `*` target.

`graph_state` is the canonical routing record for PLAN-v5 nodes and edges. Initialize one state for every declared node and edge. For pre-integration review, `fix_required` returns to the original mission task/thread and its existing worktree; after the focused verifier passes on a changed head, re-arm the same review node with a new attempt ID. Do not create a repair mission or replacement worktree for this loop. Post-integration review may traverse a bounded repair route. That repair mission receives its own direct singleton exact-head review before integration, then returns to the post-integration review before a deterministic final gate. Every retry preserves prior evidence and rechecks authorization.

New RUN files start at `mode: "local_only"` because nothing has been pushed yet. RUN v10 has two modes:

- `local_only` — nothing left the machine. No pushed head.
- `integration_push` — the explicit remote end state, and the point at which a remote run is complete. The verified integration head has been pushed to the run's own branch and `landing.pushed_head_sha` records it. Record explicit remote intent plus the `push` authorization with its exact branch target and `authorized_head_sha` before moving here.

`integration.branch` is the only branch field. The push target is built from it, so the target the landing gate checks and the target the ledger grants cannot drift apart. Resolve it from target-repository instructions; the template's value applies only when the repository defines no other model. See `references/execution-state-model.md`'s Landing State for the mode and continuity rules.

`push` requires explicit remote intent plus one exact resolved integration-branch target and the current `integration.integration_head_sha` in `authorized_head_sha`. It is refused when its target or the run's `integration.branch` resolves to literal `main`; when `observed.git.default_branch` is present, that resolved default branch is refused too. A current v10 push fails closed when the default-branch observation is unknown; this does not block unrelated local actions.

See `references/execution-state-model.md`'s closeout condition table for the full `status: complete` requirement. Every applicable condition must hold, with retained RUN-v10 verifier, batch, final, and UI evidence bound to the current head.

Create mission worktrees from the current resolved integration head. Before each parent integration, require at least one read-only review bound to the exact worktree head; repair findings in that worktree and review the changed head again. Integrate passing worktrees into the branch named by `integration.branch`. After final verification, preserve continuity at the exact integration head so the user can read that branch and land it. Worker branches and worktrees never become the default branch.

An authorized action may add `scope` and `expires_when` beside `authorized`/`source`:

```json
{
  "authorized": true,
  "source": "<explicit user statement reference>",
  "scope": {
    "run_id": "RUN-<stable-id>",
    "plan_revision": 1,
    "plan_digest_sha256": "<lowercase SHA-256 of the current semantic PLAN>",
    "mission_ids": [
      "M1"
    ],
    "targets": [
      "<exact worker, task, worktree, branch, or runtime target, or * when explicitly run-wide>"
    ]
  },
  "expires_when": "run_complete"
}
```

An execution-intent instruction such as "build it", "implement this", "fix it", or "refactor it" covers only the applicable local route actions: runtime/workspace setup, branch creation, commits, and local integration. It does not authorize a remote push. A separate explicit remote instruction such as "push" or "publish" must authorize `push` for exactly one resolved integration branch and the current integration head; `local_only` remains the default. Outer app-task workers never delegate, so that route excludes `spawn_subagents`; parent-dispatched direct sibling workers or reviewers use the parent's top-level grant. `archive_worker_tasks`, `remove_worktrees`, and `delete_branches` stay separate.

`execution_authorization_scope` at the top of the RUN is a different shape from the per-action `scope` above, and copying the action shape is the usual mistake. It carries `expires_when` **inside** the object and takes **no** `targets` key:

```json
"execution_authorization_scope": {
  "run_id": "RUN-<stable-id>",
  "plan_revision": 1,
  "plan_digest_sha256": "<lowercase SHA-256 of the current semantic PLAN>",
  "mission_ids": ["M1"],
  "expires_when": "run_complete"
}
```

See `references/execution-state-model.md`'s Authorization Action Ledger for the exact target encoding, the `expires_when` values and their `wave_closed` reset, and which read-only analysis the parent may perform before a launch-bound wave adds its own authorization requirements.

For automatic app-task fan-out, the selector emits one `dispatchable_nodes` entry per selected mission. Outer selection does not require or preauthorize `spawn_subagents` because the app task cannot delegate. After accepting the wave, the parent allocates workers, leases, and branches/refs; verifies the explicit pre-allocation `*` grant for app-assigned task/worktree identities and every already-known target under `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, and `create_local_commits`; verifies each worktree's repository, branch/ref, exact base, and clean status; creates one real Codex worktree thread per directive; and writes the returned thread/client identity into `workers[].task_thread_id`. The directive itself is neither authorization nor proof of launch. If the user requested left-sidebar tasks and project lookup, thread creation, worktree setup, follow-up messaging, or polling is unavailable, leave the worker unlaunched and report the blocked topology; never silently replace it with coordinator-owned subagents or sequential parent implementation. If that topology was not requested, a sequential parent route requires its parent-owned `runtime_worker` binding and parent-managed worktree, and blocks when that worktree is unavailable or unauthorized. The parent dispatches every independent explorer and reviewer as a sibling graph node.

For graph workers, copy the selector's complete `runtime_binding` into the allocated mission `workers[]` record or read-only verifier `review_workers[]` record. A review worker also binds node ID, attempt ID, graph revision, review path, and the exact current integrated SHA; it has no mission lease, writable worktree, branch, or commit authority. For Codex app tasks, pass non-null `model` and `reasoning_effort` as task creation `model` and `thinking`; omit null values so the host default remains explicit. For Claude Code, pass each node's own `model` (and non-null `reasoning_effort` as `effort`) into that node's own `agent()` call inside the Dynamic Workflow script; a single wave may mix models and reasoning efforts freely since each node's call carries its own. The destination host validates the exact pair at launch.

See `references/execution-state-model.md`'s Runtime Capability Axes for the `worker_runtime`, `workspace_mode`, and `completion_channel` enums, the `runtime_adapter`, `permission_boundary`, and `nested_subagents` field rules, and the host-provider match a node needs before the parent may bind it. Its Canonical Mission Phases and Canonical Task Phases sections own the mission, task, worker, and active-wave phase values; `worker_passed` never satisfies a downstream mission dependency.

When the selected driver is `dynamic_workflow`, use `subagent` + `parent_managed_worktree` + `agent_result`, omit `nested_subagents`, and treat the accepted wave as one flat workflow run. The parent allocates one worktree/branch/lease per mission, then invokes the Claude Code `Workflow` tool with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and the accepted directives supplied as structured `args`. Launch only after `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, and `create_local_commits` cover the selected missions and allocated targets. A workflow cannot wait for human sign-off mid-run; return a refinement request and close the wave when a contract or authorization decision is needed.

When the selected driver is `sequential_parent`, keep the PLAN mission's `executor: runtime_worker` and use `worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, and `completion_channel: agent_result`. RUN records a parent-owned executor/worker binding solely for lease/state validation; it is not a delegated or spawned worker and does not require `spawn_subagents`. The parent executes one mission at a time in the required parent-managed worktree, keeps the same PLAN/RUN graph and exact-head review/integration gates, and blocks if that worktree is unavailable or unauthorized rather than writing in `shared_checkout`. This is the required large no-agent path.

`CLAUDE_DYNAMIC_WORKFLOW.template.js` only launches flat mission workers: it has no `node_kind`, no `tool_profile` validation, and no `EnterWorktree` call per node. A wave that mixes mission and review graph nodes, records a `tool_profile` (`mission_write`, `code_review_readonly`, `visual_review_readonly`), or needs each node instructed to call `EnterWorktree` before its own reads/writes must instead use `assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js`, passing `tool_profile` and the typed `nodes[]` array (each with `node_kind: "mission"` or `"review"`) as structured `args`. Use the flat script only for single-role, all-mission waves with no read-only review nodes.

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
  "task_thread_id": null,
  "worktree_path": "<path or null>",
  "branch_ref": "<branch/ref or null>",
  "report_path": null,
  "phase": "leased",
  "worker_head_sha": null
}
```

Leave model and effort null unless the user explicitly selected them in the PLAN provider options. During allocation, `worktree_path` and `branch_ref` may be null. Fill them only after the runtime returns and the parent independently verifies them. `worker_head_sha` stays null until the parent verifies the reported commit.

RUN-v10 workers never delegate. Omit `nested_subagent_policy`, or record it explicitly with `enabled: false`, `max_children: 0`, empty roles, `read_only`, and `agent_result` when an app-task surface needs an explicit capability record. An enabled policy is invalid. Every current worker result reports `subagent_activity.status: "not_applicable"` with a concrete reason and empty `children`; all reviews are parent-dispatched graph nodes. Legacy RUN-v6 through v9 nested-policy behavior remains readable only.

Worker phases are `leased`, `worker_running`, `worker_passed`, `blocked`, `worker_failed`, and `superseded`. An `attempt_log` entry records `attempt_id`, nullable `mission_id`, `task_id` and `lease_id`, `kind`, `result`, and an `evidence` array. A final-gate or closeout-gate attempt belongs to no mission, so its `mission_id` is null rather than attributed to an arbitrary one. Keep observations such as timestamps inside RUN for audit only; selection output remains timestamp-free.

Each `review_workers` entry uses this exact read-only shape:

```json
{
  "worker_id": "RW1",
  "node_id": "N-FRONTEND-REVIEW",
  "attempt_id": "ATT-REVIEW-1",
  "plan_revision": 1,
  "plan_digest_sha256": "<sha256>",
  "graph_revision": 1,
  "reviewed_sha": "<direct singleton pre-integration worktree or integrated SHA>",
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
  "phase": "worker_running",
  "outcome": "pass",
  "findings": []
}
```

The matching successful node result puts exactly `reviewed_sha`, `findings`, and `evidence_summary` inside `worker_result`. The reviewed SHA must match the active review worker.

RUN v10 keeps `prior_head_shas` on each mission state and on `integration`. Before replacing a head that has review evidence, the parent appends that exact old head to the matching list, then records the new head. These lists are append-only provenance, contain only superseded heads, and never accept a worker-provided SHA without the parent's independent Git check. A retained `fix_required` correction review may use the matching integration history, but a PASS batch review must bind the current integration head. Direct singleton pre-integration history may remain long enough for the selector to detect the stale review and re-arm it.

Graph RUN schemas v8 through v10 may include `workflow_runs` to bind canonical node attempts to actual outer Claude Code Workflow executions. Invoke the Claude Code `Workflow` tool with the canonical PLAN, RUN, and immutable wave request; the parent revalidates current state, authorization, worker bindings, and checkout HEAD before launch. Add an entry only when the runtime returns a real non-empty workflow run ID; never invent one. Running entries bind every node ID to its active attempt ID and must match the current plan, graph, runtime policy, and batch base. One entry may cover node IDs with different resolved models and reasoning efforts; each node's own `model`/`reasoning_effort` still lives on its `workers[]`/`review_workers[]` `runtime_binding`, not on the `workflow_runs` entry. Completed historical entries remain as evidence after later graph revisions and do not require their superseded nodes to remain in the current PLAN.

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

Tool profiles are `mission_write`, `code_review_readonly`, and `visual_review_readonly`. These profiles are carried only by `assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js` (see above), not by the flat `CLAUDE_DYNAMIC_WORKFLOW.template.js`. A profile selects which node kinds the wave admits and which instructions go into each prompt; it is not a tool allowlist, and neither script applies one. Group Claude Graph Workflow nodes by tool profile only; model and reasoning effort travel with each node's own `agent()` call, so one wave may mix them freely. Mission and review waves require `EnterWorktree` so each worker enters its exact assigned checkout before repository reads. Both review prompts instruct read-only behavior; that is prompt text plus result validation, not a permission boundary. Visual review consumes retained screenshots or other existing evidence until a read-only browser tool is explicitly vetted.

RUN-v10 workers never delegate. Omit `nested_subagent_policy`, or set it explicitly to disabled with zero children and empty roles; an enabled policy is invalid. Legacy RUN-v6/v7/v8/v9 app-task policies retain their historical validation behavior only. Before RUN-v10 execution authorization, every writable mission must have a direct dependency to a preintegration-stage runtime review node whose `mission_ids` contains only that mission and whose `allowed_outcomes` includes `pass`; a multi-mission or integration-stage review cannot replace it. When several direct pre-integration review nodes cover the same mission, they use distinct review-worker IDs and every current-head node and worker must reconcile to PASS; one active current-head `fix_required` blocks integration. Historical or superseded attempts remain in RUN for audit and do not substitute for a current PASS. Before the mission transitions to `integrating`, the parent runs the read-only review and retains a `worker_passed` `review_workers[]` PASS whose review node covers the mission and whose `reviewed_sha` equals the current worktree head. Every retained current or historical review attempt must bind its `reviewed_sha` to a current eligible head or an explicit mission `prior_head_shas` entry; a retained `fix_required` integration review may instead bind to an explicit integration `prior_head_shas` entry. After serial mission integration, integration-stage review nodes use fresh reviewer identities and bind to the exact current integration head. Only after those reviewers pass does the one broad final validation run on the fixed candidate SHA.

Use these exact array entry shapes:

```json
{
  "deferred_mission": {
    "mission_id": "M3",
    "reason_codes": [
      "dependency_not_integrated"
    ],
    "conflicts_with": []
  },
  "conflict_edge": {
    "left": "M1",
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

## Retained Verifier Executions

RUN-v10 `verifier_executions` is append-only and parent-owned. A worker may return candidate command results, but it never appends or edits canonical RUN state. The parent resolves the PLAN verifier, validates its mission/task/attempt/lease association, normalizes the verifier and context, verifies the key document and hashes, then appends one immutable entry. Never replace a failed execution with a later pass; retain both under unique `execution_id` values. A retained failed record never satisfies PASS: only a separate current-head passing execution may satisfy the verifier.

Never hand-author a `verifier_executions` entry. Copy `run_verifier()`'s returned `verifier`, `context`, and `key_document` unchanged: `key_document` carries 26 keys and `context` 16, and `execution_key` is a SHA-256 over the canonical encoding of the whole `key_document`, so any edit invalidates it. The block below is abridged to show the shape, not a fillable form.

```json
{
  "execution_id": "VX-001",
  "verifier_id": "task-focused",
  "layer": "task",
  "mission_id": "M1",
  "task_id": "M1/T01",
  "attempt_id": "ATT-M1-T01-1",
  "lease_id": "<retained lease id>",
  "protocol": "harness-verifier-execution-v1",
  "execution_key": "<lowercase SHA-256 of key_document>",
  "evidence_key": "<retained evidence identity>",
  "key_document": {
    "<abridged - 26 keys>": "copy run_verifier()'s returned key_document verbatim",
    "run_id": "RUN-<stable-id>",
    "plan_revision": 1,
    "plan_digest_sha256": "<current PLAN digest>",
    "verifier_id": "task-focused",
    "head_sha": "<exact verified head>"
  },
  "verifier": {
    "id": "task-focused",
    "cwd": ".",
    "argv": ["<runner>", "<task-argument>"],
    "pass_signal": "exit 0"
  },
  "context": {
    "run_id": "RUN-<stable-id>",
    "plan_revision": 1,
    "plan_digest_sha256": "<current PLAN digest>",
    "head_sha": "<exact verified head>"
  },
  "status": "PASS",
  "exit_code": 0,
  "cache_status": "bypassed",
  "cache_reason": "Verifier is not eligible for reuse",
  "duration_ms": 0,
  "metrics": {"executed": 1, "reused": 0},
  "stdout_sha256": "<lowercase SHA-256>",
  "stderr_sha256": "<lowercase SHA-256>",
  "evidence_paths": []
}
```

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
| Worker, exact-head pre-integration review, mission-integration, batch, and final E2E gates exist; E2E command, current-head check, evidence, environment, and smoke disposition are named | draft / PASS / BLOCKED | |
| Every mission's write scope is covered by a review-type node (`backend_code`/`frontend_code`/`visual`), independent of `landing.mode` | draft / PASS / BLOCKED / n/a | |
| Required user decisions and authorization gaps are surfaced | draft / PASS / BLOCKED | |
| Observed Codex capability probe is complete and matches the declared driver priority | draft / PASS / BLOCKED / n/a | |

For plan-backed work, do not set the run to `running` until all required readiness rows pass, the plan revision/digest is current, `execution_authorized` is true, and every next action has its own authorization. Legacy compact RUN-only files may be read and validated for compatibility, but they are not a new authoring route: do not set a fresh run's plan identity to null or use compact state to claim current plan validation, delegation, refinement, or wave selection. Create PLAN-v5/RUN-v10 before managed execution; a large no-agent run remains `sequential_parent` inside that pair.

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
| Worktree review | at least one independent read-only review before integration | exact current worktree head |
| Mission integration | that mission's integration surface after serial integration | integration head |
| Batch | true cross-mission and shared-contract checks | post-wave integration head |
| Final / current-head | broad regression, browser E2E, and UI evidence after review repairs converge | exact accepted integration head |

For any `session_exact` verifier execution, record the execution/evidence key, `executed` or `reused`, duration, and miss/bypass reason in evidence. Reuse is valid only for an opted-in deterministic local `exit 0` command with a clean checkout, repository-external session cache, and exact immutable inputs. Parent-observed files decide verifier applicability; worker claims do not.

| Layer | Considered | Selected | Executed | Reused | Not applicable | Duration / notes |
|---|---:|---:|---:|---:|---:|---|
| Task / worker | 0 | 0 | 0 | 0 | 0 | |
| Worktree review | 0 | 0 | 0 | 0 | 0 | |
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
| Performance | yes / no | <literal signal> | planned | |

Gate values: `planned`, `PASS`, `FAIL`, `BLOCKED`, `UNVALIDATED`.

### Automated E2E And Smoke Reuse

| E2E command | CI check | Environment | Covered journeys | Head SHA | Retained evidence | Status |
|---|---|---|---|---|---|---|
| `<e2e-command>` | `<check-name>` | <local / preview / staging / deployed — deployed only for a pre-existing deployment outside the run> | <journey IDs> | <SHA> | <artifact / trace / CI log> | planned |

| Proposed manual smoke | Same journey and equivalent environment covered | Disposition | Reason / uncovered risk |
|---|---|---|---|
| <smoke> | yes / no | `required` / `not required - covered by current-head E2E` | <reason> |

Use the replacement disposition only after the automated E2E passes on the exact current head. Visual checks and external-integration smoke remain required when their environment or assertions are not equivalent.

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
```
