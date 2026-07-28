# Run: <feature or product slice>

Use this template as `docs/goal/RUN.md` only after the Project Size Gate classifies the work as large or the user explicitly requests managed planning. Small direct work does not instantiate this file. Keep mutable authorization, observed runtime facts, mission/task phases, wave selection, worker state, verification, blockers, and closeout here. Keep static plan definitions in `PLAN.md`; version support does not enable Cloudflare release state by itself.

For compact large sequential work that intentionally has no `PLAN.md`, use the supported compact RUN-only schema described by `references/execution-state-model.md`; do not copy this PLAN-backed RUN schema v10 manifest and null its PLAN fields. Compact mode does not claim static plan or graph validation and cannot delegate writes, accept execution-time task refinement, use release targets, or use a selector. Before crossing those boundaries, create and validate a PLAN schema v5 file and a fresh RUN schema v10 file from this template.

**Before the first selection, fill in what this template ships as `null`.** `observed.captured_at`, the four `observed.git` fields, and `integration.batch_base_sha` must come from a live `git status` / `git rev-parse` on the resolved integration branch. The validator does not require them — a RUN that leaves them null still reports `PASS` — but `select_ready_nodes.py` will then return empty `dispatchable_nodes`, with every mission node in `deferred_nodes` under `parent_state_unreconciled` or `batch_base_missing`. Check those two keys, not `ready_frontier`: these are dispatch-time reasons, so the frontier can still list the nodes while none of them is launchable. Once `status` is `running`, the Resume Reconciliation Gate defers every node and `ready_frontier` empties as well. A green validator next to empty `dispatchable_nodes` is what an unfilled snapshot looks like, not a planning error.

Set `max_parallel_workers`, `available_worker_slots`, and `isolation_capacity` from what you actually observed. The values shipped here are a starting point, not a limit to copy: leaving them at `1` serializes a genuinely parallel frontier and the deferral reads only as `over_budget`.

For plan-backed multi-mission execution, replace the generic fallback runtime snapshot before the first production edit. Proactively record every observed driver independently from authorization, set the configured write-worker maximum generously high unless an explicit user or runtime limit applies, and run deterministic selection immediately after Plan Readiness. Resolve the target repository's branch and landing model from its instructions before filling this template. Preserve those branches when defined; otherwise use the template's main-only defaults, where `main` is production and the run's own ephemeral `codex/<short-name>` branch is its integration branch. Set `integration.retention` to `persistent` only when repository instructions define a genuine long-lived integration branch. Create mission worktrees from the resolved current integration SHA, require one exact-head read-only review before each integration, and merge passing heads serially into the resolved integration branch. Ordinary PRD, UI, and feature work does not wait for GitHub: it starts `local_only` and moves to `integration_push` once the verified integration head is pushed to the integration branch, recording that head in `landing.pushed_head_sha`. That is where an ordinary run ends — the planned change is made, verified, and pushed. Do not open the pull request into the protected base until the user separately reads the pushed branch and asks for it. At that late checkpoint, request the exact remaining landing actions and bind them to the resolved head and base branches. Do not hide a capability or silently downgrade because authorization is missing. Never run parallel writers in `shared_checkout`.

RUN schema v10 records provider-neutral release state under `targets`, keyed by stable PLAN `release.targets[].id`. The keys must exactly equal the PLAN `release.targets[].id` set. PASS evidence is target-neutral: exact source and authorized head SHAs, retained artifact/build/version/signing proof, exact channel proof, promotion proof, availability proof, migration result, and smoke verification. Provider-specific resource IDs may appear in retained references, but never replace the stable target key.

Older RUN schemas remain readable. Historical unmarked RUN v10 files keep their generic exact-target kind and target-source rules while they omit `target_sources`; an unmarked scoped entry opts into strict per-target provenance when it records that map. New PLAN v5 and RUN v10 files declare the same `action-targets/1` marker to enable strict action-to-target validation. Older `deployments` objects retain their original meaning; do not copy that provider-shaped state into a new RUN schema v10 file.

