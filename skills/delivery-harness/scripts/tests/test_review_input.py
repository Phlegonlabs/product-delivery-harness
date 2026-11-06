#!/usr/bin/env python3
"""review_input.py builds a git-free packet from a temporary two-commit repo."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import review_input  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


class ReviewInputTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp = Path(temporary.name).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        for key, value in (("user.email", "t@example.com"), ("user.name", "T"),
                           ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
            git(self.repo, "config", key, value)
        write(self.repo, "src/app.py", "print('one')\n")
        write(self.repo, "docs/readme.md", "# readme\n")
        self.base = commit(self.repo, "first")
        write(self.repo, "src/app.py", "print('two')\n")
        write(self.repo, "src/new.py", "x = 1\n")
        write(self.repo, "docs/readme.md", "# readme\nmore\n")
        self.head = commit(self.repo, "second")
        self.out = self.tmp / "out"

    def run_main(self, *extra: str, head: str | None = None) -> tuple[int, str, str]:
        argv = ["--repo", str(self.repo), "--base", self.base, "--head", head or self.head,
                "--out", str(self.out), *extra]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = review_input.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def build(self, *extra: str) -> tuple[Path, dict]:
        code, stdout, stderr = self.run_main(*extra)
        self.assertEqual(0, code, stderr)
        self.assertEqual(1, len(stdout.splitlines()))
        summary = json.loads(stdout)
        return Path(summary["clone"]), summary

    def test_writes_every_packet_file(self) -> None:
        clone, summary = self.build("--scope", "src=src")
        packet = clone / "review-input"
        self.assertEqual(
            {"HEAD.txt", "BASE.txt", "candidate.diff", "commit-log.txt", "changed-files.txt",
             "parent-status.txt", "scope-src.diff", "tracked-files.sha256"},
            {path.name for path in packet.iterdir()},
        )
        self.assertEqual(self.head + "\n", (packet / "HEAD.txt").read_text(encoding="utf-8"))
        self.assertEqual(self.base + "\n", (packet / "BASE.txt").read_text(encoding="utf-8"))
        self.assertEqual(f"{self.head} second\n", (packet / "commit-log.txt").read_text(encoding="utf-8"))
        changed = (packet / "changed-files.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(["M\tdocs/readme.md", "M\tsrc/app.py", "A\tsrc/new.py"], changed)
        candidate = (packet / "candidate.diff").read_text(encoding="utf-8")
        self.assertIn("docs/readme.md", candidate)
        self.assertIn("+print('two')", candidate)
        scoped = (packet / "scope-src.diff").read_text(encoding="utf-8")
        self.assertIn("src/app.py", scoped)
        self.assertIn("src/new.py", scoped)
        self.assertNotIn("docs/readme.md", scoped)
        self.assertEqual(
            {"src": len(scoped.splitlines())}, summary["scope_diff_lines"]
        )
        self.assertEqual(len(candidate.splitlines()), summary["candidate_diff_lines"])
        status = (packet / "parent-status.txt").read_text(encoding="utf-8")
        self.assertEqual(
            f"repo: {self.repo.as_posix()}\nhead: {self.head}\nstatus: clean\nuntracked: 0\n"
            "note: the clone holds committed content only; untracked and ignored parent files are not in it\n",
            status,
        )

    def test_manifest_covers_every_file_except_git_and_review_input(self) -> None:
        clone, summary = self.build()
        lines = (clone / "review-input" / "tracked-files.sha256").read_text(encoding="utf-8").splitlines()
        expected = {}
        for path in clone.rglob("*"):
            relative = path.relative_to(clone).as_posix()
            if path.is_file() and not relative.startswith((".git/", "review-input/")):
                expected[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual({"docs/readme.md", "src/app.py", "src/new.py"}, set(expected))
        self.assertEqual([f"{expected[name]}  {name}" for name in sorted(expected)], lines)
        self.assertEqual(len(expected), summary["files"])

    def test_clone_is_detached_at_head(self) -> None:
        clone, _ = self.build()
        self.assertEqual(self.head, git(clone, "rev-parse", "HEAD"))
        detached = subprocess.run(
            ["git", "symbolic-ref", "-q", "HEAD"], cwd=clone, capture_output=True, check=False
        )
        self.assertNotEqual(0, detached.returncode)

    def test_existing_out_is_refused(self) -> None:
        self.out.mkdir()
        (self.out / "keep.txt").write_text("keep", encoding="utf-8")
        code, stdout, stderr = self.run_main()
        self.assertEqual(2, code)
        self.assertEqual("", stdout)
        self.assertIn("refusing existing --out", stderr)
        self.assertEqual(["keep.txt"], [path.name for path in self.out.iterdir()])

    def test_dirty_parent_is_recorded_verbatim(self) -> None:
        write(self.repo, "src/app.py", "print('dirty')\n")
        clone, _ = self.build()
        status = (clone / "review-input" / "parent-status.txt").read_text(encoding="utf-8")
        self.assertEqual(
            f"repo: {self.repo.as_posix()}\nhead: {self.head}\nstatus: dirty\nuntracked: 0\n"
            "note: the clone holds committed content only; untracked and ignored parent files are not in it\n"
            " M src/app.py\n",
            status,
        )

    def test_untracked_parent_files_are_listed_but_not_cloned(self) -> None:
        write(self.repo, "notes.txt", "scratch\n")
        clone, summary = self.build()
        status = (clone / "review-input" / "parent-status.txt").read_text(encoding="utf-8")
        self.assertIn("status: clean\nuntracked: 1\n", status)
        self.assertIn("?? notes.txt\n", status)
        self.assertFalse((clone / "notes.txt").exists())
        manifest = (clone / "review-input" / "tracked-files.sha256").read_text(encoding="utf-8")
        self.assertNotIn("notes.txt", manifest)
        self.assertEqual(summary["head"], self.head)

    def test_repo_head_must_match_head(self) -> None:
        code, _, stderr = self.run_main(head=self.base)
        self.assertEqual(2, code)
        self.assertIn("not --head", stderr)
        self.assertFalse(self.out.exists())

    def test_unknown_revision_is_a_failure(self) -> None:
        code, _, stderr = self.run_main(head="0" * 40)
        self.assertEqual(2, code)
        self.assertIn("error:", stderr)
        self.assertFalse(self.out.exists())

    def test_scope_names_must_be_plain_and_unique(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            self.run_main("--scope", "../x=src")
        self.assertEqual(2, raised.exception.code)
        code, _, stderr = self.run_main("--scope", "a=src", "--scope", "a=docs")
        self.assertEqual(2, code)
        self.assertIn("duplicate --scope", stderr)
        self.assertFalse(self.out.exists())
        code, _, stderr = self.run_main("--scope", "Docs=src", "--scope", "docs=docs")
        self.assertEqual(2, code)
        self.assertIn("duplicate --scope", stderr)
        self.assertFalse(self.out.exists())

    def test_cli_prints_one_json_line(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "review_input.py"), "--repo", str(self.repo),
             "--base", self.base, "--head", self.head, "--out", str(self.out), "--scope", "docs=docs"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual({"docs"}, set(summary["scope_diff_lines"]))
        self.assertTrue((Path(summary["clone"]) / "review-input" / "scope-docs.diff").is_file())


if __name__ == "__main__":
    unittest.main()
