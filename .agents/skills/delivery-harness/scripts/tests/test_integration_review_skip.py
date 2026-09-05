#!/usr/bin/env python3
"""An integration-stage review may be skipped only on a byte-identical tree."""

from __future__ import annotations

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
from harness_core import is_full_sha  # noqa: E402
from harness_manifest import ManifestError, plan_digest, validate_run  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402

HEAD = "c" * 40


class IntegrationReviewSkipTests(unittest.TestCase):
    def state(self, *, reviewed_sha: str, review_type: str = "visual"):
        """A run whose integration head carries a passed pre-integration review.

        The fixture's integration-stage node reviews `visual`, so the
        pre-integration PASS is relabelled to match: the short-circuit only
        applies when the same review type already covered that exact commit.
        """

        plan, run = current_preintegration_review_state()
        for node in plan["graph"]["nodes"]:
            review = node.get("review")
            if isinstance(review, dict) and node["id"] == "N-FRONTEND-REVIEW":
                review["type"] = review_type
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["integration"]["integration_head_sha"] = HEAD
        run["review_workers"] = [
            {
                "worker_id": "RW-PRE",
                "node_id": "N-FRONTEND-REVIEW",
                "attempt_id": "ATT-PRE",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": reviewed_sha,
                "review_path": "C:/repo/worktrees/M1",
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": None,
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_passed",
                "outcome": "pass",
                "findings": [],
            }
        ]
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"].update(
            {
                "phase": "skipped",
                "attempts": 0,
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        return plan, run

    def skip_errors(self, plan, run) -> list[str]:
        return [
            error
            for error in validate_run(plan, run)
            if "skipped integration review" in error
        ]

    def test_skip_is_accepted_when_the_reviewed_sha_is_the_integration_head(self) -> None:
        plan, run = self.state(reviewed_sha=HEAD)

        self.assertEqual([], self.skip_errors(plan, run))

    def test_skip_is_rejected_when_the_head_moved(self) -> None:
        # A different commit is a different tree, so "did the combination
        # break" is a real question and the review has to run.
        plan, run = self.state(reviewed_sha="d" * 40)

        self.assertTrue(self.skip_errors(plan, run))

    def test_skip_is_rejected_for_a_different_review_type(self) -> None:
        # A backend review of that commit says nothing about its visual surface.
        plan, run = self.state(reviewed_sha=HEAD, review_type="backend_code")

        self.assertTrue(self.skip_errors(plan, run))

    def test_skip_is_rejected_without_a_recorded_integration_head(self) -> None:
        plan, run = self.state(reviewed_sha=HEAD)
        run["integration"]["integration_head_sha"] = None

        self.assertTrue(self.skip_errors(plan, run))

    def test_skip_is_accepted_when_the_tree_is_byte_identical(self) -> None:
        # A merge commit integration of one mission has a new SHA but the
        # same tree as the reviewed commit; there are no new bytes to read.
        plan, run = self.state(reviewed_sha="d" * 40)
        run["integration"]["integration_tree_sha"] = "e" * 40
        run["review_workers"][0]["tree_sha"] = "e" * 40

        self.assertEqual([], self.skip_errors(plan, run))

    def test_tree_skip_is_rejected_when_the_trees_differ(self) -> None:
        plan, run = self.state(reviewed_sha="d" * 40)
        run["integration"]["integration_tree_sha"] = "e" * 40
        run["review_workers"][0]["tree_sha"] = "f" * 40

        self.assertTrue(self.skip_errors(plan, run))

    def test_tree_skip_is_rejected_without_the_recorded_integration_tree(self) -> None:
        # Without integration_tree_sha the validator cannot bind the skip;
        # a parent-claimed worker tree_sha alone proves nothing.
        plan, run = self.state(reviewed_sha="d" * 40)
        run["review_workers"][0]["tree_sha"] = "e" * 40

        self.assertTrue(self.skip_errors(plan, run))

    def test_skip_transition_binds_byte_identity_against_live_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)
            (root / "file.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            reviewed = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            # A merge-style commit: new SHA, byte-identical tree.
            subprocess.run(
                ["git", "commit", "--allow-empty", "-qm", "merge"], cwd=root, check=True
            )
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            self.assertNotEqual(reviewed, head)

            plan, run = self.state(reviewed_sha=reviewed)
            run["integration"]["integration_head_sha"] = head
            run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "dormant"

            harness_transition._skip_integration_review(
                plan,
                run,
                Namespace(node_id="N-VISUAL-REVIEW", worker_id="RW-PRE", repo_root=root),
            )

            self.assertEqual([], self.skip_errors(plan, run))
            node_state = run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]
            self.assertEqual("skipped", node_state["phase"])
            self.assertTrue(is_full_sha(run["integration"]["integration_tree_sha"]))
            self.assertEqual(
                run["review_workers"][0]["tree_sha"],
                run["integration"]["integration_tree_sha"],
            )

    def test_skip_transition_refuses_when_the_trees_differ(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)
            (root / "file.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            reviewed = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            (root / "file.txt").write_text("changed\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "changed"], cwd=root, check=True)
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()

            plan, run = self.state(reviewed_sha=reviewed)
            run["integration"]["integration_head_sha"] = head
            run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "dormant"

            with self.assertRaises(ManifestError):
                harness_transition._skip_integration_review(
                    plan,
                    run,
                    Namespace(
                        node_id="N-VISUAL-REVIEW", worker_id="RW-PRE", repo_root=root
                    ),
                )

    def test_record_review_attempt_persists_the_reviewed_tree(self) -> None:
        plan, run = self.state(reviewed_sha=HEAD)
        run["review_workers"][0]["phase"] = "leased"
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {"phase": "running", "last_attempt_id": "ATT-PRE", "bound_worker_id": "RW-PRE"}
        )
        lineage_id = next(
            node["review"]["lineage_id"]
            for node in plan["graph"]["nodes"]
            if isinstance(node.get("review"), dict)
            and node["id"] == "N-FRONTEND-REVIEW"
        )

        harness_transition._record_review_attempt(
            plan,
            run,
            Namespace(
                lineage=lineage_id,
                worker_id="RW-PRE",
                attempt_id="ATT-PRE",
                mission_id=None,
                result="pass",
                evidence=["exact-head review passed"],
                finding=None,
                failure_family_id=None,
                failure_primitive=None,
                equivalence_class=None,
                strategy=None,
                tree_sha="e" * 40,
                repo_root=None,
            ),
        )

        self.assertEqual("e" * 40, run["review_workers"][0]["tree_sha"])

    def test_tree_skip_is_rejected_for_a_malformed_tree_sha(self) -> None:
        plan, run = self.state(reviewed_sha="d" * 40)
        run["integration"]["integration_tree_sha"] = "not-a-sha"
        run["review_workers"][0]["tree_sha"] = "e" * 40

        errors = validate_run(plan, run)
        self.assertTrue(
            any("integration_tree_sha" in error for error in errors), errors
        )
        self.assertTrue(self.skip_errors(plan, run))

    def test_skip_is_rejected_when_the_prior_review_did_not_pass(self) -> None:
        plan, run = self.state(reviewed_sha=HEAD)
        run["review_workers"][0].update({"phase": "worker_failed", "outcome": "fix_required"})

        self.assertTrue(self.skip_errors(plan, run))


if __name__ == "__main__":
    unittest.main()
