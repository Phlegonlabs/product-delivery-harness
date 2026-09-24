#!/usr/bin/env python3
"""Focused tests for checkpoint tasks-view projection and durable failures."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
import render_tasks_view  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_core import plan_digest  # noqa: E402


class HarnessTransitionTaskViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        source_contents = {
            "docs/product/prd.md": b"# Test PRD\n",
            "docs/product/architecture.md": b"# Test architecture\n",
        }
        import hashlib

        for source in self.plan["sources"]:
            contents = source_contents[source["location"]]
            path = self.root / source["location"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
            source["content_sha256"] = hashlib.sha256(contents).hexdigest()
        (self.root / "file.txt").write_text("base\n", encoding="utf-8")
        mf.git(self.root, "init", "-q", "-b", "integration")
        mf.git(self.root, "config", "user.email", "t@example.com")
        mf.git(self.root, "config", "user.name", "T")
        mf.git(self.root, "add", "-A")
        mf.git(self.root, "commit", "-qm", "base")
        digest = plan_digest(self.plan)
        self.run["plan"]["digest_sha256"] = digest
        self.run["integration"]["branch"] = "integration"
        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.plan_path.write_text(
            mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", self.run),
            encoding="utf-8",
        )
        self.view_path = self.root / "docs" / "tasks.md"

    def arguments(self, command: str):
        import argparse

        return argparse.Namespace(
            command=command,
            plan=self.plan_path,
            run=self.run_path,
            repo_root=self.root,
        )

    def test_projection_uses_exact_checkpoints_and_declared_path(self) -> None:
        self.assertEqual(
            {
                "accept-wave",
                "record-worker-result",
                "reject-worker-result",
                "record-integration",
                "reconcile-candidate-head",
                "reconcile-interrupted",
                "reconcile-interrupted-reviews",
                "close-wave",
            },
            harness_transition.TASK_VIEW_CHECKPOINTS,
        )
        for command in ("heartbeat-run-lock", "lease-worker", "record-node-result"):
            with self.subTest(command=command):
                self.assertIsNone(
                    harness_transition._tasks_view_path(self.run, self.arguments(command))
                )
        self.assertEqual(
            self.view_path,
            harness_transition._tasks_view_path(self.run, self.arguments("close-wave")),
        )
        no_root = self.arguments("close-wave")
        no_root.repo_root = None
        self.assertIsNone(harness_transition._tasks_view_path(self.run, no_root))

    def test_refresh_preserves_update_log_and_refuses_foreign_file(self) -> None:
        render_tasks_view.refresh_view(
            self.plan, self.run, self.view_path, repo_root=self.root
        )
        first = self.view_path.read_text(encoding="utf-8")
        row = "- 2026-09-16 · owner · follow-up recorded"
        self.view_path.write_text(
            first.replace(
                render_tasks_view.UPDATE_LOG_START,
                render_tasks_view.UPDATE_LOG_START + "\n" + row,
                1,
            ),
            encoding="utf-8",
        )

        render_tasks_view.refresh_view(
            self.plan, self.run, self.view_path, repo_root=self.root
        )
        refreshed = self.view_path.read_text(encoding="utf-8")
        self.assertIn(row, refreshed)
        self.assertIn(render_tasks_view.GENERATED_MARKER, refreshed)

        foreign = self.root / "docs" / "foreign.md"
        foreign.write_text("hand-authored notes", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "non-generated tasks view"):
            render_tasks_view.refresh_view(
                self.plan, self.run, foreign, repo_root=self.root
            )
        self.assertEqual("hand-authored notes", foreign.read_text(encoding="utf-8"))

    def test_refresh_refuses_paths_outside_the_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "tasks.md"
            with self.assertRaisesRegex(ValueError, "outside repo root"):
                render_tasks_view.refresh_view(
                    self.plan, self.run, outside, repo_root=self.root
                )
            self.assertFalse(outside.exists())

    def test_projection_failure_after_transition_save_is_a_repair_warning(self) -> None:
        from test_new_run import NewRunTests

        fixture = NewRunTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        run_path = fixture.generate()
        view = fixture.dir / "docs/tasks.md"
        view.write_text("hand-authored notes", encoding="utf-8")
        stderr = io.StringIO()
        checkpoints = {*harness_transition.TASK_VIEW_CHECKPOINTS, "pause"}
        with unittest.mock.patch.object(harness_transition, "TASK_VIEW_CHECKPOINTS", checkpoints):
            with contextlib.redirect_stderr(stderr):
                result = harness_transition.main([
                    "--plan", str(fixture.plan_path), "--run", str(run_path),
                    "--repo-root", str(fixture.dir), "pause", "--source", "focused test",
                ])
        self.assertEqual(0, result, stderr.getvalue())
        self.assertIn("RUN pause succeeded", stderr.getvalue())
        self.assertIn("render_tasks_view.py", stderr.getvalue())
        self.assertEqual("hand-authored notes", view.read_text(encoding="utf-8"))
        self.assertEqual("paused", harness_transition.load_run(run_path)["control"]["desired_state"])

    def test_new_run_failure_after_durable_run_is_a_repair_warning(self) -> None:
        from test_new_run import NewRunTests

        fixture = NewRunTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        view = fixture.dir / "docs/tasks.md"
        view.write_text("hand-authored notes", encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            run_path = fixture.generate()
        self.assertTrue(run_path.exists())
        self.assertIn("RUN generation succeeded", stderr.getvalue())
        self.assertEqual("hand-authored notes", view.read_text(encoding="utf-8"))

    def test_new_run_creates_current_view_without_an_extra_render(self) -> None:
        from test_new_run import NewRunTests

        fixture = NewRunTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        run_path = fixture.generate()
        self.assertEqual(0, render_tasks_view.main([
            "--plan", str(fixture.plan_path), "--run", str(run_path),
            "--repo-root", str(fixture.dir), "--out", str(fixture.dir / "docs/tasks.md"),
            "--check",
        ]))

    def test_view_commit_preserves_a_concurrent_user_edit(self) -> None:
        render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root)
        self.run["mission_states"]["M1"]["phase"] = "blocked"
        concurrent = "User notes arriving at the write boundary\n"
        def edit(path):
            if path == self.view_path:
                path.write_text(concurrent, encoding="utf-8")
        with unittest.mock.patch.object(harness_transition, "_run_replace_commit_boundary", side_effect=edit):
            with self.assertRaisesRegex(harness_transition.ManifestError, "commit boundary"):
                render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root)
        self.assertEqual(concurrent, self.view_path.read_text(encoding="utf-8"))

    def test_source_change_before_view_commit_preserves_existing_view(self) -> None:
        render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root)
        original = self.view_path.read_bytes()
        guard = render_tasks_view.source_guard(self.plan, self.run, self.plan_path, self.run_path)
        changed_run = __import__("copy").deepcopy(self.run)
        changed_run["mission_states"]["M1"]["phase"] = "blocked"
        def edit(path):
            self.plan_path.write_text("concurrent PLAN revision", encoding="utf-8")
        with unittest.mock.patch.object(harness_transition, "_run_replace_commit_boundary", side_effect=edit):
            with self.assertRaisesRegex(harness_transition.ManifestError, "PLAN/RUN changed"):
                render_tasks_view.refresh_view(self.plan, changed_run, self.view_path, repo_root=self.root, check_sources=guard)
        self.assertEqual(original, self.view_path.read_bytes())

    def test_generated_view_is_coordination_but_user_and_product_dirt_are_not(self) -> None:
        mf.git(self.root, "add", "PLAN.md")
        mf.git(self.root, "commit", "-qm", "plan fixture")
        render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root)
        self.assertEqual("", harness_transition._git_status_excluding_run(self.root, self.run_path, self.run).strip())
        (self.root / "file.txt").write_text("dirty product", encoding="utf-8")
        self.assertIn("file.txt", harness_transition._git_status_excluding_run(self.root, self.run_path, self.run))
        self.view_path.write_text("hand-authored notes", encoding="utf-8")
        self.assertIn("docs/tasks.md", harness_transition._git_status_excluding_run(self.root, self.run_path, self.run))

    def test_undeclared_or_other_run_view_is_not_exempt(self) -> None:
        render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root)
        self.run["run_id"] = "RUN-other"
        self.assertNotIn("docs/tasks.md", harness_transition._coordination_ignored_paths(self.root, self.run_path, self.run))
        self.run["integration"]["coordination_paths"] = []
        self.assertNotIn("docs/tasks.md", harness_transition._coordination_ignored_paths(self.root, self.run_path, self.run))

    def test_exclusive_create_preserves_a_raced_user_file(self) -> None:
        calls = 0
        def race():
            nonlocal calls
            calls += 1
            if calls == 2:
                self.view_path.write_text("new user file", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root, check_sources=race)
        self.assertEqual("new user file", self.view_path.read_text(encoding="utf-8"))

    def test_source_drift_after_run_save_is_a_warning_not_transition_failure(self) -> None:
        from test_new_run import NewRunTests

        fixture = NewRunTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        run_path = fixture.generate()
        saved_view = (fixture.dir / "docs/tasks.md").read_bytes()
        replace = harness_transition._replace_run_document
        def race(*args, **kwargs):
            replace(*args, **kwargs)
            fixture.plan_path.write_text("concurrent PLAN edit", encoding="utf-8")
        stderr = io.StringIO()
        with unittest.mock.patch.object(harness_transition, "TASK_VIEW_CHECKPOINTS", {"pause"}), unittest.mock.patch.object(harness_transition, "_replace_run_document", side_effect=race), contextlib.redirect_stderr(stderr):
            result = harness_transition.main([
                "--plan", str(fixture.plan_path), "--run", str(run_path),
                "--repo-root", str(fixture.dir), "pause", "--source", "test",
            ])
        self.assertEqual(0, result, stderr.getvalue())
        self.assertIn("RUN pause succeeded", stderr.getvalue())
        self.assertEqual("paused", harness_transition.load_run(run_path)["control"]["desired_state"])
        self.assertEqual(saved_view, (fixture.dir / "docs/tasks.md").read_bytes())

    def test_symlink_destination_is_not_written_or_exempted(self) -> None:
        target = self.root / "notes.md"
        target.write_text("user notes", encoding="utf-8")
        self.view_path.parent.mkdir(exist_ok=True)
        try:
            self.view_path.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        with self.assertRaises((ValueError, harness_transition.ManifestError)):
            render_tasks_view.refresh_view(self.plan, self.run, self.view_path, repo_root=self.root)
        self.assertEqual("user notes", target.read_text(encoding="utf-8"))
        self.assertNotIn("docs/tasks.md", harness_transition._coordination_ignored_paths(self.root, self.run_path, self.run))


if __name__ == "__main__":
    unittest.main()
