"""Tests for docs_weight.py: word-weight visibility report vs a baseline tag."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
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

    def test_counts_real_repository_skills(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        now = docs_weight.weights(repo_root, None)
        self.assertIn("skills/delivery-harness/SKILL.md", now)
        self.assertGreater(now["skills/delivery-harness/SKILL.md"], 3000)
        # The worktree walk must find every canonical skill.
        skills = {key.split("/", 2)[1] for key in now}
        self.assertIn("product-definition-builder", skills)
        self.assertIn("product-activation", skills)


if __name__ == "__main__":
    unittest.main()
