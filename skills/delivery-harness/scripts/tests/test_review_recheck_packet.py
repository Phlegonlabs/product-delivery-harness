#!/usr/bin/env python3
"""A re-check review packet carries the prior findings and the repair range."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for path in (TESTS_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from render_review_packet import render_packet  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _contract(packet: str) -> dict:
    block = packet.split("## Contract", 1)[1].split("```json", 1)[1]
    return json.loads(block.split("```", 1)[0])


class RecheckPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "test@example.com")
        _git(self.root, "config", "user.name", "Harness Test")
        (self.root / "file.txt").write_text("base\n", encoding="utf-8")
        _git(self.root, "add", "file.txt")
        _git(self.root, "commit", "-qm", "base")
        self.base = _git(self.root, "rev-parse", "HEAD")
        (self.root / "file.txt").write_text("feature\n", encoding="utf-8")
        _git(self.root, "commit", "-qam", "feature")
        self.prior = _git(self.root, "rev-parse", "HEAD")
        (self.root / "repair.txt").write_text("fix\n", encoding="utf-8")
        _git(self.root, "add", "repair.txt")
        _git(self.root, "commit", "-qm", "repair")
        self.head = _git(self.root, "rev-parse", "HEAD")

        self.plan = valid_plan()
        self.run = valid_run(self.plan)
        self.run["integration"]["batch_base_sha"] = self.base
        self.run["integration"]["integration_head_sha"] = self.head
        self.run["mission_states"]["M1"]["head_sha"] = self.head

    def review_worker(self, **overrides: object) -> dict:
        value = {
            "worker_id": "RW-1",
            "node_id": "N-REVIEW-M1",
            "attempt_id": "ATT-1",
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": "0" * 64,
            "graph_revision": self.run["graph_state"]["graph_revision"],
            "reviewed_sha": self.prior,
            "review_path": str(self.root),
            "worker_runtime": "parent",
            "completion_channel": "agent_result",
            "runtime_binding": {},
            "task_thread_id": None,
            "report_path": None,
            "phase": "worker_failed",
            "outcome": "fix_required",
            "findings": ["file.txt:1 header text misses the accepted copy"],
        }
        value.update(overrides)
        return value

    def test_first_review_has_no_recheck_and_carries_triage_sentence(self) -> None:
        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertNotIn("## Repair re-check", packet)
        self.assertIsNone(_contract(packet)["recheck"])
        self.assertIn(
            "Classify every observation as a blocking finding (defect against"
            " accepted scope, TEST obligations, security, or correctness) or"
            " a non-blocking note; notes never block.",
            packet,
        )
        self.assertLess(
            packet.index("- Attempts:"),
            packet.index("Classify every observation as a blocking finding"),
        )
        self.assertLess(
            packet.index("Classify every observation as a blocking finding"),
            packet.index("- Scope:"),
        )

    def test_fix_required_prior_scopes_the_recheck_to_the_repair(self) -> None:
        findings = [
            "file.txt:1 header text misses the accepted copy",
            "file.txt:3 retry loop drops the last item",
        ]
        self.run["review_workers"] = [
            self.review_worker(findings=findings, notes=["helper naming reads unclear"])
        ]

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
        contract = _contract(packet)

        self.assertIn("## Repair re-check", packet)
        self.assertIn(
            f"Prior reviewed head: `{self.prior}`"
            " (attempt `ATT-1`, worker `RW-1`).",
            packet,
        )
        self.assertIn(f"- F1: {findings[0]}", packet)
        self.assertIn(f"- F2: {findings[1]}", packet)
        self.assertIn(
            "Prior non-blocking notes (they do not need a verdict):", packet
        )
        self.assertIn("- helper naming reads unclear", packet)
        self.assertIn(f"Repair range: `{self.prior}..{self.head}`", packet)
        self.assertIn("A\trepair.txt", packet)
        self.assertNotIn("M\tfile.txt", packet)
        self.assertIn(
            "Return a verdict for every prior blocking finding: resolved,"
            " unresolved, or superseded, with path and line evidence at the"
            " reviewed head.",
            packet,
        )
        self.assertIn("Do not reset the repair budget.", packet)
        self.assertIn("environment blocker with evidence", packet)
        recheck = contract["recheck"]
        self.assertEqual(self.prior, recheck["prior_reviewed_sha"])
        self.assertEqual("RW-1", recheck["prior_worker_id"])
        self.assertEqual("ATT-1", recheck["prior_attempt_id"])
        self.assertEqual(findings, recheck["prior_findings"])
        self.assertEqual(
            ["helper naming reads unclear"], recheck["prior_notes"]
        )
        self.assertEqual(f"{self.prior}..{self.head}", recheck["repair_range"])
        self.assertEqual("A\trepair.txt\n", recheck["repair_name_status"])
        repair_block = (
            packet.split("Repair diff:", 1)[1]
            .split("```diff", 1)[1]
            .split("```", 1)[0]
        )
        self.assertIn("+fix", repair_block)
        self.assertNotIn("file.txt", repair_block)
        self.assertLess(
            packet.index("## Repair re-check"), packet.index("## Diff")
        )
        full_diff = packet.split("## Diff", 1)[1]
        self.assertIn("repair.txt", full_diff)
        self.assertIn("file.txt", full_diff)

    def test_repair_diff_truncates_within_budget_and_names_the_range(self) -> None:
        (self.root / "repair.txt").write_text(
            "\n".join(f"repair line {index}" for index in range(1, 201)) + "\n",
            encoding="utf-8",
        )
        _git(self.root, "add", "repair.txt")
        _git(self.root, "commit", "-qm", "grow repair")
        self.head = _git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["integration_head_sha"] = self.head
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        self.run["review_workers"] = [self.review_worker()]

        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "full.diff"
            packet = render_packet(
                self.plan,
                self.run,
                "N-REVIEW-M1",
                self.root,
                max_diff_bytes=400,
                diff_artifact_out=artifact,
            )
            contract = _contract(packet)
            raw = artifact.read_bytes()

        repair_block = (
            packet.split("Repair diff:", 1)[1]
            .split("```diff", 1)[1]
            .split("```", 1)[0]
            .strip()
        )
        self.assertGreater(len(repair_block.encode("utf-8")), 100)
        self.assertLessEqual(len(repair_block.encode("utf-8")), 400)
        self.assertIn("+repair line 1", repair_block)
        self.assertNotIn("repair line 200", packet)
        self.assertIn("Read the fixed Git range directly", packet)
        self.assertIn("inspect the same fixed Git range directly", packet)
        self.assertIn("## Diff (truncated)", packet)
        self.assertEqual(f"{self.prior}..{self.head}", contract["recheck"]["repair_range"])
        self.assertIn("repair.txt", contract["recheck"]["repair_name_status"])
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(), contract["diff_artifact"]["sha256"]
        )
        self.assertIn(b"repair line 200", raw)

    def test_blocked_prior_worker_does_not_create_recheck(self) -> None:
        self.run["review_workers"] = [
            self.review_worker(
                outcome="blocked",
                phase="blocked",
                findings=["integration checkout unavailable"],
            )
        ]

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertNotIn("## Repair re-check", packet)
        self.assertIsNone(_contract(packet)["recheck"])

    def test_lineage_finding_scopes_recheck_when_node_matching_finds_none(self) -> None:
        self.run["review_workers"] = [
            self.review_worker(node_id="N-REVIEW-M1-V1")
        ]
        self.run["attempt_log"].append(
            {
                "attempt_id": "ATT-1",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": None,
                "kind": "review",
                "result": "fix_required",
                "evidence": [],
                "review_lineage_id": "REVIEW-M1",
            }
        )

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertIn("## Repair re-check", packet)
        self.assertEqual(
            self.prior, _contract(packet)["recheck"]["prior_reviewed_sha"]
        )

    def test_unchanged_head_after_fix_required_is_not_a_recheck(self) -> None:
        self.run["review_workers"] = [self.review_worker(reviewed_sha=self.head)]

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertNotIn("## Repair re-check", packet)
        self.assertIsNone(_contract(packet)["recheck"])

    def test_integration_security_recheck_keeps_full_scope_paragraph(self) -> None:
        node = next(
            item
            for item in self.plan["graph"]["nodes"]
            if item["id"] == "N-REVIEW-M1"
        )
        node["review"]["type"] = "security"
        node["review"]["stage"] = "integration"
        self.run["review_workers"] = [self.review_worker()]

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertIn("## Repair re-check", packet)
        self.assertIn("Perform a fresh full-scope review", packet)
        self.assertLess(
            packet.index("## Repair re-check"),
            packet.index("## Security coverage"),
        )
        recheck = _contract(packet)["recheck"]
        self.assertEqual(self.prior, recheck["prior_reviewed_sha"])
        self.assertEqual(f"{self.prior}..{self.head}", recheck["repair_range"])


if __name__ == "__main__":
    unittest.main()
