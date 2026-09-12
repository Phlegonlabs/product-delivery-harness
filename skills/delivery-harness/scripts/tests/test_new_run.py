#!/usr/bin/env python3
"""Tests for the RUN.md generator."""

from __future__ import annotations

import copy
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

    def test_security_review_lineage_is_generated_from_the_plan(self) -> None:
        run = load_run(self.generate())

        security = run["review_lineages"]["REVIEW-SECURITY"]

        self.assertEqual("security", security["review_type"])
        self.assertEqual(["M1"], security["mission_ids"])
        self.assertEqual(0, security["consumed_attempts"])

    def test_new_run_requires_an_explicit_security_policy(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan.pop("security_review")

        with self.assertRaisesRegex(
            new_run.ManifestError, "explicit plan.security_review"
        ):
            new_run.build_run(
                plan,
                run_id="RUN-missing-security-policy",
                branch="refs/heads/test-run",
            )

    def test_graph_revision_follows_a_revised_plan(self) -> None:
        revised = copy.deepcopy(self.plan)
        revised["revision"] = 2

        run = new_run.build_run(
            revised,
            run_id="RUN-revised",
            branch="refs/heads/test-revised-run",
        )

        self.assertEqual(2, run["graph_state"]["graph_revision"])
        self.assertEqual(2, run["active_wave"]["plan_revision"])
        self.assertEqual([], validate_current_plan_run(revised, run))

    def test_seeded_coordination_paths_cover_closeout_rewrites(self) -> None:
        run = load_run(self.generate())

        self.assertEqual(
            [
                "docs/goal/PLAN.md",
                "docs/goal/RUN.md",
                "docs/goal/DECISIONS.md",
                "docs/goal/REFINEMENT_BACKLOG.md",
                "docs/tasks.md",
            ],
            run["integration"]["coordination_paths"],
        )

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

    def test_refusing_a_completed_run_points_at_archive_run(self) -> None:
        import contextlib
        import io
        import json

        out = self.generate()
        out.write_text(
            "# Run\n\n## Harness Run State\n\n```json\n"
            + json.dumps({"harness_run": {"run_id": "RUN-old", "status": "complete"}})
            + "\n```\n",
            encoding="utf-8",
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
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
        self.assertIn("archive_run.py", stderr.getvalue())
        self.assertIn("complete", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
