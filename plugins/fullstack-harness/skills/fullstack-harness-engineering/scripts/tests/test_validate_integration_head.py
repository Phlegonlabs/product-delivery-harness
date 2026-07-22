#!/usr/bin/env python3
"""Tests for validate_integration_head_against_git using a real, temporary Git repo."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import validate_integration_head_against_git  # noqa: E402


def _run_git(args: list[str], cwd: Path) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}"


def _head_sha(cwd: Path, branch: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", branch],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _make_run(branch: str, head_sha: str | None) -> dict:
    return {
        "integration": {
            "branch": branch,
            "batch_base_sha": "a" * 40,
            "integration_head_sha": head_sha,
        }
    }


class ValidateIntegrationHeadAgainstGitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        _run_git(["init"], self.repo_root)
        (self.repo_root / "file.txt").write_text("first\n", encoding="utf-8")
        _run_git(["add", "file.txt"], self.repo_root)
        _run_git(["commit", "-m", "first commit"], self.repo_root)
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.branch = result.stdout.strip()
        self.first_sha = _head_sha(self.repo_root, self.branch)

    def test_matching_head_has_no_errors(self) -> None:
        run = _make_run(self.branch, self.first_sha)
        self.assertEqual(
            validate_integration_head_against_git(run, self.repo_root), []
        )

    def test_stale_recorded_head_reports_mismatch(self) -> None:
        run = _make_run(self.branch, self.first_sha)
        (self.repo_root / "file.txt").write_text("second\n", encoding="utf-8")
        _run_git(["add", "file.txt"], self.repo_root)
        _run_git(["commit", "-m", "second commit"], self.repo_root)

        errors = validate_integration_head_against_git(run, self.repo_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match the live Git head", errors[0])
        self.assertIn(self.first_sha, errors[0])
        self.assertIn("RUN.md is stale", errors[0])

    def test_nonexistent_branch_is_reported_as_unverifiable(self) -> None:
        run = _make_run("branch-that-does-not-exist", self.first_sha)
        errors = validate_integration_head_against_git(run, self.repo_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("could not be verified against live Git", errors[0])

    def test_null_head_sha_has_nothing_to_check(self) -> None:
        run = _make_run(self.branch, None)
        self.assertEqual(
            validate_integration_head_against_git(run, self.repo_root), []
        )

    def test_missing_integration_dict_has_nothing_to_check(self) -> None:
        self.assertEqual(
            validate_integration_head_against_git({}, self.repo_root), []
        )

    def test_missing_branch_is_reported_as_unverifiable(self) -> None:
        run = _make_run("", self.first_sha)
        errors = validate_integration_head_against_git(run, self.repo_root)
        self.assertEqual(len(errors), 1)
        self.assertIn("could not be verified against live Git", errors[0])


if __name__ == "__main__":
    unittest.main()
