"""Tests for docs_weight.py: word-weight visibility report vs a baseline tag."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import docs_weight  # noqa: E402


class DocsWeightTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return result.stdout

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit_all(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def run_report(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = docs_weight.main(
                ["--repo-root", str(self.root), *args]
            )
        return code, stdout.getvalue()

    def test_delta_table_against_a_tag(self) -> None:
        self.write("skills/demo/SKILL.md", "one two three four five")
        self.write("skills/demo/references/a.md", "alpha beta")
        self.write("skills/demo/scripts/run.py", "not counted at all")
        self.commit_all("base")
        self.git("tag", "v1.0.0")

        self.write("skills/demo/SKILL.md", "one two three four five six seven")
        self.write("skills/demo/references/b.md", "new file here")
        (self.root / "skills/demo/references/a.md").unlink()
        self.commit_all("grow")

        code, out = self.run_report("--baseline", "v1.0.0")
        self.assertEqual(0, code, out)
        self.assertIn("changed skills/demo/SKILL.md: 5 -> 7 (+2)", out)
        self.assertIn("added skills/demo/references/b.md: 0 -> 3 (+3)", out)
        self.assertIn("removed skills/demo/references/a.md: 2 -> 0 (-2)", out)
        self.assertIn("TOTAL demo: 7 -> 10 (+3)", out)
        self.assertIn("GRAND TOTAL: 7 -> 10 (+3) baseline: v1.0.0", out)
        self.assertNotIn("run.py", out)

    def test_defaults_to_the_latest_tag(self) -> None:
        self.write("skills/demo/SKILL.md", "one two")
        self.commit_all("base")
        self.git("tag", "v1.0.0")
        self.write("skills/demo/SKILL.md", "one two three four")
        self.commit_all("grow")
        self.git("tag", "v1.1.0")
        self.write("skills/demo/SKILL.md", "one two three four five")
        self.commit_all("grow more")

        code, out = self.run_report()
        self.assertEqual(0, code, out)
        self.assertIn("GRAND TOTAL: 4 -> 5 (+1) baseline: v1.1.0", out)

    def test_repo_without_tags_reports_absolute_counts(self) -> None:
        self.write("skills/demo/SKILL.md", "one two three")
        self.commit_all("base")

        code, out = self.run_report()
        self.assertEqual(0, code, out)
        self.assertIn("no v* tag found; reporting absolute counts only", out)
        self.assertIn("GRAND TOTAL: 0 -> 3 (+3) baseline: none", out)

    def test_worktree_move_counts_untracked_destination_and_skips_deleted_source(self) -> None:
        self.write("skills/demo/SKILL.md", "one two")
        self.write("skills/demo/references/old.md", "old words")
        self.commit_all("base")

        (self.root / "skills/demo/references/old.md").unlink()
        self.write("skills/new-skill/SKILL.md", "new live skill")

        now = docs_weight.weights(self.root, None)

        self.assertNotIn("skills/demo/references/old.md", now)
        self.assertEqual(3, now["skills/new-skill/SKILL.md"])

    def test_counts_real_repository_skills(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        now = docs_weight.weights(repo_root, None)
        self.assertIn("skills/delivery-harness/SKILL.md", now)
        self.assertGreater(now["skills/delivery-harness/SKILL.md"], 3000)
        # The worktree walk must find every canonical skill.
        skills = {key.split("/", 2)[1] for key in now}
        self.assertIn("product-definition-builder", skills)
        self.assertIn("ui-design-builder", skills)
        self.assertIn("product-activation", skills)

    def test_baseline_uses_two_git_calls_and_matches_per_file_reads(self) -> None:
        self.write("skills/demo/SKILL.md", "one two")
        self.write("skills/demo/references/empty.md", "")
        self.write("skills/demo/references/space name.md", "three four")
        self.write("skills/demo/references/unicode.md", "五 六")
        self.commit_all("base")
        self.git("tag", "v1.0.0")

        resolved = docs_weight.resolve_ref(self.root, "v1.0.0")
        self.assertRegex(resolved, r"[0-9a-f]{40,64}")
        calls: list[tuple[str, ...]] = []
        original_run_git = docs_weight.run_git

        def counting_run_git(root, *args, **kwargs):
            calls.append(args)
            return original_run_git(root, *args, **kwargs)

        with patch.object(docs_weight, "run_git", counting_run_git):
            bulk = docs_weight.weights(self.root, resolved)

        expected = {
            path.as_posix(): docs_weight._word_count(
                docs_weight.read_file(self.root, path, resolved)
            )
            for path in docs_weight.tracked_files(self.root, resolved)
        }
        self.assertEqual(expected, bulk)
        self.assertEqual(0, bulk["skills/demo/references/empty.md"])
        self.assertEqual(2, bulk["skills/demo/references/space name.md"])
        self.assertEqual(2, bulk["skills/demo/references/unicode.md"])
        command_names = [args[0] for args in calls if args]
        self.assertEqual(1, command_names.count("ls-tree"))
        self.assertEqual(1, command_names.count("cat-file"))

    def test_resolved_baseline_does_not_follow_a_moved_tag(self) -> None:
        self.write("skills/demo/SKILL.md", "one two")
        self.commit_all("base")
        self.git("tag", "v1.0.0")
        resolved = docs_weight.resolve_ref(self.root, "v1.0.0")

        self.write("skills/demo/SKILL.md", "moved three")
        self.commit_all("move")
        self.git("tag", "-f", "v1.0.0")

        self.assertEqual(2, docs_weight.weights(self.root, resolved)["skills/demo/SKILL.md"])

    def test_empty_blob_list_and_malformed_batch_fail_or_short_circuit(self) -> None:
        self.assertEqual({}, docs_weight._blob_words(self.root, []))

        with patch.object(
            docs_weight,
            "_run_git_bytes",
            return_value=(b"bad\n", None),
        ):
            with self.assertRaisesRegex(
                docs_weight.ManifestError,
                "malformed header",
            ):
                docs_weight._blob_words(
                    self.root,
                    [(Path("skills/demo/SKILL.md"), "a" * 40)],
                )

    def test_invalid_baseline_refails_without_reading_worktree_baseline(self) -> None:
        self.write("skills/demo/SKILL.md", "one")
        self.commit_all("base")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, output = self.run_report("--baseline", "does-not-exist")
        self.assertEqual(2, code)
        self.assertIn("invalid baseline ref: does-not-exist", stderr.getvalue())

    def test_unrelated_gitlink_is_not_documentation(self) -> None:
        self.write("skills/demo/SKILL.md", "one two")
        self.commit_all("base")
        head = self.git("rev-parse", "HEAD").strip()
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},skills/vendor")
        self.git("commit", "-qm", "gitlink")
        self.assertEqual({"skills/demo/SKILL.md": 2}, docs_weight.weights(self.root, "HEAD"))

    def test_batch_rejects_trailing_bytes(self) -> None:
        oid = "a" * 40
        raw = f"{oid} blob 3\none\nextra".encode()
        with patch.object(docs_weight, "_run_git_bytes", return_value=(raw, None)):
            with self.assertRaisesRegex(docs_weight.ManifestError, "trailing data"):
                docs_weight._blob_words(self.root, [(Path("skills/demo/SKILL.md"), oid)])

    def test_unicode_document_path_survives_nul_tree_listing(self) -> None:
        path = "skills/demo/references/\u6587\u4ef6 name.md"
        self.write(path, "one two")
        self.commit_all("unicode path")
        self.assertEqual({path: 2}, docs_weight.weights(self.root, "HEAD"))


if __name__ == "__main__":
    unittest.main()
