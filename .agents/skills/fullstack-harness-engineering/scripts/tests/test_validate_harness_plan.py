#!/usr/bin/env python3
"""Dedicated CLI tests for validate_harness_plan.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from test_select_parallel_missions import manifest_markdown  # noqa: E402


class ValidateHarnessPlanCliTests(unittest.TestCase):
    def run_cli(self, plan_path: Path, run_path: Path | None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPTS_DIR / "validate_harness_plan.py"), "--plan", str(plan_path)]
        if run_path is not None:
            command.extend(["--run", str(run_path), "--repo-root", str(plan_path.parent)])
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def test_valid_plan_and_run_report_pass(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, run_path)

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual([], payload["errors"])
        self.assertEqual(plan["plan_id"], payload["plan_id"])

    def test_plan_only_invocation_skips_run_validation(self) -> None:
        plan = valid_plan()
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("PASS", json.loads(result.stdout)["status"])

    def test_invalid_plan_reports_fail_with_exit_code_one(self) -> None:
        plan = valid_plan()
        plan["missions"] = []
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertTrue(payload["errors"])

    def test_malformed_manifest_reports_error_with_exit_code_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            plan_path.write_text("# not a manifest\n", encoding="utf-8")

            result = self.run_cli(plan_path, None)

        self.assertEqual(2, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("ERROR", payload["status"])
        self.assertTrue(payload["errors"])


if __name__ == "__main__":
    unittest.main()
