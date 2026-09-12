#!/usr/bin/env python3
"""Tests for the tasks.md human view renderer."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import new_run  # noqa: E402
import render_tasks_view  # noqa: E402
from manifest_fixtures import manifest_markdown  # noqa: E402

PLAN_TEMPLATE = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"


def two_mission_plan() -> dict:
    return {
        "schema_version": 6,
        "plan_id": "PLAN-view",
        "revision": 2,
        "objective": "Ship the sliced outcome",
        "graph": {
            "nodes": [
                {"id": "N-M1", "kind": "mission", "ref": "M1"},
                {"id": "N-M2", "kind": "mission", "ref": "M2"},
            ],
            "edges": [
                {"id": "E-M1-M2", "kind": "dependency", "from": "N-M1", "to": "N-M2"},
            ],
        },
        "missions": [
            {
                "id": "M1",
                "objective": "First slice",
                "tasks": [
                    {"id": "M1/T01", "objective": "Do T01", "depends_on": []},
                ],
            },
            {
                "id": "M2",
                "alias": "Second",
                "objective": "Second slice",
                "tasks": [
                    {
                        "id": "M2/T01",
                        "objective": "Do | T01",
                        "depends_on": ["M1/T01"],
                    },
                ],
            },
        ],
    }


def progressed_run(**m2_state) -> dict:
    m2_state.setdefault("phase", "worker_running")
    return {
        "run_id": "RUN-view",
        "status": "running",
        "mission_states": {
            "M1": {"phase": "integrated", "integrated_sha": "a" * 40},
            "M2": m2_state,
        },
        "task_states": {
            "M1/T01": {
                "phase": "mission_recorded",
                "verifier_status": "pass",
                "attempts": 2,
                "commit_sha": "b" * 40,
            },
            "M2/T01": {
                "phase": "running",
                "verifier_status": "planned",
                "attempts": 1,
                "commit_sha": None,
            },
        },
    }


class RenderTasksViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def generate_run(self) -> Path:
        out = self.dir / "RUN.md"
        self.assertEqual(
            0,
            new_run.main(
                [
                    "--plan",
                    str(PLAN_TEMPLATE),
                    "--run-id",
                    "RUN-test",
                    "--branch",
                    "refs/heads/test-run",
                    "--out",
                    str(out),
                ]
            ),
        )
        return out

    def test_template_pair_renders_progress_frontier_and_task_rows(self) -> None:
        from harness_manifest import load_plan, load_run

        plan = load_plan(PLAN_TEMPLATE)
        run = load_run(self.generate_run())

        view = render_tasks_view.build_view(plan, run)

        self.assertIn(render_tasks_view.GENERATED_MARKER, view)
        self.assertIn("- Progress: 0/1 missions integrated · 0/1 tasks recorded", view)
        self.assertIn("- Current frontier: next: M1 (queued)", view)
        self.assertIn("## M1 — <short stable label>", view)
        self.assertIn(
            "| M1/T01 | <independently verifiable outcome> | none | queued "
            "| planned | 0 |  |",
            view,
        )

    def test_progress_and_frontier_reflect_mission_and_task_state(self) -> None:
        plan = two_mission_plan()
        run = progressed_run()

        view = render_tasks_view.build_view(plan, run)

        self.assertIn("- Progress: 1/2 missions integrated · 1/2 tasks recorded", view)
        self.assertIn("- Current frontier: M2 (worker_running)", view)
        self.assertIn("## M1\n", view)
        self.assertIn("## M2 — Second", view)
        self.assertIn("First slice", view)
        self.assertIn(
            f"Phase: integrated · depends on: none · integrated at `{'a' * 12}`",
            view,
        )
        self.assertIn("Phase: worker_running · depends on: M1", view)
        self.assertIn(
            f"| M1/T01 | Do T01 | none | mission_recorded | pass | 2 | `{'b' * 12}` |",
            view,
        )
        self.assertIn("| M2/T01 | Do \\| T01 | M1/T01 | running | planned | 1 |  |", view)

    def test_mission_sections_render_newest_first(self) -> None:
        plan = two_mission_plan()
        run = progressed_run()

        view = render_tasks_view.build_view(plan, run)

        self.assertLess(view.index("## M2"), view.index("## M1"))

    def test_blocked_mission_lists_blockers_in_frontier(self) -> None:
        plan = two_mission_plan()
        run = progressed_run(phase="blocked", blockers=["lease unavailable"])

        view = render_tasks_view.build_view(plan, run)

        self.assertIn("- Current frontier: M2 (blocked)", view)
        self.assertIn("· depends on: M1 · blockers: lease unavailable", view)

    def test_fully_integrated_run_reports_no_frontier(self) -> None:
        plan = two_mission_plan()
        run = progressed_run(phase="integrated", integrated_sha="c" * 40)

        view = render_tasks_view.build_view(plan, run)

        self.assertIn("- Progress: 2/2 missions integrated · 1/2 tasks recorded", view)
        self.assertIn("- Current frontier: none — every mission integrated", view)

    def test_main_writes_and_regenerates_its_own_out_file(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        first = out.read_text(encoding="utf-8")
        self.assertIn(render_tasks_view.GENERATED_MARKER, first)

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        self.assertEqual(first, out.read_text(encoding="utf-8"))

    def test_fresh_render_carries_the_update_log_scaffold(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        text = out.read_text(encoding="utf-8")
        self.assertIn("## Update Log", text)
        self.assertIn(render_tasks_view.UPDATE_LOG_START, text)
        self.assertIn(render_tasks_view.UPDATE_LOG_END, text)

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out), "--check"]
            ),
        )

    def test_fresh_render_scopes_the_never_edit_warning_to_the_generated_part(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        text = out.read_text(encoding="utf-8")
        self.assertIn("never edit the generated part", text)
        self.assertIn("the one hand-maintained section", text)
        self.assertIn("## Update Log", text)

    def test_update_log_rows_survive_re_render_verbatim(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"
        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        row = "- 2026-09-11 · owner · tightened dashboard copy · rationale: review"
        text = out.read_text(encoding="utf-8")
        marked = text.replace(
            render_tasks_view.UPDATE_LOG_START,
            render_tasks_view.UPDATE_LOG_START + "\n" + row,
            1,
        )
        out.write_text(marked, encoding="utf-8")

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        self.assertIn(row, out.read_text(encoding="utf-8"))

    def test_check_ignores_log_edits_but_flags_generated_drift(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"
        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        text = out.read_text(encoding="utf-8")
        edited = text.replace(
            render_tasks_view.UPDATE_LOG_END,
            "- 2026-09-11 · agent · small fix outside missions\n"
            + render_tasks_view.UPDATE_LOG_END,
            1,
        )
        out.write_text(edited, encoding="utf-8")
        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out), "--check"]
            ),
        )

        out.write_text(
            edited.replace("0/1 missions integrated", "9/1 missions integrated", 1),
            encoding="utf-8",
        )
        self.assertEqual(
            1,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out), "--check"]
            ),
        )

    def test_markerless_generated_file_is_migrated_not_refused(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"
        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        from harness_manifest import load_plan, load_run

        legacy = render_tasks_view.build_view(
            load_plan(PLAN_TEMPLATE), load_run(run_path)
        )
        out.write_text(legacy, encoding="utf-8")

        self.assertEqual(
            0,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        migrated = out.read_text(encoding="utf-8")
        self.assertIn(render_tasks_view.UPDATE_LOG_START, migrated)

    def test_main_refuses_to_overwrite_a_foreign_file(self) -> None:
        run_path = self.generate_run()
        out = self.dir / "tasks.md"
        out.write_text("hand-authored notes", encoding="utf-8")

        self.assertEqual(
            2,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(run_path), "--out", str(out)]
            ),
        )
        self.assertEqual("hand-authored notes", out.read_text(encoding="utf-8"))

    def test_main_refuses_a_stale_plan_run_pair(self) -> None:
        from harness_manifest import load_run

        run_path = self.generate_run()
        run = load_run(run_path)
        run["plan"]["revision"] = 99
        stale = self.dir / "stale-run.md"
        stale.write_text(
            manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )

        self.assertEqual(
            2,
            render_tasks_view.main(
                ["--plan", str(PLAN_TEMPLATE), "--run", str(stale)]
            ),
        )


if __name__ == "__main__":
    unittest.main()
