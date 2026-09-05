#!/usr/bin/env python3
"""Tests for the RUN.md generator."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import new_run  # noqa: E402
from harness_manifest import (  # noqa: E402
    load_plan,
    load_run,
    plan_digest,
    validate_current_plan_run,
)

PLAN_TEMPLATE = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"


class NewRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.plan = load_plan(PLAN_TEMPLATE)

    def generate(self) -> Path:
        out = self.dir / "RUN.md"
        code = new_run.main(
            [
                "--plan",
                str(PLAN_TEMPLATE),
                "--run-id",
                "RUN-test",
                "--branch",
                "refs/heads/test-run",
                "--out",
                str(out),
            ]
        )
        self.assertEqual(0, code)
        return out

    def test_generated_run_validates_against_its_plan(self) -> None:
        run = load_run(self.generate())

        self.assertEqual([], validate_current_plan_run(self.plan, run))

    def test_graph_and_mission_state_mirror_the_plan(self) -> None:
        run = load_run(self.generate())

        plan_nodes = {node["id"] for node in self.plan["graph"]["nodes"]}
        plan_edges = {edge["id"] for edge in self.plan["graph"]["edges"]}
        plan_missions = {mission["id"] for mission in self.plan["missions"]}

        self.assertEqual(plan_nodes, set(run["graph_state"]["node_states"]))
        self.assertEqual(plan_edges, set(run["graph_state"]["edge_states"]))
        self.assertEqual(plan_missions, set(run["mission_states"]))
        self.assertEqual(plan_digest(self.plan), run["plan"]["digest_sha256"])

    def test_generated_run_grants_nothing(self) -> None:
        run = load_run(self.generate())

        self.assertFalse(run["execution_authorized"])
        self.assertEqual("draft", run["plan_readiness"])
        self.assertIsNone(run["integration"]["batch_base_sha"])
        self.assertIsNone(run["observed"]["captured_at"])
        for key, entry in run["authorizations"].items():
            with self.subTest(action=key):
                self.assertFalse(entry["authorized"])
                self.assertIsNone(entry["source"])

    def test_refuses_to_overwrite_live_run_state(self) -> None:
        out = self.generate()
        out.write_text("live state", encoding="utf-8")

        code = new_run.main(
            [
                "--plan",
                str(PLAN_TEMPLATE),
                "--run-id",
                "RUN-test",
                "--branch",
                "refs/heads/test-run",
                "--out",
                str(out),
            ]
        )

        self.assertEqual(2, code)
        self.assertEqual("live state", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
