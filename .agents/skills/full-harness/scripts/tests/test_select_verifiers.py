#!/usr/bin/env python3
"""Tests for deterministic changed-file verifier selection."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from select_verifiers import (  # noqa: E402
    VerifierSelectionError,
    applicable_targeted_verifiers,
    normalize_changed_files,
    select_verifiers,
)
from test_harness_manifest import valid_plan  # noqa: E402


class SelectVerifiersTests(unittest.TestCase):
    def targeted_plan(self) -> dict[str, object]:
        plan = valid_plan()
        mission = plan["missions"][0]
        mission["worker_verifiers"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/**"],
        }
        mission["tasks"][0]["verifiers"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/one.py"],
        }
        mission["tasks"][1]["verifiers"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/two.py"],
        }
        return plan

    def test_exact_and_subtree_selection_is_deterministic(self) -> None:
        plan = self.targeted_plan()
        result = select_verifiers(
            plan,
            "M1",
            ["src/a/one.py"],
            head_sha="f" * 40,
        )
        self.assertEqual(
            result["selected"],
            [
                {"id": "verify-m1-1", "level": "task", "task_id": "M1/T01"},
                {"id": "worker-m1", "level": "worker", "task_id": None},
            ],
        )
        self.assertEqual(
            result["not_applicable"],
            [
                {
                    "id": "verify-m1-2",
                    "level": "task",
                    "task_id": "M1/T02",
                    "reason": "no_changed_file_in_scope",
                }
            ],
        )
        self.assertEqual(
            result["metrics"],
            {"considered": 3, "selected": 2, "not_applicable": 1},
        )

    def test_empty_diff_selects_only_always_verifiers(self) -> None:
        plan = self.targeted_plan()
        mission = plan["missions"][0]
        del mission["tasks"][1]["verifiers"][0]["selection"]
        result = applicable_targeted_verifiers(mission, [])
        self.assertEqual(result["worker_verifier_ids"], [])
        self.assertEqual(
            result["task_verifier_ids"],
            {"M1/T01": [], "M1/T02": ["verify-m1-2"]},
        )

    def test_prefix_nonmatch_and_cross_cutting_scope(self) -> None:
        plan = self.targeted_plan()
        mission = plan["missions"][0]
        mission["worker_verifiers"][0]["selection"]["scopes"] = [
            "src/a/cross-cutting.py"
        ]
        result = applicable_targeted_verifiers(
            mission,
            ["src/ab/one.py", "src/a/cross-cutting.py"],
        )
        self.assertEqual(result["worker_verifier_ids"], ["worker-m1"])
        self.assertEqual(result["task_verifier_ids"], {"M1/T01": [], "M1/T02": []})

    def test_changed_files_are_exact_safe_and_unique(self) -> None:
        self.assertEqual(
            normalize_changed_files(["src/a/two.py", "src/a/one.py"]),
            ["src/a/one.py", "src/a/two.py"],
        )
        for changed_files in (
            ["../outside.py"],
            ["src/a/**"],
            ["src/a/one.py", "src/a/one.py"],
        ):
            with self.subTest(changed_files=changed_files):
                with self.assertRaises(VerifierSelectionError):
                    normalize_changed_files(changed_files)

    def test_invalid_plan_and_head_are_rejected(self) -> None:
        plan = self.targeted_plan()
        escaped = copy.deepcopy(plan)
        escaped["missions"][0]["tasks"][0]["verifiers"][0]["selection"][
            "scopes"
        ] = ["src/ab/**"]
        with self.assertRaises(VerifierSelectionError):
            select_verifiers(escaped, "M1", ["src/a/one.py"])
        with self.assertRaises(VerifierSelectionError):
            select_verifiers(plan, "M1", ["src/a/one.py"], head_sha="ABC")


if __name__ == "__main__":
    unittest.main()
