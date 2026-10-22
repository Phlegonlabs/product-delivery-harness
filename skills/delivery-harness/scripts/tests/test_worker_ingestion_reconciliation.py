#!/usr/bin/env python3
"""Focused tests for guarded stale-head result reconciliation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for entry in (str(TESTS_DIR), str(SCRIPTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import worker_ingestion_fixture as fixture


class WorkerIngestionReconciliationTests(unittest.TestCase):
    def test_real_original_ingestion_is_rejected_with_sole_diagnostic(self):
        fx = fixture.build_original_failure()
        self.addCleanup(fx.temp.cleanup)
        self.addCleanup(fx.skills_temp.cleanup)
        state = fx.run["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("failed", state["phase"])
        self.assertEqual("retryable_failure", state["last_outcome"])
        self.assertEqual(2, state["attempts"])
        self.assertEqual("A-M01-002", state["last_attempt_id"])
        self.assertEqual("worker_failed", fx.run["mission_states"]["M1"]["phase"])
        self.assertEqual(3, len(fx.verifier_paths))
        self.assertEqual(fx.head, fx.worker_result["head_sha"])


if __name__ == "__main__":
    unittest.main()
