#!/usr/bin/env python3
"""Tests for the RUN.md generator."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
PDB_TESTS_DIR = Path(__file__).resolve().parents[3] / "product-definition-builder" / "scripts" / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(PDB_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(PDB_TESTS_DIR))

import new_run  # noqa: E402
from test_product_package_checker import (  # noqa: E402
    release_architecture,
    strictize_approved_package,
    valid_prd,
    valid_stack,
)
from harness_manifest import (  # noqa: E402
    load_plan,
    load_run,
    plan_digest,
    validate_current_plan_run,
)

while str(PDB_TESTS_DIR) in sys.path:
    sys.path.remove(str(PDB_TESTS_DIR))

PLAN_TEMPLATE = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"


class NewRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.plan = load_plan(PLAN_TEMPLATE)
        self.plan_path = self.dir / "PLAN.md"
        approved_prd, approved_architecture, approved_stack = strictize_approved_package(
            valid_prd(), release_architecture(), valid_stack()
        )
        product_sources = {
            "docs/product/PRD.md": approved_prd.encode("utf-8"),
            "docs/product/architecture.md": approved_architecture.encode("utf-8"),
            "docs/product/stack-decisions.md": approved_stack.encode("utf-8"),
        }
        for location, value in product_sources.items():
            path = self.dir / location
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        for source in self.plan["sources"]:
            source["content_sha256"] = hashlib.sha256(
                product_sources[source["location"]]
            ).hexdigest()
            source["source_revision"] = None
            source["staged_revision"] = None
        body = json.dumps({"harness_plan": self.plan}, indent=2, ensure_ascii=False)
        template = PLAN_TEMPLATE.read_text(encoding="utf-8")
        start = template.index("```json\n") + len("```json\n")
        end = template.index("\n```", start)
        self.plan_path.write_text(template[:start] + body + template[end:], encoding="utf-8")

    def generate(self) -> Path:
        out = self.dir / "RUN.md"
        code = new_run.main(
            [
                "--plan",
                str(self.plan_path),
                "--run-id",
                "RUN-test",
                "--branch",
                "refs/heads/test-run",
                "--out",
                str(out),
                "--repo-root",
                str(self.dir),
            ]
        )
        self.assertEqual(0, code)
        return out

    def test_generated_run_validates_against_its_plan(self) -> None:
        run = load_run(self.generate())

        self.assertEqual([], validate_current_plan_run(self.plan, run, repo_root=self.dir))

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
        self.assertEqual([], validate_current_plan_run(revised, run, repo_root=self.dir))

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
        self.assertEqual("local_only", run["landing"]["mode"])
        self.assertIsNone(run["landing"]["pushed_head_sha"])
        self.assertFalse(run["authorizations"]["push"]["authorized"])
        self.assertFalse(
            any(
                node.get("kind") == "lifecycle" and node.get("ref") == "push"
                for node in self.plan["graph"]["nodes"]
            )
        )
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
                str(self.plan_path),
                "--run-id",
                "RUN-test",
                "--branch",
                "refs/heads/test-run",
                "--out",
                str(out),
                "--repo-root",
                str(self.dir),
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
                    str(self.plan_path),
                    "--run-id",
                    "RUN-test",
                    "--branch",
                    "refs/heads/test-run",
                    "--out",
                    str(out),
                    "--repo-root",
                    str(self.dir),
                ]
            )

        self.assertEqual(2, code)
        self.assertIn("archive_run.py", stderr.getvalue())
        self.assertIn("complete", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
