#!/usr/bin/env python3
"""The close-wave lifecycle and the tightened write-path guards."""

from __future__ import annotations

import hashlib
import json
import subprocess
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
from harness_authorization import execution_covers  # noqa: E402
from harness_core import ManifestError  # noqa: E402
import manifest_fixtures as mf  # noqa: E402


def make_repo() -> tuple[tempfile.TemporaryDirectory, Path, str, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    mf.git(root, "init", "-q", "-b", "integration")
    mf.git(root, "config", "user.email", "t@example.com")
    mf.git(root, "config", "user.name", "T")
    (root / "file.txt").write_text("base\n", encoding="utf-8")
    mf.git(root, "add", ".")
    mf.git(root, "commit", "-qm", "base")
    base = mf.git(root, "rev-parse", "HEAD")
    (root / "file.txt").write_text("integrated\n", encoding="utf-8")
    mf.git(root, "add", ".")
    mf.git(root, "commit", "-qm", "work")
    head = mf.git(root, "rev-parse", "HEAD")
    return temp, root, base, head


def load_run_block(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.find("```json\n") + len("```json\n")
    end = text.find("\n```", start)
    return json.loads(text[start:end])["harness_run"]


def save_run_block(path: Path, run: dict) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.find("```json\n")
    end = text.find("\n```", start)
    body = json.dumps({"harness_run": run}, indent=2, ensure_ascii=False)
    path.write_text(text[: start + len("```json\n")] + body + text[end:], encoding="utf-8")


class CloseWaveCliTests(unittest.TestCase):
    """Drive the real CLI main() across the full write path, then close."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.gitroot = self.root / "git"
        (self.gitroot / "docs" / "product").mkdir(parents=True)
        prd = self.gitroot / "docs" / "product" / "prd.md"
        arch = self.gitroot / "docs" / "product" / "architecture.md"
        prd.write_text("product contract\n", encoding="utf-8")
        arch.write_text("technical contract\n", encoding="utf-8")
        self.base = mf.init_repo(self.gitroot, "file.txt")
        (self.gitroot / "file.txt").write_text("work\n", encoding="utf-8")
        mf.git(self.gitroot, "add", ".")
        mf.git(self.gitroot, "commit", "-qm", "work")
        self.head = mf.git(self.gitroot, "rev-parse", "HEAD")
        self.wt1 = str(self.root / "wt-m1")

        self.plan = mf.valid_plan()
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd.read_bytes()
        ).hexdigest()
        self.plan["sources"][1]["content_sha256"] = hashlib.sha256(
            arch.read_bytes()
        ).hexdigest()
        run = mf.valid_run(self.plan)
        mf.authorize_execution(run, ["M1", "M2"])
        mf.authorize_action(
            run, "spawn_subagents", ["M1", "M2"],
            ["*", "worker:W-M1-A", "worker:RW-1"],
        )
        mf.authorize_action(
            run, "create_local_worktrees", ["M1"], [f"worktree:{self.wt1}"]
        )
        mf.authorize_action(run, "create_local_branches", ["M1"], ["branch:wt/m1"])
        mf.authorize_action(run, "create_local_commits", ["M1"], ["branch:wt/m1"])
        mf.authorize_action(
            run, "integrate_locally", ["M1"], ["branch:codex/test"]
        )
        run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["sequential_parent", "subagents"]
        run["runtime_capabilities"]["worker_runtime"] = "subagent"
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["git"]["worktrees"] = [
            {
                "path": self.wt1,
                "head_sha": None,
                "branch_ref": "wt/m1",
                "managed_by": "parent",
                "dirty": False,
            }
        ]
        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.plan_path.write_text(
            mf.manifest_markdown(
                "## Harness Plan Manifest", "harness_plan", self.plan
            ),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._temp.cleanup()

    def cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "harness_transition.py"),
                "--plan",
                str(self.plan_path),
                "--run",
                str(self.run_path),
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def _integrate_m1(self) -> None:
        result = self.cli(
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.base,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli(
            "lease-worker",
            "--mission-id", "M1", "--node-id", "N-M1",
            "--worker-id", "W-M1-A", "--lease-id", "L-M1",
            "--attempt-id", "A-M1", "--branch-ref", "wt/m1",
            "--worktree-path", self.wt1,
            "--provider", "codex", "--driver", "subagents",
        )
        self.assertEqual(0, result.returncode, result.stderr)

        live = load_run_block(self.run_path)
        live["mission_states"]["M1"].update(
            {"phase": "worker_passed", "head_sha": self.head}
        )
        worker = next(w for w in live["workers"] if w["worker_id"] == "W-M1-A")
        worker.update({"phase": "worker_passed", "worker_head_sha": self.head})
        live["observed"]["git"]["worktrees"][0]["head_sha"] = self.head
        live["attempt_log"].append(
            {
                "attempt_id": "A-M1-RESULT",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": "L-M1",
                "kind": "worker",
                "result": "pass",
                "evidence": ["worker passed"],
                "review_lineage_id": None,
                "failure_family_ids": [],
            }
        )
        live["verifier_executions"] = [
            mf.retained_gate_execution(
                self.plan, live, self.plan["missions"][0]["worker_verifiers"][0],
                layer="worker", execution_id="EXEC-W-M1", mission_id="M1",
                attempt_id="A-M1-RESULT", lease_id="L-M1", head_sha=self.head,
                checkout_role="worker",
            ),
            mf.retained_gate_execution(
                self.plan, live, self.plan["missions"][0]["integration_verifiers"][0],
                layer="mission_integration", execution_id="EXEC-I-M1",
                mission_id="M1", attempt_id=None, lease_id=None,
                head_sha=self.head,
            ),
        ]
        save_run_block(self.run_path, live)

        result = self.cli(
            "--repo-root", str(self.gitroot),
            "reserve-review-dispatch", "--node-id", "N-REVIEW-M1",
            "--worker-id", "RW-1", "--attempt-id", "RA-1",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli(
            "record-review-attempt", "--lineage", "REVIEW-M1",
            "--attempt-id", "RA-1", "--worker-id", "RW-1",
            "--mission-id", "M1", "--result", "pass", "--evidence", "reviewed",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "record-integration", "--mission-id", "M1",
            "--integrated-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_close_wave_then_accept_the_next_wave(self) -> None:
        self._integrate_m1()
        result = self.cli("close-wave", "--source", "wave W-1 fully resolved")
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("closed", live["active_wave"]["status"])
        self.assertEqual(
            [{"wave_id": "W-1", "batch_base_sha": self.base}],
            live["closed_waves"],
        )
        self.assertTrue(
            any(a["kind"] == "wave_close" for a in live["attempt_log"])
        )
        # The next wave may open on a fresh base with the tombstone retained.
        result = self.cli(
            "accept-wave", "--wave-id", "W-2", "--mission-id", "M2",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("active", live["active_wave"]["status"])
        self.assertEqual(["M2"], live["active_wave"]["selected_missions"])
        self.assertEqual(1, len(live["closed_waves"]))

    def test_close_wave_refuses_then_recovers_after_reconcile(self) -> None:
        result = self.cli(
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.base,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli(
            "lease-worker",
            "--mission-id", "M1", "--node-id", "N-M1",
            "--worker-id", "W-M1-A", "--lease-id", "L-M1",
            "--attempt-id", "A-M1", "--branch-ref", "wt/m1",
            "--worktree-path", self.wt1,
            "--provider", "codex", "--driver", "subagents",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli("close-wave", "--source", "premature")
        self.assertEqual(2, result.returncode)
        self.assertIn("live workers", result.stderr)
        # Reconciling the interrupted worker resolves the mission to blocked,
        # which is a closeable terminal state: the wave closes and a fresh
        # wave may then re-select the mission.
        self.assertEqual(
            0,
            self.cli(
                "reconcile-interrupted", "--worker-id", "W-M1-A",
                "--reason", "interrupted",
            ).returncode,
        )
        result = self.cli("close-wave", "--source", "recovered after reconcile")
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("closed", live["active_wave"]["status"])
        self.assertEqual(
            "blocked", live["mission_states"]["M1"]["phase"]
        )
        result = self.cli(
            "accept-wave", "--wave-id", "W-2", "--mission-id", "M1",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)


class AcceptWaveGuardTests(unittest.TestCase):
    """accept-wave refuses an unauthorized, unready, or unobserved RUN."""

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        self.args = dict(
            wave_id="W-1", mission_id=["M1"], batch_base_sha="a" * 40
        )

    def test_unauthorized_draft_run_is_refused(self) -> None:
        for field, value in (
            ("execution_authorized", False),
            ("status", "draft"),
            ("plan_readiness", "draft"),
        ):
            original = self.run[field]
            self.run[field] = value
            with self.assertRaises(ManifestError):
                harness_transition._accept_wave(
                    self.plan, self.run, Namespace(**self.args)
                )
            self.run[field] = original
        self.run["observed"]["captured_at"] = None
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan, self.run, Namespace(**self.args)
            )

    def test_authorized_but_uncovered_mission_is_refused(self) -> None:
        mf.authorize_execution(self.run, ["M2"])
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan, self.run, Namespace(**self.args)
            )
        self.assertFalse(execution_covers(self.run, "M1"))


class LeaseWorkerGuardTests(unittest.TestCase):
    """lease-worker binds the mission's own node on a satisfied frontier."""

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        mf.authorize_execution(self.run, ["M1", "M2"])
        self.run["active_wave"].update(
            {
                "wave_id": "W-1",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1", "M2"],
            }
        )

    def lease(self, mission_id: str, node_id: str) -> None:
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id=mission_id,
                node_id=node_id,
                worker_id=f"W-{mission_id}",
                lease_id=f"L-{mission_id}",
                attempt_id=f"A-{mission_id}",
                branch_ref=f"wt/{mission_id.lower()}",
                worktree_path=f"/tmp/{mission_id}",
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
            ),
        )

    def test_m2_is_refused_while_m1_is_unfinished(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            self.lease("M2", "N-M2")
        self.assertIn("dependency", str(caught.exception))

    def test_foreign_node_is_refused(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            self.lease("M1", "N-REVIEW-M1")
        self.assertIn("is not mission", str(caught.exception))

    def test_m1_leases_and_unblocks_m2(self) -> None:
        self.lease("M1", "N-M1")
        self.assertEqual(
            "worker_running", self.run["mission_states"]["M1"]["phase"]
        )
        with self.assertRaises(ManifestError):
            # M1 is leased but not integrated: the frontier still blocks M2.
            self.lease("M2", "N-M2")
        self.run["mission_states"]["M1"]["phase"] = "integrated"
        self.run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        self.lease("M2", "N-M2")
        self.assertEqual(
            "worker_running", self.run["mission_states"]["M2"]["phase"]
        )


class RecordIntegrationGuardTests(unittest.TestCase):
    """record-integration proves the SHA against live Git."""

    def setUp(self) -> None:
        self._temp, self.root, self.base, self.head = make_repo()
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        mf.authorize_execution(self.run, ["M1"])
        self.run["mission_states"]["M1"].update(
            {"phase": "worker_passed", "head_sha": self.head}
        )
        self.args = dict(mission_id="M1", integrated_sha=self.head)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_missing_repo_root_is_refused(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            harness_transition._record_integration(
                self.plan, self.run, Namespace(repo_root=None, **self.args)
            )
        self.assertIn("--repo-root", str(caught.exception))

    def test_non_ancestor_sha_is_refused(self) -> None:
        other = mf.git(self.root, "rev-parse", "HEAD~1")
        self.run["integration"]["batch_base_sha"] = self.head
        self.args["integrated_sha"] = other
        with self.assertRaises(ManifestError) as caught:
            harness_transition._record_integration(
                self.plan, self.run, Namespace(repo_root=self.root, **self.args)
            )
        self.assertIn("ancestor", str(caught.exception))

    def test_head_mismatch_is_refused(self) -> None:
        self.run["integration"]["batch_base_sha"] = self.base
        self.args["integrated_sha"] = self.base
        with self.assertRaises(ManifestError) as caught:
            harness_transition._record_integration(
                self.plan, self.run, Namespace(repo_root=self.root, **self.args)
            )
        self.assertIn("HEAD", str(caught.exception))


class CloseWaveUnitTests(unittest.TestCase):
    """close-wave resets wave-bounded grants and keeps run_complete ones."""

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        mf.authorize_execution(self.run, ["M1"])
        base = "a" * 40
        self.run["active_wave"].update(
            {
                "wave_id": "W-1",
                "status": "active",
                "batch_base_sha": base,
                "selected_missions": ["M1"],
            }
        )
        self.run["mission_states"]["M1"]["phase"] = "integrated"
        self.run["authorizations"]["create_local_commits"] = {
            "authorized": True,
            "source": "user granted the wave",
            "scope": {
                "run_id": self.run["run_id"],
                "plan_revision": self.run["plan"]["revision"],
                "plan_digest_sha256": self.run["plan"]["digest_sha256"],
                "mission_ids": ["M1"],
                "targets": ["branch:wt/m1"],
                "wave_id": "W-1",
                "batch_base_sha": base,
            },
            "expires_when": "wave_closed",
        }
        self.base = base

    def close(self) -> None:
        harness_transition._close_wave(
            self.run, Namespace(source="test close")
        )

    def test_wave_closed_grants_reset_run_complete_grants_survive(self) -> None:
        self.close()
        self.assertEqual("closed", self.run["active_wave"]["status"])
        self.assertEqual(
            [{"wave_id": "W-1", "batch_base_sha": self.base}],
            self.run["closed_waves"],
        )
        self.assertEqual(
            {"authorized": False, "source": None},
            self.run["authorizations"]["create_local_commits"],
        )
        # authorize_execution wrote a run_complete boundary: it survives.
        self.assertTrue(self.run["execution_authorized"])

    def test_wave_bounded_execution_authorization_clears(self) -> None:
        scope = self.run["execution_authorization_scope"]
        scope["expires_when"] = "wave_closed"
        scope["wave_id"] = "W-1"
        scope["batch_base_sha"] = self.base
        self.close()
        self.assertFalse(self.run["execution_authorized"])
        self.assertIsNone(self.run["execution_authorization_source"])
        self.assertIsNone(self.run["execution_authorization_scope"])

    def test_idle_wave_and_double_close_are_refused(self) -> None:
        self.close()
        with self.assertRaises(ManifestError):
            self.close()
        self.run["active_wave"].update(
            {"status": "idle", "wave_id": None, "batch_base_sha": None}
        )
        with self.assertRaises(ManifestError):
            self.close()

    def test_worker_passed_mission_blocks_close(self) -> None:
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        with self.assertRaises(ManifestError) as caught:
            self.close()
        self.assertIn("unresolved", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
