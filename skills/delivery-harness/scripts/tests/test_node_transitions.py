#!/usr/bin/env python3
"""Focused coverage for parent-owned typed graph node transitions."""

from __future__ import annotations

import copy
import hashlib
import sys
import json
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_core import ManifestError  # noqa: E402
from harness_manifest import load_run, plan_digest, validate_current_plan_run  # noqa: E402
from select_ready_nodes import select_ready_nodes  # noqa: E402
from verifier_runtime import protected_path_sha256, run_verifier  # noqa: E402


def verifier_dispatch(request: dict[str, object]) -> dict[str, object]:
    return {
        "branch": request["branch"],
        "head_sha": request["head_sha"],
        "checkout_root": request["checkout_root"],
        "request_sha256": harness_transition._json_sha256(request),
        "request": copy.deepcopy(request),
    }


def dispatch_attestation(
    request: dict[str, object],
    protected_paths: dict[str, str | None] | None = None,
) -> dict[str, object]:
    return {
        "request_sha256": harness_transition._json_sha256(request),
        "checkout_root": request["checkout_root"],
        "git_guard": copy.deepcopy(request["git_guard"]),
        "protected_path_sha256": dict(protected_paths or {}),
    }


def fake_verifier_dispatch(
    node_id: str, attempt_id: str, head_sha: str = "a" * 40
) -> dict[str, object]:
    request: dict[str, object] = {
        "node_id": node_id,
        "attempt_id": attempt_id,
        "branch": "codex/test",
        "head_sha": head_sha,
        "checkout_root": "C:/repo/integration",
        "reservation": {
            "node_id": node_id,
            "attempt_id": attempt_id,
            "nonce": "n" * 64,
        },
    }
    return verifier_dispatch(request)