## Harness Run State

```json
{
  "harness_run": {
    "schema_version": 10,
    "action_target_contract": "action-targets/1",
    "run_id": "RUN-<stable-id>",
    "plan": {
      "id": "PLAN-<stable-id>",
      "revision": 1,
      "digest_sha256": "a320fe66409643bdcca50ae96b0b3ae8980b421702a2b3c7d6d25089957bbcd6"
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
      "create_pr": {"authorized": false, "source": null},
      "trigger_remote_ci": {"authorized": false, "source": null},
      "configure_repository": {"authorized": false, "source": null},
      "manage_pr_review": {"authorized": false, "source": null},
      "merge_pr": {"authorized": false, "source": null},
      "provision_cloud_resources": {"authorized": false, "source": null},
      "deploy": {"authorized": false, "source": null},
      "archive_worker_tasks": {"authorized": false, "source": null},
      "remove_worktrees": {"authorized": false, "source": null},
      "delete_branches": {"authorized": false, "source": null}
    },
    "runtime_capabilities": {
      "worker_runtime": "parent",
      "workspace_mode": "shared_checkout",
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
      "nested_subagents": {
        "available": false,
        "max_depth": 1,
        "max_children_per_worker": 3,
        "allowed_roles": ["explorer", "researcher", "reviewer", "tester"],
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
      "head_branch": "refs/heads/codex/<short-name>",
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
      "auto_merge_head_sha": null,
      "continuity": {
        "status": "planned",
        "branch_ref": "refs/heads/codex/<short-name>",
        "head_sha": null,
        "reason": "Retain the reviewed run branch until the user opens and merges its pull request into main"
      }
    },
    "targets": {
      "web-production": {
        "status": "not_started",
        "source_sha": null,
        "authorized_head_sha": null,
        "artifact": null,
        "channel": null,
        "promotion": null,
        "availability": null,
        "migration_status": "not_started",
        "verification_status": "not_started",
        "destructive_migration_confirmed_sha": null
      }
    },
    "post_merge_cleanup": {
      "status": "not_started",
      "base": {"branch": "main", "head_sha": null, "merged_sha_reachable": null},
      "worktree": {
        "path": null,
        "branch_ref": null,
        "head_sha": null,
        "dirty": null,
        "managed_by": null,
        "status": "not_applicable"
      },
      "local_branch": {"ref": null, "head_sha": null, "status": "pending"},
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
        "E-FRONTEND-FINAL-GATE": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-FINAL-VISUAL-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-REVIEW-REPAIR": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-REPAIR-CODE-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-REPAIR-REREVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-VISUAL-CLOSEOUT": {"status": "dormant", "traversals": 0, "source_attempt_id": null}
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
    "workers": [],
    "review_workers": [],
    "workflow_runs": [],
    "verifier_executions": [],
    "attempt_log": []
  }
}
```

The exact fenced JSON block above is the canonical run state. Scripts read this block only; Markdown tables later in this document are non-canonical human views. Update the JSON first, keep it valid, and never infer authorization from plan readiness, a template, or a Goal prompt.

### RUN Schema Version History

