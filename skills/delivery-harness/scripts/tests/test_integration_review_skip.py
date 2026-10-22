#!/usr/bin/env python3
"""An integration-stage review skips only on a byte-identical tree or a reviewed merge chain."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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

    def acceptance_state(self):
        plan, run = self.state(reviewed_sha=HEAD)
        source = next(node["review"] for node in plan["graph"]["nodes"] if node["id"] == "N-FRONTEND-REVIEW")
        target = next(node["review"] for node in plan["graph"]["nodes"] if node["id"] == "N-VISUAL-REVIEW")
        target["required_evidence"].append("ui_acceptance")
        target["required_tools"] = ["chrome_devtools"]
        for key in ("mission_ids", "scope", "required_evidence", "required_tools"):
            source[key] = list(target[key])
        run["attempt_log"].append({
            "attempt_id": "ATT-PRE", "mission_id": "M1", "task_id": None,
            "lease_id": None, "kind": "review", "result": "pass",
            "review_lineage_id": source["lineage_id"], "failure_family_ids": [],
            "evidence": ["ui_parity:captures/manifest.json", "ui_page_quality:review/report.md"],
        })
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["review_workers"][0]["plan_digest_sha256"] = digest
        return plan, run, source, target

    def test_combined_acceptance_can_reuse_complete_same_tree_review(self) -> None:
        plan, run, _, _ = self.acceptance_state()
        self.assertEqual([], self.skip_errors(plan, run))
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "dormant"
        with patch("harness_transition._git_tree", return_value="e" * 40):
            harness_transition._skip_integration_review(
                plan, run, Namespace(node_id="N-VISUAL-REVIEW", worker_id="RW-PRE", repo_root=Path.cwd())
            )
        self.assertEqual([], self.skip_errors(plan, run))

    def test_combined_acceptance_rejects_incomplete_prior_coverage_and_evidence(self) -> None:
        for missing in ("marker", "scope", "mission_ids", "required_evidence", "required_tools", "parity", "quality", "blank_quality"):
            with self.subTest(missing=missing):
                plan, run, source, target = self.acceptance_state()
                if missing == "marker":
                    source["required_evidence"].remove("ui_acceptance")
                elif missing == "scope":
                    source["scope"] = ["other/**"]
                elif missing == "mission_ids":
                    source["mission_ids"] = []
                elif missing == "required_evidence":
                    target["required_evidence"].append("extra-comparison")
                elif missing == "required_tools":
                    source["required_tools"] = []
                elif missing == "blank_quality":
                    run["attempt_log"][-1]["evidence"][1] = "ui_page_quality: "
                else:
                    index = 0 if missing == "parity" else 1
                    del run["attempt_log"][-1]["evidence"][index]
                self.assertTrue(self.skip_errors(plan, run))
                run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "dormant"
                with patch("harness_transition._git_tree") as git_tree:
                    with self.assertRaisesRegex(ManifestError, "required acceptance coverage"):
                        harness_transition._skip_integration_review(
                            plan, run, Namespace(node_id="N-VISUAL-REVIEW", worker_id="RW-PRE", repo_root=Path.cwd())
                        )
                    git_tree.assert_not_called()

    def test_combined_acceptance_pass_cannot_omit_component_evidence(self) -> None:
        plan, run, _, _ = self.acceptance_state()
        state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        state.update(phase="succeeded", last_attempt_id="ATT-PRE", last_outcome="pass", attempts=1)
        self.assertFalse(any("UI acceptance PASS requires" in error for error in validate_run(plan, run)))
        run["attempt_log"][-1]["evidence"] = ["ui_parity:captures/manifest.json"]
        self.assertTrue(any("UI acceptance PASS requires" in error for error in validate_run(plan, run)))

    def test_combined_acceptance_supports_semantic_scope_containment(self) -> None:
        plan, run, source, target = self.acceptance_state()
        source["scope"] = ["web/**"]
        target["scope"] = ["web/pages/home.tsx"]
        self.assertEqual([], self.skip_errors(plan, run))

    def test_record_combined_acceptance_requires_both_component_anchors(self) -> None:
        for complete in (False, True):
            with self.subTest(complete=complete):
                plan, run, source, _ = self.acceptance_state()
                run["attempt_log"] = [item for item in run["attempt_log"] if item["attempt_id"] != "ATT-PRE"]
                run["review_workers"][0]["phase"] = "leased"
                run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
                    phase="running", last_attempt_id="ATT-PRE", bound_worker_id="RW-PRE"
                )
                evidence = ["ui_parity:captures/manifest.json"]
                if complete:
                    evidence.append("ui_page_quality:review/report.md")
                arguments = Namespace(
                    lineage=source["lineage_id"], worker_id="RW-PRE", attempt_id="ATT-PRE",
                    mission_id=None, result="pass", evidence=evidence, finding=None,
                    failure_family_id=None, failure_primitive=None, equivalence_class=None,
                    strategy=None, tree_sha="e" * 40, repo_root=None,
                )
                if complete:
                    harness_transition._record_review_attempt(plan, run, arguments)
                    self.assertEqual("worker_passed", run["review_workers"][0]["phase"])
                else:
                    with self.assertRaisesRegex(ManifestError, "UI acceptance PASS requires"):
                        harness_transition._record_review_attempt(plan, run, arguments)
                    self.assertEqual("leased", run["review_workers"][0]["phase"])

    def test_skip_is_rejected_when_the_head_moved(self) -> None:
        # A different commit is a different tree, so "did the combination
        # break" is a real question and the review has to run.
        plan, run = self.state(reviewed_sha="d" * 40)

        self.assertTrue(self.skip_errors(plan, run))

    def test_skip_is_rejected_for_a_different_review_type(self) -> None:
        # A backend review of that commit says nothing about its visual surface.
        plan, run = self.state(reviewed_sha=HEAD, review_type="backend_code")

        self.assertTrue(self.skip_errors(plan, run))

    def test_security_review_is_never_skippable(self) -> None:
        plan, run = self.state(reviewed_sha=HEAD, review_type="security")
        for node in plan["graph"]["nodes"]:
            review = node.get("review")
            if isinstance(review, dict) and node["id"] == "N-VISUAL-REVIEW":
                review["type"] = "security"

        errors = self.skip_errors(plan, run)

        self.assertTrue(
            any("security integration review must run fresh" in error for error in errors),
            errors,
        )

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

    def test_skip_transition_refuses_security_even_on_the_same_tree(self) -> None:
        plan, run = self.state(reviewed_sha=HEAD, review_type="security")
        for node in plan["graph"]["nodes"]:
            review = node.get("review")
            if isinstance(review, dict) and node["id"] == "N-VISUAL-REVIEW":
                review["type"] = "security"
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "dormant"

        with self.assertRaisesRegex(
            ManifestError, "security integration review must run fresh"
        ):
            harness_transition._skip_integration_review(
                plan,
                run,
                Namespace(
                    node_id="N-VISUAL-REVIEW",
                    worker_id="RW-PRE",
                    repo_root=Path.cwd(),
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


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


class MergeChainSkipTests(unittest.TestCase):
    """A code integration review may skip on clean merges of reviewed heads."""

    def repo(self, root: Path, *, conflict: bool = False, extra: str | None = None) -> dict[str, str]:
        git(root, "init", "-q", "-b", "run")
        git(root, "config", "user.email", "t@example.com")
        git(root, "config", "user.name", "T")
        for path in ("src/example/a.txt", "src/other/b.txt"):
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text("base\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "base")
        base = git(root, "rev-parse", "HEAD")
        heads = {}
        for mission, path in (("M1", "src/example/a.txt"), ("M3", "src/other/b.txt")):
            git(root, "checkout", "-q", "-b", mission, base)
            target = "src/example/a.txt" if conflict else path
            (root / target).write_text(f"{mission}\n", encoding="utf-8")
            if extra == "out_of_scope" and mission == "M3":
                (root / "src/example/m3.txt").write_text("M3\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", mission)
            heads[mission] = git(root, "rev-parse", "HEAD")
        git(root, "checkout", "-q", "run")
        if extra == "direct_commit":
            (root / "src/unreviewed.txt").write_text("unreviewed\n", encoding="utf-8")
            git(root, "add", ".")
            git(root, "commit", "-qm", "unreviewed")
        git(root, "merge", "-q", "--no-ff", "-m", "merge M1", "M1")
        if conflict:
            subprocess.run(["git", "merge", "-q", "--no-ff", "M3"], cwd=root, capture_output=True)
            (root / "src/example/a.txt").write_text("resolved\n", encoding="utf-8")
            git(root, "commit", "-qam", "merge M3")
        else:
            git(root, "merge", "-q", "--no-ff", "--no-commit", "M3")
            if extra == "evil_merge":
                (root / "src/example/a.txt").write_text("edited in merge\n", encoding="utf-8")
                git(root, "add", ".")
            git(root, "commit", "-qm", "merge M3")
        heads["head"] = git(root, "rev-parse", "HEAD")
        return heads

    def state(self, heads: dict[str, str], *, review_type: str = "frontend_code"):
        plan, run = current_preintegration_review_state()
        missions = {mission["id"]: mission for mission in plan["missions"]}
        missions["M3"]["write_scope"] = ["src/other/**"]
        nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
        nodes["N-VISUAL-REPAIR-CODE-REVIEW"]["review"]["scope"] = ["src/other/**"]
        target = nodes["N-VISUAL-REVIEW"]["review"]
        target.update(type=review_type, mission_ids=["M1", "M3"], scope=["src/example/**", "src/other/**"])
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["integration"]["integration_head_sha"] = heads["head"]
        run["review_workers"] = [
            {
                "worker_id": f"RW-{mission}",
                "node_id": node_id,
                "attempt_id": f"ATT-{mission}",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": heads[mission],
                "review_path": f"C:/repo/worktrees/{mission}",
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": None,
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_passed",
                "outcome": "pass",
                "findings": [],
            }
            for mission, node_id in (("M1", "N-FRONTEND-REVIEW"), ("M3", "N-VISUAL-REPAIR-CODE-REVIEW"))
        ]
        return plan, run

    def skip(self, plan, run, root: Path) -> None:
        harness_transition._skip_integration_review(
            plan, run, Namespace(node_id="N-VISUAL-REVIEW", worker_id=None, repo_root=root)
        )

    def skip_errors(self, plan, run) -> list[str]:
        return [error for error in validate_run(plan, run) if "skipped integration review" in error]

    def test_clean_merges_of_reviewed_heads_skip_with_a_recorded_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            heads = self.repo(root)
            plan, run = self.state(heads)

            self.skip(plan, run, root)

            self.assertEqual("skipped", run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"])
            chain = run["integration"]["reviewed_merge_chain"]
            self.assertEqual(heads["head"], chain["head_sha"])
            self.assertEqual(
                [("M3", heads["M3"]), ("M1", heads["M1"])],
                [(link["mission_id"], link["reviewed_sha"]) for link in chain["links"]],
            )
            self.assertEqual([], self.skip_errors(plan, run))
            self.assertFalse(
                [error for error in validate_run(plan, run) if "reviewed_merge_chain" in error]
            )

    def test_merge_chain_skip_fails_closed(self) -> None:
        cases = {
            "conflict": ({"conflict": True}, None),
            "evil_merge": ({"extra": "evil_merge"}, None),
            "unreviewed_base_commit": ({"extra": "direct_commit"}, None),
            "outside_write_scope": ({"extra": "out_of_scope"}, None),
            "unreviewed_head": ({}, "unreviewed_head"),
            "overlapping_scope": ({}, "overlapping_scope"),
            "visual_review": ({}, "visual_review"),
        }
        for name, (repo_options, change) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                heads = self.repo(root, **repo_options)
                plan, run = self.state(heads, review_type="visual" if change == "visual_review" else "frontend_code")
                if change == "unreviewed_head":
                    run["review_workers"][1].update(phase="worker_failed", outcome="fix_required")
                elif change == "overlapping_scope":
                    next(m for m in plan["missions"] if m["id"] == "M3")["write_scope"].append("src/example/**")
                state = run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]

                with self.assertRaisesRegex(ManifestError, "review must run|applies only to"):
                    self.skip(plan, run, root)

                self.assertEqual("dormant", state["phase"])
                self.assertNotIn("reviewed_merge_chain", run["integration"])

    def test_validator_rejects_a_chain_without_live_proof_or_for_another_head(self) -> None:
        heads = {"M1": "1" * 40, "M3": "3" * 40, "head": "c" * 40}
        links = [
            {"mission_id": "M3", "reviewed_sha": heads["M3"], "commit_sha": heads["head"]},
            {"mission_id": "M1", "reviewed_sha": heads["M1"], "commit_sha": "b" * 40},
        ]
        plan, run = self.state(heads)
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "skipped"
        self.assertTrue(self.skip_errors(plan, run))

        run["integration"]["reviewed_merge_chain"] = {"head_sha": heads["head"], "links": links}
        self.assertEqual([], self.skip_errors(plan, run))

        for change in ("other_head", "missing_mission", "unreviewed_head", "overlapping_scope", "security"):
            with self.subTest(change=change):
                plan, run = self.state(heads)
                run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["phase"] = "skipped"
                chain = {"head_sha": heads["head"], "links": [dict(link) for link in links]}
                run["integration"]["reviewed_merge_chain"] = chain
                if change == "other_head":
                    chain["head_sha"] = "d" * 40
                elif change == "missing_mission":
                    chain["links"].pop()
                elif change == "unreviewed_head":
                    chain["links"][0]["reviewed_sha"] = "4" * 40
                elif change == "overlapping_scope":
                    next(m for m in plan["missions"] if m["id"] == "M3")["write_scope"] = ["src/**"]
                else:
                    next(n for n in plan["graph"]["nodes"] if n["id"] == "N-VISUAL-REVIEW")["review"]["type"] = "security"
                self.assertTrue(self.skip_errors(plan, run))

    def test_a_new_integration_head_drops_the_chain(self) -> None:
        plan, run = self.state({"M1": "1" * 40, "M3": "3" * 40, "head": "c" * 40})
        run["integration"]["reviewed_merge_chain"] = {"head_sha": "c" * 40, "links": []}

        harness_transition._invalidate_stale_current_projections(plan, run, "c" * 40, "d" * 40)

        self.assertNotIn("reviewed_merge_chain", run["integration"])


if __name__ == "__main__":
    unittest.main()
