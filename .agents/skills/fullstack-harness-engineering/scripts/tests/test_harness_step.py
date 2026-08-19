#!/usr/bin/env python3
"""Tests for the combined read-only re-observe + select step."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_step  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402

HEADINGS = {"PLAN.md": "## Harness Plan Manifest", "RUN.md": "## Harness Run State"}


def write_manifest(directory: Path, name: str, payload: object) -> Path:
    path = directory / name
    body = (
        f"{HEADINGS[name]}\n\n```json\n"
        + json.dumps(payload, indent=2)
        + "\n```\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class HarnessStepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-b", "work")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "t")
        (self.repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "seed")

        self.plan = valid_graph_plan()
        self.run = valid_graph_run(self.plan)
        self.plan_path = write_manifest(self.repo, "PLAN.md", {"harness_plan": self.plan})
        self.run_path = write_manifest(self.repo, "RUN.md", {"harness_run": self.run})
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "manifests")

    def run_step(self, *extra: str) -> tuple[int, dict]:
        argv = [
            "--plan",
            str(self.plan_path),
            "--run",
            str(self.run_path),
            "--repo-root",
            str(self.repo),
            *extra,
        ]
        buffer = StringIO()
        with redirect_stdout(buffer):
            code = harness_step.main(argv)
        return code, json.loads(buffer.getvalue())

    def test_one_call_reports_every_derivable_fact(self) -> None:
        code, payload = self.run_step("--observe-only")

        self.assertEqual(0, code)
        observed = payload["observed"]
        self.assertTrue(observed["plan"]["digest_matches"])
        self.assertEqual("work", observed["git"]["branch"])
        self.assertEqual(40, len(observed["git"]["head_sha"]))
        self.assertFalse(observed["git"]["dirty"])
        self.assertEqual(12, len(observed["authorizations"]))

    def test_names_what_the_parent_must_still_observe(self) -> None:
        _, payload = self.run_step("--observe-only")

        remaining = payload["observed"]["still_observe_yourself"]
        self.assertIn("available worker slots and isolation capacity", remaining)
        self.assertIn("observed provider and available runtime drivers", remaining)

    def test_dirty_checkout_is_reported_with_its_paths(self) -> None:
        (self.repo / "scratch.txt").write_text("x\n", encoding="utf-8")

        _, payload = self.run_step("--observe-only")

        self.assertTrue(payload["observed"]["git"]["dirty"])
        self.assertTrue(
            any("scratch.txt" in line for line in payload["observed"]["git"]["dirty_paths"])
        )
        self.assertTrue(
            any("checkout is dirty" in note for note in payload["notes"])
        )

    def test_stale_plan_digest_is_flagged(self) -> None:
        self.run["plan"]["digest_sha256"] = "0" * 64
        write_manifest(self.repo, "RUN.md", {"harness_run": self.run})

        _, payload = self.run_step("--observe-only")

        self.assertFalse(payload["observed"]["plan"]["digest_matches"])
        self.assertTrue(any("plan digest" in note for note in payload["notes"]))

    def test_observation_survives_a_selection_error(self) -> None:
        # The point of one call is that a failed selection still hands back the
        # live facts, so the parent does not spend another turn re-reading them.
        self.run["plan"]["digest_sha256"] = "0" * 64
        write_manifest(self.repo, "RUN.md", {"harness_run": self.run})

        code, payload = self.run_step()

        self.assertEqual(2, code)
        self.assertIn("errors", payload)
        self.assertIn("observed", payload)
        self.assertEqual("work", payload["observed"]["git"]["branch"])

    def test_step_writes_nothing(self) -> None:
        before = {
            path: path.read_bytes()
            for path in sorted(self.repo.rglob("*"))
            if path.is_file() and ".git" not in path.parts
        }

        self.run_step()

        after = {
            path: path.read_bytes()
            for path in sorted(self.repo.rglob("*"))
            if path.is_file() and ".git" not in path.parts
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
