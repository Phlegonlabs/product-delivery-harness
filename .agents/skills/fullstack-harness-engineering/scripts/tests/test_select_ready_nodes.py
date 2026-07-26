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

from select_ready_nodes import GraphSelectionError, select_ready_nodes  # noqa: E402
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


class SelectReadyNodesTests(unittest.TestCase):
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
