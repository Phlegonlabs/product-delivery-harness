"""End-to-end coverage for the shipped Harness command-line flow."""

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

from test_select_parallel_missions import (  # noqa: E402
    configure_app_task_fanout,
    make_plan,
    make_run,
    manifest_markdown,
    mission,
    upgrade_to_schema_v6,
)


class HarnessCliE2ETests(unittest.TestCase):
    def run_cli(
        self, script: str, plan_path: Path, run_path: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / script),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
            ],
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
                mission("M2", priority=10, merge_rank=20),
                mission("M1", priority=20, merge_rank=10),
            ]
        )
        run = make_run(plan)
        configure_app_task_fanout(run, ["M1", "M2"])
        upgrade_to_schema_v6(
            run,
            "codex",
            ["sequential_parent", "subagents", "app_threads"],
        )
        proposal = self.validate_and_select(plan, run)

        self.assertEqual(["M1", "M2"], proposal["selected_missions"])
        self.assertEqual(
            {
                "provider": "codex",
                "driver": "app_threads",
                "detection_source": "observed",
            },
            proposal["runtime_route"],
        )
        self.assertEqual(
            ["create_thread", "create_thread"],
            [item["launch_kind"] for item in proposal["launch_directives"]],
        )
        self.assertEqual(
            ["M1", "M2"],
            [item["mission_id"] for item in proposal["launch_directives"]],
        )


if __name__ == "__main__":
    unittest.main()
