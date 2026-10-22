#!/usr/bin/env python3
"""Regression test for retry-head clearing on a new mission lease."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for entry in (str(TESTS_DIR), str(SCRIPTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import harness_transition  # noqa: E402
from test_write_path_transitions import WritePathTransitionTests  # noqa: E402


class LeaseRetryHeadTests(WritePathTransitionTests):
    def test_new_lease_clears_the_stale_mission_head(self) -> None:
        harness_transition._record_observation(
            self.plan, self.run, argparse.Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            argparse.Namespace(
                wave_id="B-RETRY",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        self.run["mission_states"]["M1"].update(
            {
                "phase": "worker_failed",
                "head_sha": "a" * 40,
                "blockers": ["stale attempt one head"],
            }
        )
        self.run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "failed",
                "last_outcome": "retryable_failure",
                "attempts": 1,
                "last_attempt_id": "ATT-OLD",
                "blockers": ["stale attempt one head"],
            }
        )
        self.run["attempt_log"].append(
            {
                "attempt_id": "ATT-OLD",
                "mission_id": "M1",
                "task_id": "M1/T01",
                "lease_id": "LEASE-OLD",
                "kind": "dispatch",
                "result": "retryable_failure",
                "evidence": ["stale head rejected"],
            }
        )
        harness_transition._lease_worker(
            self.plan,
            self.run,
            argparse.Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-M1-RETRY",
                lease_id="LEASE-M1-RETRY",
                attempt_id="ATT-M1-RETRY",
                branch_ref="feature/m1-retry",
                worktree_path=str(self.root / "wt-m1-retry"),
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
                report_path=None,
            ),
        )
        state = self.run["mission_states"]["M1"]
        self.assertEqual("worker_running", state["phase"])
        self.assertIsNone(state["head_sha"])
        self.assertEqual("LEASE-M1-RETRY", state["lease_id"])
        self.assertEqual("W-M1-RETRY", state["worker_id"])
        self.assertIsNone(self.run["workers"][-1]["worker_head_sha"])
        self.assertEqual("ATT-OLD", self.run["attempt_log"][-2]["attempt_id"])
        self.assertEqual("retryable_failure", self.run["attempt_log"][-2]["result"])


if __name__ == "__main__":
    unittest.main()
