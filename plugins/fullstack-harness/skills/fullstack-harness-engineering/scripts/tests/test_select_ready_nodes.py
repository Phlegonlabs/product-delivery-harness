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
    run["observed"]["runtime"].update(
        {"available_worker_slots": 0, "isolation_capacity": 0}
    )
    return run


class SelectReadyNodesTests(unittest.TestCase):
    def test_entry_node_is_dispatchable_once_authorized(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)

        result = select_ready_nodes(plan, run)

        self.assertEqual(
            ["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]]
        )
        self.assertEqual("run_parent", result["dispatchable_nodes"][0]["launch_kind"])
        self.assertEqual("parent", result["dispatchable_nodes"][0]["worker_runtime"])

    def test_dependent_node_stays_deferred_until_its_edge_fires(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)

        result = select_ready_nodes(plan, run)

        self.assertNotIn(
            "N-M2", [item["node_id"] for item in result["dispatchable_nodes"]]
        )

    def test_schema_mismatch_is_rejected_before_selection(self) -> None:
        # Structural validate_plan/validate_run already reject a v4 PLAN paired
        # with a non-8/9 RUN, so isolate select_ready_nodes's own schema gate
        # (the line this test guards) by stubbing structural validation out.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        run["schema_version"] = 6

        with patch("select_ready_nodes.validate_plan", return_value=[]), patch(
            "select_ready_nodes.validate_run", return_value=[]
        ):
            with self.assertRaises(GraphSelectionError) as ctx:
                select_ready_nodes(plan, run)

        self.assertIn("PLAN v4 and RUN v8 or v9", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