New RUN files always use RUN schema v10 (see `SKILL.md`'s Default Runtime And Wave Policy). Older RUN schemas remain readable; their own recorded `schema_version` decides which fields apply.

| Schema | Added | Still readable |
|---|---|---|
| v2 | Baseline 13-action ledger | yes |
| v3 | Repository/review/merge actions and `landing` | yes |
| v4 | SHA-bound auto-merge state | yes |
| v5 | `post_merge_cleanup` | yes |
| v6 | `runtime_adapter` and `future-pr:` targets | yes |
| v7 | Legacy provider-shaped `deployments` | yes |
| v8 | PLAN-v4 graph state and `invoke_external_runtime` | yes |
| v9 | Batch/final/UI evidence and workflow runs | yes |
| v10 (current default) | PLAN-v5 binding, provider-neutral `targets`, two new action gates, local branch continuity, and append-only `verifier_executions` | current |

RUN schema v10 has 19 independent action entries. Keep every entry false unless an explicit user instruction authorizes that exact action. Every authorized execution scope and action scope binds `run_id`, current `plan_revision`, current `plan_digest_sha256`, mission IDs, and the lifecycle boundary; action scopes also bind exact targets. A PLAN revision or digest change invalidates the grant. `invoke_external_runtime` uses `runtime:<provider>`. `trigger_remote_ci` requires `workflow:<identity>`. `provision_cloud_resources` requires `cloud-resource:<provider>:<environment>:<kind>:<logical-name>`. Head-bound remote actions also record `authorized_head_sha` and cannot use `*` targets.

`graph_state` is the canonical routing record for PLAN-v5 nodes and edges. Initialize one state for every declared node and edge. For pre-integration review, `fix_required` returns to the original mission task/thread and its existing worktree; after the focused verifier passes on a changed head, re-arm the same review node with a new attempt ID. Do not create a repair mission or replacement worktree for this loop. Post-integration review may traverse a bounded repair route. That repair mission receives its own direct singleton exact-head review before integration, then returns to the post-integration review before a deterministic final gate. Every retry preserves prior evidence and rechecks authorization.

New RUN files start at `mode: "local_only"` because nothing has been pushed yet. RUN v10 has four modes:

- `local_only` — nothing left the machine. No pushed head, no PR, no remote evidence.
- `integration_push` — the ordinary end state for feature work under the default branch model, and the point at which the run is complete. The verified integration head has been pushed to the run's own branch; `landing.pushed_head_sha` is required, and there is still no PR and no remote check/review/merge evidence. Record the `push` authorization with its exact branch target before moving here.
- `integration_pull_request` — a feature head is reviewed and merged into `integration.branch` through a PR. `landing.base_branch` equals the retained integration branch, while `landing.head_branch` is the disposable feature branch. CI, review, and merge bind the feature PR head; after merge, `landing.merged_sha` and `integration.integration_head_sha` match, and continuity is preserved there. If the retained integration branch resolves to `main`, do not request auto-merge; stop merge-ready for a later exact human instruction naming that PR.
- `pull_request` — only after the user separately asks for the pull request into the protected base. Sets continuity to `not_required`. The harness opens it, watches current-head CI, and requests review. If the human merges, leave `merge_pr` false and record observed merged state; if the harness performs the merge, require exact current-head `merge_pr` authorization.

Resolve `integration.branch`, `landing.head_branch`, and `landing.base_branch` from target-repository instructions; the template's values apply only when the repository defines no other model. See `references/execution-state-model.md`'s Pull Request Landing State for that resolution rule, the exact head-SHA equalities each mode requires before CI, review, ready state, and auto-merge, and the `closed`/`closed_unmerged` terminal pair a PR closed without merge must record.

When PLAN declares release targets, `run.targets` keys must exactly equal the PLAN `release.targets[].id` set. PASS requires exact source/head binding plus retained artifact, channel, promotion, and availability evidence. Every evidence object has a retained reference and lowercase SHA-256; artifact evidence also records build ID, version, and signing status. Release execution never weakens action boundaries: a native merge-triggered publication always requires independent exact production `deploy` authorization for the release target and head. A harness-performed or auto-merge path additionally requires exact `merge_pr` authorization; an observed human merge leaves `merge_pr` false rather than fabricating a harness grant.

See `references/execution-state-model.md`'s closeout condition table for the full `status: complete` requirement. Every applicable condition must hold, with retained RUN-v10 verifier, batch, final, UI, and release evidence bound to the current head.

Schemas v5 through v10 use `post_merge_cleanup` only after a pull request reaches `merged`. See `references/execution-state-model.md`'s Post-Merge Cleanup State for every `ready` precondition, the `remove_worktrees`/`delete_branches` targets, the exact removal order, and the `preserved` rule for a persistent integration branch. For `integration_pull_request`, retention applies to the PR base, so the feature head may be deleted once those cleanup gates pass.

Create mission worktrees from the current resolved integration head. Before each parent integration, require at least one read-only review bound to the exact worktree head; repair findings in that worktree and review the changed head again. Integrate passing worktrees into the branch named by `integration.branch`, either locally or through `integration_pull_request` when repository policy requires an integration-base PR. In `local_only` and `integration_push`, do not create remote PR, CI, review, or merge evidence. After final verification, preserve continuity at the exact integration head. In `pull_request`, which begins only when the user separately asks for it, set continuity to `not_required` and offer the resolved integration head to the protected base. Worker branches and worktrees never become protected landing branches.

Do not include protected-branch promotion in an ordinary mission run's authorization bundle. After the user separately approves the resolved head-to-base promotion, require matching unexpired authorization for every remaining exact action—normally `push`, `create_pr`, `trigger_remote_ci` when a workflow must be dispatched, and `manage_pr_review`—and then treat that order as one continuous parent-owned landing loop that stops at a merge-ready PR. For the unborn promotion PR, bind `create_pr` and `manage_pr_review` to `future-pr:<owner>/<repo>:base=<resolved-base>:head=<resolved-head>`; after creation, verify those fields and append `pr:<full-PR-URL>` while keeping the future target and source. Poll CI and review concurrently, repair only authorized in-scope failures on the resolved head branch, and restart both after every new push. Do not merge and do not enable auto-merge: report the PR as merge-ready once checks and review PASS with zero blocking findings and unresolved threads, and hand it over. `merge_pr` is recorded only when the user separately asks the harness to merge that exact PR. If the human merges it instead, leave `merge_pr` false and record the merged landing as observed external state.

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
      "<exact branch, worktree, task, environment, or * when explicitly run-wide>"
    ]
  },
  "expires_when": "run_complete"
}
```

Per-target provenance holds for every marked RUN-v10 artifact and for any unmarked scoped entry that opts in by recording `target_sources`; this template's `action_target_contract: "action-targets/1"` marker also enables the strict action-to-target kind table. `push`, `merge_pr`, and `deploy` take one more optional key. The execution-intent instruction covers `push` only for the resolved integration branch, and never covers `merge_pr` or `deploy` under the default branch model; any other target on those three entries names the separate instruction that authorized it:

```json
"target_sources": {
  "branch:main": "<the separate user statement authorizing this exact target>"
}
```

That source must differ from the entry's own `source`, every key must appear in `scope.targets`, and a marked RUN fails validation when an out-of-scope target has no entry — in every landing mode. An existing unmarked legacy RUN-v10 entry keeps historical validation only while it omits `target_sources`; adding `target_sources` opts that entry into the same strict provenance rules. See `../../references/execution-state-model.md`'s Per-Target Provenance For The Scoped Three.

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

See `references/execution-state-model.md`'s Authorization Action Ledger for the exact target encoding, the `future-pr:` form, the `expires_when` values and their `wave_closed` reset, and which read-only analysis the parent may perform before a launch-bound wave adds its own authorization requirements.

For automatic app-task fan-out, the selector emits one `launch_directives` entry per selected mission. After accepting the wave, the parent allocates workers, leases, and branches/refs; verifies the explicit pre-allocation `*` grant for app-assigned task/worktree identities and every already-known target under `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, and `create_local_commits`; creates one real Codex worktree thread per directive; and writes the returned thread/client identity into `workers[].task_thread_id`. The directive itself is neither authorization nor proof of launch. If the user requested left-sidebar tasks and project lookup, thread creation, worktree setup, follow-up messaging, or polling is unavailable, leave the worker unlaunched and report the blocked topology; never silently replace it with coordinator-owned subagents or sequential parent implementation. If that topology was not requested, a sequential parent fallback remains valid. When the capability handshake proves nested-agent capability unavailable, assign a disabled task-local policy before implementation and require an equivalent parent-owned read-only review before integration.

