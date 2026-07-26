#!/usr/bin/env python3
"""Dedicated tests for select_ready_nodes.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    load_plan,
    load_run,
    plan_digest,
    validate_run,
)
from select_ready_nodes import (  # noqa: E402
    GraphSelectionError,
    _preintegration_review_source_ready,
    select_ready_nodes,
)
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402


def authorized_parent_run(plan: dict[str, object]) -> dict[str, object]:
    run = valid_graph_run(plan)
    run.update(
        {
            "status": "running",
            "intent": "plan-then-execute",
            "plan_readiness": "ready",
            "execution_authorized": True,
            "execution_authorization_source": "user requested execution",
            "execution_authorization_scope": {
                "run_id": run["run_id"],
                "mission_ids": ["M1"],
                "expires_when": "run_complete",
            },
        }
    )
    run["observed"]["captured_at"] = "2026-07-25T00:00:00Z"
    run["observed"]["runtime"].update(
        {"available_worker_slots": 0, "isolation_capacity": 0}
    )
    return run


def current_preintegration_review_state() -> tuple[dict[str, object], dict[str, object]]:
    root = SCRIPTS_DIR.parent
    plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
    run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")
    digest = plan_digest(plan)
    run.update(
        {
            "status": "ready",
            "intent": "plan-then-execute",
            "plan_readiness": "ready",
            "execution_authorized": True,
            "execution_authorization_source": "user requested execution",
            "execution_authorization_scope": {
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "mission_ids": ["M1"],
                "expires_when": "run_complete",
            },
        }
    )
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 2,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
            },
            "permission_boundary": {
                "selected_mode": "ask_for_approval",
                "profile_name": None,
                "approval_policy": "on-request",
                "filesystem_scope": "workspace",
                "network_scope": "filtered",
                "local_binding": "allowed",
                "worker_inheritance": "inherited",
                "status": "ready",
            },
        }
    )
    run["observed"]["captured_at"] = "2026-07-26T00:00:00Z"
    run["observed"]["runtime"].update(
        {
            "available_worker_slots": 2,
            "isolation_capacity": 2,
            "completion_channel_available": True,
        }
    )
    run["observed"]["git"].update(
        {
            "parent_worktree_path": "C:/repo",
            "parent_branch": "refs/heads/development",
            "parent_head_sha": "a" * 40,
            "parent_dirty": False,
        }
    )
    run["integration"].update(
        {
            "batch_base_sha": "a" * 40,
            "integration_head_sha": "a" * 40,
        }
    )
    run["mission_states"]["M1"].update(
        {
            "phase": "worker_passed",
            "lease_id": "LEASE-M1",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": "W-M1",
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "integration_gate": "planned",
            "integrated_sha": None,
        }
    )
    run["workers"] = [
        {
            "worker_id": "W-M1",
            "mission_id": "M1",
            "lease_id": "LEASE-M1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": "a" * 40,
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "runtime_binding": {
                "provider": "codex",
                "driver": "subagents",
                "source": "host",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "option_source": "plan_provider_options",
            },
            "task_thread_id": None,
            "worktree_path": "C:/repo/worktrees/M1",
            "branch_ref": "refs/heads/codex/m1",
            "report_path": None,
            "phase": "worker_passed",
            "worker_head_sha": "b" * 40,
        }
    ]
    run["graph_state"]["node_states"]["N-M1"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-M1",
            "last_outcome": None,
            "bound_worker_id": "W-M1",
            "blockers": [],
        }
    )
    run["authorizations"]["spawn_subagents"] = {
        "authorized": True,
        "source": "user authorized review",
        "scope": {
            "run_id": run["run_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "mission_ids": ["M1"],
            "targets": ["*"],
        },
        "expires_when": "run_complete",
    }
    return plan, run


class SelectReadyNodesTests(unittest.TestCase):
    def test_current_review_dispatches_before_integration_and_gates_transition(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": [
                        "app_threads",
                        "subagents",
                        "sequential_parent",
                    ],
                    "detection_source": "observed",
                },
                "nested_subagents": {
                    "available": True,
                    "max_depth": 1,
                    "max_children_per_worker": 3,
                    "allowed_roles": ["reviewer"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
                "platform_lifecycle": {
                    "owner": "app",
                    "automatic_retention_cleanup_possible": True,
                    "durable_branch_required_before_unique_work": True,
                },
            }
        )
        mission_worker = run["workers"][0]
        mission_worker.update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "task_thread_id": "THREAD-M1",
                "nested_subagent_policy": {
                    "enabled": False,
                    "max_children": 0,
                    "allowed_roles": [],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        mission_worker["runtime_binding"]["driver"] = "app_threads"
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/repo/worktrees/M1",
                "branch_ref": "refs/heads/codex/m1",
                "head_sha": "b" * 40,
                "managed_by": "app",
                "dirty": False,
            }
        ]
        run["authorizations"]["create_user_owned_tasks"] = {
            "authorized": True,
            "source": "user authorized review task",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "mission_ids": ["M1"],
                "targets": ["*"],
            },
            "expires_when": "run_complete",
        }
        self.assertEqual([], validate_run(plan, run))

        selected = select_ready_nodes(plan, run)

        self.assertIn(
            "N-FRONTEND-REVIEW",
            [item["node_id"] for item in selected["dispatchable_nodes"]],
        )
        review_directive = next(
            item
            for item in selected["dispatchable_nodes"]
            if item["node_id"] == "N-FRONTEND-REVIEW"
        )
        self.assertEqual("create_thread", review_directive["launch_kind"])

        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-M1",
                "last_outcome": None,
                "bound_worker_id": "RW-M1",
                "blockers": [],
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-M1",
                "node_id": "N-FRONTEND-REVIEW",
                "attempt_id": "ATT-REVIEW-M1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "b" * 40,
                "review_path": "C:/repo/worktrees/M1",
                "worker_runtime": "app_task",
                "completion_channel": "thread_poll",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "app_threads",
                    "source": "host",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": "THREAD-REVIEW-M1",
                "report_path": None,
                "phase": "worker_passed",
                "outcome": "pass",
                "findings": [],
            }
        ]
        run["mission_states"]["M1"]["phase"] = "integrating"

        self.assertEqual([], validate_run(plan, run))

    def test_preintegration_fix_returns_to_original_worktree_before_rereview(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "ready",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-OLD",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-OLD",
                "node_id": "N-FRONTEND-REVIEW",
                "attempt_id": "ATT-REVIEW-OLD",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "b" * 40,
                "review_path": "C:/repo/worktrees/M1",
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "subagents",
                    "source": "host",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_failed",
                "outcome": "fix_required",
                "findings": ["src/example/file.ts:1 fix required"],
            }
        ]
        self.assertEqual([], validate_run(plan, run))

        unchanged = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in unchanged["deferred_nodes"]
        }
        self.assertIn("review_head_unchanged", deferred["N-FRONTEND-REVIEW"])

        original_worker = run["workers"][0]
        original_identity = (
            original_worker["worker_id"],
            original_worker["worktree_path"],
            original_worker["branch_ref"],
        )
        run["mission_states"]["M1"]["head_sha"] = "c" * 40
        original_worker["worker_head_sha"] = "c" * 40

        selected = select_ready_nodes(plan, run)
        directives = {
            item["node_id"]: item for item in selected["dispatchable_nodes"]
        }

        self.assertIn("N-FRONTEND-REVIEW", directives)
        self.assertEqual(
            original_identity,
            (
                original_worker["worker_id"],
                original_worker["worktree_path"],
                original_worker["branch_ref"],
            ),
        )
        self.assertNotIn("M2", {mission["id"] for mission in plan["missions"]})
        self.assertNotIn(
            "N-M1-REPAIR",
            {node["id"] for node in plan["graph"]["nodes"]},
        )
        self.assertFalse(
            any(
                item["kind"] == "mission"
                for item in selected["dispatchable_nodes"]
            )
        )

    def test_preintegration_shortcut_rejects_multi_mission_review(self) -> None:
        plan, run = current_preintegration_review_state()
        nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
        review = nodes["N-FRONTEND-REVIEW"]
        review["review"]["mission_ids"] = ["M1", "M3"]

        self.assertFalse(
            _preintegration_review_source_ready(
                review,
                nodes["N-M1"],
                run,
            )
        )

    def test_malformed_current_mission_states_return_validation_errors(self) -> None:
        plan, run = current_preintegration_review_state()
        run["mission_states"] = None

        errors = validate_run(plan, run)

        self.assertTrue(
            any("run.mission_states: must be an object" in error for error in errors)
        )

    def test_current_enabled_nested_policy_requires_retained_review_evidence(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": [
                        "app_threads",
                        "subagents",
                        "sequential_parent",
                    ],
                    "detection_source": "observed",
                },
                "nested_subagents": {
                    "available": True,
                    "max_depth": 1,
                    "max_children_per_worker": 3,
                    "allowed_roles": ["reviewer"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
                "platform_lifecycle": {
                    "owner": "app",
                    "automatic_retention_cleanup_possible": True,
                    "durable_branch_required_before_unique_work": True,
                },
            }
        )
        worker = run["workers"][0]
        worker.update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "task_thread_id": "THREAD-M1",
                "nested_subagent_policy": {
                    "enabled": True,
                    "max_children": 1,
                    "allowed_roles": ["reviewer"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        worker["runtime_binding"]["driver"] = "app_threads"
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/repo/worktrees/M1",
                "branch_ref": "refs/heads/codex/m1",
                "head_sha": "b" * 40,
                "managed_by": "app",
                "dirty": False,
            }
        ]
        run["authorizations"]["spawn_subagents"]["scope"]["targets"] = [
            "worker:W-M1"
        ]
        run["mission_states"]["M1"]["phase"] = "integrating"

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "requires retained task-local exact-head PASS review evidence"
                in error
                for error in errors
            )
        )

        worker["nested_review_evidence"] = {
            "agent_id": "A-REVIEW-M1",
            "role": "reviewer",
            "task": "Review the exact proposed mission head.",
            "status": "completed",
            "summary": "No blocking findings.",
            "evidence_paths": ["evidence/review-m1.json"],
            "reviewed_sha": "b" * 40,
            "decision": "PASS",
        }

        self.assertEqual([], validate_run(plan, run))

        worker["nested_review_evidence"]["reviewed_sha"] = None
        worker["worker_head_sha"] = None
        run["mission_states"]["M1"]["head_sha"] = None
        null_sha_errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "nested_review_evidence.reviewed_sha: must be a full lowercase Git SHA"
                in error
                for error in null_sha_errors
            )
        )
        self.assertTrue(
            any(
                "requires retained task-local exact-head PASS review evidence"
                in error
                for error in null_sha_errors
            )
        )

    def test_plan_backed_parent_write_is_not_dispatched_in_shared_checkout(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("workspace_not_isolated", deferred["N-M1"])

    def test_dependent_node_stays_deferred_until_its_edge_fires(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)

        result = select_ready_nodes(plan, run)

        self.assertNotIn(
            "N-M2", [item["node_id"] for item in result["dispatchable_nodes"]]
        )

    def test_running_resume_fails_closed_on_unknown_parent_state(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)
        run["observed"]["captured_at"] = None
        run["observed"]["git"]["parent_dirty"] = None

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["ready_frontier"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("parent_state_unreconciled", deferred["N-M1"])

    def test_running_resume_reconciles_every_linked_worktree(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/repo/untracked-worker",
                "branch_ref": "refs/heads/untracked",
                "head_sha": "b" * 40,
                "managed_by": "parent",
                "dirty": False,
            }
        ]

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["ready_frontier"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("worktree_state_unreconciled", deferred["N-M1"])

    def test_schema_mismatch_is_rejected_before_selection(self) -> None:
        # Structural validate_plan/validate_run already reject unsupported
        # PLAN/RUN pairs, so isolate select_ready_nodes's own schema gate (the
        # line this test guards) by stubbing structural validation out.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        run["schema_version"] = 6

        with patch("select_ready_nodes.validate_plan", return_value=[]), patch(
            "select_ready_nodes.validate_run", return_value=[]
        ):
            with self.assertRaises(GraphSelectionError) as ctx:
                select_ready_nodes(plan, run)

        self.assertIn(
            "PLAN v4 with RUN v8/v9 or PLAN v5 with RUN v10",
            str(ctx.exception),
        )


if __name__ == "__main__":
    unittest.main()
