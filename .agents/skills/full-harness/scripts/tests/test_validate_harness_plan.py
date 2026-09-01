#!/usr/bin/env python3
"""Dedicated CLI tests for validate_harness_plan.py."""

from __future__ import annotations

import hashlib
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

from harness_manifest import plan_digest  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from manifest_fixtures import manifest_markdown  # noqa: E402


HOME_SURFACE = {
    "id": "home",
    "trace_ids": ["REQ-001"],
    "route": "/home",
    "breakpoints": ["390"],
    "states": ["ready"],
    "evidence_gate": "required",
}


class ValidateHarnessPlanCliTests(unittest.TestCase):
    def run_cli(
        self,
        plan_path: Path,
        run_path: Path | None,
        design_system: Path | None = None,
        repo_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPTS_DIR / "validate_harness_plan.py"), "--plan", str(plan_path)]
        if run_path is not None:
            command.extend(["--run", str(run_path)])
        if repo_root is None and run_path is not None:
            repo_root = plan_path.parent
        if repo_root is not None:
            command.extend(["--repo-root", str(repo_root)])
        if design_system is not None:
            command.extend(["--design-system", str(design_system)])
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def cross_check(self, registry: dict[str, object]) -> dict[str, object]:
        """Validate a one-surface PLAN against `registry`; return the CLI payload."""
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            registry_path = root / "design-system.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            result = self.run_cli(plan_path, None, design_system=registry_path)
        return json.loads(result.stdout)

    def test_valid_plan_and_run_report_pass(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "harness@example.invalid"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "checkout", "-b", run["integration"]["branch"]],
                cwd=root, check=True, capture_output=True, text=True,
            )
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "base"],
                cwd=root, check=True, capture_output=True, text=True,
            )
            head_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root, check=True, capture_output=True, text=True,
            ).stdout.strip()
            run["integration"]["integration_head_sha"] = head_sha
            for source in plan["sources"]:
                location = source["location"]
                contents = f"{source['id']} frozen source\n".encode()
                source_path = root / location
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(contents)
                source["content_sha256"] = hashlib.sha256(contents).hexdigest()
            run["plan"]["digest_sha256"] = plan_digest(plan)

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

    def test_canonical_single_mission_plan_only_validation_allows_no_batch_gate(self) -> None:
        plan_path = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"
        result = self.run_cli(plan_path, None)

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PASS", payload["status"])
        self.assertEqual([], payload["errors"])

    def test_repo_root_binds_current_plan_sources_when_requested(self) -> None:
        plan = valid_plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )

            result = self.run_cli(plan_path, None, repo_root=root)

        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("FAIL", payload["status"])
        self.assertTrue(any("does not exist under --repo-root" in error for error in payload["errors"]))

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

    def test_recipe_state_coverage_is_cross_checked_against_the_registry(self) -> None:
        payload = self.cross_check(
            {"viewports": [390], "stateMatrix": ["ready", "loading", "empty", "n/a"]}
        )

        self.assertEqual("FAIL", payload["status"])
        joined = " ".join(payload["errors"])
        self.assertIn("omits state loading", joined)
        self.assertIn("omits state empty", joined)
        self.assertIn("omits state n/a", joined)
        self.assertNotIn("/settings", joined)

    def test_registry_cross_check_enforces_responsive_values_per_surface(self) -> None:
        payload = self.cross_check(
            {"viewports": [390, 768], "stateMatrix": ["ready", "error"]}
        )

        joined = " ".join(payload["errors"])
        self.assertIn("surface home route /home omits state error", joined)
        self.assertIn("surface home route /home omits responsive target 768", joined)
        self.assertNotIn("UI-001", joined)

    def test_registry_cross_check_rejects_malformed_evidence_contract(self) -> None:
        payload = self.cross_check(
            {
                "viewports": [0],
                "stateMatrix": ["ready", " "],
                "$note": "both halves malformed; stateMatrix is reported first",
            }
        )

        joined = " ".join(payload["errors"])
        # A malformed stateMatrix stops the cross-check before the responsive
        # set is read, so only the first defect is reported per run.
        self.assertIn("stateMatrix: must be a non-empty string list", joined)

    def test_registry_cross_check_is_skipped_without_the_flag(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [dict(HOME_SURFACE)]
        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            plan_path.write_text(manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")

            result = self.run_cli(plan_path, None)

        self.assertEqual(0, result.returncode)

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
