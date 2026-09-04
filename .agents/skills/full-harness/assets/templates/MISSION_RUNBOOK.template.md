# Run: <feature or product slice>

Use this template as `docs/goal/RUN.md` only after the parent-only, read-only `System Review And Route` classifies the work as large and routes it into the managed graph. Small direct work does not instantiate this file. Keep mutable authorization, observed runtime facts, mission/task phases, worker state, verification, blockers, and closeout here; keep static definitions in `PLAN.md`. A large managed route executes one mission at a time when it is sequential; this template is not a new authoring route for legacy compact state.

All new managed work uses PLAN schema v6 plus RUN schema v11 (RUN-v11). Older RUN schemas remain readable through the compatibility path. Legacy compact RUN-only files remain readable and validatable through the compatibility path, but cannot authorize new managed execution or enter the current graph. A large no-agent route is still PLAN/RUN-backed: it follows `references/execution-state-model.md`'s Sequential Parent Route, keeping the PLAN mission as `executor: runtime_worker` with RUN's parent-owned binding recorded solely for lease/state validation.

The System Review And Route stage completes before this file exists. It is parent-only and read-only: no task-specific skill, adapter/model selection, worker preflight, PLAN/RUN creation, external runtime, or worker launch occurs during that stage.

Before the first selection, fill `observed.captured_at` and the null observations from live `git status` / `git rev-parse` on the resolved integration branch. The validator does not require the snapshot, but the selector will defer every state-mutating mission or lifecycle node under `parent_state_unreconciled` or `batch_base_missing` until it is filled. It returns `dispatchable_nodes` and `deferred_nodes`; these are dispatch-time reasons, not a readiness shortcut. Set capacity from observed facts, even when the derived `execution_route` is `managed_sequential`. On an observed Codex route that may select two writers, record the complete eight-entry `runtime_adapter.capability_probe`; a provably sequential route records only the facts needed to prove its selected driver. For every PLAN review `required_tools` entry, replace the generic `reviewer_tools` placeholder with a fresh reviewer-session probe from the exact selected provider and driver. Never mark a parent-only probe available. Never run parallel writers in `shared_checkout`.

A managed-sequential route is selected when fewer than two safe write missions are actually selected. It avoids fan-out-only ceremony: no fan-out claim, no mandatory `tasks.md` view, no true cross-mission batch gate for one mission, and no inventory of unused parallel drivers. It still proves the selected `runtime_driver`, uses an isolated writer, checks authorization and exact scope/head bindings, and requires the same exact-head review and final gates. Two or more selected safe writers produce `parallel_graph`; this derived route is separate from the runtime transport driver and is never persisted as a PLAN/RUN schema field. New RUN files start at `mode: "local_only"`; only an explicit remote outcome moves to `integration_push`.

## Harness Run State

```json
{
  "harness_run": {
    "schema_version": 11,
    "run_id": "RUN-<stable-id>",
    "plan": {
      "id": "PLAN-<stable-id>",
      "revision": 1,
      "digest_sha256": "a3103eaad4e2a1d77e7309e108b2ae98fa48eaee421de62cf980e515df9f376b"
    },
    "status": "draft",
    "intent": "plan-only",
    "plan_readiness": "draft",
    "execution_authorized": false,
    "execution_authorization_source": null,
    "execution_authorization_scope": null,
    "control": {
      "desired_state": "running",
      "requested_at": null,
      "source": null,
      "acknowledged_at": null
    },
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
      "max_parallel_workers": 1,
      "runtime_adapter": {
        "provider": "generic",
        "available_drivers": ["sequential_parent"],
        "detection_source": "fallback",
        "version_gate": {
          "host_version": null,
          "minimum_host_version": null,
          "harness_version": null,
          "required_harness_version": "0.21.12",
          "session_id": null,
          "loaded_contract_digest": null,
          "installed_contract_digest": null,
          "status": "unobserved",
          "evidence": "Runtime and Harness versions have not been observed yet"
        }
      },
      "reviewer_tools": {
        "chrome_devtools": {
          "status": "unobserved",
          "provider": "generic",
          "driver": "sequential_parent",
          "surface": "none",
          "probe_scope": "unobserved",
          "session_id": null,
          "evidence": "No fresh reviewer session has probed Chrome DevTools yet"
        }
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
        "available_worker_slots": 1,
        "isolation_capacity": 1,
        "completion_channel_available": true
      }
    },
    "integration": {
      "branch": "refs/heads/<exact-run-branch>",
      "retention": "ephemeral",
      "batch_base_sha": null,
      "integration_head_sha": null,
      "prior_head_shas": [],
      "coordination_paths": ["docs/goal/PLAN.md", "docs/goal/RUN.md", "docs/goal/DECISIONS.md"]
    },
    "batch_gate_results": [],
    "final_gate_results": [
      {"id": "final-check", "status": "planned", "head_sha": null, "evidence": []},
      {"id": "final-closeout", "status": "planned", "head_sha": null, "evidence": []}
    ],
    "ui_evidence": [],
    "landing": {
      "mode": "local_only",
      "remote": "origin",
      "pushed_head_sha": null,
      "continuity": {
        "status": "planned",
        "branch_ref": "refs/heads/<exact-run-branch>",
        "head_sha": null,
        "reason": "Keep the reviewed run branch so the user can read it and land it"
      }
    },
    "graph_state": {
      "graph_revision": 1,
      "node_states": {
        "N-M1": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-M1-REVIEW": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-FINAL-GATE": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-CLOSEOUT-GATE": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []}
      },
      "edge_states": {
        "E-M1-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M1-REVIEW-FINAL": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
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
    "closed_waves": [],
    "workers": [],
    "review_workers": [],
    "review_lineages": {
      "REVIEW-M1": {
        "review_type": "backend_code",
        "mission_ids": ["M1"],
        "base_allowance": 2,
        "additional_allowance": 0,
        "consumed_attempts": 0,
        "failure_families": [],
        "owner_decisions": []
      }
    },
    "workflow_runs": [],
    "verifier_executions": [],
    "runtime_metrics": null,
    "attempt_log": []
  }
}
```

