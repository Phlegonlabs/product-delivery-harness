#!/usr/bin/env python3
"""The scripted write path: observation, wave accept, lease, integration."""

from __future__ import annotations

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
from harness_core import ManifestError  # noqa: E402
from manifest_fixtures import git  # noqa: E402
from test_select_ready_nodes import (  # noqa: E402

    current_preintegration_review_state,
)


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
        plan, run = current_preintegration_review_state()
        plan["revision"] = run["plan"]["revision"]
        run["plan"]["digest_sha256"] = __import__("harness_manifest").plan_digest(plan)
        run["integration"]["branch"] = "integration"
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
            Namespace(wave_id="B-1", mission_id=["M1"], batch_base_sha=self.head),
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

    def test_guards_refuse_the_wrong_states(self) -> None:
        with self.assertRaises(ManifestError):
            harness_transition._record_observation(self.run, Namespace(repo_root=None))

        self.run["active_wave"].update({"status": "active", "wave_id": "B-OTHER"})
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(wave_id="B-1", mission_id=["M1"], batch_base_sha=self.head),
            )

        self.run["active_wave"].update({"status": "idle", "wave_id": None})
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1", mission_id=["M1"], batch_base_sha="not-the-observed-head"
                ),
            )

        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(wave_id="B-1", mission_id=["M1"], batch_base_sha=self.head),
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


if __name__ == "__main__":
    unittest.main()
