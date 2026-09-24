"""Exact-path regressions for candidate scope enforcement."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for candidate in (TESTS_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import harness_transition  # noqa: E402


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


class CandidateChangedPathTests(unittest.TestCase):
    def test_leading_space_path_cannot_match_trimmed_allowed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repository(root)
            (root / "seed.txt").write_text("base\n", encoding="utf-8")
            base = _commit_all(root, "base")
            (root / " allowed.txt").write_text("repair\n", encoding="utf-8")
            candidate = _commit_all(root, "leading space")

            plan = {"missions": [{"id": "M1", "write_scope": ["allowed.txt"]}]}
            run = {"integration": {"coordination_paths": []}}
            with self.assertRaisesRegex(
                harness_transition.ManifestError,
                "canonical path spelling",
            ):
                harness_transition._reject_unplanned_candidate_paths(
                    plan,
                    run,
                    root,
                    base,
                    candidate,
                    allowed_scopes=["allowed.txt"],
                )

    def test_dynamic_route_unicode_and_internal_space_remain_literal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repository(root)
            (root / "seed.txt").write_text("base\n", encoding="utf-8")
            base = _commit_all(root, "base")
            route = root / "app" / "[slug]" / "Café page.tsx"
            route.parent.mkdir(parents=True)
            route.write_text("export default null;\n", encoding="utf-8")
            candidate = _commit_all(root, "literal route")

            self.assertEqual(
                ["app/[slug]/Café page.tsx"],
                harness_transition._candidate_changed_paths(root, base, candidate),
            )

    def test_rename_reports_source_and_destination_for_scope_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repository(root)
            source = root / "outside" / "old.txt"
            source.parent.mkdir()
            source.write_text("base\n", encoding="utf-8")
            base = _commit_all(root, "base")
            destination = root / "allowed" / "new.txt"
            destination.parent.mkdir()
            _git(root, "mv", "outside/old.txt", "allowed/new.txt")
            candidate = _commit_all(root, "move into allowed scope")

            self.assertEqual(
                ["allowed/new.txt", "outside/old.txt"],
                harness_transition._candidate_changed_paths(root, base, candidate),
            )
            with self.assertRaisesRegex(
                harness_transition.ManifestError,
                "outside/old.txt",
            ):
                harness_transition._reject_unplanned_candidate_paths(
                    {"missions": [{"id": "M1", "write_scope": ["allowed/**"]}]},
                    {"integration": {"coordination_paths": []}},
                    root,
                    base,
                    candidate,
                    allowed_scopes=["allowed/**"],
                )

    def test_unsupported_literal_names_and_invalid_utf8_fail_closed(self) -> None:
        cases = (
            (b"safe\\evil.py\0", "repository-relative POSIX path"),
            (b"safe\nfile.py\0", "control characters"),
            (b"bad-\xff.py\0", "not valid UTF-8"),
        )
        for output, expected in cases:
            with self.subTest(output=output), mock.patch.object(
                harness_transition, "reject_object_substitution"
            ), mock.patch.object(
                harness_transition,
                "run_git",
                return_value=SimpleNamespace(returncode=0, stdout=output),
            ) as run_git:
                with self.assertRaisesRegex(harness_transition.ManifestError, expected):
                    harness_transition._candidate_changed_paths(
                        Path("unused"), "a" * 40, "b" * 40
                    )
                self.assertIn("-z", run_git.call_args.args)
                self.assertIn("--no-renames", run_git.call_args.args)
                self.assertIs(run_git.call_args.kwargs["text"], False)

    def test_git_failure_remains_fail_closed(self) -> None:
        with mock.patch.object(
            harness_transition, "reject_object_substitution"
        ), mock.patch.object(
            harness_transition,
            "run_git",
            return_value=SimpleNamespace(returncode=1, stdout=b""),
        ):
            with self.assertRaisesRegex(
                harness_transition.ManifestError,
                "cannot observe candidate changed paths from Git",
            ):
                harness_transition._candidate_changed_paths(
                    Path("unused"), "a" * 40, "b" * 40
                )


if __name__ == "__main__":
    unittest.main()
