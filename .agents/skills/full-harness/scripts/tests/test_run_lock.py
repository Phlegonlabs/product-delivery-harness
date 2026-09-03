#!/usr/bin/env python3
"""The run lock prevents two parents from mutating one RUN."""

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


class RunLockTests(unittest.TestCase):
    def base_run(self) -> dict:
        plan, run = current_preintegration_review_state()
        return plan, run

    def lock_errors(self, run) -> list[str]:
        return [error for error in validate_run(self.plan, run) if "run_lock" in error]

    def setUp(self) -> None:
        self.plan, self.run = self.base_run()
        self.run["run_lock"] = {
            "session_id": "session-a",
            "acquired_at": _iso(datetime.now(timezone.utc) - timedelta(minutes=5)),
            "heartbeat_at": _iso(datetime.now(timezone.utc) - timedelta(minutes=1)),
        }

    def test_schema_accepts_a_well_formed_lock(self) -> None:
        self.assertEqual([], self.lock_errors(self.run))

    def test_schema_rejects_a_heartbeat_before_acquisition(self) -> None:
        self.run["run_lock"]["heartbeat_at"] = "2000-01-01T00:00:00Z"
        self.assertTrue(self.lock_errors(self.run))
        self.run["run_lock"]["heartbeat_at"] = 7
        self.assertTrue(self.lock_errors(self.run))

    def test_a_fresh_foreign_lock_blocks_other_sessions(self) -> None:
        with self.assertRaises(ManifestError):
            harness_transition._ensure_run_lock_free(self.run, "session-b")
        with self.assertRaises(ManifestError):
            harness_transition._ensure_run_lock_free(self.run, None)

    def test_the_holding_session_and_missing_locks_pass(self) -> None:
        harness_transition._ensure_run_lock_free(self.run, "session-a")
        del self.run["run_lock"]
        harness_transition._ensure_run_lock_free(self.run, "session-b")

    def test_a_stale_lock_is_takeover_eligible(self) -> None:
        self.run["run_lock"]["heartbeat_at"] = _iso(
            datetime.now(timezone.utc) - timedelta(hours=2)
        )
        harness_transition._ensure_run_lock_free(self.run, "session-b")

    def test_acquire_release_and_heartbeat_round_trip(self) -> None:
        del self.run["run_lock"]
        harness_transition._acquire_run_lock(
            self.run, Namespace(session_id="s1", owner="parent")
        )
        self.assertEqual("s1", self.run["run_lock"]["session_id"])
        with self.assertRaises(ManifestError):
            harness_transition._acquire_run_lock(
                self.run, Namespace(session_id="s2", owner=None)
            )
        harness_transition._heartbeat_run_lock(self.run, Namespace(session_id="s1"))
        with self.assertRaises(ManifestError):
            harness_transition._release_run_lock(self.run, Namespace(session_id="s2"))
        harness_transition._release_run_lock(self.run, Namespace(session_id="s1"))
        self.assertNotIn("run_lock", self.run)

    def test_watchdog_reports_staleness_and_running_candidates(self) -> None:
        self.run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]["phase"] = "running"
        live = harness_transition._watchdog_report(self.run, stale_after=15)
        self.assertTrue(any("is live" in line for line in live))
        self.assertTrue(any("parent live" in line for line in live))

        self.run["run_lock"]["heartbeat_at"] = _iso(
            datetime.now(timezone.utc) - timedelta(hours=2)
        )
        stale = harness_transition._watchdog_report(self.run, stale_after=15)
        self.assertTrue(any("safe to reclaim" in line for line in stale))
        self.assertTrue(any("interrupted-work candidates" in line for line in stale))


if __name__ == "__main__":
    unittest.main()
