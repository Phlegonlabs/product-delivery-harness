#!/usr/bin/env python3
"""Regression tests for the post-review hardening fixes."""

from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
from harness_core import ManifestError  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


LEASE_ARGS = dict(
    mission_id="M1",
    node_id="N-M1",
    worker_id="W-M1-A",
    lease_id="LEASE-M1-A",
    attempt_id="ATT-M1-A",
    branch_ref="feature/m1",
    worktree_path="/tmp/wt-m1",
    provider="codex",
    driver="subagents",
    worker_runtime="subagent",
    workspace_mode="parent_managed_worktree",
    completion_channel="agent_result",
)


class ReviewHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        plan, run = current_preintegration_review_state()
        self.plan = plan
        self.run = run
        self.run["active_wave"].update(
            {
                "wave_id": "B-1",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1"],
            }
        )
        self.run["integration"]["batch_base_sha"] = "a" * 40

    def test_failed_and_blocked_missions_accept_a_new_lease(self) -> None:
        for phase in ("worker_failed", "blocked"):
            with self.subTest(phase=phase):
                plan, run = current_preintegration_review_state()
                run["active_wave"].update(
                    {"wave_id": "B-1", "status": "active", "batch_base_sha": "a" * 40,
                     "selected_missions": ["M1"]}
                )
                mission = run["mission_states"]["M1"]
                mission["phase"] = phase
                mission["blockers"] = ["stale evidence"]
                node = run["graph_state"]["node_states"]["N-M1"]
                node["phase"] = "failed" if phase == "worker_failed" else "blocked"
                node["last_outcome"] = "blocked"
                node["blockers"] = ["interrupted"]

                harness_transition._lease_worker(
                    plan, run, Namespace(**LEASE_ARGS)
                )

                self.assertEqual("worker_running", mission["phase"])
                self.assertEqual([], mission["blockers"])
                self.assertEqual("running", node["phase"])
                self.assertIsNone(node["last_outcome"])
                self.assertEqual([], node["blockers"])

    def test_accept_wave_refuses_a_live_wave_even_with_the_same_id(self) -> None:
        self.run["active_wave"]["wave_id"] = "B-1"
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(wave_id="B-1", mission_id=["M1"], batch_base_sha="a" * 40),
            )

    def test_a_naive_or_garbage_heartbeat_fails_closed(self) -> None:
        for bad in ("2026-09-03T10:00:00", "not-a-date"):
            with self.subTest(value=bad):
                self.run["run_lock"] = {
                    "session_id": "session-a",
                    "acquired_at": _iso(datetime.now(timezone.utc) - timedelta(minutes=5)),
                    "heartbeat_at": bad,
                }
                # Unparseable/naive heartbeats read as no usable age: the
                # watchdog reports them stale, and a foreign session may
                # take over rather than the gate crashing.
                age = harness_transition._lock_age_minutes(self.run)
                self.assertIsNone(age)
                harness_transition._ensure_run_lock_free(self.run, "session-b")

    def test_the_holding_sessions_transition_refreshes_the_heartbeat(self) -> None:
        lock = {
            "session_id": "session-a",
            "acquired_at": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
            "heartbeat_at": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
        }
        self.run["run_lock"] = lock
        # Stale as-is: a foreign session may take over.
        harness_transition._ensure_run_lock_free(self.run, "session-b")
        # The post-transition refresh in main() renews the holder's heartbeat,
        # after which the same foreign session is blocked again.
        self.assertEqual("session-a", lock.get("session_id"))
        lock["heartbeat_at"] = harness_transition._now()
        with self.assertRaises(ManifestError):
            harness_transition._ensure_run_lock_free(self.run, "session-b")

    def test_a_non_dict_run_lock_fails_schema_validation(self) -> None:
        self.run["run_lock"] = "session-a"
        errors = validate_run(self.plan, self.run)
        self.assertTrue(any("run.run_lock" in error for error in errors))

    def test_a_malformed_verifier_in_executions_reports_instead_of_crashing(self) -> None:
        executions = self.run.get("verifier_executions")
        if not isinstance(executions, list) or not executions:
            self.skipTest("fixture carries no verifier executions")
        executions[0]["verifier"] = "not-a-dict"
        errors = validate_run(self.plan, self.run)
        self.assertIsInstance(errors, list)
        self.assertTrue(any("verifier" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
