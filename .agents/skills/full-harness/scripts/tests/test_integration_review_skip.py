#!/usr/bin/env python3
"""An integration-stage review may be skipped only on a byte-identical tree."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import plan_digest, validate_run  # noqa: E402
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
