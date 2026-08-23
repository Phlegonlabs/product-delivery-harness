#!/usr/bin/env python3
"""Focused tests for current-pair validation and derived execution routing."""

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

from harness_core import classify_execution_route  # noqa: E402
from harness_manifest import (  # noqa: E402
    validate_current_manifests,
    validate_current_plan_run,
    validate_plan,
    validate_run,
)
from select_ready_nodes import select_ready_nodes  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402
from test_harness_manifest import legacy_plan, legacy_run  # noqa: E402


class CurrentValidationAndRoutingTests(unittest.TestCase):
    def test_current_entrypoint_rejects_before_legacy_dispatch(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        plan["schema_version"] = 4
        run["schema_version"] = 9

        with patch("harness_manifest.validate_plan") as validate_plan_mock, patch(
            "harness_manifest.validate_run"
        ) as validate_run_mock:
            errors = validate_current_plan_run(plan, run)

        self.assertEqual(
            ["current PLAN/RUN validation requires PLAN v6 with RUN v11"], errors
        )
        validate_plan_mock.assert_not_called()
        validate_run_mock.assert_not_called()

    def test_current_entrypoint_validates_the_pair_and_aliases_it(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)

        self.assertEqual([], validate_current_plan_run(plan, run))
        self.assertEqual([], validate_current_manifests(plan, run))

    def test_legacy_validators_keep_accepted_shapes(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 5)

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(
            ["current PLAN/RUN validation requires PLAN v6 with RUN v11"],
            validate_current_plan_run(plan, run),
        )

    def test_execution_route_prefers_direct_before_managed_artifacts(self) -> None:
        self.assertEqual(
            "direct",
            classify_execution_route(
                direct=True,
                managed_artifacts=True,
                selected_safe_write_missions=4,
            ),
        )
        self.assertEqual(
            "direct",
            classify_execution_route(
                direct=False,
                managed_artifacts=False,
                selected_safe_write_missions=4,
            ),
        )

    def test_execution_route_uses_selected_safe_writers_not_runtime_driver(self) -> None:
        self.assertEqual(
            "managed_sequential",
            classify_execution_route(
                managed_artifacts=True,
                selected_safe_write_missions=1,
            ),
        )
        self.assertEqual(
            "parallel_graph",
            classify_execution_route(
                managed_artifacts=True,
                selected_safe_write_missions=2,
            ),
        )

    def test_selector_exposes_derived_route_without_persisting_schema_state(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = select_ready_nodes(plan, run)

        self.assertEqual("managed_sequential", result["execution_route"])
        self.assertNotIn("execution_route", plan)
        self.assertNotIn("execution_route", run)


if __name__ == "__main__":
    unittest.main()
