"""End-to-end coverage for the shipped Harness command-line flow."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from manifest_fixtures import manifest_markdown  # noqa: E402
from test_harness_manifest import (  # noqa: E402
    authorize_execution,
    codex_capability_probe,
    current_version_gate,
    legacy_plan,
    legacy_run,
    mark_legacy_complete,
    mark_complete,
    valid_closeout_run,
    valid_plan,
)
from test_graph_orchestration import (  # noqa: E402
    authorize,
    detach_mission_edges,
    mission_nodes,
    valid_graph_plan,
    valid_graph_run,
)
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
        if script in {"validate_harness_plan.py", "select_ready_nodes.py"}:
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
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source in plan["sources"]:
                location = source["location"]
                if "://" in location:
                    continue
                contents = f"{source['id']} frozen source\n".encode()
                source_path = root / location
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(contents)
                source["content_sha256"] = hashlib.sha256(contents).hexdigest()
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

            selection = self.run_cli("select_ready_nodes.py", plan_path, run_path)
            self.assertEqual(0, selection.returncode, selection.stderr)
            self.assertEqual("", selection.stderr)
            proposal = json.loads(selection.stdout)
            self.assertEqual(plan_text, plan_path.read_text(encoding="utf-8"))
            self.assertEqual(run_text, run_path.read_text(encoding="utf-8"))
            return proposal

    def test_validated_claude_run_selects_dynamic_workflow_launch_path(self) -> None:
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
                    "provider": "claude_code",
                    "available_drivers": [
                        "dynamic_workflow",
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
            ["run_dynamic_workflow", "run_dynamic_workflow"],
            [item["launch_kind"] for item in proposal["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["runtime_provider"] == "claude_code"
                and item["runtime_driver"] == "dynamic_workflow"
                and item["runtime_source"] == "host"
                for item in proposal["dispatchable_nodes"]
            )
        )

    def test_validated_codex_run_selects_app_thread_wave(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        for node in mission_nodes(plan):
            node["runtime"] = {
                "preferred_provider": "codex",
                "allowed_providers": ["codex"],
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "max_parallel_workers": 2,
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": [
                        "app_threads",
                        "subagents",
                        "sequential_parent",
                    ],
                    "detection_source": "observed",
                    "capability_probe": codex_capability_probe(
                        app_threads=True,
                        subagents=True,
                    ),
                    "version_gate": current_version_gate(),
                },
                "nested_subagents": {
                    "available": True,
                    "max_depth": 1,
                    "max_children_per_worker": 3,
                    "allowed_roles": ["reviewer"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
                "platform_lifecycle": {
                    "owner": "app",
                    "automatic_retention_cleanup_possible": True,
                    "durable_branch_required_before_unique_work": True,
                },
            }
        )
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        for action in (
            "spawn_subagents",
            "create_user_owned_tasks",
            "create_app_managed_worktrees",
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
            ["create_thread", "create_thread"],
            [item["launch_kind"] for item in proposal["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["runtime_provider"] == "codex"
                and item["runtime_driver"] == "app_threads"
                and item["runtime_source"] == "host"
                for item in proposal["dispatchable_nodes"]
            )
        )

    @unittest.skipUnless(shutil.which("git"), "git is required for worktree handoff coverage")
    def test_codex_candidates_are_git_verified_before_serial_integration(self) -> None:
        plan = valid_graph_plan()
        plan["missions"][0]["tasks"] = [plan["missions"][0]["tasks"][0]]
        plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        plan["graph"]["edges"] = [
            edge for edge in plan["graph"]["edges"] if edge["id"] != "E-M1-M2"
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
                        "plan_revision": plan["revision"],
                        "plan_digest_sha256": digest,
                        "mission_ids": ["M1", "M2"],
                        "expires_when": "run_complete",
                    },
                }
            )
            run["integration"].update(
                {"branch": "integration", "batch_base_sha": base_sha, "integration_head_sha": base_sha}
            )
            run["landing"]["mode"] = "local_only"
            run["landing"]["continuity"] = {
                "status": "planned",
                "branch_ref": "refs/heads/integration",
                "head_sha": None,
                "reason": None,
            }
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
                "capability_probe": codex_capability_probe(subagents=True),
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
                "spawn_subagents": [
                    "*",
                    "worker:W-M1-CODEX",
                    "worker:W-M2-CODEX",
                ],
                "create_local_worktrees": [
                    f"worktree:{worktrees['M1']}",
                    f"worktree:{worktrees['M2']}",
                ],
                "create_local_branches": [
                    f"branch:{branches['M1']}",
                    f"branch:{branches['M2']}",
                ],
            }.items():
                run["authorizations"][action] = {
                    "authorized": True,
                    "source": f"test {action} authorization",
                    "scope": {
                        "run_id": run["run_id"],
                        "plan_revision": plan["revision"],
                        "plan_digest_sha256": digest,
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
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": digest,
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
                for prior_review in run["review_workers"]:
                    prior_review["phase"] = "superseded"
                review_attempt_id = f"ATT-REVIEW-{mission_id}"
                review_worker_id = f"RW-{mission_id}"
                review_node_id = f"N-REVIEW-{mission_id}"
                run["mission_states"][mission_id]["head_sha"] = heads[mission_id]
                run["graph_state"]["node_states"][review_node_id].update(
                    {
                        "phase": "succeeded",
                        "attempts": len(run["review_workers"]) + 1,
                        "last_attempt_id": review_attempt_id,
                        "last_outcome": "pass",
                        "bound_worker_id": review_worker_id,
                    }
                )
                run["review_workers"].append(
                    {
                        "worker_id": review_worker_id,
                        "node_id": review_node_id,
                        "attempt_id": review_attempt_id,
                        "plan_revision": plan["revision"],
                        "plan_digest_sha256": digest,
                        "graph_revision": run["graph_state"]["graph_revision"],
                        "reviewed_sha": heads[mission_id],
                        "review_path": str(worktrees[mission_id]),
                        "worker_runtime": "subagent",
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
                        "report_path": None,
                        "phase": "worker_passed",
                        "outcome": "pass",
                        "findings": [],
                    }
                )
                self.assertEqual(
                    [],
                    validate_worker_result_data(
                        plan,
                        run,
                        worker_result,
                        observed_head_sha=heads[mission_id],
                        observed_changed_files=observed_files,
                        ancestry_confirmed=ancestry,
                        retained_verifier_results=candidate[
                            "retained_verifier_results"
                        ],
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

    def retained_verifier_result(
        self,
        plan: dict[str, object],
        run: dict[str, object],
        verifier: dict[str, object],
        *,
        head_sha: str,
        changed_files: list[str],
        layer: str,
        mission_id: str,
        task_id: str | None,
        attempt_id: str,
        lease_id: str,
    ) -> dict[str, object]:
        changed_files = sorted(changed_files)
        context = {
            "run_id": run["run_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "head_sha": head_sha,
            "changed_files": changed_files,
            "trust_domain": "parent_local",
            "checkout_role": "worker",
            "checkout_dirty": False,
            "cache_safe": True,
            "layer": layer,
            "mission_id": mission_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "lease_id": lease_id,
        }
        key_document = {
            "protocol": "harness-verifier-execution-v1",
            "verifier_id": verifier["id"],
            "layer": layer,
            "mission_id": mission_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "lease_id": lease_id,
            "run_id": context["run_id"],
            "plan_revision": context["plan_revision"],
            "plan_digest_sha256": context["plan_digest_sha256"],
            "graph_revision": context["graph_revision"],
            "batch_base_sha": context["batch_base_sha"],
            "head_sha": context["head_sha"],
            "changed_files_digest": hashlib.sha256(
                json.dumps(
                    changed_files,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "trust_domain": context["trust_domain"],
            "checkout_role": context["checkout_role"],
            "checkout_dirty": context["checkout_dirty"],
            "cache_safe": context["cache_safe"],
            "cwd": verifier["cwd"],
            "argv": verifier["argv"],
            "pass_signal": verifier["pass_signal"],
            "cache_mode": "disabled",
            "environment_keys": [],
            "platform": {"system": "test", "machine": "test"},
            "executable_identity": {
                "path": "C:/python",
                "size": 1,
                "mtime_ns": 1,
                "device": 1,
                "inode": 1,
            },
            "environment_digests": {},
        }
        execution_key = hashlib.sha256(
            json.dumps(
                key_document,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return {
            "protocol": "harness-verifier-execution-v1",
            "verifier_id": verifier["id"],
            "status": "PASS",
            "exit_code": 0,
            "execution_key": execution_key,
            "evidence_key": execution_key,
            "verifier": {
                "id": verifier["id"],
                "cwd": verifier["cwd"],
                "argv": verifier["argv"],
                "pass_signal": verifier["pass_signal"],
                "cache": {"mode": "disabled", "environment_keys": []},
            },
            "context": context,
            "key_document": key_document,
        }

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
        task_verifier = task_item["verifiers"][0]
        worker_verifier = mission_item["worker_verifiers"][0]
        task_attempt_id = f"{attempt_id}-TASK"
        retained_results = [
            self.retained_verifier_result(
                plan,
                run,
                task_verifier,
                head_sha=head_sha,
                changed_files=[changed_file],
                layer="task",
                mission_id=mission_id,
                task_id=task_item["id"],
                attempt_id=task_attempt_id,
                lease_id=lease_id,
            ),
            self.retained_verifier_result(
                plan,
                run,
                worker_verifier,
                head_sha=head_sha,
                changed_files=[changed_file],
                layer="worker",
                mission_id=mission_id,
                task_id=None,
                attempt_id=attempt_id,
                lease_id=lease_id,
            ),
        ]
        run["attempt_log"].extend(
            [
                {
                    "attempt_id": task_attempt_id,
                    "mission_id": mission_id,
                    "task_id": task_item["id"],
                    "lease_id": lease_id,
                    "kind": "task_verifier",
                    "result": "PASS",
                    "evidence": [],
                },
                {
                    "attempt_id": attempt_id,
                    "mission_id": mission_id,
                    "task_id": None,
                    "lease_id": lease_id,
                    "kind": "worker_verifier",
                    "result": "PASS",
                    "evidence": [],
                },
            ]
        )
        task_verifier_id = task_verifier["id"]
        worker_verifier_id = worker_verifier["id"]
        retained_by_id = {
            item["verifier_id"]: item for item in retained_results
        }
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
                    "evidence": retained_by_id[task_verifier_id]["execution_key"],
                },
                {
                    "id": worker_verifier_id,
                    "status": "PASS",
                    "evidence": retained_by_id[worker_verifier_id]["execution_key"],
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
            "retained_verifier_results": retained_results,
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
        plan = legacy_plan()
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
        run = legacy_run(plan, 9)
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

            mark_legacy_complete(plan, run)
            buffer = io.BytesIO()
            Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
            contents = buffer.getvalue()
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