The exact fenced JSON block is canonical; Markdown tables are non-canonical. Update JSON first. `tasks.md` is an optional on-demand human view derived from `RUN.md`, never a second source of truth. The selector's top-level `execution_route` is output-only and must not be copied into PLAN or RUN.

Use `scripts/harness_transition.py` for `pause`, `resume`, `cancel`, `record-observation`, `accept-wave`, `lease-worker`, `record-integration`, `reconcile-interrupted`, `reconcile-interrupted-reviews`, `reserve-review-dispatch` (with `--packet-out` to render the reviewer packet in the same command), `record-review-attempt`, `grant-review-attempts`, `skip-integration-review`, `acquire-run-lock`, `release-run-lock`, `heartbeat-run-lock`, and `watchdog`. Reserve every managed review after selection and before launch; accept only the matching reserved result. These transitions validate the full pair and replace RUN atomically. A resume fails while a worker is still recorded active. Use `scripts/render_review_packet.py` to produce the exact-head reviewer handoff with a bounded diff.

RUN schema v11 has 12 independent action entries. Keep every entry false unless an explicit user instruction authorizes the exact action and its target. `push` remains separate, exact-branch/head-bound, and remote intent is never implied by local execution; a separate explicit remote intent is required. `integration_push` is the remote end state and `landing.pushed_head_sha` records the verified branch head. A separate explicit remote instruction is required before moving there; keep the phrase separate remote intent in the checkpoint. Legacy RUN schemas remain readable with their historical ledger and result shapes; do not copy their weaker fields into a new run. RUN-v11 workers never delegate; all reviews are parent-dispatched graph nodes. The dynamic_workflow and app_threads adapters are transport choices, not execution routes; their typed `mission_write` profile, `EnterWorktree` handoff, and task creation `model`/`thinking` fields remain adapter-specific. App task creation passes the task creation `model` and `thinking` values only after the parent proves the route.

When the selected driver is `sequential_parent`, follow `references/execution-state-model.md`'s Sequential Parent Route: the PLAN mission keeps `executor: runtime_worker`, and the route blocks rather than writing in `shared_checkout` when its worktree is unavailable or unauthorized.

For a managed-sequential route, prove the chosen driver and exact host axes, allocate one isolated writer, bind the lease to PLAN revision/digest and batch base, validate changed files against write/deny scope, retain commits and observed head, and run the direct singleton pre-integration review before integration. The absence of a cross-mission batch gate does not remove any of those checks. If the selector returns `parallel_graph`, follow `references/parallel-mission-selection.md` and record only real cross-mission checks that apply. A focused verifier may use `session_exact` only for a clean, cache-safe command with a repository-external cache; broad regression runs after exact-SHA code review and repair loops converge. Record evidence against the exact head with lowercase SHA-256 values under `docs/goal/evidence/`; for RUN-v11 UI proof, read and safely decode each artifact from its recorded accepted Git commit/ref before comparing `artifact_sha256`, while RUN-v9 remains working-tree compatible. UI proof uses breakpoint-by-state artifacts when applicable.

## Goal And Checkpoint

```text
Objective:
Canonical PLAN path:
Current mission / task:
Derived execution route / transport driver:
Last verified integrated result:
Remaining:
Blocked / waiting authorization:
Next action:
```

## Plan Readiness View

For plan-backed work, do not set the run to `running` until static validation passes, the plan revision/digest is current, execution is explicitly authorized, and every next action has its own authorization. `plan_readiness` in the JSON manifest above is the machine gate; do not duplicate it as a hand-filled table. `tasks.md` may be created later if the human view is useful.

## Mission And Task View

The mission/task listing is intentionally omitted here for the single-mission example. If a human view is useful, render it on demand with `scripts/render_tasks_view.py` (see `assets/templates/TASKS.template.md`); `RUN.md` remains authoritative.

## Verification Dashboard

Gate layers, their scope, and their head bindings are defined once in `references/verification-gates.md`. Do not restate them here.

## UX Evidence

Include only when Builder UX Direction or a `UX-*` trace exists. Builder approval proves direction conformance only; usability evidence remains a separate gate.

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

Every commit this run lands stays atomic per `commit-convention.md` — one verified task outcome, one repair, one mission integration, or one bookkeeping change per commit; the closeout itself never lands a mixed catch-all commit.
