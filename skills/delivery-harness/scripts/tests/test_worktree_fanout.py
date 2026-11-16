"""Focused tests for the fan-out scope disjointness and merge readiness checks."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import worktree_fanout  # noqa: E402


def call_run(argv: list[str]) -> tuple[int, dict]:
    """Run one ``worktree_fanout`` invocation and return (exit code, JSON report)."""

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = worktree_fanout.run(argv)
    return code, json.loads(buffer.getvalue())


def call_run_expecting_usage(test: unittest.TestCase, argv: list[str]) -> int:
    """Run one invocation that must end in a usage error and return its exit code."""

    with contextlib.redirect_stderr(io.StringIO()):
        with test.assertRaises(SystemExit) as captured:
            worktree_fanout.run(argv)
    code = captured.exception.code
    assert isinstance(code, int)
    return code


class ScopeTests(unittest.TestCase):
    def test_disjoint_parts_exit_zero(self):
        code, report = call_run(
            [
                "scopes",
                "--part",
                "docs=docs/**",
                "--part",
                "feature=src/feature.py",
                "--part",
                "assets=assets/logo.svg",
            ]
        )
        self.assertEqual(0, code)
        self.assertTrue(report["disjoint"])
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["invalid"])
        self.assertEqual(["assets", "docs", "feature"], report["parts"])

    def test_exact_claim_overlap_reports_scope_overlap(self):
        code, report = call_run(
            ["scopes", "--part", "left=src/feature.py", "--part", "right=src/feature.py"]
        )
        self.assertEqual(1, code)
        self.assertFalse(report["disjoint"])
        self.assertEqual(
            [
                {
                    "claims": ["src/feature.py", "src/feature.py"],
                    "left": "left",
                    "reason": "scope_overlap",
                    "right": "right",
                }
            ],
            report["conflicts"],
        )

    def test_subtree_claim_overlap_reports_scope_overlap(self):
        code, report = call_run(
            ["scopes", "--part", "docs=docs/**", "--part", "guide=docs/guide.md"]
        )
        self.assertEqual(1, code)
        self.assertEqual(
            [("docs", "guide", "scope_overlap", ["docs/**", "docs/guide.md"])],
            [
                (item["left"], item["right"], item["reason"], item["claims"])
                for item in report["conflicts"]
            ],
        )

    def test_case_only_collision_reports_case_scope_collision(self):
        code, report = call_run(["scopes", "--part", "upper=Src", "--part", "lower=src"])
        self.assertEqual(1, code)
        self.assertEqual(
            [("lower", "upper", "case_scope_collision", ["src", "Src"])],
            [
                (item["left"], item["right"], item["reason"], item["claims"])
                for item in report["conflicts"]
            ],
        )

    def test_invalid_claims_are_reported_without_conflicts(self):
        code, report = call_run(
            [
                "scopes",
                "--part",
                "escape=../x",
                "--part",
                "absolute=/abs/path",
                "--part",
                "feature=src/**",
            ]
        )
        self.assertEqual(1, code)
        self.assertFalse(report["disjoint"])
        self.assertEqual([], report["conflicts"])
        self.assertEqual(
            [
                {"claim": "/abs/path", "error": "must be a repository-relative POSIX path", "part": "absolute"},
                {"claim": "../x", "error": "contains an empty, . or .. path segment", "part": "escape"},
            ],
            report["invalid"],
        )

    def test_overlapping_claims_inside_one_part_are_not_a_conflict(self):
        code, report = call_run(
            ["scopes", "--part", "one=src/**,src/a.py", "--part", "two=docs/**"]
        )
        self.assertEqual(0, code)
        self.assertTrue(report["disjoint"])
        self.assertEqual([], report["conflicts"])

    def test_fewer_than_two_parts_is_a_usage_error(self):
        self.assertEqual(2, call_run_expecting_usage(self, ["scopes", "--part", "one=src/**"]))

    def test_duplicate_part_ids_are_a_usage_error(self):
        self.assertEqual(
            2,
            call_run_expecting_usage(
                self, ["scopes", "--part", "one=src/**", "--part", "one=docs/**"]
            ),
        )

    def test_part_without_claims_is_a_usage_error(self):
        self.assertEqual(
            2,
            call_run_expecting_usage(self, ["scopes", "--part", "one=src/**", "--part", "two"]),
        )

    def test_part_with_empty_claim_list_is_a_usage_error(self):
        self.assertEqual(
            2,
            call_run_expecting_usage(self, ["scopes", "--part", "one=src/**", "--part", "two="]),
        )


if __name__ == "__main__":
    unittest.main()