class NodeTransitionTests(unittest.TestCase):
    def _approval_pair(self):
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run["status"] = "running"
        run["plan_readiness"] = "ready"
        run["runtime_capabilities"]["runtime_adapter"]["detection_source"] = "observed"
        run["runtime_capabilities"]["runtime_adapter"]["available_drivers"] = [
            "sequential_parent"
        ]
        plan["graph"]["nodes"].append(
            {
                "id": "N-APP",
                "kind": "approval",
                "ref": "approval-1",
                "executor": "human",
                "allowed_outcomes": ["pass", "blocked"],
                "max_attempts": 2,
                "runtime": None,
            }
        )
        plan["graph"]["nodes"].append(
            {
                "id": "N-RETRY",
                "kind": "approval",
                "ref": "retry",
                "executor": "human",
                "allowed_outcomes": ["pass", "blocked"],
                "max_attempts": 2,
                "runtime": None,
            }
        )
        plan["graph"]["entry_nodes"].append("N-APP")
        plan["graph"]["edges"].append(
            {
                "id": "E-APP-RETRY",
                "kind": "route",
                "from": "N-APP",
                "to": "N-RETRY",
                "on_outcomes": ["blocked"],
                "max_traversals": 1,
            }
        )
        for node_id in ("N-APP", "N-RETRY"):
            run["graph_state"]["node_states"][node_id] = {
                "phase": "dormant",
                "attempts": 0,
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
                "blockers": [],
            }
        run["graph_state"]["edge_states"]["E-APP-RETRY"] = {
            "status": "dormant",
            "traversals": 0,
            "source_attempt_id": None,
        }
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        return plan, run

    def test_cli_local_verifier_reserve_execute_record_spine(self) -> None:
        with (
            tempfile.TemporaryDirectory() as repo_dir,
            tempfile.TemporaryDirectory() as control_dir,
        ):
            root = Path(repo_dir)
            control = Path(control_dir)
            mf.init_repo(root, "README.md", default_branch="codex/test")
            plan = mf.valid_plan()
            plan["final_gates"][0]["argv"] = [
                sys.executable,
                "-c",
                "raise SystemExit(0)",
            ]
            plan["final_gates"][0]["pass_signal"] = "exit 0"
            plan["graph"]["nodes"].append(
                {
                    "id": "N-CLI-FINAL",
                    "kind": "verifier",
                    "ref": plan["final_gates"][0]["id"],
                    "executor": "local_command",
                    "allowed_outcomes": ["pass", "blocked"],
                    "max_attempts": 1,
                    "runtime": None,
                }
            )
            plan["graph"]["entry_nodes"].append("N-CLI-FINAL")
            source_contents = {
                "prd": b"# Test PRD\n",
                "architecture": b"# Test architecture\n",
            }
            for source in plan["sources"]:
                payload = source_contents[source["kind"]]
                source_path = root / source["location"]
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(payload)
                source["content_sha256"] = hashlib.sha256(payload).hexdigest()
            mf.git(root, "add", "docs/product")
            mf.git(root, "commit", "-qm", "contracts")
            head = mf.git(root, "rev-parse", "HEAD")

            run = mf.valid_run(plan)
            mf.authorize_execution(run, ["M1", "M2"])
            run.update({"status": "running", "plan_readiness": "ready"})
            run["observed"].update({"captured_at": "2026-01-01T00:00:00Z"})
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                }
            )
            run["integration"].update(
                {
                    "branch": "codex/test",
                    "batch_base_sha": head,
                    "integration_head_sha": head,
                }
            )
            digest = plan_digest(plan)
            run["plan"]["digest_sha256"] = digest
            run["execution_authorization_scope"]["plan_digest_sha256"] = digest

            plan_path = control / "PLAN.md"
            run_path = control / "RUN.md"
            request_path = control / "verifier-request.json"
            result_path = control / "verifier-result.json"
            plan_path.write_text(
                mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                mf.manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            common = [
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--repo-root",
                str(root),
                "--session-id",
                "CLI-TEST",
            ]
            self.assertEqual(
                0,
                harness_transition.main([*common, "acquire-run-lock"]),
            )
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        *common,
                        "reserve-node-attempt",
                        "--node-id",
                        "N-CLI-FINAL",
                        "--attempt-id",
                        "ATT-CLI-FINAL",
                        "--request-out",
                        str(request_path),
                    ]
                ),
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "verifier_runtime.py"),
                    "--request",
                    str(request_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            result_path.write_text(completed.stdout, encoding="utf-8")
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        *common,
                        "record-node-result",
                        "--node-id",
                        "N-CLI-FINAL",
                        "--attempt-id",
                        "ATT-CLI-FINAL",
                        "--outcome",
                        "pass",
                        "--evidence",
                        "CLI verifier exited 0",
                        "--verifier-result",
                        str(result_path),
                    ]
                ),
            )
            recorded = load_run(run_path)
            self.assertEqual(
                "succeeded",
                recorded["graph_state"]["node_states"]["N-CLI-FINAL"]["phase"],
            )

    def test_reserve_record_keeps_attempt_and_rearms_declared_route(self) -> None:
        plan, run = self._approval_pair()
        harness_transition._reserve_node_attempt(
            plan,
            run,
            Namespace(
                node_id="N-APP",
                attempt_id="ATT-APP-1",
                evidence=["approval requested"],
                repo_root=None,
            ),
        )
        receipt = harness_transition._record_node_result(
            plan,
            run,
            Namespace(
                node_id="N-APP",
                attempt_id="ATT-APP-1",
                outcome="blocked",
                evidence=["owner unavailable"],
                blocker=["awaiting owner"],
                verifier_result=[],
                node_result=None,
            ),
        )
        self.assertEqual("blocked", receipt["outcome"])
        self.assertEqual("blocked", run["graph_state"]["node_states"]["N-APP"]["phase"])
        self.assertEqual("traversed", run["graph_state"]["edge_states"]["E-APP-RETRY"]["status"])
        self.assertEqual("ATT-APP-1", run["graph_state"]["edge_states"]["E-APP-RETRY"]["source_attempt_id"])
        self.assertEqual("node_attempt", run["attempt_log"][-1]["kind"])
        self.assertEqual([], validate_current_plan_run(plan, run))
        selected = select_ready_nodes(plan, run)
        self.assertIn(
            "N-RETRY",
            [item["node_id"] for item in selected["dispatchable_nodes"]],
        )

    def test_local_final_gate_retention_projects_gate_array(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run["status"] = "running"
        run["plan_readiness"] = "ready"
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as evidence_dir:
            root = Path(repo_dir)
            head = mf.init_repo(root, "README.md", default_branch="codex/test")
            run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                }
            )
            run["integration"].update(
                {
                    "branch": "codex/test",
                    "integration_head_sha": head,
                    "batch_base_sha": head,
                }
            )
            request = harness_transition._local_verifier_request(
                plan,
                run,
                next(
                    node
                    for node in plan["graph"]["nodes"]
                    if node["id"] == "N-FINAL"
                ),
                attempt_id="ATT-FINAL-1",
                repo_root=root,
            )
            run["graph_state"]["node_states"]["N-FINAL"].update(
                {
                    "phase": "running",
                    "attempts": 1,
                    "last_attempt_id": "ATT-FINAL-1",
                }
            )
            run["attempt_log"].append(
                {
                    "attempt_id": "ATT-FINAL-1",
                    "node_id": "N-FINAL",
                    "mission_id": None,
                    "task_id": None,
                    "lease_id": None,
                    "kind": "node_attempt",
                    "result": "reserved",
                    "evidence": ["final gate scheduled"],
                    "verifier_dispatch": verifier_dispatch(request),
                }
            )
            digest = plan_digest(plan)
            run["plan"]["digest_sha256"] = digest
            run["execution_authorization_scope"]["plan_digest_sha256"] = digest
            retained = mf.retained_gate_execution(
                plan,
                run,
                plan["final_gates"][0],
                layer="final",
                execution_id="EXEC-FINAL-1",
            )
            retained["reservation"] = request["reservation"]
            retained["dispatch_attestation"] = dispatch_attestation(request)
            verifier_path = Path(evidence_dir) / "final.json"
            wrong_checkout = copy.deepcopy(retained)
            wrong_checkout["dispatch_attestation"]["checkout_root"] = str(
                Path(evidence_dir)
            )
            verifier_path.write_text(
                json.dumps({"verifier_execution": wrong_checkout}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ManifestError, "dispatch attestation"):
                harness_transition._record_node_result(
                    plan,
                    run,
                    Namespace(
                        node_id="N-FINAL",
                        attempt_id="ATT-FINAL-1",
                        outcome="pass",
                        evidence=["wrong checkout"],
                        blocker=[],
                        verifier_result=[verifier_path],
                        repo_root=root,
                        run=None,
                    ),
                )
            verifier_path.write_text(
                json.dumps({"verifier_execution": retained}), encoding="utf-8"
            )
            result = harness_transition._record_node_result(
                plan,
                run,
                Namespace(
                    node_id="N-FINAL",
                    attempt_id="ATT-FINAL-1",
                    outcome="pass",
                    evidence=["final verifier passed"],
                    blocker=[],
                    verifier_result=[verifier_path],
                    repo_root=root,
                    run=None,
                ),
            )
        self.assertEqual("succeeded", result["phase"])
        self.assertEqual("PASS", run["final_gate_results"][0]["status"])
        self.assertEqual(1, len(run["verifier_executions"]))
        self.assertEqual([], validate_current_plan_run(plan, run))
        tampered = copy.deepcopy(run)
        tampered["verifier_executions"][0]["reservation"]["nonce"] = "tampered"
        self.assertTrue(
            any(
                "must match the persisted node-attempt reservation" in error
                for error in validate_current_plan_run(plan, tampered)
            )
        )

    def test_app_task_lease_materializes_exact_targets_and_binding(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1"])
        run.update({"status": "running", "plan_readiness": "ready"})
        run["active_wave"].update(
            {
                "wave_id": "W-APP",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1"],
            }
        )
        run["integration"]["batch_base_sha"] = "a" * 40
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
            }
        )
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter.update(
            {
                "provider": "codex",
                "available_drivers": ["app_threads"],
                "detection_source": "observed",
                "capability_probe": mf.codex_capability_probe(app_threads=True),
            }
        )
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for entry in run["authorizations"].values():
            if isinstance(entry, dict) and isinstance(entry.get("scope"), dict):
                entry["scope"]["plan_digest_sha256"] = digest
        for action in (
            "create_user_owned_tasks",
            "create_app_managed_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            mf.authorize_action(run, action, ["M1"], ["*"])
        harness_transition._lease_worker(
            plan,
            run,
            Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-APP",
                lease_id="L-APP",
                attempt_id="ATT-APP-WORKER",
                branch_ref="refs/heads/codex/m1-app",
                worktree_path="C:/tmp/m1-app",
                provider=None,
                driver=None,
                worker_runtime=None,
                workspace_mode=None,
                completion_channel=None,
                task_thread_id="thread-123",
                report_path=None,
            ),
        )
        worker = run["workers"][-1]
        self.assertEqual("app_threads", worker["runtime_binding"]["driver"])
        self.assertEqual("thread-123", worker["task_thread_id"])
        self.assertIn("task:thread-123", run["authorizations"]["create_user_owned_tasks"]["scope"]["targets"])
        self.assertIn("worktree:C:/tmp/m1-app", run["authorizations"]["create_app_managed_worktrees"]["scope"]["targets"])
        self.assertIn("*", run["authorizations"]["create_user_owned_tasks"]["scope"]["targets"])

        with self.assertRaisesRegex(ManifestError, "already bound to another worker"):
            harness_transition._lease_worker(
                plan,
                run,
                Namespace(
                    mission_id="M1",
                    node_id="N-M1",
                    worker_id="W-APP-SECOND",
                    lease_id="L-APP-SECOND",
                    attempt_id="ATT-APP-WORKER-SECOND",
                    branch_ref="refs/heads/codex/m1-app-second",
                    worktree_path="C:/tmp/m1-app-second",
                    provider=None,
                    driver=None,
                    worker_runtime=None,
                    workspace_mode=None,
                    completion_channel=None,
                    task_thread_id="thread-123",
                    report_path=None,
                ),
            )

        duplicate = copy.deepcopy(worker)
        duplicate.update(
            {
                "worker_id": "W-APP-DUPLICATE",
                "mission_id": "M2",
                "lease_id": "L-APP-DUPLICATE",
                "worktree_path": "C:/tmp/m2-app",
                "branch_ref": "refs/heads/codex/m2-app",
            }
        )
        run["workers"].append(duplicate)
        errors = validate_current_plan_run(plan, run)
        self.assertTrue(
            any("task_thread_id: must be unique across workers" in error for error in errors),
            errors,
        )

    def test_fallback_parent_lease_still_materializes_exact_targets(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1"])
        run.update({"status": "running", "plan_readiness": "ready"})
        run["active_wave"].update(
            {
                "wave_id": "W-FALLBACK",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1"],
            }
        )
        run["integration"]["batch_base_sha"] = "a" * 40
        for action in (
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            mf.authorize_action(run, action, ["M1"], ["*"])

        harness_transition._lease_worker(
            plan,
            run,
            Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-FALLBACK",
                lease_id="L-FALLBACK",
                attempt_id="ATT-FALLBACK",
                branch_ref="refs/heads/run/fallback",
                worktree_path="C:/tmp/fallback",
                provider=None,
                driver=None,
                worker_runtime=None,
                workspace_mode=None,
                completion_channel=None,
                task_thread_id=None,
                report_path=None,
            ),
        )

        self.assertIn(
            "worktree:C:/tmp/fallback",
            run["authorizations"]["create_local_worktrees"]["scope"]["targets"],
        )
        self.assertIn(
            "branch:refs/heads/run/fallback",
            run["authorizations"]["create_local_branches"]["scope"]["targets"],
        )

    def test_local_verifier_request_contains_exact_head_and_context(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            head = mf.init_repo(root, "README.md", default_branch="codex/test")
            run["integration"]["batch_base_sha"] = head
            run["integration"]["integration_head_sha"] = head
            run["integration"]["branch"] = "codex/test"
            run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                }
            )
            request = harness_transition._local_verifier_request(
                plan,
                run,
                next(node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL"),
                attempt_id="ATT-FINAL-REQUEST",
                repo_root=root,
            )
            request["verifier"]["argv"] = [sys.executable, "-c", "raise SystemExit(0)"]
            execution = run_verifier(
                request["verifier"],
                request["context"],
                checkout_root=root,
                environment={},
                git_guard=request["git_guard"],
                reservation=request["reservation"],
                request_sha256=harness_transition._json_sha256(request),
            )
            self.assertEqual("PASS", execution["status"])
            self.assertEqual(request["reservation"], execution["reservation"])
            self.assertEqual(
                dispatch_attestation(request), execution["dispatch_attestation"]
            )
            self.assertIn("verifier", request)
            self.assertIn("context", request)
            self.assertIn("checkout_root", request)
        self.assertEqual("N-FINAL", request["node_id"])
        self.assertEqual("ATT-FINAL-REQUEST", request["attempt_id"])
        self.assertEqual(head, request["head_sha"])
        self.assertEqual("final", request["layer"])
        self.assertEqual("final", request["context"]["layer"])
        self.assertIsNone(request["context"]["attempt_id"])

    def test_verifier_request_output_is_exclusive_and_directly_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "request.json"
            payload = {
                "verifier": {"id": "final"},
                "context": {"head_sha": "a" * 40},
                "checkout_root": temp_dir,
            }
            text = json.dumps(payload)
            harness_transition._write_text_exclusive(path, text)
            self.assertEqual(payload, json.loads(path.read_text(encoding="utf-8")))
            with self.assertRaisesRegex(ManifestError, "refusing to overwrite"):
                harness_transition._write_text_exclusive(path, "replacement")
            self.assertEqual(text, path.read_text(encoding="utf-8"))

    def test_local_verifier_request_proves_root_head_and_clean_state(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            head = mf.init_repo(root, "README.md", default_branch="codex/test")
            run["integration"].update(
                {
                    "branch": "codex/test",
                    "batch_base_sha": head,
                    "integration_head_sha": head,
                }
            )
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                }
            )
            run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
            final_node = next(node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL")
            with self.assertRaisesRegex(ManifestError, "observed integration checkout"):
                harness_transition._local_verifier_request(
                    plan,
                    run,
                    final_node,
                    attempt_id="ATT-BAD-ROOT",
                    repo_root=root / "other",
                )
            run["integration"]["integration_head_sha"] = "b" * 40
            with self.assertRaisesRegex(ManifestError, "head differs"):
                harness_transition._local_verifier_request(
                    plan,
                    run,
                    final_node,
                    attempt_id="ATT-BAD-HEAD",
                    repo_root=root,
                )
            run["integration"]["integration_head_sha"] = head
            (root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "clean integration checkout"):
                harness_transition._local_verifier_request(
                    plan,
                    run,
                    final_node,
                    attempt_id="ATT-DIRTY",
                    repo_root=root,
                )

    def test_local_verifier_result_rechecks_the_live_integration_head(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        run.update({"status": "running", "plan_readiness": "ready"})
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as evidence_dir:
            root = Path(repo_dir)
            head = mf.init_repo(root, "README.md", default_branch="codex/test")
            run["integration"].update(
                {
                    "branch": "codex/test",
                    "batch_base_sha": head,
                    "integration_head_sha": head,
                }
            )
            run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                }
            )
            request = harness_transition._local_verifier_request(
                plan,
                run,
                next(
                    node
                    for node in plan["graph"]["nodes"]
                    if node["id"] == "N-FINAL"
                ),
                attempt_id="ATT-FINAL-DRIFT",
                repo_root=root,
            )
            run["graph_state"]["node_states"]["N-FINAL"].update(
                {
                    "phase": "running",
                    "attempts": 1,
                    "last_attempt_id": "ATT-FINAL-DRIFT",
                }
            )
            run["attempt_log"].append(
                {
                    "attempt_id": "ATT-FINAL-DRIFT",
                    "node_id": "N-FINAL",
                    "mission_id": None,
                    "task_id": None,
                    "lease_id": None,
                    "kind": "node_attempt",
                    "result": "reserved",
                    "evidence": ["scheduled"],
                    "verifier_dispatch": verifier_dispatch(request),
                }
            )
            retained = mf.retained_gate_execution(
                plan,
                run,
                plan["final_gates"][0],
                layer="final",
                execution_id="EXEC-FINAL-DRIFT",
            )
            retained["reservation"] = request["reservation"]
            retained["dispatch_attestation"] = dispatch_attestation(request)
            result_path = Path(evidence_dir) / "execution.json"
            result_path.write_text(
                json.dumps({"verifier_execution": retained}), encoding="utf-8"
            )
            (root / "drift.txt").write_text("drift\n", encoding="utf-8")
            mf.git(root, "add", "drift.txt")
            mf.git(root, "commit", "-qm", "drift")

            with self.assertRaisesRegex(ManifestError, "head differs"):
                harness_transition._record_node_result(
                    plan,
                    run,
                    Namespace(
                        node_id="N-FINAL",
                        attempt_id="ATT-FINAL-DRIFT",
                        outcome="pass",
                        evidence=["stale pass"],
                        blocker=[],
                        verifier_result=[result_path],
                        repo_root=root,
                        run=None,
                    ),
                )
            moved_head = mf.git(root, "rev-parse", "HEAD")
            run["integration"]["integration_head_sha"] = moved_head
            run["observed"]["git"].update(
                {"parent_head_sha": moved_head, "parent_dirty": False}
            )
            moved_request = harness_transition._local_verifier_request(
                plan,
                run,
                next(
                    node
                    for node in plan["graph"]["nodes"]
                    if node["id"] == "N-FINAL"
                ),
                attempt_id="ATT-FINAL-DRIFT",
                repo_root=root,
            )
            moved_result = mf.retained_gate_execution(
                plan,
                run,
                plan["final_gates"][0],
                layer="final",
                execution_id="EXEC-FINAL-RETARGET",
            )
            moved_result["reservation"] = moved_request["reservation"]
            moved_result["dispatch_attestation"] = dispatch_attestation(
                moved_request
            )
            result_path.write_text(
                json.dumps({"verifier_execution": moved_result}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ManifestError, "reservation no longer matches"):
                harness_transition._record_node_result(
                    plan,
                    run,
                    Namespace(
                        node_id="N-FINAL",
                        attempt_id="ATT-FINAL-DRIFT",
                        outcome="pass",
                        evidence=["retargeted pass"],
                        blocker=[],
                        verifier_result=[result_path],
                        repo_root=root,
                        run=None,
                    ),
                )

    def test_local_verifier_result_rejects_changed_protected_run(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        run.update({"status": "running", "plan_readiness": "ready"})
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as evidence_dir:
            root = Path(repo_dir)
            head = mf.init_repo(root, "README.md", default_branch="codex/test")
            run_path = root / "docs" / "goal" / "RUN.md"
            run_path.parent.mkdir(parents=True)
            run_path.write_text("reserved run state\n", encoding="utf-8")
            run["integration"].update(
                {
                    "branch": "codex/test",
                    "batch_base_sha": head,
                    "integration_head_sha": head,
                }
            )
            run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                }
            )
            node = next(
                item for item in plan["graph"]["nodes"] if item["id"] == "N-FINAL"
            )
            request = harness_transition._local_verifier_request(
                plan,
                run,
                node,
                attempt_id="ATT-PROTECTED-RUN",
                repo_root=root,
                run_path=run_path,
            )
            run["graph_state"]["node_states"]["N-FINAL"].update(
                {
                    "phase": "running",
                    "attempts": 1,
                    "last_attempt_id": "ATT-PROTECTED-RUN",
                }
            )
            run["attempt_log"].append(
                {
                    "attempt_id": "ATT-PROTECTED-RUN",
                    "node_id": "N-FINAL",
                    "mission_id": None,
                    "task_id": None,
                    "lease_id": None,
                    "kind": "node_attempt",
                    "result": "reserved",
                    "evidence": ["final gate scheduled"],
                    "verifier_dispatch": verifier_dispatch(request),
                }
            )
            retained = mf.retained_gate_execution(
                plan,
                run,
                plan["final_gates"][0],
                layer="final",
                execution_id="EXEC-PROTECTED-RUN",
            )
            retained["reservation"] = request["reservation"]
            retained["dispatch_attestation"] = dispatch_attestation(
                request,
                protected_path_sha256(root, request["git_guard"]["ignored_paths"]),
            )
            result_path = Path(evidence_dir) / "execution.json"
            result_path.write_text(
                json.dumps({"verifier_execution": retained}), encoding="utf-8"
            )
            before_authorizations = copy.deepcopy(run["authorizations"])
            before_state = copy.deepcopy(
                run["graph_state"]["node_states"]["N-FINAL"]
            )
            run_path.write_text("forged authorization state\n", encoding="utf-8")

            with self.assertRaisesRegex(
                ManifestError, "protected coordination files changed"
            ):
                harness_transition._record_node_result(
                    plan,
                    run,
                    Namespace(
                        node_id="N-FINAL",
                        attempt_id="ATT-PROTECTED-RUN",
                        outcome="pass",
                        evidence=["forged pass"],
                        blocker=[],
                        verifier_result=[result_path],
                        repo_root=root,
                        run=run_path,
                    ),
                )

            self.assertEqual(before_authorizations, run["authorizations"])
            self.assertEqual(
                before_state,
                run["graph_state"]["node_states"]["N-FINAL"],
            )

    def test_interrupted_local_verifier_may_block_without_a_result(self) -> None:
        plan = mf.valid_plan()
        next(
            node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL"
        )["allowed_outcomes"].append("retryable_failure")
        run = mf.valid_run(plan)
        run.update({"status": "running", "plan_readiness": "ready"})
        run["integration"]["batch_base_sha"] = "a" * 40
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"]["N-FINAL"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-FINAL-ONE",
            }
        )
        run["attempt_log"].append(
            {
                "attempt_id": "ATT-FINAL-ONE",
                "node_id": "N-FINAL",
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "node_attempt",
                "result": "reserved",
                "evidence": ["scheduled"],
                "verifier_dispatch": fake_verifier_dispatch(
                    "N-FINAL", "ATT-FINAL-ONE"
                ),
            }
        )
        with self.assertRaisesRegex(ManifestError, "exactly one --verifier-result"):
            harness_transition._record_node_result(
                plan,
                run,
                Namespace(
                    node_id="N-FINAL",
                    attempt_id="ATT-FINAL-ONE",
                    outcome="retryable_failure",
                    evidence=["gate failed"],
                    blocker=[],
                    verifier_result=[],
                    node_result=None,
                ),
            )
        receipt = harness_transition._record_node_result(
            plan,
            run,
            Namespace(
                node_id="N-FINAL",
                attempt_id="ATT-FINAL-ONE",
                outcome="blocked",
                evidence=["verifier process ended without a result"],
                blocker=["execution interrupted"],
                verifier_result=[],
                node_result=None,
            ),
        )
        self.assertEqual("blocked", receipt["phase"])
        self.assertEqual("BLOCKED", run["final_gate_results"][0]["status"])

    def test_local_verifier_retry_retains_fail_then_pass_on_same_head(self) -> None:
        plan = mf.valid_plan()
        next(
            node for node in plan["graph"]["nodes"] if node["id"] == "N-FINAL"
        )["allowed_outcomes"].append("retryable_failure")
        run = mf.valid_run(plan)
        run.update({"status": "running", "plan_readiness": "ready"})
        repo_temp = tempfile.TemporaryDirectory()
        evidence_temp = tempfile.TemporaryDirectory()
        self.addCleanup(repo_temp.cleanup)
        self.addCleanup(evidence_temp.cleanup)
        root = Path(repo_temp.name)
        head = mf.init_repo(root, "README.md", default_branch="codex/test")
        run["integration"].update(
            {
                "branch": "codex/test",
                "batch_base_sha": head,
                "integration_head_sha": head,
            }
        )
        run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
        run["observed"]["git"].update(
            {
                "parent_worktree_path": str(root),
                "parent_branch": "codex/test",
                "parent_head_sha": head,
                "parent_dirty": False,
            }
        )
        state = run["graph_state"]["node_states"]["N-FINAL"]
        declaration = plan["final_gates"][0]
        first = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="final",
            execution_id="EXEC-FINAL-RETRY-1",
        )
        first.update({"status": "FAIL", "exit_code": 1})

        previous_execution = None
        for attempt_id, outcome, execution in (
            ("ATT-FINAL-FAIL", "retryable_failure", first),
            (
                "ATT-FINAL-PASS",
                "pass",
                mf.retained_gate_execution(
                    plan,
                    run,
                    declaration,
                    layer="final",
                    execution_id="EXEC-FINAL-RETRY-2",
                ),
            ),
        ):
            request = harness_transition._local_verifier_request(
                plan,
                run,
                next(
                    node
                    for node in plan["graph"]["nodes"]
                    if node["id"] == "N-FINAL"
                ),
                attempt_id=attempt_id,
                repo_root=root,
            )
            execution = copy.deepcopy(execution)
            execution["reservation"] = request["reservation"]
            execution["dispatch_attestation"] = dispatch_attestation(request)
            state.update(
                {
                    "phase": "running",
                    "attempts": state["attempts"] + 1,
                    "last_attempt_id": attempt_id,
                    "last_outcome": None,
                    "bound_worker_id": None,
                    "blockers": [],
                }
            )
            run["attempt_log"].append(
                {
                    "attempt_id": attempt_id,
                    "node_id": "N-FINAL",
                    "mission_id": None,
                    "task_id": None,
                    "lease_id": None,
                    "kind": "node_attempt",
                    "result": "reserved",
                    "evidence": ["scheduled"],
                    "verifier_dispatch": verifier_dispatch(request),
                }
            )
            if previous_execution is not None:
                replay_path = Path(evidence_temp.name) / "replay.json"
                replay_path.write_text(
                    json.dumps({"verifier_execution": previous_execution}),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ManifestError, "reservation"):
                    harness_transition._record_node_result(
                        plan,
                        run,
                        Namespace(
                            node_id="N-FINAL",
                            attempt_id=attempt_id,
                            outcome=outcome,
                            evidence=["replayed result"],
                            blocker=[],
                            verifier_result=[replay_path],
                            repo_root=root,
                            run=None,
                        ),
                    )
            result_path = Path(evidence_temp.name) / f"{attempt_id}.json"
            result_path.write_text(
                json.dumps({"verifier_execution": execution}),
                encoding="utf-8",
            )
            harness_transition._record_node_result(
                plan,
                run,
                Namespace(
                    node_id="N-FINAL",
                    attempt_id=attempt_id,
                    outcome=outcome,
                    evidence=[f"gate {outcome}"],
                    blocker=[],
                    verifier_result=[result_path],
                    repo_root=root,
                    run=None,
                ),
            )
            previous_execution = copy.deepcopy(execution)

        self.assertEqual(2, len(run["verifier_executions"]))
        self.assertNotEqual(
            run["verifier_executions"][0]["execution_id"],
            run["verifier_executions"][1]["execution_id"],
        )
        self.assertEqual(
            run["verifier_executions"][0]["execution_key"],
            run["verifier_executions"][1]["execution_key"],
        )
        self.assertEqual("PASS", run["final_gate_results"][0]["status"])

    def test_lifecycle_reservation_rejects_a_changed_authorized_head(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run.update({"status": "running", "plan_readiness": "ready"})
        run["integration"].update(
            {
                "branch": "codex/test",
                "batch_base_sha": "a" * 40,
                "integration_head_sha": "a" * 40,
            }
        )
        run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
        run["observed"]["git"].update(
            {
                "parent_branch": "codex/test",
                "parent_head_sha": "a" * 40,
                "parent_dirty": False,
                "default_branch": "main",
            }
        )
        lifecycle = {
            "id": "N-PUSH",
            "kind": "lifecycle",
            "ref": "push",
            "executor": "harness_parent",
            "allowed_outcomes": ["pass", "blocked"],
            "max_attempts": 1,
            "runtime": None,
            "target": "branch:codex/test",
        }
        plan["graph"]["nodes"].append(lifecycle)
        plan["graph"]["entry_nodes"].append("N-PUSH")
        run["graph_state"]["node_states"]["N-PUSH"] = {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-PUSH",
            "last_outcome": None,
            "bound_worker_id": None,
            "blockers": [],
        }
        run["attempt_log"].append(
            {
                "attempt_id": "ATT-PUSH",
                "node_id": "N-PUSH",
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "node_attempt",
                "result": "reserved",
                "evidence": ["push reserved"],
                "node_dispatch": {
                    "target": "branch:codex/test",
                    "authorized_head_sha": "a" * 40,
                },
            }
        )
        run["authorizations"]["push"] = {
            "authorized": True,
            "source": "user hereby authorizes push",
            "authorized_head_sha": "a" * 40,
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": ["M1", "M2"],
                "targets": ["branch:codex/test"],
            },
            "expires_when": "run_complete",
        }
        run["integration"]["integration_head_sha"] = "b" * 40
        with self.assertRaisesRegex(ManifestError, "authorization target or head is stale"):
            harness_transition._record_node_result(
                plan,
                run,
                Namespace(
                    node_id="N-PUSH",
                    attempt_id="ATT-PUSH",
                    outcome="pass",
                    evidence=["push complete"],
                    blocker=[],
                    verifier_result=[],
                    node_result=None,
                ),
            )
        run["authorizations"]["push"] = {"authorized": False, "source": None}
        receipt = harness_transition._record_node_result(
            plan,
            run,
            Namespace(
                node_id="N-PUSH",
                attempt_id="ATT-PUSH",
                outcome="blocked",
                evidence=["push result became uncertain after head drift"],
                blocker=["authorization revoked before the result was observed"],
                verifier_result=[],
                repo_root=None,
            ),
        )
        self.assertEqual("blocked", receipt["phase"])

    def test_node_attempt_requires_null_worker_identity_fields(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        run["attempt_log"].append(
            {
                "attempt_id": "ATT-BAD-NODE",
                "node_id": "N-FINAL",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": None,
                "kind": "node_attempt",
                "result": "reserved",
                "evidence": ["bad"],
            }
        )
        self.assertTrue(
            any(
                "node_attempt mission_id, task_id, and lease_id must all be null" in error
                for error in validate_current_plan_run(plan, run)
            )
        )

    def test_root_retryable_verifier_rearms_without_route(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run.update({"status": "running", "plan_readiness": "ready"})
        node = {
            "id": "N-ROOT-VERIFIER",
            "kind": "verifier",
            "ref": "final",
            "executor": "local_command",
            "allowed_outcomes": ["pass", "retryable_failure", "blocked"],
            "max_attempts": 2,
            "runtime": None,
        }
        plan["graph"]["nodes"].append(node)
        plan["graph"]["entry_nodes"].append(node["id"])
        run["graph_state"]["node_states"][node["id"]] = {
            "phase": "failed",
            "attempts": 1,
            "last_attempt_id": "ATT-ROOT-VERIFIER",
            "last_outcome": "retryable_failure",
            "bound_worker_id": None,
            "blockers": ["transient verifier error"],
        }
        run["attempt_log"].append(
            {
                "attempt_id": "ATT-ROOT-VERIFIER",
                "node_id": node["id"],
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "node_attempt",
                "result": "retryable_failure",
                "evidence": ["transient verifier error"],
                "verifier_dispatch": fake_verifier_dispatch(
                    node["id"], "ATT-ROOT-VERIFIER"
                ),
            }
        )
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        directives = select_ready_nodes(plan, run)["dispatchable_nodes"]
        self.assertIn(node["id"], [item["node_id"] for item in directives])

    def test_root_retryable_lifecycle_stays_route_gated(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run.update({"status": "running", "plan_readiness": "ready"})
        run["observed"].update({"captured_at": "2026-01-01T00:00:00Z"})
        run["observed"]["git"].update(
            {
                "parent_branch": "codex/test",
                "parent_head_sha": "a" * 40,
                "parent_dirty": False,
            }
        )
        run["integration"].update(
            {
                "branch": "codex/test",
                "batch_base_sha": "a" * 40,
                "integration_head_sha": "a" * 40,
            }
        )
        node = {
            "id": "N-ROOT-LIFECYCLE",
            "kind": "lifecycle",
            "ref": "remove_worktrees",
            "executor": "harness_parent",
            "allowed_outcomes": ["pass", "retryable_failure", "blocked"],
            "max_attempts": 2,
            "runtime": None,
            "target": "worktree:C:/tmp",
        }
        plan["graph"]["nodes"].append(node)
        plan["graph"]["entry_nodes"].append(node["id"])
        run["graph_state"]["node_states"][node["id"]] = {
            "phase": "failed",
            "attempts": 1,
            "last_attempt_id": "ATT-ROOT-LIFECYCLE",
            "last_outcome": "retryable_failure",
            "bound_worker_id": None,
            "blockers": ["unknown side effect"],
        }
        run["attempt_log"].append(
            {
                "attempt_id": "ATT-ROOT-LIFECYCLE",
                "node_id": node["id"],
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "node_attempt",
                "result": "retryable_failure",
                "evidence": ["unknown side effect"],
                "node_dispatch": {
                    "target": "worktree:C:/tmp",
                    "authorized_head_sha": None,
                },
            }
        )
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        run["authorizations"]["remove_worktrees"] = {
            "authorized": True,
            "source": "user requested lifecycle action",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": digest,
                "mission_ids": ["M1", "M2"],
                "targets": ["worktree:C:/tmp"],
            },
            "expires_when": "run_complete",
        }
        directives = select_ready_nodes(plan, run)["dispatchable_nodes"]
        self.assertNotIn(node["id"], [item["node_id"] for item in directives])


if __name__ == "__main__":
    unittest.main()
