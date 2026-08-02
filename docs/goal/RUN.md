# Run: System-first Harness orchestration

This RUN records the parent-owned state for the three isolated implementation missions in `PLAN.md`.

## Harness Run State

```json
{
  "harness_run": {
    "schema_version": 10,
    "run_id": "RUN-SYSTEM-FIRST-HARNESS",
    "plan": {
      "id": "PLAN-SYSTEM-FIRST-HARNESS",
      "revision": 2,
      "digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7"
    },
    "status": "running",
    "intent": "plan-then-execute",
    "plan_readiness": "ready",
    "execution_authorized": true,
    "execution_authorization_source": "User: 按照這個方式去修改，記得開 Multi workers",
    "execution_authorization_scope": {
      "run_id": "RUN-SYSTEM-FIRST-HARNESS",
      "plan_revision": 2,
      "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
      "mission_ids": ["M1", "M2", "M3"],
      "expires_when": "run_complete"
    },
    "authorizations": {
      "invoke_external_runtime": {"authorized": false, "source": null},
      "spawn_subagents": {
        "authorized": true,
        "source": "User explicitly requested Multi workers",
        "scope": {
          "run_id": "RUN-SYSTEM-FIRST-HARNESS",
          "plan_revision": 2,
          "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
          "mission_ids": ["M1", "M2", "M3"],
          "targets": ["worker:W-M1", "worker:W-M2", "worker:W-M3"]
        },
        "expires_when": "run_complete"
      },
      "create_user_owned_tasks": {"authorized": false, "source": null},
      "create_local_worktrees": {
        "authorized": true,
        "source": "User requested implementation with Multi workers",
        "scope": {
          "run_id": "RUN-SYSTEM-FIRST-HARNESS",
          "plan_revision": 2,
          "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
          "mission_ids": ["M1", "M2", "M3"],
          "targets": [
            "worktree:/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m1",
            "worktree:/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m2",
            "worktree:/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m3"
          ]
        },
        "expires_when": "run_complete"
      },
      "create_app_managed_worktrees": {"authorized": false, "source": null},
      "create_local_branches": {
        "authorized": true,
        "source": "User requested implementation with Multi workers",
        "scope": {
          "run_id": "RUN-SYSTEM-FIRST-HARNESS",
          "plan_revision": 2,
          "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
          "mission_ids": ["M1", "M2", "M3"],
          "targets": [
            "branch:refs/heads/codex/system-first-m1-core",
            "branch:refs/heads/codex/system-first-m2-runtime",
            "branch:refs/heads/codex/system-first-m3-adapters"
          ]
        },
        "expires_when": "run_complete"
      },
      "create_local_commits": {
        "authorized": true,
        "source": "User requested implementation with Multi workers",
        "scope": {
          "run_id": "RUN-SYSTEM-FIRST-HARNESS",
          "plan_revision": 2,
          "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
          "mission_ids": ["M1", "M2", "M3"],
          "targets": [
            "branch:refs/heads/codex/system-first-m1-core",
            "branch:refs/heads/codex/system-first-m2-runtime",
            "branch:refs/heads/codex/system-first-m3-adapters"
          ]
        },
        "expires_when": "run_complete"
      },
      "integrate_locally": {
        "authorized": true,
        "source": "User requested implementation with Multi workers",
        "scope": {
          "run_id": "RUN-SYSTEM-FIRST-HARNESS",
          "plan_revision": 2,
          "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
          "mission_ids": ["M1", "M2", "M3"],
          "targets": ["branch:refs/heads/codex/system-first-harness"]
        },
        "expires_when": "run_complete"
      },
      "push": {"authorized": false, "source": null},
      "archive_worker_tasks": {"authorized": false, "source": null},
      "remove_worktrees": {"authorized": false, "source": null},
      "delete_branches": {"authorized": false, "source": null}
    },
    "runtime_capabilities": {
      "worker_runtime": "subagent",
      "workspace_mode": "parent_managed_worktree",
      "completion_channel": "agent_result",
      "max_parallel_workers": 8,
      "runtime_adapter": {
        "provider": "codex",
        "available_drivers": ["subagents", "sequential_parent"],
        "detection_source": "observed"
      },
      "permission_boundary": {
        "selected_mode": "full_access",
        "profile_name": null,
        "approval_policy": "never",
        "filesystem_scope": "unrestricted",
        "network_scope": "open",
        "local_binding": "allowed",
        "worker_inheritance": "inherited",
        "status": "ready"
      },
      "platform_lifecycle": {
        "owner": "parent",
        "automatic_retention_cleanup_possible": false,
        "durable_branch_required_before_unique_work": true
      }
    },
    "observed": {
      "captured_at": "2026-08-02T06:59:32-07:00",
      "git": {
        "parent_worktree_path": "/Users/jacky/Documents/Github/fullstack-goal-dev",
        "parent_branch": "refs/heads/codex/system-first-harness",
        "parent_head_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
        "parent_dirty": false,
        "worktrees": [
          {
            "path": "/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m1",
            "branch_ref": "refs/heads/codex/system-first-m1-core",
            "head_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
            "managed_by": "parent",
            "dirty": false
          },
          {
            "path": "/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m2",
            "branch_ref": "refs/heads/codex/system-first-m2-runtime",
            "head_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
            "managed_by": "parent",
            "dirty": false
          },
          {
            "path": "/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m3",
            "branch_ref": "refs/heads/codex/system-first-m3-adapters",
            "head_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
            "managed_by": "parent",
            "dirty": false
          }
        ]
      },
      "runtime": {
        "available_worker_slots": 3,
        "isolation_capacity": 3,
        "completion_channel_available": true
      }
    },
    "integration": {
      "branch": "refs/heads/codex/system-first-harness",
      "retention": "ephemeral",
      "batch_base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
      "integration_head_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
      "prior_head_shas": []
    },
    "batch_gate_results": [
      {"id": "batch", "status": "planned", "head_sha": null, "evidence": []}
    ],
    "final_gate_results": [
      {"id": "final", "status": "planned", "head_sha": null, "evidence": []}
    ],
    "ui_evidence": [],
    "landing": {
      "mode": "local_only",
      "remote": "origin",
      "pushed_head_sha": null,
      "continuity": {
        "status": "planned",
        "branch_ref": "refs/heads/codex/system-first-harness",
        "head_sha": null,
        "reason": "Preserve the verified run branch for user landing"
      }
    },
    "graph_state": {
      "graph_revision": 2,
      "node_states": {
        "N-M1": {"phase": "running", "attempts": 1, "last_attempt_id": "ATT-M1-1", "last_outcome": null, "bound_worker_id": "W-M1", "blockers": []},
        "N-REVIEW-M1": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-REVIEW-PASS-M1": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-M2": {"phase": "running", "attempts": 1, "last_attempt_id": "ATT-M2-1", "last_outcome": null, "bound_worker_id": "W-M2", "blockers": []},
        "N-REVIEW-M2": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-REVIEW-PASS-M2": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-M3": {"phase": "running", "attempts": 1, "last_attempt_id": "ATT-M3-1", "last_outcome": null, "bound_worker_id": "W-M3", "blockers": []},
        "N-REVIEW-M3": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-REVIEW-PASS-M3": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []},
        "N-FINAL": {"phase": "dormant", "attempts": 0, "last_attempt_id": null, "last_outcome": null, "bound_worker_id": null, "blockers": []}
      },
      "edge_states": {
        "E-M1-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M1-REVIEW-PASS": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M1-FINAL": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M2-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M2-REVIEW-PASS": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M2-FINAL": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M3-REVIEW": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M3-REVIEW-PASS": {"status": "dormant", "traversals": 0, "source_attempt_id": null},
        "E-M3-FINAL": {"status": "dormant", "traversals": 0, "source_attempt_id": null}
      }
    },
    "mission_states": {
      "M1": {"phase": "worker_running", "lease_id": "LEASE-M1-1", "lease_plan_revision": 2, "lease_plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7", "worker_id": "W-M1", "base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d", "head_sha": null, "prior_head_shas": [], "integration_gate": "planned", "integrated_sha": null, "blockers": [], "report_path": null},
      "M2": {"phase": "worker_running", "lease_id": "LEASE-M2-1", "lease_plan_revision": 2, "lease_plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7", "worker_id": "W-M2", "base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d", "head_sha": null, "prior_head_shas": [], "integration_gate": "planned", "integrated_sha": null, "blockers": [], "report_path": null},
      "M3": {"phase": "worker_running", "lease_id": "LEASE-M3-1", "lease_plan_revision": 2, "lease_plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7", "worker_id": "W-M3", "base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d", "head_sha": null, "prior_head_shas": [], "integration_gate": "planned", "integrated_sha": null, "blockers": [], "report_path": null}
    },
    "task_states": {
      "M1/T01": {"phase": "queued", "attempts": 0, "commit_sha": null, "verifier_status": "planned", "blockers": [], "refinement_request": null},
      "M1/T02": {"phase": "queued", "attempts": 0, "commit_sha": null, "verifier_status": "planned", "blockers": [], "refinement_request": null},
      "M2/T01": {"phase": "queued", "attempts": 0, "commit_sha": null, "verifier_status": "planned", "blockers": [], "refinement_request": null},
      "M2/T02": {"phase": "queued", "attempts": 0, "commit_sha": null, "verifier_status": "planned", "blockers": [], "refinement_request": null},
      "M3/T01": {"phase": "queued", "attempts": 0, "commit_sha": null, "verifier_status": "planned", "blockers": [], "refinement_request": null},
      "M3/T02": {"phase": "queued", "attempts": 0, "commit_sha": null, "verifier_status": "planned", "blockers": [], "refinement_request": null}
    },
    "active_wave": {
      "wave_id": "B01",
      "status": "active",
      "plan_revision": 2,
      "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
      "batch_base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
      "selected_missions": ["M1", "M2", "M3"],
      "deferred_missions": [],
      "conflict_edges": []
    },
    "workers": [
      {
        "worker_id": "W-M1",
        "mission_id": "M1",
        "lease_id": "LEASE-M1-1",
        "plan_revision": 2,
        "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
        "batch_base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
        "worker_runtime": "subagent",
        "workspace_mode": "parent_managed_worktree",
        "completion_channel": "agent_result",
        "task_thread_id": "/root/m1_system_contract",
        "worktree_path": "/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m1",
        "branch_ref": "refs/heads/codex/system-first-m1-core",
        "report_path": null,
        "phase": "worker_running",
        "worker_head_sha": null,
        "runtime_binding": {"provider": "codex", "driver": "subagents", "source": "host", "model": "gpt-5.6-terra", "reasoning_effort": "high", "option_source": "plan_provider_options"}
      },
      {
        "worker_id": "W-M2",
        "mission_id": "M2",
        "lease_id": "LEASE-M2-1",
        "plan_revision": 2,
        "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
        "batch_base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
        "worker_runtime": "subagent",
        "workspace_mode": "parent_managed_worktree",
        "completion_channel": "agent_result",
        "task_thread_id": "/root/m2_sequential_runtime",
        "worktree_path": "/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m2",
        "branch_ref": "refs/heads/codex/system-first-m2-runtime",
        "report_path": null,
        "phase": "worker_running",
        "worker_head_sha": null,
        "runtime_binding": {"provider": "codex", "driver": "subagents", "source": "host", "model": "gpt-5.6-terra", "reasoning_effort": "high", "option_source": "plan_provider_options"}
      },
      {
        "worker_id": "W-M3",
        "mission_id": "M3",
        "lease_id": "LEASE-M3-1",
        "plan_revision": 2,
        "plan_digest_sha256": "e7ef1407c53b8a61ae01bbb88f00c5933bb69b698959d5f1654ffa8121ad7bf7",
        "batch_base_sha": "a48a236d64988047d44c3890f6f9d0bd76ad827d",
        "worker_runtime": "subagent",
        "workspace_mode": "parent_managed_worktree",
        "completion_channel": "agent_result",
        "task_thread_id": "/root/m3_adapter_handoff",
        "worktree_path": "/Users/jacky/Documents/Github/fullstack-goal-dev/.claude/worktrees/system-first-m3",
        "branch_ref": "refs/heads/codex/system-first-m3-adapters",
        "report_path": null,
        "phase": "worker_running",
        "worker_head_sha": null,
        "runtime_binding": {"provider": "codex", "driver": "subagents", "source": "host", "model": "gpt-5.6-terra", "reasoning_effort": "high", "option_source": "plan_provider_options"}
      }
    ],
    "review_workers": [],
    "workflow_runs": [],
    "verifier_executions": [],
    "attempt_log": []
  }
}
```

## Plan Readiness View

| Readiness check | Status | Evidence / decision |
|---|---|---|
| Canonical PLAN JSON validates and digest matches | PASS | Digest recorded above. |
| Mission/task graph is acyclic and scopes do not overlap | PASS | Three independent mission roots. |
| Runtime/workspace/completion route exists | PASS | Codex direct subagents with parent-managed worktrees and agent results. |
| Required implementation actions are authorized | PASS | User explicitly requested implementation and Multi Workers. |
| UI/UX evidence | n/a | Non-UI orchestration and documentation changes. |

## Goal And Checkpoint

```text
Objective: Implement system-first Harness orchestration without a schema bump.
Canonical PLAN path: docs/goal/PLAN.md
Current mission / task: Plan readiness
Last verified integrated result: none
Remaining: M1, M2, M3, generated bundle sync, full verification, push
Blocked / waiting authorization: none for implementation; cleanup remains unauthorized
Next action: commit the plan baseline, allocate three isolated worktrees, and launch the accepted wave
```
