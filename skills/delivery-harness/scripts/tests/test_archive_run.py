"""Tests for archive_run.py: completed-run archival of the coordination set."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def run_markdown(status: str = "complete", gates: object = None) -> str:
    payload = {
        "run_id": "RUN-20260911-demo",
        "status": status,
    }
    if gates is not None:
        payload["final_gate_results"] = gates
    return (
        "# Run\n\n## Harness Run State\n\n```json\n"
        + json.dumps({"harness_run": payload}, indent=2)
        + "\n```\n"
    )


class ArchiveRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.goal = self.root / "docs" / "goal"
        self.goal.mkdir(parents=True)
        (self.goal / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
        (self.goal / "RUN.md").write_text(run_markdown(), encoding="utf-8")
        (self.goal / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
        evidence = self.goal / "evidence"
        evidence.mkdir()
        (evidence / "home-390-ready.png").write_bytes(b"png")
        (self.root / "docs" / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def archive(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "archive_run.py"),
                "--repo-root",
                str(self.root),
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def archived_dir(self) -> Path:
        archived = self.goal / "archived"
        entries = list(archived.iterdir())
        self.assertEqual(1, len(entries), archived)
        return entries[0]

    def test_incomplete_run_is_refused(self) -> None:
        (self.goal / "RUN.md").write_text(
            run_markdown(status="running"), encoding="utf-8"
        )
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("only a complete run", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_non_passing_final_gate_is_refused(self) -> None:
        (self.goal / "RUN.md").write_text(
            run_markdown(
                gates=[{"id": "final-closeout", "status": "planned"}]
            ),
            encoding="utf-8",
        )
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("final gate", result.stderr)

    def test_missing_plan_is_refused(self) -> None:
        (self.goal / "PLAN.md").unlink()
        result = self.archive()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("required coordination file missing", result.stderr)

    def test_dry_run_lists_moves_and_moves_nothing(self) -> None:
        result = self.archive()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("dry run only", result.stdout)
        self.assertIn("move: docs/goal/PLAN.md", result.stdout)
        self.assertIn("move: docs/goal/evidence", result.stdout)
        self.assertIn("move: docs/tasks.md", result.stdout)
        self.assertFalse((self.goal / "archived").exists())
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_apply_moves_the_whole_coordination_set_and_never_deletes(self) -> None:
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        archived = self.archived_dir()
        self.assertEqual(
            {"PLAN.md", "RUN.md", "DECISIONS.md", "evidence", "tasks.md"},
            {entry.name for entry in archived.iterdir()},
        )
        self.assertEqual(
            b"png", (archived / "evidence" / "home-390-ready.png").read_bytes()
        )
        self.assertFalse((self.goal / "PLAN.md").exists())
        self.assertFalse((self.goal / "RUN.md").exists())
        self.assertFalse((self.goal / "DECISIONS.md").exists())
        self.assertFalse((self.goal / "evidence").exists())
        self.assertFalse((self.root / "docs" / "tasks.md").exists())
        self.assertTrue(self.goal.exists(), "docs/goal itself is never removed")

    def test_apply_records_the_documents_row(self) -> None:
        documents = self.root / "docs" / "DOCUMENTS.md"
        documents.write_text(
            "# Documents\n\n| Path | Role | Owner |\n|---|---|---|\n"
            "| `docs/goal/PLAN.md` | static plan manifest | parent |\n",
            encoding="utf-8",
        )
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        text = documents.read_text(encoding="utf-8")
        self.assertIn("docs/goal/archived/", text)

        # A second archival pass with the row present does not duplicate it.
        (self.goal / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
        (self.goal / "RUN.md").write_text(run_markdown(), encoding="utf-8")
        result = self.archive("--apply", "--slug", "second-pass")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(
            1,
            sum(
                1
                for line in documents.read_text(encoding="utf-8").splitlines()
                if "docs/goal/archived/" in line
            ),
        )

    def test_a_second_archive_into_an_existing_target_is_refused(self) -> None:
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        (self.goal / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
        (self.goal / "RUN.md").write_text(run_markdown(), encoding="utf-8")
        result = self.archive("--apply")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("archive target already exists", result.stderr)
        self.assertTrue((self.goal / "RUN.md").exists())

    def test_slug_defaults_to_the_run_id(self) -> None:
        result = self.archive("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("run-20260911-demo", self.archived_dir().name)


if __name__ == "__main__":
    unittest.main()
