#!/usr/bin/env python3
"""Dedicated tests for validate_node_result.py."""

from __future__ import annotations

import copy
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

from harness_manifest import plan_digest  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402
from validate_node_result import validate_node_result  # noqa: E402


def running_result(plan: dict[str, object], run: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    run["graph_state"]["node_states"]["N-M1"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-N-M1-1",
            "bound_worker_id": "W-M1",
        }
    )
    run["mission_states"]["M1"].update(
        {
            "phase": "worker_running",
            "lease_id": "LEASE-M1-1",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": "W-M1",
            "base_sha": "a" * 40,
        }
    )
    return {
        "run_id": run["run_id"],
        "node_id": "N-M1",
        "attempt_id": "ATT-N-M1-1",
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "plan_digest_sha256": digest,
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "status": "succeeded",
        "outcome": "pass",
        "worker_result": {"status": "PASS"},
        "refinement_request": None,
        "evidence_paths": ["worker-result.json"],
    }


class ValidateNodeResultTests(unittest.TestCase):
    def test_matching_result_for_a_running_node_passes(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)

        self.assertEqual([], validate_node_result(plan, run, result))

    def test_stale_attempt_id_is_rejected(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)
        result["attempt_id"] = "ATT-STALE"

        errors = validate_node_result(plan, run, result)

        self.assertTrue(any("active attempt" in error for error in errors))

    def test_schema_mismatch_reports_the_required_versions(self) -> None:
        # Structural validate_plan/validate_run already reject a v4 PLAN paired
        # with a non-8/9 RUN, so isolate validate_node_result's own schema gate
        # (the line this test guards) by stubbing structural validation out.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)
        run["schema_version"] = 6

        with patch("validate_node_result.validate_plan", return_value=[]), patch(
            "validate_node_result.validate_run", return_value=[]
        ):
            errors = validate_node_result(plan, run, result)

        self.assertIn(
            "node result validation requires PLAN v4 with RUN v8/v9 or PLAN v5 with RUN v10",
            errors,
        )

    def test_plan_v5_run_v10_pair_uses_graph_node_result_validation(self) -> None:
        plan = valid_graph_plan()
        plan["schema_version"] = 5
        run = valid_graph_run(plan)
        run["schema_version"] = 10
        result = running_result(plan, run)

        with patch("validate_node_result.validate_plan", return_value=[]), patch(
            "validate_node_result.validate_run", return_value=[]
        ):
            errors = validate_node_result(plan, run, result)

        self.assertEqual([], errors)

    def test_contract_gap_outcome_requires_a_refinement_request(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)
        result["status"] = "blocked"
        result["outcome"] = "contract_gap"
        result["worker_result"] = None

        errors = validate_node_result(plan, run, copy.deepcopy(result))

        self.assertTrue(any("refinement_request" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
