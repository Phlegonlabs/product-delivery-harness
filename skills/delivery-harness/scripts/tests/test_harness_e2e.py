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

import manifest_fixtures as mf
from manifest_fixtures import manifest_markdown  # noqa: E402
from test_harness_manifest import (  # noqa: E402
    authorize_execution,
    native_capability_probe,
    current_version_gate,
)
from test_graph_orchestration import (  # noqa: E402
    authorize,
    detach_mission_edges,
    mission_nodes,
    valid_graph_plan,
    valid_graph_run,
)
from harness_manifest import plan_digest  # noqa: E402


class HarnessCliE2ETests(unittest.TestCase):
    def run_cli(
        self,
        script: str,
        plan_path: Path,
        run_path: Path,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPTS_DIR / script),
            "--plan",
            str(plan_path),
            "--run",
            str(run_path),
        ]
        if script in {"validate_harness_plan.py", "select_ready_nodes.py"}:
            command.extend(["--repo-root", str(plan_path.parent)])
        if extra_args:
            command.extend(extra_args)
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )

    def validate_and_select(
        self, plan: dict[str, object], run: dict[str, object]
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mf.materialize_plan_sources(root, plan)
            states = run["graph_state"]["edge_states"]
            run["graph_state"]["edge_states"] = {
                edge["id"]: states.get(edge["id"], {"status": "dormant", "traversals": 0, "source_attempt_id": None})
                for edge in plan["graph"]["edges"]
            }
            digest = plan_digest(plan)
            run["plan"]["digest_sha256"] = digest

            def refresh_plan_bindings(value: object) -> None:
                if isinstance(value, dict):
                    if "plan_digest_sha256" in value:
                        value["plan_digest_sha256"] = digest
                    for child in value.values():
                        refresh_plan_bindings(child)
                elif isinstance(value, list):
                    for child in value:
                        refresh_plan_bindings(child)

            refresh_plan_bindings(run)
            plan_text = manifest_markdown(
                "## Harness Plan Manifest", "harness_plan", plan
            )
            self.git(root, "init")
            self.git(root, "config", "user.name", "Harness Test")
            self.git(root, "config", "user.email", "harness@example.invalid")
            self.git(root, "checkout", "-b", run["integration"]["branch"])
            (root / "README.md").write_text("base\n", encoding="utf-8")
            self.git(root, "add", "README.md", "docs/product")
            self.git(root, "commit", "-m", "base")
            head_sha = self.git(root, "rev-parse", "HEAD").stdout.strip()
            run["integration"]["batch_base_sha"] = head_sha
            run["integration"]["integration_head_sha"] = head_sha
            if isinstance(run.get("observed", {}).get("git"), dict):
                run["observed"]["git"]["parent_head_sha"] = head_sha

            run_text = manifest_markdown("## Harness Run State", "harness_run", run)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(plan_text, encoding="utf-8")
            run_path.write_text(run_text, encoding="utf-8")

            validation = self.run_cli(
                "validate_harness_plan.py",
                plan_path,
                run_path,
                ["--prd", str(root / "docs" / "product" / "PRD.md")],
            )
            self.assertEqual(0, validation.returncode, validation.stdout + validation.stderr)
            self.assertEqual("", validation.stderr)
            self.assertEqual("PASS", json.loads(validation.stdout)["status"])

            selection = self.run_cli("select_ready_nodes.py", plan_path, run_path)
            self.assertEqual(0, selection.returncode, selection.stderr)
            self.assertEqual("", selection.stderr)
            proposal = json.loads(selection.stdout)
            self.assertEqual(plan_text, plan_path.read_text(encoding="utf-8"))
            self.assertEqual(run_text, run_path.read_text(encoding="utf-8"))
            return proposal

    def test_validated_host_run_selects_native_subagent_launch_path(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        for node in mission_nodes(plan):
            node["runtime"] = {
                "preferred_provider": "claude_code",
                "allowed_providers": ["claude_code"],
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
                "runtime_adapter": {
                    "capability_probe": native_capability_probe(subagents=True),
                    "provider": "claude_code",
                    "available_drivers": [
                        "subagents",
                        "sequential_parent",
                    ],
                    "detection_source": "observed",
                    "version_gate": current_version_gate(),
                },
            }
        )
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        proposal = self.validate_and_select(plan, run)

        self.assertEqual(
            ["N-M1", "N-M2"],
            [item["node_id"] for item in proposal["dispatchable_nodes"]],
        )
        self.assertEqual(
            ["spawn_subagent", "spawn_subagent"],
            [item["launch_kind"] for item in proposal["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["runtime_provider"] == "claude_code"
                and item["runtime_driver"] == "subagents"
                and item["runtime_source"] == "host"
                for item in proposal["dispatchable_nodes"]
            )
        )


    def git(
        self, cwd: Path, *args: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and completed.returncode != 0:
            self.fail(
                f"git {' '.join(args)} failed in {cwd}:\n{completed.stdout}\n{completed.stderr}"
            )
        return completed


if __name__ == "__main__":
    unittest.main()
