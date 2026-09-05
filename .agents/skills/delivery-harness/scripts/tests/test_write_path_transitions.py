#!/usr/bin/env python3
"""The scripted write path: observation, wave accept, lease, integration."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import subprocess
import tempfile
import time
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
from harness_core import ManifestError, plan_digest  # noqa: E402
from harness_manifest import load_run  # noqa: E402
from harness_worker_result_transition import (  # noqa: E402
    _observe_bound_worker,
    record_worker_result,
    reject_worker_result,
    verify_worker_observation,
)
import manifest_fixtures as mf  # noqa: E402
from manifest_fixtures import git  # noqa: E402
from verifier_runtime import run_verifier  # noqa: E402


def make_repo() -> tuple[tempfile.TemporaryDirectory, Path, str, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-q", "-b", "integration")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "T")
    (root / "file.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    (root / "file.txt").write_text("integrated\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "work")
    head = git(root, "rev-parse", "HEAD")
    return temp, root, base, head


class WritePathTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp, self.root, self.base, self.head = make_repo()
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            mf.authorize_action(run, action, ["M1", "M2"], ["*"])
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["subagents", "sequential_parent"]
        adapter["detection_source"] = "observed"
        adapter["capability_probe"] = mf.codex_capability_probe(subagents=True)
        adapter["version_gate"] = mf.current_version_gate()
        run["runtime_capabilities"]["worker_runtime"] = "subagent"
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["runtime"].update(
            {
                "available_worker_slots": 2,
                "isolation_capacity": 2,
                "completion_channel_available": True,
            }
        )
        source_contents = {
            "prd": b"# Test PRD\n",
            "architecture": b"# Test architecture\n",
        }
        for source in plan["sources"]:
            contents = source_contents[source["kind"]]
            source_path = self.root / source["location"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(contents)
            source["content_sha256"] = hashlib.sha256(contents).hexdigest()
        git(self.root, "add", "docs/product")
        git(self.root, "commit", "-qm", "contracts")
        self.head = git(self.root, "rev-parse", "HEAD")
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for authorization in run["authorizations"].values():
            if isinstance(authorization, dict) and isinstance(
                authorization.get("scope"), dict
            ):
                authorization["scope"]["plan_digest_sha256"] = digest
        run["integration"]["branch"] = "integration"
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        run["integration"]["batch_base_sha"] = self.head
        run["integration"]["integration_head_sha"] = None
        run["active_wave"].update(
            {
                "wave_id": None,
                "status": "idle",
                "batch_base_sha": None,
                "selected_missions": [],
            }
        )
        run["observed"]["captured_at"] = None
        self.plan, self.run = plan, run

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _sync_plan_digest(self) -> None:
        digest = plan_digest(self.plan)
        self.run["plan"]["digest_sha256"] = digest
        self.run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for authorization in self.run["authorizations"].values():
            if isinstance(authorization, dict) and isinstance(
                authorization.get("scope"), dict
            ):
                authorization["scope"]["plan_digest_sha256"] = digest

    def test_observation_wave_lease_and_integration_chain(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        observed = self.run["observed"]
        self.assertEqual(self.head, observed["git"]["parent_head_sha"])
        self.assertEqual("integration", observed["git"]["parent_branch"])
        self.assertFalse(observed["git"]["parent_dirty"])
        self.assertTrue(observed["captured_at"])

        self.run["active_wave"]["status"] = "idle"
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-1",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        wave = self.run["active_wave"]
        self.assertEqual("active", wave["status"])
        self.assertEqual(["M1"], wave["selected_missions"])
        self.assertEqual(self.head, self.run["integration"]["batch_base_sha"])

        self.run["mission_states"]["M1"]["phase"] = "queued"
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-M1-A",
                lease_id="LEASE-M1-A",
                attempt_id="ATT-M1-A",
                branch_ref="feature/m1",
                worktree_path=str(self.root / "wt-m1"),
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
            ),
        )
        worker = self.run["workers"][-1]
        self.assertEqual("W-M1-A", worker["worker_id"])
        self.assertEqual("worker_running", self.run["mission_states"]["M1"]["phase"])
        node_state = self.run["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("running", node_state["phase"])
        self.assertTrue(
            any(a["attempt_id"] == "ATT-M1-A" for a in self.run["attempt_log"])
        )
        with self.assertRaisesRegex(ManifestError, "lease id 'LEASE-M1-A' already exists"):
            harness_transition._lease_worker(
                self.plan,
                self.run,
                Namespace(
                    mission_id="M1",
                    node_id="N-M1",
                    worker_id="W-M1-B",
                    lease_id="LEASE-M1-A",
                    attempt_id="ATT-M1-B",
                    branch_ref="feature/m1-retry",
                    worktree_path=str(self.root / "wt-m1-retry"),
                    provider="codex",
                    driver="subagents",
                    worker_runtime="subagent",
                    workspace_mode="parent_managed_worktree",
                    completion_channel="agent_result",
                ),
            )

        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        harness_transition._record_integration(
            self.plan,
            self.run,
            Namespace(mission_id="M1", integrated_sha=self.head, repo_root=self.root),
        )
        mission = self.run["mission_states"]["M1"]
        self.assertEqual("integrated", mission["phase"])
        self.assertEqual("PASS", mission["integration_gate"])
        self.assertEqual(self.head, self.run["integration"]["integration_head_sha"])

    def test_record_worker_result_stages_the_validated_handoff(self) -> None:
        mission = self.plan["missions"][0]
        declarations = [
            (mission["tasks"][0]["verifiers"][0], "task", "M1/T01", "ATT-T01"),
            (mission["tasks"][1]["verifiers"][0], "task", "M1/T02", "ATT-T02"),
            (mission["worker_verifiers"][0], "worker", None, "ATT-WORKER"),
        ]
        for declaration, _, _, _ in declarations:
            declaration["argv"] = [sys.executable, "-c", "raise SystemExit(0)"]
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-RESULT",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        worker_root = self.root / "wt-m1"
        git(
            self.root,
            "worktree",
            "add",
            "-q",
            "-b",
            "feature/m1-result",
            str(worker_root),
            self.head,
        )
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-M1-RESULT",
                lease_id="LEASE-M1-RESULT",
                attempt_id="ATT-M1-RESULT",
                branch_ref="feature/m1-result",
                worktree_path=str(worker_root),
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
                report_path=None,
            ),
        )

        changed_files = ["src/a/one.py", "src/a/two.py"]
        source_root = worker_root / "src" / "a"
        source_root.mkdir(parents=True)
        (source_root / "one.py").write_text("ONE = 1\n", encoding="utf-8")
        git(worker_root, "add", "src/a/one.py")
        git(worker_root, "commit", "-qm", "task one")
        task_one_head = git(worker_root, "rev-parse", "HEAD")
        (source_root / "two.py").write_text("TWO = 2\n", encoding="utf-8")
        git(worker_root, "add", "src/a/two.py")
        git(worker_root, "commit", "-qm", "task two")
        worker_head = git(worker_root, "rev-parse", "HEAD")
        retained = []
        for declaration, layer, task_id, attempt_id in declarations:
            context = {
                "run_id": self.run["run_id"],
                "plan_revision": self.plan["revision"],
                "plan_digest_sha256": plan_digest(self.plan),
                "graph_revision": self.run["graph_state"]["graph_revision"],
                "batch_base_sha": self.head,
                "head_sha": worker_head,
                "changed_files": changed_files,
                "trust_domain": "parent_local",
                "checkout_role": "worker",
                "checkout_dirty": False,
                "cache_safe": False,
                "layer": layer,
                "mission_id": "M1",
                "task_id": task_id,
                "attempt_id": attempt_id,
                "lease_id": "LEASE-M1-RESULT",
            }
            retained.append(
                run_verifier(
                    declaration,
                    context,
                    checkout_root=worker_root,
                    environment={},
                )
            )
        by_id = {result["verifier_id"]: result for result in retained}
        worker_result = {
            "type": "WORKER_RESULT",
            "run_id": self.run["run_id"],
            "plan_id": self.plan["plan_id"],
            "mission_id": "M1",
            "lease_id": "LEASE-M1-RESULT",
            "status": "worker_passed",
            "current_task_id": None,
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "base_sha": self.head,
            "head_sha": worker_head,
            "diff_summary": "Completed both atomic tasks.",
            "changed_files": changed_files,
            "task_results": [
                {
                    "task_id": "M1/T01",
                    "status": "worker_passed",
                    "head_sha": task_one_head,
                    "verifier_ids": ["verify-m1-1"],
                    "commits": [task_one_head],
                    "evidence_paths": ["evidence/t01.txt"],
                },
                {
                    "task_id": "M1/T02",
                    "status": "worker_passed",
                    "head_sha": worker_head,
                    "verifier_ids": ["verify-m1-2"],
                    "commits": [worker_head],
                    "evidence_paths": ["evidence/t02.txt"],
                },
            ],
            "verifiers": [
                {
                    "id": verifier_id,
                    "status": "PASS",
                    "evidence": by_id[verifier_id]["execution_key"],
                }
                for verifier_id in ("verify-m1-1", "verify-m1-2", "worker-m1")
            ],
            "commits": [task_one_head, worker_head],
            "evidence_paths": ["evidence/mission.txt"],
            "blockers": [],
            "residual_risks": [],
            "integration_notes": "",
            "subagent_activity": {
                "status": "not_applicable",
                "skip_reason": "flat mission worker",
                "children": [],
            },
        }
        node_result = {
            "run_id": self.run["run_id"],
            "node_id": "N-M1",
            "attempt_id": "ATT-M1-RESULT",
            "plan_id": self.plan["plan_id"],
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": self.run["graph_state"]["graph_revision"],
            "batch_base_sha": self.head,
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": worker_result,
            "refinement_request": None,
            "evidence_paths": ["evidence/node.txt"],
        }
        node_path = self.root / "node-result.json"
        node_path.write_text(json.dumps({"node_result": node_result}), encoding="utf-8")
        retained_paths = []
        for index, result in enumerate(retained, start=1):
            path = self.root / f"verifier-{index}.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            retained_paths.append(path)
        mf.authorize_action(
            self.run,
            "spawn_subagents",
            ["M1"],
            ["worker:W-M1-RESULT"],
        )
        mf.authorize_action(
            self.run,
            "create_local_worktrees",
            ["M1"],
            [f"worktree:{worker_root}"],
        )
        for action in ("create_local_branches", "create_local_commits"):
            mf.authorize_action(
                self.run,
                action,
                ["M1"],
                ["branch:feature/m1-result"],
            )

        rejected_run = copy.deepcopy(self.run)
        rejected_worker_result = copy.deepcopy(worker_result)
        rejected_worker_result["changed_files"] = ["src/a/one.py"]
        rejected_node_result = copy.deepcopy(node_result)
        rejected_node_result["worker_result"] = rejected_worker_result
        rejected_path = self.root / "rejected-node-result.json"
        rejected_path.write_text(
            json.dumps({"node_result": rejected_node_result}), encoding="utf-8"
        )
        rejected_receipt = record_worker_result(
            self.plan,
            rejected_run,
            Namespace(
                repo_root=self.root,
                node_result=rejected_path,
                worker_result=None,
                verifier_result=retained_paths,
            ),
        )
        self.assertEqual(
            "worker_failed", rejected_run["mission_states"]["M1"]["phase"]
        )
        self.assertEqual("worker_failed", rejected_receipt["phase"])
        self.assertTrue(rejected_run["mission_states"]["M1"]["blockers"])
        self.assertEqual(
            [], harness_transition.validate_current_plan_run(self.plan, rejected_run)
        )
        self.assertEqual("worker_running", self.run["mission_states"]["M1"]["phase"])

        record_args = Namespace(
            repo_root=self.root,
            node_result=node_path,
            worker_result=None,
            verifier_result=retained_paths,
        )
        passing_receipt = record_worker_result(
            self.plan,
            self.run,
            record_args,
        )

        self.assertEqual("worker_passed", self.run["mission_states"]["M1"]["phase"])
        self.assertEqual("worker_passed", passing_receipt["phase"])
        self.assertEqual(worker_head, self.run["mission_states"]["M1"]["head_sha"])
        self.assertEqual("worker_passed", self.run["workers"][-1]["phase"])
        self.assertEqual("running", self.run["graph_state"]["node_states"]["N-M1"]["phase"])
        self.assertTrue(
            all(
                self.run["task_states"][task_id]["phase"] == "mission_recorded"
                for task_id in ("M1/T01", "M1/T02")
            )
        )
        self.assertEqual(3, len(self.run["verifier_executions"]))
        self.assertEqual([], harness_transition.validate_current_plan_run(self.plan, self.run))
        (source_root / "three.py").write_text("THREE = 3\n", encoding="utf-8")
        git(worker_root, "add", "src/a/three.py")
        git(worker_root, "commit", "-qm", "move worker head")
        with self.assertRaisesRegex(ManifestError, "worker worktree changed"):
            verify_worker_observation(record_args.worker_observation)
        git(worker_root, "mv", "docs/product/prd.md", "src/a/moved-prd.py")
        git(worker_root, "commit", "-qm", "rename an out-of-scope source")
        rename_observation = _observe_bound_worker(
            self.plan, self.run, node_result, self.root
        )
        self.assertIn("docs/product/prd.md", rename_observation["changed_files"])
        self.assertIn("src/a/moved-prd.py", rename_observation["changed_files"])

    def test_record_worker_result_retains_a_retryable_failure(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-FAIL",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        worker_root = self.root / "wt-m1-failed"
        git(
            self.root,
            "worktree",
            "add",
            "-q",
            "-b",
            "feature/m1-failed",
            str(worker_root),
            self.head,
        )
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-M1-FAILED",
                lease_id="LEASE-M1-FAILED",
                attempt_id="ATT-M1-FAILED",
                branch_ref="feature/m1-failed",
                worktree_path=str(worker_root),
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
                report_path=None,
            ),
        )
        mf.authorize_action(
            self.run, "spawn_subagents", ["M1"], ["worker:W-M1-FAILED"]
        )
        mf.authorize_action(
            self.run,
            "create_local_worktrees",
            ["M1"],
            [f"worktree:{worker_root}"],
        )
        for action in ("create_local_branches", "create_local_commits"):
            mf.authorize_action(
                self.run,
                action,
                ["M1"],
                ["branch:feature/m1-failed"],
            )
        node_result = {
            "run_id": self.run["run_id"],
            "node_id": "N-M1",
            "attempt_id": "ATT-M1-FAILED",
            "plan_id": self.plan["plan_id"],
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": self.run["graph_state"]["graph_revision"],
            "batch_base_sha": self.head,
            "status": "failed",
            "outcome": "retryable_failure",
            "worker_result": None,
            "refinement_request": None,
            "evidence_paths": ["evidence/worker-failure.txt"],
        }
        node_path = self.root / "failed-node-result.json"
        node_path.write_text(json.dumps({"node_result": node_result}), encoding="utf-8")

        explicitly_rejected = copy.deepcopy(self.run)
        rejection_receipt = reject_worker_result(
            self.plan,
            explicitly_rejected,
            Namespace(
                repo_root=self.root,
                node_id="N-M1",
                worker_id="W-M1-FAILED",
                outcome="retryable_failure",
                reason=["parent rejected stale worker evidence"],
            ),
        )
        self.assertEqual(
            "worker_failed", explicitly_rejected["mission_states"]["M1"]["phase"]
        )
        self.assertEqual("worker_failed", rejection_receipt["phase"])
        self.assertIn(
            "parent rejected stale worker evidence",
            explicitly_rejected["mission_states"]["M1"]["blockers"],
        )

        record_worker_result(
            self.plan,
            self.run,
            Namespace(
                repo_root=self.root,
                node_result=node_path,
                worker_result=None,
                verifier_result=[],
            ),
        )

        self.assertEqual("worker_failed", self.run["mission_states"]["M1"]["phase"])
        self.assertEqual("worker_failed", self.run["workers"][-1]["phase"])
        node_state = self.run["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("failed", node_state["phase"])
        self.assertEqual("retryable_failure", node_state["last_outcome"])
        self.assertEqual([], harness_transition.validate_current_plan_run(self.plan, self.run))

    def test_guards_refuse_the_wrong_states(self) -> None:
        with self.assertRaises(ManifestError):
            harness_transition._record_observation(self.run, Namespace(repo_root=None))

        self.run["active_wave"].update({"status": "active", "wave_id": "B-OTHER"})
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

        self.run["active_wave"].update({"status": "idle", "wave_id": None})
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha="not-the-observed-head",
                    repo_root=self.root,
                ),
            )

        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-1",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        self.run["mission_states"]["M1"]["phase"] = "queued"
        lease_args = dict(
            mission_id="M1",
            node_id="N-M1",
            worker_id="W-M1-A",
            branch_ref="b",
            worktree_path="w",
            provider="codex",
            driver="subagents",
            worker_runtime="subagent",
            workspace_mode="parent_managed_worktree",
            completion_channel="agent_result",
        )
        harness_transition._lease_worker(
            self.plan, self.run, Namespace(lease_id="L", attempt_id="A", **lease_args)
        )
        # duplicate worker id on a re-queued mission is refused
        self.run["mission_states"]["M1"]["phase"] = "queued"
        with self.assertRaises(ManifestError):
            harness_transition._lease_worker(
                self.plan,
                self.run,
                Namespace(lease_id="L2", attempt_id="A2", **lease_args),
            )

        with self.assertRaises(ManifestError):
            harness_transition._record_integration(
                self.plan,
                self.run,
                Namespace(
                    mission_id="M1", integrated_sha=self.head, repo_root=self.root
                ),
            )

    def test_plan_compare_and_swap_rejects_a_changed_plan(self) -> None:
        plan_path = self.root / "PLAN.md"
        plan_path.write_text("original\n", encoding="utf-8")
        harness_transition._ensure_plan_unchanged(plan_path, "original\n")
        plan_path.write_text("changed\n", encoding="utf-8")

        with self.assertRaisesRegex(ManifestError, "PLAN.md changed"):
            harness_transition._ensure_plan_unchanged(plan_path, "original\n")

    def test_accept_wave_uses_the_selector_frontier(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        with self.assertRaisesRegex(ManifestError, "selector's dispatchable"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-M2",
                    mission_id=["M2"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

        self.plan["missions"][0]["worktree_eligible"] = False
        self.run["plan"]["digest_sha256"] = plan_digest(self.plan)
        for action in self.run["authorizations"].values():
            if isinstance(action, dict) and isinstance(action.get("scope"), dict):
                action["scope"]["plan_digest_sha256"] = self.run["plan"][
                    "digest_sha256"
                ]
        self.run["execution_authorization_scope"]["plan_digest_sha256"] = self.run[
            "plan"
        ]["digest_sha256"]
        with self.assertRaisesRegex(ManifestError, "worktree_ineligible"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-M1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_lease_refuses_a_pause_after_wave_acceptance(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-1",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        self.run["control"]["desired_state"] = "paused"
        with self.assertRaisesRegex(ManifestError, "lease-worker runs only"):
            harness_transition._lease_worker(
                self.plan,
                self.run,
                Namespace(
                    mission_id="M1",
                    node_id="N-M1",
                    worker_id="W-M1-A",
                    lease_id="LEASE-M1-A",
                    attempt_id="ATT-M1-A",
                    branch_ref="feature/m1",
                    worktree_path=str(self.root / "wt-m1"),
                    provider="codex",
                    driver="subagents",
                    worker_runtime="subagent",
                    workspace_mode="parent_managed_worktree",
                    completion_channel="agent_result",
                ),
            )

    def test_accept_wave_rejects_live_git_drift_after_observation(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        (self.root / "later.txt").write_text("later\n", encoding="utf-8")
        git(self.root, "add", "later.txt")
        git(self.root, "commit", "-qm", "later")
        with self.assertRaisesRegex(ManifestError, "differs from observed parent head"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_rejects_product_dirt_after_observation(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        (self.root / "dirty-product.txt").write_text("dirty\n", encoding="utf-8")

        with self.assertRaisesRegex(ManifestError, "clean live integration checkout"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_record_integration_rejects_a_different_checkout(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        with tempfile.TemporaryDirectory() as directory:
            other_checkout = Path(directory)
            with self.assertRaisesRegex(ManifestError, "observed parent worktree"):
                harness_transition._record_integration(
                    self.plan,
                    self.run,
                    Namespace(
                        mission_id="M1",
                        integrated_sha=self.head,
                        repo_root=other_checkout,
                    ),
                )

    def test_record_integration_ignores_only_the_tracked_run_file(self) -> None:
        run_path = self.root / "docs/goal/RUN.md"
        run_path.parent.mkdir(parents=True, exist_ok=True)
        run_path.write_text("baseline\n", encoding="utf-8")
        git(self.root, "add", "docs/goal/RUN.md")
        git(self.root, "commit", "-qm", "track run state")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["batch_base_sha"] = self.head
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root, run=run_path)
        )
        run_path.write_text("transition update\n", encoding="utf-8")
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.run["mission_states"]["M1"]["head_sha"] = self.head

        harness_transition._record_integration(
            self.plan,
            self.run,
            Namespace(
                mission_id="M1",
                integrated_sha=self.head,
                repo_root=self.root,
                run=run_path,
            ),
        )

        self.assertEqual("integrated", self.run["mission_states"]["M1"]["phase"])

    def test_accept_wave_blocks_a_missing_ui_contract_source(self) -> None:
        self.plan["ui_surfaces"] = [
            {
                "id": "UI-001",
                "trace_ids": ["REQ-001"],
                "route": "/home",
                "breakpoints": ["390"],
                "states": ["ready"],
                "evidence_gate": "required",
            }
        ]
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_text = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n"
        )
        prd_path.write_text(prd_text, encoding="utf-8")
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        git(self.root, "add", "docs/product/prd.md")
        git(self.root, "commit", "-qm", "add UI contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "frozen wireframes.html source"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_blocks_semantic_prd_route_drift(self) -> None:
        self.plan["ui_surfaces"] = [
            {
                "id": "UI-001",
                "trace_ids": ["REQ-001"],
                "route": "/home",
                "breakpoints": ["390"],
                "states": ["ready"],
                "evidence_gate": "required",
            }
        ]
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_path.write_text(
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /alias\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n",
            encoding="utf-8",
        )
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        wireframe_path = self.root / "docs/product/wireframes.html"
        wireframe_path.write_text(
            mf.wireframes_html(
                [{"id": "UI-001", "route": "/home", "states": ["ready"]}]
            ),
            encoding="utf-8",
        )
        self.plan["sources"].append(
            {
                "id": "SRC-WIREFRAME",
                "kind": "wireframe",
                "location": "docs/product/wireframes.html",
                "owner": "product",
                "status": "frozen",
                "content_sha256": hashlib.sha256(
                    wireframe_path.read_bytes()
                ).hexdigest(),
                "source_revision": None,
                "staged_revision": None,
                "notes": "approved projection",
            }
        )
        git(self.root, "add", "docs/product")
        git(self.root, "commit", "-qm", "add drifted UI artifacts")
        self.head = git(self.root, "rev-parse", "HEAD")
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "differs from the PRD route"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_cannot_hide_prd_ui_by_emptying_plan_surfaces(self) -> None:
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_path.write_text(
            "<!-- ui-surface-contract:start -->\n"
            "## 介面契約\n\n"
            "### UI-001 — 首頁\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n",
            encoding="utf-8",
        )
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        git(self.root, "add", "docs/product/prd.md")
        git(self.root, "commit", "-qm", "freeze UI contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["batch_base_sha"] = self.head
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "PRD surfaces absent from the PLAN"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_rejects_ui_headings_outside_the_machine_boundary(
        self,
    ) -> None:
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_path.write_text(
            "<!-- ui-surface-contract:start -->\n"
            "## 介面契約\n"
            "<!-- ui-surface-contract:end -->\n"
            "### UI-001 — Outside\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n",
            encoding="utf-8",
        )
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        git(self.root, "add", "docs/product/prd.md")
        git(self.root, "commit", "-qm", "freeze malformed UI contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["batch_base_sha"] = self.head
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "headings outside"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_tracked_run_cli_chain_works_from_a_linked_integration_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            container = Path(directory)
            main_root = container / "main"
            linked_root = container / "integration"
            main_root.mkdir()
            git(main_root, "init", "-q", "-b", "main")
            git(main_root, "config", "user.email", "t@example.com")
            git(main_root, "config", "user.name", "T")
            (main_root / "base.txt").write_text("base\n", encoding="utf-8")
            git(main_root, "add", "base.txt")
            git(main_root, "commit", "-qm", "base")
            git(main_root, "worktree", "add", "-q", "-b", "integration", str(linked_root))

            plan = mf.valid_plan()
            for source, contents in zip(
                plan["sources"],
                (b"# Product contract\n", b"# Architecture contract\n"),
            ):
                source_path = linked_root / source["location"]
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(contents)
                source["content_sha256"] = hashlib.sha256(contents).hexdigest()
            run = mf.valid_run(plan)
            mf.authorize_execution(run, ["M1", "M2"])
            for action in (
                "spawn_subagents",
                "create_local_worktrees",
                "create_local_branches",
                "create_local_commits",
            ):
                mf.authorize_action(run, action, ["M1", "M2"], ["*"])
            adapter = run["runtime_capabilities"]["runtime_adapter"]
            adapter["available_drivers"] = ["subagents", "sequential_parent"]
            adapter["detection_source"] = "observed"
            adapter["capability_probe"] = mf.codex_capability_probe(subagents=True)
            adapter["version_gate"] = mf.current_version_gate()
            run["runtime_capabilities"]["worker_runtime"] = "subagent"
            run["runtime_capabilities"]["max_parallel_workers"] = 2
            run["observed"]["runtime"].update(
                {
                    "available_worker_slots": 2,
                    "isolation_capacity": 2,
                    "completion_channel_available": True,
                }
            )
            run["integration"].update(
                {
                    "branch": "integration",
                    "batch_base_sha": None,
                    "integration_head_sha": None,
                }
            )
            run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
            run["active_wave"].update(
                {
                    "wave_id": None,
                    "status": "idle",
                    "batch_base_sha": None,
                    "selected_missions": [],
                }
            )
            run["observed"]["captured_at"] = None

            goal_root = linked_root / "docs" / "goal"
            goal_root.mkdir(parents=True, exist_ok=True)
            plan_path = goal_root / "PLAN.md"
            run_path = goal_root / "RUN.md"
            plan_path.write_text(
                mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                mf.manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            git(linked_root, "add", ".")
            git(linked_root, "commit", "-qm", "tracked harness layout")
            head = git(linked_root, "rev-parse", "HEAD")

            base_command = [
                sys.executable,
                str(SCRIPTS_DIR / "harness_transition.py"),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--repo-root",
                str(linked_root),
                "--session-id",
                "tracked-layout",
            ]
            for command in (
                ["acquire-run-lock"],
                ["record-observation"],
                [
                    "accept-wave",
                    "--wave-id",
                    "B-1",
                    "--mission-id",
                    "M1",
                    "--batch-base-sha",
                    head,
                ],
            ):
                result = subprocess.run(
                    [*base_command, *command],
                    cwd=linked_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)

            live = load_run(run_path)
            self.assertTrue(
                harness_transition._same_path(
                    linked_root, live["observed"]["git"]["parent_worktree_path"]
                )
            )
            self.assertFalse(live["observed"]["git"]["parent_dirty"])
            self.assertEqual("active", live["active_wave"]["status"])
            self.assertEqual(["M1"], live["active_wave"]["selected_missions"])
            status = git(linked_root, "status", "--porcelain")
            self.assertEqual("M docs/goal/RUN.md", status.strip())

    def test_transition_lock_serializes_separate_processes(self) -> None:
        target = self.root / "RUN.md"
        script = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
            "from harness_transition import _run_transition_lock; "
            "\nwith _run_transition_lock(Path(sys.argv[1])): print('acquired')"
        )
        with harness_transition._run_transition_lock(target):
            process = subprocess.Popen(
                [sys.executable, "-c", script, str(target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.25)
            self.assertIsNone(process.poll())
        stdout, stderr = process.communicate(timeout=15)
        self.assertEqual(0, process.returncode, stderr)
        self.assertIn("acquired", stdout)


if __name__ == "__main__":
    unittest.main()