For graph workers, copy the selector's complete `runtime_binding` into the allocated mission `workers[]` record or read-only verifier `review_workers[]` record. A review worker also binds node ID, attempt ID, graph revision, review path, and exact current integrated or PR-head SHA; it has no mission lease, writable worktree, branch, or commit authority. For Codex app tasks, pass non-null `model` and `reasoning_effort` as task creation `model` and `thinking`; omit null values so the host default remains explicit. For Claude Code, pass each node's own `model` (and non-null `reasoning_effort` as `effort`) into that node's own `agent()` call inside the Dynamic Workflow script; a single wave may mix models and reasoning efforts freely since each node's call carries its own. The destination host validates the exact pair at launch.

See `references/execution-state-model.md`'s Runtime Capability Axes for the `worker_runtime`, `workspace_mode`, and `completion_channel` enums, the `runtime_adapter`, `permission_boundary`, and `nested_subagents` field rules, and the host-provider match a node needs before the parent may bind it. Its Canonical Mission Phases and Canonical Task Phases sections own the mission, task, worker, and active-wave phase values; `worker_passed` never satisfies a downstream mission dependency.

When the selected driver is `dynamic_workflow`, use `subagent` + `parent_managed_worktree` + `agent_result`, omit `nested_subagents`, and treat the accepted wave as one flat workflow run. The parent allocates one worktree/branch/lease per mission, then invokes the Claude Code `Workflow` tool with `scriptPath` set to `assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js` and the accepted directives supplied as structured `args`. Launch only after `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, and `create_local_commits` cover the selected missions and allocated targets. A workflow cannot wait for human sign-off mid-run; return a refinement request and close the wave when a contract or authorization decision is needed.

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
  "nested_subagent_policy": {
    "enabled": false,
    "max_children": 0,
    "allowed_roles": [],
    "write_policy": "read_only",
    "completion_channel": "agent_result"
  },
  "nested_review_evidence": null,
  "task_thread_id": null,
  "worktree_path": "<path or null>",
  "branch_ref": "<branch/ref or null>",
  "report_path": null,
  "phase": "leased",
  "worker_head_sha": null
}
```

