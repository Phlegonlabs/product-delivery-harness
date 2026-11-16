"""Focused tests for the fan-out scope disjointness and merge readiness checks."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


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


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _init_repository(root: Path) -> None:
    _git(root, "init", "-q", "-b", "integration")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Harness Test")


def _commit_all(root: Path, message: str) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "-qm", message)
    return _git(root, "rev-parse", "HEAD")


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _worker_fanout(temp: str) -> tuple[Path, Path, str]:
    """Create an integration checkout plus a worker worktree cut from its base commit."""

    integration = Path(temp) / "integration"
    worker = Path(temp) / "worker"
    integration.mkdir(parents=True)
    _init_repository(integration)
    _write(integration, "seed.txt", "base\n")
    base = _commit_all(integration, "base")
    _git(integration, "worktree", "add", "-b", "worker-1", str(worker), base)
    return integration, worker, base


def _commit_worker_file(worker: Path, relative: str, content: str) -> str:
    _write(worker, relative, content)
    _git(worker, "add", "--all")
    _git(worker, "commit", "-qm", f"worker change: {relative}")
    return _git(worker, "rev-parse", "HEAD")


def run_merge_check(
    repo_root: Path,
    base: str,
    head: str,
    scopes: list[str],
    deny: list[str] = (),
    into: str | None = None,
    worktree: Path | None = None,
) -> tuple[int, dict]:
    argv = [
        "merge-check",
        "--repo-root",
        str(repo_root),
        "--base",
        str(base),
        "--head",
        str(head),
    ]
    for scope in scopes:
        argv += ["--scope", scope]
    for claim in deny:
        argv += ["--deny", claim]
    if into is not None:
        argv += ["--into", str(into)]
    if worktree is not None:
        argv += ["--worktree", str(worktree)]
    return call_run(argv)


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


class MergeCheckTests(unittest.TestCase):
    def test_happy_path_prints_a_merge_command_that_succeeds(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            head = _commit_worker_file(worker, "src/feature.py", "feature\n")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "worktree_fanout.py"),
                    "merge-check",
                    "--repo-root",
                    str(integration),
                    "--base",
                    base,
                    "--head",
                    "worker-1",
                    "--scope",
                    "src/**",
                    "--worktree",
                    str(worker),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=120,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(
                {
                    "base",
                    "changed_paths",
                    "commits",
                    "details",
                    "head",
                    "into",
                    "merge_command",
                    "mergeable",
                    "reasons",
                },
                set(report),
            )
            self.assertTrue(report["mergeable"])
            self.assertEqual([], report["reasons"])
            self.assertEqual({}, report["details"])
            self.assertEqual(base, report["base"])
            self.assertEqual(head, report["head"])
            self.assertEqual(base, report["into"])
            self.assertEqual(1, report["commits"])
            self.assertEqual(["src/feature.py"], report["changed_paths"])
            self.assertEqual(f"git merge --no-ff --no-edit {head}", report["merge_command"])
            merged = subprocess.run(
                ["git", "merge", "--no-ff", "--no-edit", head],
                cwd=integration,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(0, merged.returncode, merged.stderr)

    def test_base_not_ancestor_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            _write(integration, "advanced.txt", "advanced\n")
            advanced_base = _commit_all(integration, "advance")
            code, report = run_merge_check(
                integration, advanced_base, "worker-1", ["src/**", "advanced.txt"]
            )
            self.assertEqual(1, code)
            self.assertEqual(["base_not_ancestor"], report["reasons"])

    def test_no_commits_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            code, report = run_merge_check(integration, base, base, ["src/**"])
            self.assertEqual(1, code)
            self.assertEqual(["no_commits"], report["reasons"])
            self.assertEqual(0, report["commits"])
            self.assertEqual([], report["changed_paths"])

    def test_into_missing_base_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            _git(integration, "checkout", "--orphan", "orphan-into")
            _git(integration, "rm", "-rf", "--quiet", ".")
            _write(integration, "o.txt", "orphan\n")
            orphan = _commit_all(integration, "orphan")
            _git(integration, "checkout", "--quiet", "integration")
            code, report = run_merge_check(integration, base, "worker-1", ["src/**"], into=orphan)
            self.assertEqual(1, code)
            self.assertIn("into_missing_base", report["reasons"])
            self.assertNotIn("integration_checkout_dirty", report["reasons"])

    def test_worktree_dirty_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            _write(worker, "junk.txt", "uncommitted\n")
            code, report = run_merge_check(
                integration, base, "worker-1", ["src/**"], worktree=worker
            )
            self.assertEqual(1, code)
            self.assertEqual(["worktree_dirty"], report["reasons"])
            self.assertEqual(["?? junk.txt"], report["details"]["worktree_dirty"])

    def test_worktree_head_mismatch_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            head_a = _commit_worker_file(worker, "src/feature.py", "feature\n")
            second = Path(temp) / "worker-2"
            _git(integration, "worktree", "add", "-b", "worker-2", str(second), base)
            head_b = _commit_worker_file(second, "src/other.py", "other\n")
            self.assertNotEqual(head_a, head_b)
            code, report = run_merge_check(
                integration, base, "worker-2", ["src/**"], worktree=worker
            )
            self.assertEqual(1, code)
            self.assertEqual(["worktree_head_mismatch"], report["reasons"])
            self.assertEqual(
                [f"worktree HEAD is {head_a}, --head resolves to {head_b}"],
                report["details"]["worktree_head_mismatch"],
            )

    def test_integration_checkout_dirty_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            _write(integration, "seed.txt", "uncommitted edit\n")
            code, report = run_merge_check(integration, base, "worker-1", ["src/**"])
            self.assertEqual(1, code)
            self.assertEqual(["integration_checkout_dirty"], report["reasons"])
            self.assertEqual(
                [" M seed.txt"], report["details"]["integration_checkout_dirty"]
            )

    def test_invalid_claims_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            code, report = run_merge_check(
                integration, base, "worker-1", ["src/**"], deny=["../x"]
            )
            self.assertEqual(1, code)
            self.assertEqual(["invalid_scope"], report["reasons"])
            self.assertEqual(
                ["../x: contains an empty, . or .. path segment"],
                report["details"]["invalid_scope"],
            )
            code, report = run_merge_check(integration, base, "worker-1", ["../x"])
            self.assertEqual(1, code)
            self.assertEqual(["invalid_scope", "out_of_scope"], report["reasons"])

    def test_out_of_scope_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "other/thing.txt", "outside\n")
            code, report = run_merge_check(integration, base, "worker-1", ["src/**"])
            self.assertEqual(1, code)
            self.assertEqual(["out_of_scope"], report["reasons"])
            self.assertEqual(["other/thing.txt"], report["details"]["out_of_scope"])
            self.assertEqual(["other/thing.txt"], report["changed_paths"])

    def test_denied_path_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/private.txt", "secret\n")
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            code, report = run_merge_check(
                integration, base, "worker-1", ["src/**"], deny=["src/private.txt"]
            )
            self.assertEqual(1, code)
            self.assertEqual(["denied_path"], report["reasons"])
            self.assertEqual(["src/private.txt"], report["details"]["denied_path"])

    def test_parent_owned_file_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "PLAN.md", "plan\n")
            code, report = run_merge_check(integration, base, "worker-1", ["PLAN.md"])
            self.assertEqual(1, code)
            self.assertEqual(["parent_owned_file"], report["reasons"])
            self.assertEqual(["PLAN.md"], report["details"]["parent_owned_file"])

    def test_whitespace_error_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "trailing space \n")
            code, report = run_merge_check(integration, base, "worker-1", ["src/**"])
            self.assertEqual(1, code)
            self.assertEqual(["whitespace_error"], report["reasons"])
            self.assertEqual(
                ["+trailing space ", "src/feature.py:1: trailing whitespace."],
                report["details"]["whitespace_error"],
            )

    def test_merge_conflict_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _write(integration, "seed.txt", "integration edit\n")
            _commit_all(integration, "integration edit")
            _commit_worker_file(worker, "seed.txt", "worker edit\n")
            code, report = run_merge_check(integration, base, "worker-1", ["seed.txt"])
            self.assertEqual(1, code)
            self.assertEqual(["merge_conflict"], report["reasons"])
            self.assertEqual(["seed.txt"], report["details"]["merge_conflict"])

    def test_merge_tree_unavailable_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")
            unknown_subcommand = SimpleNamespace(
                returncode=129,
                stdout="",
                stderr="error: unknown subcommand: `--write-tree'\n",
            )
            with mock.patch.object(
                worktree_fanout, "_merge_tree", return_value=unknown_subcommand
            ):
                code, report = run_merge_check(integration, base, "worker-1", ["src/**"])
            self.assertEqual(1, code)
            self.assertEqual(["merge_tree_unavailable"], report["reasons"])
            self.assertEqual(1, len(report["details"]["merge_tree_unavailable"]))
            self.assertIsNone(report["merge_command"])

    def test_two_failures_are_both_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "other/thing.txt", "outside\n")
            _commit_worker_file(worker, "PLAN.md", "plan\n")
            code, report = run_merge_check(integration, base, "worker-1", ["PLAN.md"])
            self.assertEqual(1, code)
            self.assertEqual(["out_of_scope", "parent_owned_file"], report["reasons"])
            self.assertEqual(
                {"out_of_scope": ["other/thing.txt"], "parent_owned_file": ["PLAN.md"]},
                report["details"],
            )

    def test_the_check_changes_nothing_in_either_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            _commit_worker_file(worker, "src/feature.py", "feature\n")

            def snapshot(root: Path) -> tuple[str, str, str]:
                return (
                    _git(root, "status", "--porcelain"),
                    _git(root, "rev-parse", "HEAD"),
                    _git(root, "for-each-ref", "refs/heads", "--format=%(refname) %(objectname)"),
                )

            before = (snapshot(integration), snapshot(worker))
            code, report = run_merge_check(
                integration, base, "worker-1", ["src/**"], worktree=worker
            )
            self.assertEqual(0, code)
            self.assertTrue(report["mergeable"])
            after = (snapshot(integration), snapshot(worker))
            self.assertEqual(before, after)

    def test_unresolved_ref_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as temp:
            integration, worker, base = _worker_fanout(temp)
            self.assertEqual(
                2,
                call_run_expecting_usage(
                    self,
                    [
                        "merge-check",
                        "--repo-root",
                        str(integration),
                        "--base",
                        base,
                        "--head",
                        "no-such-branch",
                        "--scope",
                        "src/**",
                    ],
                ),
            )


if __name__ == "__main__":
    unittest.main()
