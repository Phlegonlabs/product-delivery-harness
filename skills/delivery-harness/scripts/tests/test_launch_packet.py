#!/usr/bin/env python3
"""Focused tests for complete-message launch and review packet budgets."""

from __future__ import annotations

import contextlib
import argparse
import io
import json
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

import manifest_fixtures as mf
import harness_transition  # noqa: E402
from check_launch_packet import (  # noqa: E402
    InvalidMessageBudgetError,
    MessageBudgetOverflowError,
    check_message,
)
from manifest_fixtures import manifest_markdown  # noqa: E402
from harness_manifest import ManifestError  # noqa: E402
from render_review_packet import main as render_main  # noqa: E402
from render_review_packet import render_packet  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


class LaunchPacketCheckTests(unittest.TestCase):
    def test_exact_utf8_boundaries_and_one_byte_over(self) -> None:
        self.assertEqual(3, check_message("水", 3))
        self.assertEqual(4, check_message("😀", 4))
        self.assertEqual(7, check_message("水😀", 7))
        self.assertEqual(8, check_message("a水😀", 8))
        with self.assertRaisesRegex(
            MessageBudgetOverflowError, "9 UTF-8 bytes.*is 8"
        ):
            check_message("a水😀 ", 8)

    def test_strict_budget_and_message_types_are_rejected(self) -> None:
        for budget in (0, -1, True, False, 1.0, "1", None):
            with self.subTest(budget=budget):
                with self.assertRaises(InvalidMessageBudgetError):
                    check_message("ok", budget)
        with self.assertRaises(InvalidMessageBudgetError):
            check_message(b"ok", 2)

    def test_cli_reports_metadata_without_message_contents_or_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            message = root / "message.txt"
            message.write_text("水😀", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "check_launch_packet.py"),
                    "--message-file",
                    str(message),
                    "--max-message-bytes",
                    "7",
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
            )
            self.assertEqual(
                {"message_bytes": 7, "max_message_bytes": 7},
                json.loads(result.stdout),
            )
            self.assertEqual({message.name}, {item.name for item in root.iterdir()})

    def test_cli_overflow_and_invalid_utf8_return_two_without_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            message = root / "message.txt"
            message.write_text("a水😀 ", encoding="utf-8")
            invalid = root / "invalid.txt"
            invalid.write_bytes(b"\xff")
            for path, budget in ((message, 8), (invalid, 10)):
                with self.subTest(case=path.name):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPTS_DIR / "check_launch_packet.py"),
                            "--message-file",
                            str(path),
                            "--max-message-bytes",
                            str(budget),
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=15,
                    )
                    self.assertEqual(2, result.returncode)
                    self.assertNotIn("水", result.stderr)
                    self.assertNotIn("\xff", result.stderr)

    def test_cli_rejects_oversized_file_without_reading_it_all(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            message = Path(temp) / "huge.txt"
            with message.open("wb") as stream:
                stream.write(b"a" * (64 * 1024))
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "check_launch_packet.py"),
                    "--message-file",
                    str(message),
                    "--max-message-bytes",
                    "1",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("exceeds 1 UTF-8 bytes", result.stderr)
            self.assertNotIn("a" * 100, result.stderr)


