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


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", check=False, cwd=cwd,
    )


def listing(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def make_dir_link(link: Path, target: Path) -> None:
    """A directory symlink, or a junction where symlinks need a privilege."""
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


def remove_link(link: Path) -> None:
    # Remove the link itself; never delete through it.
    if os.path.lexists(link):
        (os.rmdir if os.name == "nt" else os.unlink)(link)


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

    def build_packet(self, out: Path | None = None) -> Path:
        out = out or self.tmp / "packet"
        built = run("--repo", str(self.repo), "--base", self.base, "--head", self.head, "--out", str(out))
        self.assertEqual(0, built.returncode, built.stderr)
        return out

    def link(self, link: Path, target: Path) -> Path:
        make_dir_link(link, target)
        self.addCleanup(remove_link, link)
        return link

    def assert_refused(self, target: Path, reason: str, cwd: Path | None = None) -> None:
        before = listing(target) if target.exists() else None
        result = run("--remove", str(target), cwd=cwd)
        self.assertEqual(2, result.returncode, result.stdout)
        self.assertEqual("", result.stdout)
        self.assertIn("error: not a review packet", result.stderr)
        self.assertIn(reason, result.stderr)
        self.assertEqual(1, len(result.stderr.splitlines()), result.stderr)
        self.assertEqual(before, listing(target) if target.exists() else None)

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

    def test_refuses_a_clone_holding_a_file_the_build_did_not_list(self) -> None:
        out = self.build_packet()
        (out / "clone" / "valuable.db").write_bytes(b"saved here after the build")
        self.assert_refused(out, "does not list with their bytes")

    def test_refuses_a_clone_whose_listed_file_changed(self) -> None:
        out = self.build_packet()
        tracked = next(path for path in sorted((out / "clone").rglob("*"))
                       if path.is_file() and ".git" not in path.parts and "review-input" not in path.parts)
        tracked.write_bytes(tracked.read_bytes() + b" edited after the build")
        self.assert_refused(out, "does not list with their bytes")

    def test_refuses_review_input_holding_a_file_the_build_does_not_write(self) -> None:
        out = self.build_packet()
        (out / "clone" / "review-input" / "notes.txt").write_text("keep me\n", encoding="utf-8")
        self.assert_refused(out, "also holds notes.txt")

    def test_refuses_the_clone_folder_itself(self) -> None:
        out = self.build_packet()
        self.assert_refused(out / "clone", "clone/review-input/HEAD.txt is missing")

    def fake_packet(self, root: Path) -> Path:
        """Marker files that look right, with no clone behind them."""
        review = root / "clone" / "review-input"
        review.mkdir(parents=True)
        (review / "HEAD.txt").write_bytes(f"{self.head}\n".encode())
        (review / "BASE.txt").write_bytes(f"{self.base}\n".encode())
        (review / "tracked-files.sha256").write_bytes(f"{'0' * 64}  app.py\n".encode())
        return root

    def test_refuses_markers_without_a_git_clone(self) -> None:
        self.assert_refused(self.fake_packet(self.tmp / "no-git"), "clone/.git is missing")
        empty_git = self.fake_packet(self.tmp / "empty-git")
        (empty_git / "clone" / ".git").mkdir()
        self.assert_refused(empty_git, "is not a Git checkout of its own")
        # Git looks upward from an empty clone/.git and finds the repository, whose HEAD matches HEAD.txt.
        inside_repo = self.fake_packet(self.repo / "fake")
        (inside_repo / "clone" / ".git").mkdir()
        self.assert_refused(inside_repo, "is not a Git checkout of its own")

    def test_refuses_a_clone_not_detached_at_head_txt(self) -> None:
        out = self.build_packet()
        clone = out / "clone"
        head_txt = clone / "review-input" / "HEAD.txt"
        original = head_txt.read_bytes()
        head_txt.write_bytes(f"{self.base}\n".encode())
        self.assert_refused(out, f"not detached at {self.base}")
        head_txt.write_bytes(original)
        git(clone, "checkout", "-q", "-b", "review")
        self.assert_refused(out, "(refs/heads/review), not detached")

    def test_refuses_malformed_markers(self) -> None:
        out = self.build_packet()
        review = out / "clone" / "review-input"
        digest = "0" * 64
        cases = (
            ("HEAD.txt", self.head[:12] + "\n", "HEAD.txt in"),
            ("HEAD.txt", f"{self.head}\n{self.base}\n", "HEAD.txt in"),
            ("HEAD.txt", self.head.upper() + "\n", "HEAD.txt in"),
            ("BASE.txt", "main\n", "BASE.txt in"),
            ("tracked-files.sha256", "abc  app.py\n", "line 1"),
            ("tracked-files.sha256", f"{digest} app.py\n", "line 1"),
            ("tracked-files.sha256", f"{digest}  app.py\n{digest}  /etc/passwd\n", "line 2"),
            ("tracked-files.sha256", f"{digest}  ../outside.txt\n", "line 1"),
            ("tracked-files.sha256", f"{digest}  C:/Windows/win.ini\n", "line 1"),
            ("tracked-files.sha256", f"{digest}  \n", "line 1"),
            ("tracked-files.sha256", f"{digest}  app.py", "line 1"),
            ("tracked-files.sha256", f"{digest}  app.py\r\n", "line 1"),
        )
        for name, content, reason in cases:
            with self.subTest(name=name, content=content):
                original = (review / name).read_bytes()
                (review / name).write_bytes(content.encode("utf-8"))
                self.assert_refused(out, reason)
                (review / name).write_bytes(original)

    def test_refuses_a_packet_holding_the_current_directory(self) -> None:
        out = self.build_packet()
        for cwd in (out, out / "clone", out / "clone" / "review-input"):
            with self.subTest(cwd=cwd.relative_to(self.tmp).as_posix()):
                self.assert_refused(out, "holds the current working directory", cwd=cwd)

    def test_refuses_a_packet_that_is_a_git_work_tree_root(self) -> None:
        outer = self.tmp / "outer"
        outer.mkdir()
        git(outer, "init", "-q")
        out = self.build_packet(outer / "packet")
        git(outer, "config", "core.worktree", out.as_posix())
        self.assert_refused(out, "is a Git work tree root")

    def test_removes_a_packet_inside_another_work_tree(self) -> None:
        out = self.build_packet(self.repo / "packet")
        result = run("--remove", str(out))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(out.exists())
        self.assertEqual("print('two')\n", (self.repo / "app.py").read_text(encoding="utf-8"))

    def test_refuses_a_link_to_a_packet_and_keeps_the_target(self) -> None:
        out = self.build_packet(self.tmp / "area" / "packet")
        before = listing(out)
        to_packet = self.link(self.tmp / "to-packet", out)
        through = self.link(self.tmp / "to-area", out.parent) / "packet"
        for given in (to_packet, through):
            with self.subTest(path=given.relative_to(self.tmp).as_posix()):
                self.assert_refused(given, "is or passes through a link or junction")
                self.assertEqual(before, listing(out))

    def test_refuses_a_link_inside_the_packet_and_keeps_its_target(self) -> None:
        out = self.build_packet()
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep\n", encoding="utf-8")
        self.link(out / "clone" / "linked", outside)
        self.assert_refused(out, "clone/linked")
        self.assertEqual("keep\n", (outside / "keep.txt").read_text(encoding="utf-8"))

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
