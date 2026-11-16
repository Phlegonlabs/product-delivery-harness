#!/usr/bin/env python3
"""`--check` validates a result packet and writes nothing."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
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
import test_node_transitions as node_tests  # noqa: E402
import test_write_path_transitions as write_tests  # noqa: E402
from harness_core import plan_digest  # noqa: E402
from harness_manifest import load_run  # noqa: E402
from harness_worker_result_transition import _observe_bound_worker  # noqa: E402
from manifest_fixtures import git  # noqa: E402
from verifier_runtime import observe_plan_host_runtimes, run_verifier  # noqa: E402


class CheckCli(unittest.TestCase):
    def write_control(self, plan: dict, run: dict) -> None:
        control = tempfile.TemporaryDirectory()
        self.addCleanup(control.cleanup)
        self.plan_path = Path(control.name) / "PLAN.md"
        self.run_path = Path(control.name) / "RUN.md"
        self.control = Path(control.name)
        self.plan_path.write_text(
            mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )

    def cli(self, *argv: str, repo_root: Path | None = None) -> tuple[int, str, str]:
        common = ["--plan", str(self.plan_path), "--run", str(self.run_path)]
        if repo_root is not None:
            common += ["--repo-root", str(repo_root)]
        common += ["--session-id", "CHECK-TEST"]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = harness_transition.main([*common, *argv])
        return code, out.getvalue(), err.getvalue()


class RecordNodeResultCheckTests(CheckCli):
    def setUp(self) -> None:
        plan, run = node_tests.NodeTransitionTests._approval_pair(self)
        self.write_control(plan, run)
        self.assertEqual(0, self.cli("acquire-run-lock")[0])
        code, _, err = self.cli(
            "reserve-node-attempt", "--node-id", "N-APP", "--attempt-id", "ATT-APP-1",
            "--evidence", "approval requested",
        )
        self.assertEqual(0, code, err)

    def record(self, attempt_id: str, *extra: str) -> tuple[int, str, str]:
        return self.cli(
            "record-node-result", "--node-id", "N-APP", "--attempt-id", attempt_id,
            "--outcome", "pass", "--evidence", "owner approved", *extra,
        )

    def test_check_with_a_wrong_attempt_fails_and_writes_nothing(self) -> None:
        before = self.run_path.read_bytes()
        code, _, err = self.record("ATT-APP-OLD", "--check")
        self.assertEqual(2, code)
        self.assertIn("matching reserved running attempt", err)
        self.assertEqual(before, self.run_path.read_bytes())
        state = load_run(self.run_path)["graph_state"]["node_states"]["N-APP"]
        self.assertEqual("running", state["phase"])

        code, _, err = self.record("ATT-APP-1")
        self.assertEqual(0, code, err)
        state = load_run(self.run_path)["graph_state"]["node_states"]["N-APP"]
        self.assertEqual("succeeded", state["phase"])

    def test_check_with_a_valid_result_passes_and_writes_nothing(self) -> None:
        before = self.run_path.read_bytes()
        code, out, err = self.record("ATT-APP-1", "--check")
        self.assertEqual(0, code, err)
        self.assertIn("check passed: record-node-result", out)
        self.assertEqual(before, self.run_path.read_bytes())


class RecordWorkerResultCheckTests(CheckCli):
    setUp = write_tests.WritePathTransitionTests.setUp
    tearDown = write_tests.WritePathTransitionTests.tearDown
    _sync_plan_digest = write_tests.WritePathTransitionTests._sync_plan_digest

    def stage_worker(self) -> dict:
        """Lease M1, commit both tasks, run every verifier, return the packet."""

        mission = self.plan["missions"][0]
        declarations = [
            (mission["tasks"][0]["verifiers"][0], "task", "M1/T01", "ATT-T01"),
            (mission["tasks"][1]["verifiers"][0], "task", "M1/T02", "ATT-T02"),
            (mission["worker_verifiers"][0], "worker", None, "ATT-WORKER"),
        ]
        for declaration, _, _, _ in declarations:
            declaration["argv"] = [sys.executable, "-c", "raise SystemExit(0)"]
            declaration["read_only"] = True
            declaration["execution"] = {"parallel_safe": False, "resources": [], "isolation": "host"}
        self._sync_plan_digest()
        harness_transition._record_observation(self.plan, self.run, Namespace(repo_root=self.root))
        harness_transition._accept_wave(self.plan, self.run, Namespace(
            wave_id="B-CHECK", mission_id=["M1"], batch_base_sha=self.head, repo_root=self.root))
        worker_root = self.root / "wt-m1"
        git(self.root, "worktree", "add", "-q", "-b", "feature/m1-check", str(worker_root), self.head)
        harness_transition._lease_worker(self.plan, self.run, Namespace(
            mission_id="M1", node_id="N-M1", worker_id="W-M1-CHECK", lease_id="LEASE-M1-CHECK",
            attempt_id="ATT-M1-CHECK", branch_ref="feature/m1-check", worktree_path=str(worker_root),
            provider="codex", driver="subagents", worker_runtime="subagent",
            workspace_mode="parent_managed_worktree", completion_channel="agent_result",
            report_path=None))
        mf.authorize_action(self.run, "spawn_subagents", ["M1"], ["worker:W-M1-CHECK"])
        mf.authorize_action(self.run, "create_local_worktrees", ["M1"], [f"worktree:{worker_root}"])
        for action in ("create_local_branches", "create_local_commits"):
            mf.authorize_action(self.run, action, ["M1"], ["branch:feature/m1-check"])

        def execute(declaration, layer, task_id, attempt_id, head, files):
            context = {
                "run_id": self.run["run_id"], "plan_revision": self.plan["revision"],
                "plan_digest_sha256": plan_digest(self.plan),
                "graph_revision": self.run["graph_state"]["graph_revision"],
                "batch_base_sha": self.head, "head_sha": head, "changed_files": files,
                "trust_domain": "parent_local", "checkout_role": "worker",
                "checkout_dirty": False, "cache_safe": False, "layer": layer,
                "mission_id": "M1", "task_id": task_id, "attempt_id": attempt_id,
                "lease_id": "LEASE-M1-CHECK",
            }
            entries, errors = observe_plan_host_runtimes({"final_gates": [declaration]}, worker_root)
            self.assertEqual([], errors)
            return run_verifier(declaration, context, checkout_root=worker_root,
                host_preflight=entries[0], environment={}, git_guard={
                    "expected_branch": "feature/m1-check", "expected_head_sha": head,
                    "ignored_paths": []})

        source = worker_root / "src" / "a"
        source.mkdir(parents=True)
        (source / "one.py").write_text("ONE = 1\n", encoding="utf-8")
        git(worker_root, "add", "src/a/one.py")
        git(worker_root, "commit", "-qm", "task one")
        task_one = git(worker_root, "rev-parse", "HEAD")
        retained = [execute(*declarations[0], task_one, ["src/a/one.py"])]
        (source / "two.py").write_text("TWO = 2\n", encoding="utf-8")
        git(worker_root, "add", "src/a/two.py")
        git(worker_root, "commit", "-qm", "task two")
        head = git(worker_root, "rev-parse", "HEAD")
        changed = ["src/a/one.py", "src/a/two.py"]
        retained.append(execute(*declarations[1], head, ["src/a/two.py"]))
        retained.append(execute(*declarations[2], head, changed))
        results_dir = tempfile.TemporaryDirectory()
        self.addCleanup(results_dir.cleanup)
        self.verifier_paths = []
        for index, result in enumerate(retained, start=1):
            path = Path(results_dir.name) / f"verifier-{index}.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            self.verifier_paths.append(path)
        keys = {result["verifier_id"]: result["execution_key"] for result in retained}
        worker_result = {
            "type": "WORKER_RESULT", "run_id": self.run["run_id"],
            "plan_id": self.plan["plan_id"], "mission_id": "M1",
            "lease_id": "LEASE-M1-CHECK", "status": "worker_passed",
            "current_task_id": None, "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan), "base_sha": self.head,
            "head_sha": head, "diff_summary": "Completed both atomic tasks.",
            "changed_files": changed,
            "task_results": [
                {"task_id": "M1/T01", "status": "worker_passed", "head_sha": task_one,
                 "verifier_ids": ["verify-m1-1"], "commits": [task_one],
                 "evidence_paths": ["evidence/t01.txt"]},
                {"task_id": "M1/T02", "status": "worker_passed", "head_sha": head,
                 "verifier_ids": ["verify-m1-2"], "commits": [head],
                 "evidence_paths": ["evidence/t02.txt"]},
            ],
            "verifiers": [
                {"id": verifier_id, "status": "PASS", "evidence": keys[verifier_id]}
                for verifier_id in ("verify-m1-1", "verify-m1-2", "worker-m1")
            ],
            "commits": [task_one, head], "evidence_paths": ["evidence/mission.txt"],
            "blockers": [], "residual_risks": [], "integration_notes": "",
            "subagent_activity": {"status": "not_applicable",
                                  "skip_reason": "flat mission worker", "children": []},
        }
        return {
            "run_id": self.run["run_id"], "node_id": "N-M1", "attempt_id": "ATT-M1-CHECK",
            "plan_id": self.plan["plan_id"], "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": self.run["graph_state"]["graph_revision"],
            "batch_base_sha": self.head, "status": "succeeded", "outcome": "pass",
            "worker_result": worker_result, "refinement_request": None,
            "evidence_paths": ["evidence/node.txt"],
        }

    def prepare(self) -> dict:
        node_result = self.stage_worker()
        _observe_bound_worker(self.plan, self.run, node_result, self.root)
        self.write_control(self.plan, self.run)
        code, _, err = self.cli("acquire-run-lock", repo_root=self.root)
        self.assertEqual(0, code, err)
        return node_result

    def record(self, node_result: dict, name: str, *extra: str) -> tuple[int, str, str]:
        path = self.control / name
        path.write_text(json.dumps({"node_result": node_result}), encoding="utf-8")
        verifiers = [arg for item in self.verifier_paths for arg in ("--verifier-result", str(item))]
        return self.cli("record-worker-result", "--node-result", str(path), *verifiers, *extra,
                        repo_root=self.root)

    def test_check_with_a_stale_lease_fails_and_keeps_the_attempt_open(self) -> None:
        node_result = self.prepare()
        stale = copy.deepcopy(node_result)
        stale["worker_result"]["lease_id"] = "LEASE-M1-OLD"
        before = self.run_path.read_bytes()
        code, out, err = self.record(stale, "stale.json", "--check")
        self.assertEqual(2, code, out)
        self.assertIn("worker result does not validate", err)
        self.assertIn("stale_binding", err)
        self.assertEqual(before, self.run_path.read_bytes())
        run = load_run(self.run_path)
        self.assertEqual("running", run["graph_state"]["node_states"]["N-M1"]["phase"])
        self.assertEqual("worker_running", run["mission_states"]["M1"]["phase"])
        self.assertEqual([], run["verifier_executions"])

        code, _, err = self.record(node_result, "corrected.json")
        self.assertEqual(0, code, err)
        run = load_run(self.run_path)
        self.assertEqual("worker_passed", run["mission_states"]["M1"]["phase"])
        self.assertEqual(3, len(run["verifier_executions"]))

    def test_check_with_a_valid_packet_passes_and_writes_nothing(self) -> None:
        node_result = self.prepare()
        before = self.run_path.read_bytes()
        code, out, err = self.record(node_result, "valid.json", "--check")
        self.assertEqual(0, code, err)
        self.assertIn("check passed: record-worker-result", out)
        self.assertEqual(before, self.run_path.read_bytes())

    def test_without_check_a_stale_lease_is_still_retained_as_a_failure(self) -> None:
        stale = self.prepare()
        stale["worker_result"]["lease_id"] = "LEASE-M1-OLD"
        code, out, err = self.record(stale, "stale.json")
        self.assertEqual(0, code, err)
        self.assertEqual("worker_failed", json.loads(out)["phase"])
        self.assertEqual("failed", load_run(self.run_path)["graph_state"]["node_states"]["N-M1"]["phase"])


if __name__ == "__main__":
    unittest.main()
