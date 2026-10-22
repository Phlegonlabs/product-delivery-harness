#!/usr/bin/env python3
"""The security review packet carries the PLAN required checks."""

from __future__ import annotations

import json
import hashlib
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for path in (TESTS_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from render_review_packet import render_packet  # noqa: E402
from security_review_result import validate_security_review_result  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from test_security_review_result import valid_result  # noqa: E402


KEY = "c" * 64


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _contract(packet: str) -> dict:
    block = packet.split("## Contract", 1)[1].split("```json", 1)[1]
    return json.loads(block.split("```", 1)[0])


class SecurityPacketCheckTests(unittest.TestCase):
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
        (self.root / "file.txt").write_text("head\n", encoding="utf-8")
        _git(self.root, "commit", "-qam", "head")
        self.head = _git(self.root, "rev-parse", "HEAD")

        self.plan = valid_plan()
        self.run = valid_run(self.plan)
        self.run["integration"]["batch_base_sha"] = self.base
        self.run["integration"]["integration_head_sha"] = self.head
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        node = next(
            item for item in self.plan["graph"]["nodes"] if item["id"] == "N-REVIEW-M1"
        )
        node["review"]["type"] = "security"
        node["review"]["stage"] = "integration"
        self.plan["security_review"] = {
            "status": "required",
            "skill_slot": "code_security_verification",
            "reason": None,
            "required_checks": ["sec-deps"],
        }

    def execution(self, **overrides: object) -> dict:
        value = {
            "verifier_id": "sec-deps",
            "layer": "batch",
            "status": "PASS",
            "exit_code": 0,
            "execution_key": KEY,
            "context": {"head_sha": self.head},
        }
        value.update(overrides)
        return value

    def test_result_built_from_packet_checks_validates(self) -> None:
        self.run["verifier_executions"] = [
            self.execution(),
            self.execution(execution_key="d" * 64, context={"head_sha": self.base}),
        ]

        contract = _contract(render_packet(self.plan, self.run, "N-REVIEW-M1", self.root))

        self.assertEqual(
            [{"id": "sec-deps", "execution_key": KEY}], contract["required_checks"]
        )
        result = valid_result(reviewed_sha=self.head, base_sha=self.base)
        result["checks"] = contract["required_checks"]
        self.assertEqual(
            [],
            validate_security_review_result(result, required_checks=["sec-deps"]),
        )

    def test_missing_or_stale_execution_gives_null_key_that_cannot_validate(self) -> None:
        for executions in (
            [],
            [self.execution(context={"head_sha": self.base})],
            [self.execution(status="FAIL", exit_code=1)],
            [self.execution(), self.execution(execution_key="d" * 64)],
        ):
            with self.subTest(executions=executions):
                self.run["verifier_executions"] = executions
                contract = _contract(
                    render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
                )
                self.assertEqual(
                    [{"id": "sec-deps", "execution_key": None}],
                    contract["required_checks"],
                )
                result = valid_result(reviewed_sha=self.head, base_sha=self.base)
                result["checks"] = contract["required_checks"]
                self.assertTrue(
                    validate_security_review_result(result, required_checks=["sec-deps"])
                )

    def test_non_security_packet_has_no_required_checks(self) -> None:
        self.run["verifier_executions"] = [self.execution()]
        node = next(
            item for item in self.plan["graph"]["nodes"] if item["id"] == "N-REVIEW-M1"
        )
        node["review"]["type"] = "backend_code"

        contract = _contract(render_packet(self.plan, self.run, "N-REVIEW-M1", self.root))

        self.assertEqual([], contract["required_checks"])

    def test_security_packet_does_not_reduce_scope_to_merge_seams(self) -> None:
        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
        self.assertIn("fresh full-scope review", packet)
        self.assertNotIn("Focus this pass on what combination", packet)

    def test_architecture_guidance_routes_only_to_code_reviews(self) -> None:
        node = next(n for n in self.plan["graph"]["nodes"] if n["id"] == "N-REVIEW-M1")
        packets = {}
        for review_type in ("frontend_code", "backend_code", "visual", "security"):
            with self.subTest(review_type=review_type):
                node["review"]["type"] = review_type
                packets[review_type] = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
                contract = _contract(packets[review_type])
                self.assertEqual(review_type, contract["review_type"])
                self.assertEqual(self.plan["missions"][0]["tasks"][0]["acceptance_matrix"],
                                 contract["acceptance"][0]["acceptance_matrix"])
                self.assertEqual(set(_contract(packets["frontend_code"])), set(contract))
                self.assertEqual(review_type in {"frontend_code", "backend_code"},
                                 "## Architecture review" in packets[review_type])
        self.assertIn("For unchanged boundaries, reuse the accepted design", packets["backend_code"])
        self.assertIn("do not reset repair budgets", packets["frontend_code"])

    def test_combined_node_packet_carries_every_lens(self) -> None:
        node = next(n for n in self.plan["graph"]["nodes"] if n["id"] == "N-REVIEW-M1")
        self.plan["ui_surfaces"] = [{"id": "dashboard"}]
        node["review"]["lenses"] = ["frontend_code", "visual", "security"]
        node["review"]["required_evidence"].append("ui_acceptance")

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
        contract = _contract(packet)

        self.assertEqual("security", contract["review_type"])
        self.assertEqual(["frontend_code", "security", "visual"], contract["review_lenses"])
        self.assertEqual("code_security_verification", contract["skill_binding_slot"])
        for section in ("## Security coverage", "## Architecture review", "## Final UI Acceptance"):
            self.assertIn(section, packet)

    def test_ui_acceptance_combines_parity_and_quality_at_either_visual_stage(self) -> None:
        node = next(n for n in self.plan["graph"]["nodes"] if n["id"] == "N-REVIEW-M1")
        self.plan["ui_surfaces"] = [{"id": "dashboard"}]
        node["review"]["required_evidence"].append("ui_acceptance")
        for review_type in ("visual", "frontend_code", "backend_code", "security"):
            for stage in ("preintegration", "integration"):
                with self.subTest(review_type=review_type, stage=stage):
                    node["review"].update(type=review_type, stage=stage)
                    packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
                    expected = review_type == "visual"
                    self.assertEqual(expected, "## Final UI Acceptance" in packet)
                    if expected:
                        self.assertIn("parity and page quality in this one review", packet)
                        self.assertIn("target_comparison", packet)
                        self.assertIn("layout_check", packet)
                        self.assertIn("full required UI matrix", packet)
                        self.assertIn("original defects and affected consumers", packet)
                        self.assertIn("existing lineage budget", packet)
                        self.assertIn("pinned contract", packet)
                        self.assertIn("ui_parity:<retained comparison anchor>", packet)
                        self.assertIn("ui_page_quality:<retained quality-report anchor>", packet)
                        contract = _contract(packet)
                        self.assertEqual("visual", contract["review_type"])
                        self.assertEqual([], contract["required_checks"])
        node["review"].update(type="visual", stage="integration")
        node["review"]["required_evidence"].remove("ui_acceptance")
        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
        self.assertNotIn("## Final UI Acceptance", packet)
        node["review"]["required_evidence"].append("ui_acceptance")
        self.plan["ui_surfaces"] = []
        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)
        self.assertNotIn("## Final UI Acceptance", packet)

    def test_truncated_packet_retains_complete_external_binary_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            (self.root / "file.txt").write_text("large tail\n" * 10000, encoding="utf-8")
            (self.root / "binary.bin").write_bytes(bytes(range(256)) * 20)
            _git(self.root, "add", ".")
            _git(self.root, "commit", "-qm", "large and binary")
            self.run["integration"]["integration_head_sha"] = _git(self.root, "rev-parse", "HEAD")
            path = Path(directory) / "full.diff"
            packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root,
                max_diff_bytes=50, diff_artifact_out=path)
            contract = _contract(packet)
            artifact = contract["diff_artifact"]
            raw = path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), artifact["sha256"])
            self.assertEqual(len(raw), artifact["bytes"])
            self.assertIn(b"GIT binary patch", raw)
            self.assertIn(b"large tail", raw)
            self.assertIn("binary.bin", artifact["name_status"])
            self.assertIn("## Diff (truncated)", packet)
            self.assertIn("do not return PASS", packet)

    def test_artifact_refuses_checkout_path_and_existing_file_without_overwrite(self) -> None:
        from harness_core import ManifestError
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "existing.diff"
            existing.write_bytes(b"valuable data")
            for path in (existing, self.root / "review.diff"):
                with self.subTest(path=path), self.assertRaises(ManifestError):
                    render_packet(self.plan, self.run, "N-REVIEW-M1", self.root, diff_artifact_out=path)
            self.assertEqual(b"valuable data", existing.read_bytes())
            self.assertFalse((self.root / "review.diff").exists())

    def test_preintegration_artifact_cannot_dirty_the_worker_checkout(self) -> None:
        from harness_core import ManifestError
        with tempfile.TemporaryDirectory() as directory:
            worker_root = Path(directory)
            node = next(n for n in self.plan["graph"]["nodes"] if n["id"] == "N-REVIEW-M1")
            node["review"]["stage"] = "preintegration"
            self.run["mission_states"]["M1"]["worker_id"] = "worker-M1"
            self.run["workers"] = [{"worker_id": "worker-M1", "worktree_path": str(worker_root)}]
            with self.assertRaises(ManifestError):
                render_packet(self.plan, self.run, "N-REVIEW-M1", self.root,
                    diff_artifact_out=worker_root / "full.diff")
            self.assertFalse((worker_root / "full.diff").exists())

    def test_standalone_packet_and_artifact_paths_must_differ_before_writes(self) -> None:
        from render_review_packet import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "same-output"
            with patch("render_review_packet.load_plan", return_value=self.plan), patch("render_review_packet.load_run", return_value=self.run), patch("render_review_packet.validate_current_plan_run", return_value=[]), contextlib.redirect_stderr(io.StringIO()):
                code = main(["--plan", "PLAN.md", "--run", "RUN.md", "--node", "N-REVIEW-M1",
                    "--repo-root", str(self.root), "--out", str(path), "--diff-artifact-out", str(path)])
            self.assertEqual(2, code)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
