"""End-to-end coverage for the shipped Harness command-line flow."""

from __future__ import annotations

import hashlib
import json
import shutil
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
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402
from harness_manifest import plan_digest  # noqa: E402
from validate_node_result import validate_node_result  # noqa: E402
from validate_worker_result import validate_worker_result_data  # noqa: E402


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

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init")
            self.git(root, "config", "user.name", "Harness Test")
            self.git(root, "config", "user.email", "harness@example.invalid")
            self.git(root, "checkout", "-b", run["integration"]["branch"])
            (root / "README.md").write_text("base\n", encoding="utf-8")
            self.git(root, "add", "README.md")
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

    @unittest.skipUnless(shutil.which("git"), "git is required for worktree handoff coverage")
    def test_codex_candidates_are_git_verified_before_serial_integration(self) -> None:
        plan = valid_graph_plan()
        plan["missions"][0]["tasks"] = [plan["missions"][0]["tasks"][0]]
        plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        plan["graph"]["edges"] = [
            edge for edge in plan["graph"]["edges"] if edge["to"] == "N-COVERAGE-REVIEW"
        ]
        for node in plan["graph"]["nodes"]:
            if node["kind"] != "mission":
                continue
            node["runtime"] = {
                "preferred_provider": "codex",
                "allowed_providers": ["codex"],
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repo"
            repository.mkdir()
            self.git(repository, "init")
            self.git(repository, "config", "user.name", "Harness Test")
            self.git(repository, "config", "user.email", "harness@example.invalid")
            (repository / "README.md").write_text("base\n", encoding="utf-8")
            self.git(repository, "add", "README.md")
            self.git(repository, "commit", "-m", "base")
            base_sha = self.git(repository, "rev-parse", "HEAD").stdout.strip()
            self.git(repository, "switch", "-c", "integration")

            worktrees = {
                "M1": root / "worker-m1",
                "M2": root / "worker-m2",
            }
            branches = {
                "M1": "refs/heads/codex/worker-m1",
                "M2": "refs/heads/codex/worker-m2",
            }
            changes = {
                "M1": ("src/a/one.py", "mission one\n"),
                "M2": ("src/ab/one.py", "mission two\n"),
            }
            heads: dict[str, str] = {}
            for mission_id in ("M1", "M2"):
                short_branch = branches[mission_id].removeprefix("refs/heads/")
                self.git(
                    repository,
                    "worktree",
                    "add",
                    "-b",
                    short_branch,
                    str(worktrees[mission_id]),
                    base_sha,
                )
                changed_file, contents = changes[mission_id]
                target = worktrees[mission_id] / changed_file
                target.parent.mkdir(parents=True)
                target.write_text(contents, encoding="utf-8")
                self.git(worktrees[mission_id], "add", changed_file)
                self.git(worktrees[mission_id], "commit", "-m", f"implement {mission_id}")
                heads[mission_id] = self.git(
                    worktrees[mission_id], "rev-parse", "HEAD"
                ).stdout.strip()

            run = valid_graph_run(plan)
            digest = plan_digest(plan)
            run.update(
                {
                    "status": "running",
                    "intent": "execute-ready-plan",
                    "plan_readiness": "ready",
                    "execution_authorized": True,
                    "execution_authorization_source": "test execution authorization",
                    "execution_authorization_scope": {
                        "run_id": run["run_id"],
                        "mission_ids": ["M1", "M2"],
                        "expires_when": "run_complete",
                    },
                }
            )
            run["integration"].update(
                {"branch": "integration", "batch_base_sha": base_sha, "integration_head_sha": base_sha}
            )
            run["landing"]["mode"] = "local_only"
            run["active_wave"].update(
                {
                    "wave_id": "B-CODEX-1",
                    "status": "active",
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": digest,
                    "batch_base_sha": base_sha,
                    "selected_missions": ["M1", "M2"],
                    "deferred_missions": [],
                    "conflict_edges": [],
                }
            )
            run["runtime_capabilities"].update(
                {
                    "worker_runtime": "subagent",
                    "workspace_mode": "parent_managed_worktree",
                    "completion_channel": "agent_result",
                    "max_parallel_workers": 2,
                }
            )
            run["runtime_capabilities"]["runtime_adapter"] = {
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
            }
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(repository),
                    "parent_branch": "integration",
                    "parent_head_sha": base_sha,
                    "parent_dirty": False,
                    "worktrees": [
                        {
                            "path": str(worktrees[mission_id]),
                            "branch_ref": branches[mission_id],
                            "head_sha": heads[mission_id],
                            "managed_by": "parent",
                            "dirty": False,
                        }
                        for mission_id in ("M1", "M2")
                    ],
                }
            )
            run["observed"]["runtime"].update(
                {"available_worker_slots": 2, "isolation_capacity": 2}
            )
            for action, targets in {
                "spawn_subagents": ["*"],
                "create_local_worktrees": ["*"],
                "create_local_branches": ["*"],
            }.items():
                run["authorizations"][action] = {
                    "authorized": True,
                    "source": f"test {action} authorization",
                    "scope": {
                        "run_id": run["run_id"],
                        "mission_ids": ["M1", "M2"],
                        "targets": targets,
                    },
                    "expires_when": "run_complete",
                }
            run["authorizations"]["create_local_commits"] = {
                "authorized": True,
                "source": "test commit authorization",
                "scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1", "M2"],
                    "targets": [f"branch:{branches['M1']}", f"branch:{branches['M2']}"],
                },
                "expires_when": "run_complete",
            }

            candidates: dict[str, dict[str, object]] = {}
            for mission_id, node_id in (("M1", "N-M1"), ("M2", "N-M2")):
                attempt_id = f"ATT-{node_id}-1"
                worker_id = f"W-{mission_id}-CODEX"
                lease_id = f"LEASE-{mission_id}-CODEX"
                run["graph_state"]["node_states"][node_id].update(
                    {
                        "phase": "running",
                        "attempts": 1,
                        "last_attempt_id": attempt_id,
                        "bound_worker_id": worker_id,
                    }
                )
                run["mission_states"][mission_id].update(
                    {
                        "phase": "worker_running",
                        "lease_id": lease_id,
                        "lease_plan_revision": plan["revision"],
                        "lease_plan_digest_sha256": digest,
                        "worker_id": worker_id,
                        "base_sha": base_sha,
                    }
                )
                task_id = plan["missions"][[item["id"] for item in plan["missions"]].index(mission_id)][
                    "tasks"
                ][0]["id"]
                run["task_states"][task_id].update({"phase": "running", "attempts": 1})
                run["workers"].append(
                    {
                        "worker_id": worker_id,
                        "mission_id": mission_id,
                        "lease_id": lease_id,
                        "plan_revision": plan["revision"],
                        "plan_digest_sha256": digest,
                        "batch_base_sha": base_sha,
                        "worker_runtime": "subagent",
                        "workspace_mode": "parent_managed_worktree",
                        "completion_channel": "agent_result",
                        "runtime_binding": {
                            "provider": "codex",
                            "driver": "subagents",
                            "source": "host",
                            "model": None,
                            "reasoning_effort": None,
                            "option_source": "provider_default",
                        },
                        "task_thread_id": None,
                        "worktree_path": str(worktrees[mission_id]),
                        "branch_ref": branches[mission_id],
                        "report_path": None,
                        "phase": "worker_running",
                        "worker_head_sha": None,
                    }
                )
                candidates[mission_id] = self.codex_candidate(
                    plan,
                    run,
                    mission_id=mission_id,
                    node_id=node_id,
                    attempt_id=attempt_id,
                    lease_id=lease_id,
                    head_sha=heads[mission_id],
                    changed_file=changes[mission_id][0],
                    worktree_path=worktrees[mission_id],
                    branch_ref=branches[mission_id],
                )

            for mission_id in ("M1", "M2"):
                candidate = candidates[mission_id]
                node_result = candidate["node_result"]
                worker_result = node_result["worker_result"]
                self.assertEqual([], validate_node_result(plan, run, node_result))
                self.git(repository, "cat-file", "-e", f"{heads[mission_id]}^{{commit}}")
                ancestry = self.git(
                    repository,
                    "merge-base",
                    "--is-ancestor",
                    base_sha,
                    heads[mission_id],
                    check=False,
                ).returncode == 0
                observed_files = self.git(
                    repository,
                    "diff",
                    "--name-only",
                    base_sha,
                    heads[mission_id],
                ).stdout.splitlines()
                self.assertEqual(
                    [],
                    validate_worker_result_data(
                        plan,
                        run,
                        worker_result,
                        observed_head_sha=heads[mission_id],
                        observed_changed_files=observed_files,
                        ancestry_confirmed=ancestry,
                    ),
                )
                self.assertEqual(
                    "worker_running", run["mission_states"][mission_id]["phase"]
                )
                self.assertEqual(
                    "planned", run["mission_states"][mission_id]["integration_gate"]
                )

            integrated_heads: list[str] = []
            for mission_id in ("M1", "M2"):
                self.git(repository, "cherry-pick", heads[mission_id])
                integrated_head = self.git(repository, "rev-parse", "HEAD").stdout.strip()
                integrated_heads.append(integrated_head)
                run["mission_states"][mission_id].update(
                    {
                        "phase": "integrated",
                        "head_sha": heads[mission_id],
                        "integration_gate": "PASS",
                        "integrated_sha": integrated_head,
                    }
                )
                run["graph_state"]["node_states"][f"N-{mission_id}"].update(
                    {"phase": "succeeded", "last_outcome": "pass"}
                )
                run["integration"]["integration_head_sha"] = integrated_head

            self.assertEqual(2, len(set(heads.values())))
            self.assertNotEqual(integrated_heads[0], integrated_heads[1])
            self.assertEqual("PASS", run["mission_states"]["M1"]["integration_gate"])
            self.assertEqual("PASS", run["mission_states"]["M2"]["integration_gate"])

    def codex_candidate(
        self,
        plan: dict[str, object],
        run: dict[str, object],
        *,
        mission_id: str,
        node_id: str,
        attempt_id: str,
        lease_id: str,
        head_sha: str,
        changed_file: str,
        worktree_path: Path,
        branch_ref: str,
    ) -> dict[str, object]:
        mission_item = next(item for item in plan["missions"] if item["id"] == mission_id)
        task_item = mission_item["tasks"][0]
        task_verifier_id = task_item["verifiers"][0]["id"]
        worker_verifier_id = mission_item["worker_verifiers"][0]["id"]
        worker_result = {
            "type": "WORKER_RESULT",
            "run_id": run["run_id"],
            "plan_id": plan["plan_id"],
            "mission_id": mission_id,
            "lease_id": lease_id,
            "status": "worker_passed",
            "current_task_id": None,
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "base_sha": run["integration"]["batch_base_sha"],
            "head_sha": head_sha,
            "diff_summary": f"Implemented {mission_id} in its isolated worktree.",
            "changed_files": [changed_file],
            "task_results": [
                {
                    "task_id": task_item["id"],
                    "status": "worker_passed",
                    "head_sha": head_sha,
                    "verifier_ids": [task_verifier_id],
                    "commits": [head_sha],
                    "evidence_paths": [f"evidence/{mission_id}-task.txt"],
                }
            ],
            "verifiers": [
                {
                    "id": task_verifier_id,
                    "status": "PASS",
                    "evidence": hashlib.sha256(
                        f"{mission_id}-{task_verifier_id}-{head_sha}".encode()
                    ).hexdigest(),
                },
                {
                    "id": worker_verifier_id,
                    "status": "PASS",
                    "evidence": hashlib.sha256(
                        f"{mission_id}-{worker_verifier_id}-{head_sha}".encode()
                    ).hexdigest(),
                },
            ],
            "commits": [head_sha],
            "evidence_paths": [f"evidence/{mission_id}-worker.txt"],
            "subagent_activity": {
                "status": "not_applicable",
                "skip_reason": "native codex subagents use flat parent orchestration",
                "children": [],
            },
            "blockers": [],
            "residual_risks": [],
            "integration_notes": "Parent must verify Git facts before integration.",
        }
        return {
            "node_result": {
                "run_id": run["run_id"],
                "node_id": node_id,
                "attempt_id": attempt_id,
                "plan_id": plan["plan_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "graph_revision": run["graph_state"]["graph_revision"],
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "status": "succeeded",
                "outcome": "pass",
                "worker_result": worker_result,
                "refinement_request": None,
                "evidence_paths": [f"evidence/{mission_id}-node.json"],
            },
            "runtime_evidence": {
                "worktree_path": str(worktree_path),
                "branch_ref": branch_ref,
                "head_sha": head_sha,
            },
        }

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
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init")
            self.git(root, "config", "user.name", "Harness Test")
            self.git(root, "config", "user.email", "harness@example.invalid")
            self.git(root, "checkout", "-b", run["integration"]["branch"])
            (root / "README.md").write_text("base\n", encoding="utf-8")
            self.git(root, "add", "README.md")
            self.git(root, "commit", "-m", "base")
            head_sha = self.git(root, "rev-parse", "HEAD").stdout.strip()
            run["integration"]["batch_base_sha"] = head_sha
            run["integration"]["integration_head_sha"] = head_sha
            if isinstance(run.get("observed", {}).get("git"), dict):
                run["observed"]["git"]["parent_head_sha"] = head_sha

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