Leave model and effort null unless the user explicitly selected them in the PLAN provider options. During allocation, `worktree_path` and `branch_ref` may be null. Fill them only after the runtime returns and the parent independently verifies them. `worker_head_sha` stays null until the parent verifies the reported commit.

Omit `nested_subagent_policy` entirely when the routed driver is `dynamic_workflow`; it applies only to `app_task` workers, and leaving it in the shape above is rejected as "must be omitted for flat dynamic-workflow orchestration".

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
  "reviewed_sha": "<direct singleton pre-integration worktree, integrated, or PR-head SHA>",
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

RUN v10 keeps `prior_head_shas` on each mission state and on `integration`. Before replacing a head that has review evidence, the parent appends that exact old head to the matching list, then records the new head. These lists are append-only provenance, contain only superseded heads, and never accept a worker-provided SHA without the parent's independent Git check. A retained `fix_required` correction review may use the matching integration history, but a PASS batch review must bind the current integration or PR head. Direct singleton pre-integration history may remain long enough for the selector to detect the stale review and re-arm it.

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

For an enabled RUN-v10 app-task nested policy, use `max_children` from 1 to 3, require `reviewer`, and use a non-empty subset of the runtime `allowed_roles`. Legacy RUN-v8/v9 app-task policies retain their declared roles and matching spawn authorization even when `reviewer` is absent. The app task stays the only writer. A non-trivial mission must complete a post-edit read-only reviewer bound to its exact current head and record that reviewer in WORKER_RESULT; exploration, research, and test-analysis lanes remain optional. An enabled worker cannot pass with `partial` or `unavailable` activity unless it still contains a completed exact-head PASS reviewer. After validating WORKER_RESULT, copy that completed reviewer child into the worker's `nested_review_evidence`; retain its agent ID, role, task, status, summary, evidence paths, reviewed SHA, and PASS decision. RUN validation requires that canonical record to match the mission and worker head before `integrating`. Before RUN-v10 execution authorization, every writable mission must have a direct dependency to a runtime review node whose `mission_ids` contains only that mission and whose `allowed_outcomes` includes `pass`; a multi-mission batch review cannot replace it. When several direct pre-integration review nodes cover the same mission, they use distinct review-worker IDs; at least one current `worker_passed` PASS record must match the retained task-local reviewer agent. When capability is initially unknown, require `spawn_subagents` authorization before the no-production-edit handshake, record its tool/result observation, and then assign the explicit enabled or disabled policy. If that handshake proves the child runtime or reviewer lane unavailable, assign a disabled policy before implementation and record the reason. A disabled-policy worker result, or a graph-backed direct worker with no nested policy, may first validate and make its downstream review node selectable. Before the mission transitions to `integrating`, run the equivalent parent-owned read-only review and retain a `worker_passed` `review_workers[]` PASS whose review node covers the mission and whose `reviewed_sha` equals the current worktree head. Every retained current or historical review attempt must bind its `reviewed_sha` to a current eligible head or an explicit mission `prior_head_shas` entry; a retained `fix_required` batch review may instead bind to an explicit integration `prior_head_shas` entry. A review node may use worktree or integrated SHAs only from its declared `mission_ids`; current integration and PR heads remain valid batch review targets. Trivial disabled-policy missions use the same parent-review path. Older schema-v2 RUN files may omit both optional nested fields; once a RUN includes `runtime_capabilities.nested_subagents`, every app-task worker must include `nested_subagent_policy`, while enabled worker passes also retain `nested_review_evidence`.

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

