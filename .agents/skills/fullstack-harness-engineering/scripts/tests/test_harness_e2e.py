"""End-to-end coverage for the shipped Harness command-line flow."""

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

from test_select_parallel_missions import (  # noqa: E402
    configure_app_task_fanout,
    make_plan,
    make_run,
    manifest_markdown,
    mission,
    upgrade_to_schema_v6,
)
from test_harness_manifest import (  # noqa: E402
    mark_complete,
    valid_closeout_run,
    valid_plan,
)


class HarnessCliE2ETests(unittest.TestCase):
    def run_cli(
        self, script: str, plan_path: Path, run_path: Path
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPTS_DIR / script),
            "--plan",
            str(plan_path),
            "--run",
            str(run_path),
        ]
        if script == "validate_harness_plan.py":
            command.extend(["--repo-root", str(plan_path.parent)])
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )

    def validate_and_select(
        self, plan: dict[str, object], run: dict[str, object]
    ) -> dict[str, object]:
        plan_text = manifest_markdown(
            "## Harness Plan Manifest", "harness_plan", plan
        )
        run_text = manifest_markdown("## Harness Run State", "harness_run", run)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(plan_text, encoding="utf-8")
            run_path.write_text(run_text, encoding="utf-8")

            validation = self.run_cli(
                "validate_harness_plan.py", plan_path, run_path
            )
            self.assertEqual(0, validation.returncode, validation.stderr)
            self.assertEqual("", validation.stderr)
            self.assertEqual("PASS", json.loads(validation.stdout)["status"])

            selection = self.run_cli(
                "select_parallel_missions.py", plan_path, run_path
            )
            self.assertEqual(0, selection.returncode, selection.stderr)
            self.assertEqual("", selection.stderr)
            proposal = json.loads(selection.stdout)
            self.assertEqual(plan_text, plan_path.read_text(encoding="utf-8"))
            self.assertEqual(run_text, run_path.read_text(encoding="utf-8"))
            return proposal

    def test_validated_claude_run_selects_one_dynamic_workflow(self) -> None:
        plan = make_plan(
            [
                mission("M2", priority=10, merge_rank=20),
                mission("M1", priority=20, merge_rank=10),
            ]
        )
        run = make_run(plan)
        upgrade_to_schema_v6(
            run,
            "claude_code",
            ["sequential_parent", "subagents", "dynamic_workflow"],
        )
        proposal = self.validate_and_select(plan, run)

        self.assertEqual(["M1", "M2"], proposal["selected_missions"])
        self.assertEqual(
            {
                "provider": "claude_code",
                "driver": "dynamic_workflow",
                "detection_source": "observed",
            },
            proposal["runtime_route"],
        )
        self.assertEqual(
            {
                "launch_kind": "run_dynamic_workflow",
                "mission_ids": ["M1", "M2"],
                "script_path": "assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js",
                "args_source": "accepted_wave",
            },
            proposal["wave_launch"],
        )

    def test_validated_codex_run_selects_app_thread_wave(self) -> None:
        plan = make_plan(
            [
                mission("M3", priority=5, merge_rank=30),
                mission("M2", priority=10, merge_rank=20),
                mission("M1", priority=20, merge_rank=10),
            ]
        )
        run = make_run(plan)
        configure_app_task_fanout(run, ["M1", "M2", "M3"])
        upgrade_to_schema_v6(
            run,
            "codex",
            ["sequential_parent", "subagents", "app_threads"],
        )
        proposal = self.validate_and_select(plan, run)

        self.assertEqual(["M1", "M2", "M3"], proposal["selected_missions"])
        self.assertEqual(
            {
                "provider": "codex",
                "driver": "app_threads",
                "detection_source": "observed",
            },
            proposal["runtime_route"],
        )
        self.assertEqual(
            ["create_thread", "create_thread", "create_thread"],
            [item["launch_kind"] for item in proposal["launch_directives"]],
        )
        self.assertEqual(
            ["M1", "M2", "M3"],
            [item["mission_id"] for item in proposal["launch_directives"]],
        )

    def test_validator_checks_schema_v9_screenshot_artifacts(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        contents = b"\x89PNG\r\n\x1a\nfixture"
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": hashlib.sha256(contents).hexdigest(),
                "head_sha": run["integration"]["integration_head_sha"],
                "status": "PASS",
            }
        ]
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

            missing = self.run_cli("validate_harness_plan.py", plan_path, run_path)
            self.assertEqual(1, missing.returncode)
            self.assertTrue(
                any("does not exist" in error for error in json.loads(missing.stdout)["errors"])
            )

            screenshot = root / "docs" / "goal" / "evidence" / "dashboard-desktop-loaded.png"
            screenshot.parent.mkdir(parents=True)
            screenshot.write_bytes(contents)
            present = self.run_cli("validate_harness_plan.py", plan_path, run_path)
            self.assertEqual(0, present.returncode, present.stdout)


if __name__ == "__main__":
    unittest.main()
