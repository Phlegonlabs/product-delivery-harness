#!/usr/bin/env python3
"""amend-scope: a RUN-recorded write-scope amendment for one mission."""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import shlex
import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
import inspect_harness_run  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
import test_harness_transition_record_commands as record_commands  # noqa: E402
import test_validate_worker_result as worker_result  # noqa: E402
from harness_core import effective_write_scope  # noqa: E402
from harness_manifest import plan_digest, validate_current_plan_run, validate_run  # noqa: E402


SESSION = record_commands.SESSION


class AmendScopeCommandTests(record_commands.RecordCommandsFixture):
    def setUp(self) -> None:
        super().setUp()
        mf.authorize_execution(self.run, ["M1", "M2"])
        self.rewrite_run()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, self.transition("acquire-run-lock"))

    def amend(self, mission_id: str, *paths: str, reason: str = "remove scaffold") -> tuple[int, str]:
        argv = ["amend-scope", "--mission-id", mission_id, "--reason", reason]
        for path in paths:
            argv += ["--path", path]
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = self.transition(*argv)
        return code, stderr.getvalue()

    def assert_refused(self, expected: str, mission_id: str, *paths: str, **kwargs: str) -> None:
        before = self.run_path.read_bytes()
        code, stderr = self.amend(mission_id, *paths, **kwargs)
        self.assertEqual(2, code, stderr)
        self.assertIn(expected, stderr)
        self.assertEqual(before, self.run_path.read_bytes())

    def test_records_a_row_and_keeps_the_plan(self) -> None:
        plan_before = self.plan_path.read_bytes()
        code, stderr = self.amend("M1", "src/shared/util.py", "src/shared/fixtures/**")
        self.assertEqual(0, code, stderr)
        live = self.reload_run()
        row = live["scope_amendments"][0]
        self.assertEqual("SA-001", row["id"])
        self.assertEqual("M1", row["mission_id"])
        self.assertEqual(["src/shared/util.py", "src/shared/fixtures/**"], row["paths"])
        self.assertEqual("remove scaffold", row["reason"])
        self.assertTrue(row["recorded_at"].endswith("Z"))
        self.assertEqual(plan_before, self.plan_path.read_bytes())
        self.assertEqual(plan_digest(self.plan), live["plan"]["digest_sha256"])
        self.assertEqual([], validate_current_plan_run(self.plan, live))

        code, stderr = self.amend("M2", "src/other/two.py")
        self.assertEqual(0, code, stderr)
        self.assertEqual("SA-002", self.reload_run()["scope_amendments"][1]["id"])

    def test_requires_the_held_run_lock(self) -> None:
        before = self.run_path.read_bytes()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = self.transition(
                "amend-scope", "--mission-id", "M1", "--path", "src/shared/util.py",
                "--reason", "x", session=record_commands.OTHER_SESSION,
            )
        self.assertEqual(2, code)
        self.assertEqual(before, self.run_path.read_bytes())

    def test_refuses_a_run_that_is_not_running(self) -> None:
        self.run = self.reload_run()
        self.run["status"] = "ready"
        self.rewrite_run()
        self.assert_refused("the RUN is not running", "M1", "src/shared/util.py")

    def test_refuses_a_mission_outside_the_plan(self) -> None:
        self.assert_refused("mission 'M9' is not in the PLAN", "M9", "src/shared/util.py")

    def test_refuses_an_integrated_or_superseded_mission(self) -> None:
        for phase in ("integrated", "superseded"):
            with self.subTest(phase=phase):
                self.run = self.reload_run()
                self.run["mission_states"]["M1"]["phase"] = phase
                self.rewrite_run()
                self.assert_refused(f"mission 'M1' is {phase}", "M1", "src/shared/util.py")

    def test_refuses_bad_paths(self) -> None:
        cases = {
            "/etc/passwd": "repository-relative POSIX path",
            "src\\x.py": "repository-relative POSIX path",
            "C:/x.py": "Windows drive",
            "../outside.py": "path segment",
            "src/../x.py": "path segment",
            "src/./x.py": "path segment",
            "src//x.py": "canonical path spelling",
            " src/x.py": "canonical path spelling",
            "src/*.py": "terminal /** wildcard",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assert_refused(expected, "M1", path)

    def test_refuses_duplicate_paths_and_empty_reason(self) -> None:
        self.assert_refused("must be unique", "M1", "src/x.py", "src/x.py")
        self.assert_refused("--reason must be non-empty", "M1", "src/x.py", reason=" ")

    def test_refuses_parent_owned_and_coordination_paths(self) -> None:
        self.assert_refused("is parent-owned", "M1", "src/shared/RUN.md")
        self.assert_refused("is a coordination path", "M1", "docs/goal/DECISIONS.md")
        self.assert_refused("is a coordination path", "M1", "docs/tasks.md")
        self.assert_refused("is a coordination path", "M1", "docs/goal/**")

    def test_refuses_acceptance_register_paths(self) -> None:
        self.plan["final_gates"][0]["argv"] = [
            "python", "check_delivery_acceptance.py", "--results", "docs/acceptance/results.json",
        ]
        self.run = self.reload_run()
        self.run["plan"]["digest_sha256"] = plan_digest(self.plan)
        self.rewrite_run()
        self.assert_refused("acceptance-register path", "M1", "docs/acceptance/results.json")
        self.assert_refused("acceptance-register path", "M1", "docs/acceptance/evidence/a.png")
        self.assert_refused("acceptance-register path", "M1", "docs/acceptance/**")

    def test_refuses_the_mission_deny_scope(self) -> None:
        self.plan["missions"][0]["deny_scope"].append("src/a/generated/**")
        self.run = self.reload_run()
        self.run["plan"]["digest_sha256"] = plan_digest(self.plan)
        self.rewrite_run()
        self.assert_refused("matches mission 'M1' deny_scope", "M1", "src/a/generated/x.py")

    def test_refuses_frozen_plan_sources(self) -> None:
        self.assert_refused("frozen PLAN source", "M1", "docs/product/PRD.md")
        self.assert_refused("frozen PLAN source", "M1", "docs/product/**")

    def test_refuses_overlap_with_a_mission_that_is_not_integrated(self) -> None:
        self.assert_refused("overlaps the write scope of mission 'M2' (queued)", "M1", "src/ab/one.py")
        self.assert_refused("overlaps the write scope of mission 'M2' (queued)", "M1", "src/**")
        self.assert_refused("overlaps the write scope of mission 'M2' (queued)", "M1", "SRC/AB/one.py")
        # An earlier amendment counts as part of that mission's scope.
        code, stderr = self.amend("M2", "src/shared/util.py")
        self.assertEqual(0, code, stderr)
        self.assert_refused("overlaps the write scope of mission 'M2' (queued)", "M1", "src/shared/**")


class AmendScopeIntegratedOverlapTests(unittest.TestCase):
    """An integrated mission's files are the case amend-scope exists for."""

    def test_overlap_with_an_integrated_mission_is_accepted(self) -> None:
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run["mission_states"]["M1"]["phase"] = "integrated"
        args = argparse.Namespace(
            mission_id="M2", path=["src/a/placeholder.py"], reason="drop M1 placeholder"
        )
        harness_transition._amend_scope(plan, run, args)
        self.assertEqual(["src/a/placeholder.py"], run["scope_amendments"][0]["paths"])
        self.assertEqual(
            ["src/ab/**", "src/a/placeholder.py"],
            effective_write_scope(plan["missions"][1], run),
        )

        run["mission_states"]["M1"]["phase"] = "worker_running"
        with self.assertRaisesRegex(Exception, "overlaps the write scope of mission 'M1'"):
            harness_transition._amend_scope(plan, run, args)


class AmendedWorkerResultTests(unittest.TestCase):
    """The mission-level scope check reads the effective write scope."""

    EXTRA = "src/shared/util.py"

    def setUp(self, *, acceptance_gate: bool = False) -> None:
        self.plan = worker_result.make_plan()
        if acceptance_gate:
            self.plan["final_gates"][0]["argv"] = [
                "python", "check_delivery_acceptance.py", "--results", "docs/acc/results.json",
            ]
        self.run = worker_result.make_run(self.plan)
        self.result = copy.deepcopy(worker_result.make_result(self.plan))
        changed = [worker_result.CHANGED_FILE, self.EXTRA]
        self.result["changed_files"] = changed
        for item in self.result["verifiers"]:
            item["evidence"] = worker_result.retained_verifier_result(
                item["id"], self.plan, changed
            )["execution_key"]

    def validate(self, run: dict) -> set[str]:
        errors = worker_result.validate(
            self.plan, run, self.result,
            observed_files=[worker_result.CHANGED_FILE, self.EXTRA],
        )
        return worker_result.error_codes(errors)

    def amended_run(self) -> dict:
        run = copy.deepcopy(self.run)
        run["scope_amendments"] = [
            {
                "id": "SA-001",
                "mission_id": "M1",
                "paths": [self.EXTRA],
                "reason": "shared helper",
                "recorded_at": "2026-11-16T00:00:00Z",
            }
        ]
        return run

    def test_without_the_amendment_the_path_escapes(self) -> None:
        self.assertIn("scope_escape", self.validate(self.run))

    def test_the_amendment_lets_the_same_result_validate(self) -> None:
        run = self.amended_run()
        self.assertEqual([], validate_run(self.plan, run))
        self.assertEqual(set(), self.validate(run))

    def test_another_missions_amendment_does_not_widen_this_one(self) -> None:
        run = self.amended_run()
        run["scope_amendments"][0]["mission_id"] = "M2"
        self.assertIn("scope_escape", self.validate(run))

    def test_an_acceptance_gate_counts_the_amendment_as_task_scope(self) -> None:
        self.setUp(acceptance_gate=True)
        self.assertIn("scope_escape", self.validate(self.run))
        self.assertEqual(set(), self.validate(self.amended_run()))


class ScopeAmendmentShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        self.row = {
            "id": "SA-001",
            "mission_id": "M1",
            "paths": ["src/shared/util.py"],
            "reason": "shared helper",
            "recorded_at": "2026-11-16T00:00:00Z",
        }

    def errors(self, rows: object) -> list[str]:
        run = copy.deepcopy(self.run)
        run["scope_amendments"] = rows
        return [item for item in validate_run(self.plan, run) if "scope_amendments" in item]

    def test_absent_and_valid_rows_pass(self) -> None:
        self.assertEqual([], validate_run(self.plan, self.run))
        self.assertEqual([], self.errors([self.row]))

    def test_malformed_rows_fail(self) -> None:
        cases = [
            ("not a list", "must be a list"),
            ([{**self.row, "id": "SA-7"}], "must equal SA-001"),
            ([{**self.row, "mission_id": "M9"}], "must name a PLAN mission"),
            ([{**self.row, "paths": []}], "must not be empty"),
            ([{**self.row, "paths": ["/abs.py"]}], "paths"),
            ([{**self.row, "paths": ["src/RUN.md"]}], "parent-owned"),
            ([{**self.row, "reason": ""}], "reason"),
            ([{**self.row, "extra": 1}], "unknown keys"),
        ]
        for rows, expected in cases:
            with self.subTest(expected=expected):
                found = self.errors(rows)
                self.assertTrue(any(expected in item for item in found), found)


class DocumentedAmendScopeTests(unittest.TestCase):
    def test_card_command_parses_and_flag_surface_lists_it(self) -> None:
        references = SCRIPTS_DIR.parent / "references"
        cards = (references / "stages/stage-cards.md").read_text(encoding="utf-8")
        lines = [
            line.strip() for line in cards.splitlines()
            if line.strip().startswith("python ") and " amend-scope " in line
        ]
        self.assertEqual(1, len(lines))
        parsed = harness_transition.build_parser().parse_args(shlex.split(lines[0])[2:])
        self.assertEqual("amend-scope", parsed.command)
        self.assertEqual(["<path>"], parsed.path)
        state = (references / "execution-state-model.md").read_text(encoding="utf-8")
        self.assertIn("- `amend-scope`: `--mission-id`, repeatable `--path`, `--reason`", state)


class InspectScopeAmendmentTests(unittest.TestCase):
    def run_document(self) -> dict:
        return {
            "schema_version": 11,
            "run_id": "RUN-SA",
            "status": "running",
            "active_wave": None,
            "integration": {},
            "mission_states": {},
            "workers": [],
        }

    def test_shows_one_line_per_amendment(self) -> None:
        run = self.run_document()
        run["scope_amendments"] = [
            {"id": "SA-001", "mission_id": "M2", "paths": ["a.py", "b/**"],
             "reason": "drop placeholders", "recorded_at": "2026-11-16T00:00:00Z"},
        ]
        rendered = inspect_harness_run.render_text(
            inspect_harness_run.summarize_run(Path.cwd(), run)
        )
        self.assertIn("Scope amendment SA-001: M2 + a.py, b/** — drop placeholders", rendered)

    def test_no_amendments_add_nothing(self) -> None:
        summary = inspect_harness_run.summarize_run(Path.cwd(), self.run_document())
        self.assertNotIn("scope_amendments", summary)
        self.assertNotIn("Scope amendment", inspect_harness_run.render_text(summary))


if __name__ == "__main__":
    unittest.main()