## Release Target Evidence

A target may move to `PASS` only with artifact, channel, promotion, and availability objects. Each object records the exact subject, retained reference, and lowercase `evidence_sha256`. Artifact evidence also records `build_id`, `version`, and `signing_status`; channel evidence names the exact PLAN channel. For example:

```json
{
  "artifact": {
    "subject": "web-production artifact",
    "retained_reference": "<artifact URL or immutable repository path>",
    "evidence_sha256": "<lowercase SHA-256>",
    "build_id": "<provider-neutral build ID>",
    "version": "<artifact version>",
    "signing_status": "not_required"
  },
  "channel": {
    "subject": "web-production channel",
    "retained_reference": "<channel observation>",
    "evidence_sha256": "<lowercase SHA-256>",
    "name": "workers-production"
  },
  "promotion": {
    "subject": "web-production promotion",
    "retained_reference": "<promotion evidence>",
    "evidence_sha256": "<lowercase SHA-256>",
    "status": "PASS"
  },
  "availability": {
    "subject": "web-production availability",
    "retained_reference": "<smoke or availability evidence>",
    "evidence_sha256": "<lowercase SHA-256>",
    "status": "PASS"
  }
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
| Worker, exact-head pre-integration review, mission-integration, batch, final E2E, and release gates exist; E2E command, current-head check, evidence, environment, and smoke disposition are named | draft / PASS / BLOCKED | |
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
| Worktree review | at least one independent read-only review before integration | exact current worktree head |
| Mission integration | that mission's integration surface after serial integration | integration head |
| Batch | true cross-mission and shared-contract checks | post-wave integration head |
| Final / current-head | broad regression, browser E2E, UI evidence, and release gates after review repairs converge | exact accepted integration or PR head |

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
