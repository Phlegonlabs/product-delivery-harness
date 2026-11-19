#!/usr/bin/env python3
"""review_input.py --remove deletes a review packet and refuses anything else."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "review_input.py"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )


class RemovePacketTests(unittest.TestCase):
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
        (self.repo / "app.py").write_text("print('one')\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "first")
        self.base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "app.py").write_text("print('two')\n", encoding="utf-8")
        git(self.repo, "commit", "-q", "-am", "second")
        self.head = git(self.repo, "rev-parse", "HEAD")

    def build_packet(self) -> Path:
        out = self.tmp / "packet"
        built = run("--repo", str(self.repo), "--base", self.base, "--head", self.head, "--out", str(out))
        self.assertEqual(0, built.returncode, built.stderr)
        return out

    def assert_refused(self, target: Path, reason: str) -> None:
        before = sorted(path.relative_to(target).as_posix() for path in target.rglob("*")) if target.exists() else None
        result = run("--remove", str(target))
        self.assertEqual(2, result.returncode, result.stdout)
        self.assertEqual("", result.stdout)
        self.assertIn("error: not a review packet", result.stderr)
        self.assertIn(reason, result.stderr)
        after = sorted(path.relative_to(target).as_posix() for path in target.rglob("*")) if target.exists() else None
        self.assertEqual(before, after)

    def test_removes_a_packet_the_script_built(self) -> None:
        out = self.build_packet()
        objects = [path for path in (out / "clone" / ".git" / "objects").rglob("*") if path.is_file()]
        self.assertTrue(objects)
        result = run("--remove", str(out))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"removed": out.as_posix()}, json.loads(result.stdout))
        self.assertFalse(out.exists())
        self.assertEqual(self.head, git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual("", git(self.repo, "status", "--porcelain"))

    def test_read_only_files_do_not_stop_removal(self) -> None:
        out = self.build_packet()
        files = [path for path in out.rglob("*") if path.is_file() and not path.is_symlink()]
        for path in files:
            os.chmod(path, stat.S_IREAD)
        self.assertTrue(files)
        self.assertFalse(os.access(files[0], os.W_OK))
        result = run("--remove", str(out))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(out.exists())

    def test_refuses_a_plain_folder(self) -> None:
        folder = self.tmp / "plain"
        (folder / "notes").mkdir(parents=True)
        (folder / "notes" / "keep.txt").write_text("keep\n", encoding="utf-8")
        self.assert_refused(folder, "clone/review-input/HEAD.txt is missing")

    def test_refuses_a_repository_working_tree(self) -> None:
        self.assert_refused(self.repo, "clone/review-input/HEAD.txt is missing")
        self.assertEqual(self.head, git(self.repo, "rev-parse", "HEAD"))

    def test_refuses_a_missing_path(self) -> None:
        missing = self.tmp / "missing"
        self.assert_refused(missing, "does not exist")
        self.assertFalse(missing.exists())

    def test_refuses_a_packet_with_a_missing_marker(self) -> None:
        out = self.build_packet()
        for name in ("HEAD.txt", "BASE.txt", "tracked-files.sha256"):
            with self.subTest(marker=name):
                marker = out / "clone" / "review-input" / name
                data = marker.read_bytes()
                marker.unlink()
                self.assert_refused(out, f"clone/review-input/{name} is missing")
                marker.write_bytes(data)

    def test_refuses_a_packet_holding_other_files(self) -> None:
        out = self.build_packet()
        (out / "review-result.json").write_text("{}\n", encoding="utf-8")
        self.assert_refused(out, "review-result.json")

    def test_refuses_the_clone_folder_itself(self) -> None:
        out = self.build_packet()
        self.assert_refused(out / "clone", "clone/review-input/HEAD.txt is missing")

    def test_remove_takes_no_build_options(self) -> None:
        out = self.build_packet()
        result = run("--remove", str(out), "--repo", str(self.repo))
        self.assertEqual(2, result.returncode)
        self.assertIn("--remove takes no other option", result.stderr)
        self.assertTrue((out / "clone" / "review-input" / "HEAD.txt").is_file())

    def test_build_still_requires_its_options(self) -> None:
        result = run("--repo", str(self.repo), "--base", self.base, "--head", self.head)
        self.assertEqual(2, result.returncode)
        self.assertIn("--out", result.stderr)


if __name__ == "__main__":
    unittest.main()
