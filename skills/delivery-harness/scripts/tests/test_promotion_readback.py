"""Promotion readback tests: pre proves the frozen pre-state, post classifies the landing."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import promotion_readback as subject  # noqa: E402

FORBIDDEN_GIT_VERBS = {"fetch", "push", "pull", "merge", "tag"}
FULL_SHA_RE = r"^[0-9a-f]{40}$"


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class PromotionReadbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temps: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self) -> None:
        for item in self._temps:
            item.cleanup()

    def _fixture(self) -> dict[str, Path | str]:
        """Create one repo whose remote main is one commit ahead of the frozen base."""
        holder = tempfile.TemporaryDirectory()
        self._temps.append(holder)
        root = Path(holder.name).resolve() / "repo"
        root.mkdir()
        remote_holder = tempfile.TemporaryDirectory(prefix="readback-remote-")
        self._temps.append(remote_holder)
        remote = Path(remote_holder.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], check=True)
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Harness Test")
        (root / "docs").mkdir()
        (root / "docs/base.txt").write_text("base\n", encoding="utf-8")
        git(root, "add", "docs")
        git(root, "commit", "-qm", "base")
        base = git(root, "rev-parse", "HEAD")
        (root / "docs/main.txt").write_text("main\n", encoding="utf-8")
        git(root, "add", "docs/main.txt")
        git(root, "commit", "-qm", "advance main")
        main_before = git(root, "rev-parse", "HEAD")
        git(root, "remote", "add", "origin", str(remote))
        git(root, "push", "-q", "origin", "main")
        git(root, "checkout", "-qb", "work")
        (root / "docs/candidate.txt").write_text("candidate\n", encoding="utf-8")
        git(root, "add", "docs/candidate.txt")
        git(root, "commit", "-qm", "candidate")
        candidate = git(root, "rev-parse", "HEAD")
        return {
            "root": root, "remote": remote, "base": base,
            "main_before": main_before, "candidate": candidate,
        }

    def _argv(
        self,
        fixture: dict[str, Path | str],
        command: str,
        *,
        candidate: str | None = None,
        base: str | None = None,
        main_before: str | None = None,
        out: str | None = None,
    ) -> list[str]:
        values = {
            "--repo-root": str(fixture["root"]),
            "--remote": "origin",
            "--candidate": candidate or str(fixture["candidate"]),
            "--base": base or str(fixture["base"]),
            "--main-before": main_before or str(fixture["main_before"]),
        }
        argv = [command]
        for flag in sorted(values):
            argv += [flag, values[flag]]
        if out is not None:
            argv += ["--out", out]
        return argv

    def _run(self, fixture: dict[str, Path | str], command: str, **overrides: str | None) -> tuple[int, dict]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = subject.main(self._argv(fixture, command, **overrides))
        return code, json.loads(stdout.getvalue())

    def _commit_on_main_and_push(self, fixture: dict[str, Path | str], name: str) -> str:
        root = Path(fixture["root"])
        git(root, "checkout", "-q", "main")
        (root / f"docs/{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        git(root, "add", "docs")
        git(root, "commit", "-qm", name)
        head = git(root, "rev-parse", "HEAD")
        git(root, "push", "-q", "origin", "main")
        git(root, "checkout", "-q", "work")
        return head

    def test_pre_passes_at_the_frozen_pre_state(self) -> None:
        fixture = self._fixture()
        code, value = self._run(fixture, "pre")
        self.assertEqual(0, code)
        self.assertEqual("PASS", value["status"])
        self.assertEqual("refs/heads/main", value["branch_ref"])
        self.assertEqual(fixture["main_before"], value["observed_main"])
        self.assertTrue(value["main_matches_pre_state"])
        self.assertTrue(value["base_ancestor_of_candidate"])
        self.assertTrue(value["main_before_ancestor_of_candidate"])
        self.assertRegex(value["candidate_tree"], FULL_SHA_RE)
        self.assertEqual(
            git(Path(fixture["root"]), "rev-parse", "--verify", f"{fixture['main_before']}^{{tree}}"),
            value["main_tree"],
        )
        self.assertIn("grants no landing", value["authority"])

    def test_pre_blocks_when_remote_main_moved(self) -> None:
        fixture = self._fixture()
        moved = self._commit_on_main_and_push(fixture, "late")
        code, value = self._run(fixture, "pre")
        self.assertEqual(1, code)
        self.assertEqual("BLOCKED", value["status"])
        self.assertEqual(moved, value["observed_main"])
        self.assertFalse(value["main_matches_pre_state"])
        self.assertTrue(value["base_ancestor_of_candidate"])
        self.assertTrue(value["main_before_ancestor_of_candidate"])
        self.assertTrue(any("pre-state" in reason for reason in value["reasons"]))

    def test_pre_blocks_when_the_candidate_skips_the_frozen_base(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        git(root, "checkout", "--orphan", "stray")
        (root / "docs/orphan.txt").write_text("orphan\n", encoding="utf-8")
        git(root, "add", "docs/orphan.txt")
        git(root, "commit", "-qm", "orphan")
        orphan = git(root, "rev-parse", "HEAD")
        code, value = self._run(fixture, "pre", candidate=orphan)
        self.assertEqual(1, code)
        self.assertEqual("BLOCKED", value["status"])
        self.assertFalse(value["base_ancestor_of_candidate"])
        self.assertFalse(value["main_before_ancestor_of_candidate"])
        self.assertEqual(2, len(value["reasons"]))

    def test_pre_refuses_short_shas(self) -> None:
        fixture = self._fixture()
        code, value = self._run(fixture, "pre", candidate=str(fixture["candidate"])[:7])
        self.assertEqual(2, code)
        self.assertEqual("ERROR", value["status"])
        self.assertIn("full 40-character", value["errors"][0])
        code, value = self._run(fixture, "pre", base=str(fixture["base"])[:7])
        self.assertEqual(2, code)
        self.assertEqual("ERROR", value["status"])
        code, value = self._run(fixture, "pre", main_before=str(fixture["main_before"])[:7])
        self.assertEqual(2, code)
        self.assertEqual("ERROR", value["status"])

    def test_post_passes_for_the_exact_candidate(self) -> None:
        fixture = self._fixture()
        git(Path(fixture["root"]), "push", "-q", "origin", "work:main")
        code, value = self._run(fixture, "post")
        self.assertEqual(0, code)
        self.assertEqual("PASS", value["status"])
        self.assertEqual("exact", value["landing"])
        self.assertEqual(fixture["candidate"], value["observed_main"])
        self.assertTrue(value["new_main_exists_locally"])
        self.assertTrue(value["main_before_ancestor_of_new_main"])
        self.assertEqual(value["candidate_tree"], value["main_tree"])
        self.assertEqual([], value["reasons"])

    def test_post_passes_for_a_tree_equal_server_sha(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        candidate_tree = git(root, "rev-parse", "--verify", f"{fixture['candidate']}^{{tree}}")
        server_sha = git(root, "commit-tree", candidate_tree, "-p", str(fixture["main_before"]), "-m", "server merge")
        git(root, "push", "-q", "origin", f"{server_sha}:main")
        code, value = self._run(fixture, "post")
        self.assertEqual(0, code)
        self.assertEqual("PASS", value["status"])
        self.assertEqual("tree_equal_S", value["landing"])
        self.assertEqual(server_sha, value["observed_main"])
        self.assertNotEqual(server_sha, fixture["candidate"])
        self.assertEqual(candidate_tree, value["main_tree"])

    def test_post_blocks_on_a_new_candidate_tree(self) -> None:
        fixture = self._fixture()
        replaced = self._commit_on_main_and_push(fixture, "replacement")
        code, value = self._run(fixture, "post")
        self.assertEqual(1, code)
        self.assertEqual("BLOCKED", value["status"])
        self.assertEqual("new_candidate", value["landing"])
        self.assertEqual(replaced, value["observed_main"])
        self.assertTrue(value["main_before_ancestor_of_new_main"])
        self.assertTrue(any("new candidate" in reason for reason in value["reasons"]))

    def test_post_blocks_when_the_observed_main_is_absent_locally(self) -> None:
        fixture = self._fixture()
        holder = tempfile.TemporaryDirectory()
        self._temps.append(holder)
        clone = Path(holder.name).resolve() / "clone"
        subprocess.run(["git", "clone", "-q", str(fixture["remote"]), str(clone)], check=True)
        git(clone, "config", "user.email", "test@example.com")
        git(clone, "config", "user.name", "Harness Test")
        (clone / "late.txt").write_text("late\n", encoding="utf-8")
        git(clone, "add", "late.txt")
        git(clone, "commit", "-qm", "late")
        git(clone, "push", "-q", "origin", "main")
        absent = git(clone, "rev-parse", "HEAD")
        code, value = self._run(fixture, "post")
        self.assertEqual(1, code)
        self.assertEqual("BLOCKED", value["status"])
        self.assertEqual(absent, value["observed_main"])
        self.assertFalse(value["new_main_exists_locally"])
        self.assertEqual("unknown", value["landing"])
        self.assertTrue(any("fetch" in reason for reason in value["reasons"]))

    def test_post_blocks_when_main_before_is_not_an_ancestor(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        candidate_tree = git(root, "rev-parse", "--verify", f"{fixture['candidate']}^{{tree}}")
        unrelated = git(root, "commit-tree", candidate_tree, "-m", "unrelated root")
        git(root, "push", "-q", "--force", "origin", f"{unrelated}:main")
        code, value = self._run(fixture, "post")
        self.assertEqual(1, code)
        self.assertEqual("BLOCKED", value["status"])
        self.assertEqual("tree_equal_S", value["landing"])
        self.assertFalse(value["main_before_ancestor_of_new_main"])
        self.assertTrue(any("ancestor" in reason for reason in value["reasons"]))

    def test_post_writes_the_json_only_outside_the_checkout(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        git(root, "push", "-q", "origin", "work:main")
        holder = tempfile.TemporaryDirectory()
        self._temps.append(holder)
        out = Path(holder.name).resolve() / "evidence" / "post.json"
        code, value = self._run(fixture, "post", out=str(out))
        self.assertEqual(0, code)
        self.assertTrue(out.is_file())
        self.assertEqual(value, json.loads(out.read_text(encoding="utf-8")))
        inside = root / "evidence.json"
        code, value = self._run(fixture, "post", out=str(inside))
        self.assertEqual(2, code)
        self.assertEqual("ERROR", value["status"])
        self.assertFalse(inside.exists())
        code, value = self._run(fixture, "post", out=str(out))
        self.assertEqual(2, code)
        self.assertIn("new path", value["errors"][0])

    def test_git_argv_stays_read_only(self) -> None:
        fixture = self._fixture()
        self._assert_read_only_argv(fixture, "pre")
        git(Path(fixture["root"]), "push", "-q", "origin", "work:main")
        self._assert_read_only_argv(fixture, "post")

    def _assert_read_only_argv(self, fixture: dict[str, Path | str], command: str) -> None:
        def verb(argv: tuple[object, ...]) -> str | None:
            for token in argv[1:]:
                if isinstance(token, str) and not token.startswith("-"):
                    return token
            return None

        with patch("subprocess.run", wraps=subprocess.run) as spy:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = subject.main(self._argv(fixture, command))
        self.assertEqual(0, code)
        verbs = [verb(call.args[0]) for call in spy.call_args_list]
        self.assertNotIn(None, verbs)
        self.assertEqual([], [item for item in verbs if item in FORBIDDEN_GIT_VERBS])
        self.assertIn("ls-remote", verbs)

    def test_cli_exit_codes_reach_the_process(self) -> None:
        fixture = self._fixture()
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "promotion_readback.py"), *self._argv(fixture, "pre")],
            capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
            env=environment,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual("PASS", json.loads(result.stdout)["status"])
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "promotion_readback.py"),
                *self._argv(fixture, "pre", candidate=str(fixture["candidate"])[:7]),
            ],
            capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
            env=environment,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("ERROR", json.loads(result.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