class ReviewPacketBudgetTests(unittest.TestCase):
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
        mf.materialize_plan_sources(self.root, self.plan)
        _git(self.root, "add", "docs/product")
        _git(self.root, "commit", "-qm", "freeze contracts")
        self.head = _git(self.root, "rev-parse", "HEAD")
        self.run = valid_run(self.plan)
        self.run["integration"]["branch"] = _git(self.root, "branch", "--show-current")
        self.run["integration"]["batch_base_sha"] = self.base
        self.run["integration"]["integration_head_sha"] = self.head
        self.run["mission_states"]["M1"]["head_sha"] = self.head

    def test_small_diff_full_metadata_can_exceed_the_message_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "full.diff"
            with self.assertRaisesRegex(ValueError, "full-message budget"):
                render_packet(
                    self.plan,
                    self.run,
                    "N-REVIEW-M1",
                    self.root,
                    max_message_bytes=1,
                    diff_artifact_out=artifact,
                )
            self.assertFalse(artifact.exists())

    def test_invalid_budget_is_rejected_before_git_or_artifact_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "full.diff"
            with patch(
                "render_review_packet.run_git",
                side_effect=AssertionError("budget validation must precede Git"),
            ), self.assertRaisesRegex(
                ManifestError, "invalid review packet budget"
            ):
                render_packet(
                    self.plan,
                    self.run,
                    "N-REVIEW-M1",
                    self.root,
                    max_message_bytes=0,
                    diff_artifact_out=artifact,
                )
            self.assertFalse(artifact.exists())

    def test_collector_is_unchanged_on_rejection_and_populated_on_success(self) -> None:
        artifacts: list[tuple[Path, bytes]] = []
        with self.assertRaisesRegex(ValueError, "full-message budget"):
            render_packet(
                self.plan,
                self.run,
                "N-REVIEW-M1",
                self.root,
                max_message_bytes=1,
                artifacts=artifacts,
            )
        self.assertEqual([], artifacts)
        packet = render_packet(
            self.plan,
            self.run,
            "N-REVIEW-M1",
            self.root,
            max_message_bytes=100000,
            artifacts=artifacts,
        )
        self.assertEqual(0, len(artifacts))
        self.assertEqual(
            len(packet.encode("utf-8")), check_message(packet, 100000)
        )

    def test_collector_receives_diff_after_budget_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifacts: list[tuple[Path, bytes]] = []
            artifact = Path(temp) / "full.diff"
            baseline = Path(temp) / "baseline.diff"
            render_packet(
                self.plan,
                self.run,
                "N-REVIEW-M1",
                self.root,
                diff_artifact_out=baseline,
            )
            expected = baseline.read_bytes()
            packet = render_packet(
                self.plan,
                self.run,
                "N-REVIEW-M1",
                self.root,
                max_message_bytes=100000,
                diff_artifact_out=artifact,
                artifacts=artifacts,
            )
            self.assertEqual([(artifact, expected)], artifacts)
            self.assertEqual(len(packet.encode("utf-8")), check_message(packet, 100000))

    def test_cli_overflow_leaves_all_outputs_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            packet_path = root / "packet.md"
            artifact_path = root / "full.diff"
            with patch(
                "render_review_packet.load_plan", return_value=self.plan
            ), patch(
                "render_review_packet.load_run", return_value=self.run
            ), patch(
                "render_review_packet.validate_current_plan_run", return_value=[]
            ), contextlib.redirect_stderr(io.StringIO()):
                code = render_main(
                    [
                        "--plan", "PLAN.md", "--run", "RUN.md",
                        "--node", "N-REVIEW-M1", "--repo-root", str(self.root),
                        "--max-message-bytes", "1",
                        "--out", str(packet_path),
                        "--diff-artifact-out", str(artifact_path),
                    ]
                )
            self.assertEqual(2, code)
            self.assertFalse(packet_path.exists())
            self.assertFalse(artifact_path.exists())

    def test_omitted_budget_preserves_direct_artifact_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "full.diff"
            packet = render_packet(
                self.plan,
                self.run,
                "N-REVIEW-M1",
                self.root,
                diff_artifact_out=artifact,
            )
            self.assertTrue(artifact.exists())
            self.assertIn("## Diff", packet)


class TransitionBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        _git(self.root, "init", "-q", "-b", "integration")
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
        mf.materialize_plan_sources(self.root, self.plan)
        _git(self.root, "add", "docs/product")
        _git(self.root, "commit", "-qm", "freeze contracts")
        self.head = _git(self.root, "rev-parse", "HEAD")
        self.run = valid_run(self.plan)
        self.run["integration"]["branch"] = _git(self.root, "branch", "--show-current")
        self.run["integration"]["batch_base_sha"] = self.base
        self.run["integration"]["integration_head_sha"] = self.head
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.plan_path.write_text(
            manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan),
            encoding="utf-8",
        )
        self.run_path.write_text(
            manifest_markdown("## Harness Run State", "harness_run", self.run),
            encoding="utf-8",
        )
        self.base_arguments = [
            "--plan", str(self.plan_path),
            "--run", str(self.run_path),
            "--repo-root", str(self.root),
            "--session-id", "packet-test",
        ]

    def _reserve_arguments(self, *extra: str) -> list[str]:
        return [
            *self.base_arguments,
            "reserve-review-dispatch",
            "--node-id", "N-REVIEW-M1",
            "--worker-id", "RW-1",
            "--attempt-id", "ATT-1",
            *extra,
        ]

    def test_budget_without_packet_out_is_rejected_before_durable_write(self) -> None:
        before = self.run_path.read_bytes()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = harness_transition.main(self._reserve_arguments(
                "--max-diff-bytes", "50",
                "--max-message-bytes", "100000",
            ))
        self.assertEqual(2, code)
        self.assertIn("require --packet-out", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_invalid_packet_budget_is_rejected_before_manifest_reads(self) -> None:
        args = argparse.Namespace(
            command="reserve-review-dispatch",
            plan=self.root / "missing-PLAN.md",
            run=self.run_path,
            repo_root=self.root,
            session_id="packet-test",
            packet_out=self.root / "packet.md",
            max_message_bytes=0,
        )
        before = self.run_path.read_bytes()
        with self.assertRaisesRegex(
            harness_transition.ManifestError, "invalid packet message budget"
        ):
            harness_transition._transition_under_lock(args, self.plan)
        self.assertEqual(before, self.run_path.read_bytes())

    def test_packet_overflow_leaves_run_artifact_and_packet_unchanged(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0, harness_transition.main([*self.base_arguments, "acquire-run-lock"])
            )
        before = self.run_path.read_bytes()
        packet_path = self.root.parent / f"{self.root.name}-packet.md"
        artifact_path = self.root.parent / f"{self.root.name}-full.diff"
        directive = {
            "node_id": "N-REVIEW-M1",
            "launch_kind": "spawn_subagent",
            "required_actions": [],
            "runtime_binding": {},
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "workspace_mode": "shared_checkout",
        }
        with patch.object(
            harness_transition,
            "_reserve_review_dispatch",
            return_value={"dispatch_receipt": {"node_id": "N-REVIEW-M1"}},
        ), patch.object(
            harness_transition,
            "select_ready_nodes",
            return_value={"dispatchable_nodes": [directive], "deferred_nodes": []},
        ), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = harness_transition.main(self._reserve_arguments(
                "--max-message-bytes", "1",
                "--max-diff-bytes", "50",
                "--packet-out", str(packet_path),
                "--diff-artifact-out", str(artifact_path),
            ))
        self.assertEqual(2, code)
        self.assertIn("full-message budget", stderr.getvalue())
        self.assertIn("smaller inline diff", stderr.getvalue())
        self.assertNotIn("increase", stderr.getvalue().lower())
        self.assertEqual(before, self.run_path.read_bytes())
        self.assertFalse(packet_path.exists())
        self.assertFalse(artifact_path.exists())

    def test_distinct_diff_and_message_budgets_reserve_successfully(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0, harness_transition.main([*self.base_arguments, "acquire-run-lock"])
            )
        before = self.run_path.read_bytes()
        directive = {
            "node_id": "N-REVIEW-M1",
            "launch_kind": "spawn_subagent",
            "required_actions": [],
            "runtime_binding": {},
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "workspace_mode": "shared_checkout",
        }
        with tempfile.TemporaryDirectory() as output_temp:
            output_root = Path(output_temp)
            packet_path = output_root / "packet.md"
            artifact_path = output_root / "full.diff"
            with patch.object(
                harness_transition,
                "_reserve_review_dispatch",
                return_value={"dispatch_receipt": {"node_id": "N-REVIEW-M1"}},
            ), patch.object(
                harness_transition,
                "select_ready_nodes",
                return_value={"dispatchable_nodes": [directive], "deferred_nodes": []},
            ), contextlib.redirect_stdout(io.StringIO()):
                code = harness_transition.main(self._reserve_arguments(
                    "--max-diff-bytes", "1",
                    "--max-message-bytes", "100000",
                    "--packet-out", str(packet_path),
                    "--diff-artifact-out", str(artifact_path),
                ))
            self.assertEqual(0, code)
            packet = packet_path.read_text(encoding="utf-8")
            self.assertIn("## Diff (truncated)", packet)
            self.assertLess(len(packet.encode("utf-8")), 100000)
            self.assertGreater(artifact_path.stat().st_size, 1)
            self.assertNotEqual(before, self.run_path.read_bytes())

    def _reserve_packet_with_omitted_diff_budget(
        self,
        budget_arguments: list[str],
    ) -> str:
        """Run the CLI without --max-diff-bytes and return its packet."""
        before = self.run_path.read_bytes()
        directive = {
            "node_id": "N-REVIEW-M1",
            "launch_kind": "spawn_subagent",
            "required_actions": [],
            "runtime_binding": {},
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "workspace_mode": "shared_checkout",
        }
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0, harness_transition.main([*self.base_arguments, "acquire-run-lock"])
            )
        with tempfile.TemporaryDirectory() as output_temp:
            packet_path = Path(output_temp) / "packet.md"
            with patch.object(
                harness_transition,
                "_reserve_review_dispatch",
                return_value={"dispatch_receipt": {"node_id": "N-REVIEW-M1"}},
            ), patch.object(
                harness_transition,
                "select_ready_nodes",
                return_value={"dispatchable_nodes": [directive], "deferred_nodes": []},
            ), contextlib.redirect_stdout(io.StringIO()):
                code = harness_transition.main(self._reserve_arguments(
                    "--packet-out", str(packet_path), *budget_arguments
                ))
            self.assertEqual(0, code)
            self.assertTrue(packet_path.is_file())
            packet = packet_path.read_text(encoding="utf-8")
        self.assertNotEqual(before, self.run_path.read_bytes())
        return packet

    def test_packet_reserves_with_all_budget_flags_omitted(self) -> None:
        packet = self._reserve_packet_with_omitted_diff_budget([])
        self.assertIn("# Review packet: N-REVIEW-M1", packet)
        self.assertIn("## Diff", packet)
        self.assertNotIn("## Diff (truncated)", packet)

    def test_packet_reserves_with_only_message_budget(self) -> None:
        packet = self._reserve_packet_with_omitted_diff_budget(
            ["--max-message-bytes", "100000"]
        )
        self.assertIn("# Review packet: N-REVIEW-M1", packet)
        self.assertIn("## Diff", packet)
        self.assertNotIn("## Diff (truncated)", packet)


if __name__ == "__main__":
    unittest.main()
