#!/usr/bin/env python3
"""Focused tests for guarded runtime observation transitions."""

from __future__ import annotations

import contextlib
import copy
import io
import sys
import unittest
import unittest.mock
from datetime import datetime, timezone
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
import test_harness_transition as transition_fixture  # noqa: E402


def _event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "provider": "generic",
        "node_id": None,
        "attempt_id": None,
        "phase": "transition_prepare:pause",
        "status": "complete",
        "started_at": "2026-09-01T00:00:00Z",
        "completed_at": "2026-09-01T00:00:01Z",
        "duration_ms": 1000,
        "wait_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "context_bytes": None,
    }


def _metrics() -> dict[str, object]:
    return {
        "target_reduction_percent": {"minimum": 10, "stretch": 20},
        "baseline_wall_time_ms": None,
        "run_wall_time_ms": None,
        "critical_path_ms": None,
        "events": [_event("prior")],
    }


class RuntimeObservationTransitionTests(unittest.TestCase):
    def _fixture(self) -> transition_fixture.HarnessTransitionTaskViewTests:
        fixture = transition_fixture.HarnessTransitionTaskViewTests()
        fixture.setUp()
        fixture.run["integration"]["integration_head_sha"] = mf.git(fixture.root, "rev-parse", "HEAD").strip()
        fixture.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", fixture.run), encoding="utf-8"
        )
        self.addCleanup(fixture.doCleanups)
        return fixture

    def _seed_metrics(self, fixture) -> dict[str, object]:
        metrics = _metrics()
        fixture.run["runtime_metrics"] = metrics
        fixture.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", fixture.run),
            encoding="utf-8",
        )
        return copy.deepcopy(metrics)

    def _pause_argv(self, fixture) -> list[str]:
        return [
            "--plan", str(fixture.plan_path),
            "--run", str(fixture.run_path),
            "--repo-root", str(fixture.root),
            "pause", "--source", "runtime observation test",
        ]

    def test_successful_pause_appends_and_preserves_prior_observations(self) -> None:
        fixture = self._fixture()
        prior = self._seed_metrics(fixture)
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = harness_transition.main(self._pause_argv(fixture))

        self.assertEqual(0, result)
        self.assertIn("updated", stdout.getvalue())
        self.assertEqual(
            "paused", harness_transition.load_run(fixture.run_path)["control"]["desired_state"]
        )
        metrics = harness_transition.load_run(fixture.run_path)["runtime_metrics"]
        self.assertEqual(prior["target_reduction_percent"], metrics["target_reduction_percent"])
        self.assertEqual(prior["events"], metrics["events"][:-1])
        self.assertEqual(2, len(metrics["events"]))

        event = metrics["events"][-1]
        self.assertNotEqual("prior", event["event_id"])
        self.assertEqual("generic", event["provider"])
        self.assertEqual("transition_prepare:pause", event["phase"])
        self.assertEqual("complete", event["status"])
        self.assertIsNone(event["node_id"])
        self.assertIsNone(event["attempt_id"])
        for key in ("wait_ms", "input_tokens", "output_tokens", "cached_input_tokens", "context_bytes"):
            self.assertIsNone(event[key])
        self.assertIsInstance(event["duration_ms"], int)
        self.assertFalse(isinstance(event["duration_ms"], bool))
        self.assertGreaterEqual(event["duration_ms"], 0)

        started = datetime.fromisoformat(event["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(event["completed_at"].replace("Z", "+00:00"))
        self.assertEqual(timezone.utc, started.tzinfo)
        self.assertEqual(timezone.utc, completed.tzinfo)
        self.assertLessEqual(started, completed)

    def test_failed_validation_writes_no_runtime_observation(self) -> None:
        fixture = self._fixture()
        prior = self._seed_metrics(fixture)
        original = fixture.run_path.read_bytes()
        stderr = io.StringIO()

        def reject_validation(*_args, **_kwargs):
            return ["forced validation failure"]

        with unittest.mock.patch.object(
            harness_transition,
            "validate_current_plan_run",
            side_effect=reject_validation,
        ), contextlib.redirect_stderr(stderr):
            result = harness_transition.main(self._pause_argv(fixture))

        self.assertEqual(2, result)
        self.assertIn("forced validation failure", stderr.getvalue())
        self.assertEqual(original, fixture.run_path.read_bytes())
        self.assertEqual(
            prior, harness_transition.load_run(fixture.run_path)["runtime_metrics"]
        )

    def test_commit_boundary_race_preserves_competition_without_new_event(self) -> None:
        fixture = self._fixture()
        prior = self._seed_metrics(fixture)
        competing_run = copy.deepcopy(fixture.run)
        harness_transition._control(competing_run, "paused", "competing writer")
        self.assertEqual(
            [], harness_transition.validate_current_plan_run(
                fixture.plan, competing_run, repo_root=fixture.root
            )
        )
        competing = mf.manifest_markdown(
            "## Harness Run State", "harness_run", competing_run
        )

        def replace_at_commit_boundary(path: Path) -> None:
            path.write_text(competing, encoding="utf-8", newline="\n")

        stderr = io.StringIO()
        with unittest.mock.patch.object(
            harness_transition,
            "_run_replace_commit_boundary",
            side_effect=replace_at_commit_boundary,
        ), contextlib.redirect_stderr(stderr):
            result = harness_transition.main(self._pause_argv(fixture))

        self.assertEqual(2, result)
        self.assertIn("commit boundary", stderr.getvalue())
        self.assertEqual(competing.encode("utf-8"), fixture.run_path.read_bytes())
        self.assertEqual(
            prior, harness_transition.load_run(fixture.run_path)["runtime_metrics"]
        )

    def test_null_metrics_are_initialized_only_on_successful_mutation(self) -> None:
        fixture = self._fixture()
        self.assertIsNone(fixture.run.get("runtime_metrics"))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, harness_transition.main(self._pause_argv(fixture)))
        metrics = harness_transition.load_run(fixture.run_path)["runtime_metrics"]
        self.assertEqual(1, len(metrics["events"]))
        for key in ("baseline_wall_time_ms", "run_wall_time_ms", "critical_path_ms"):
            self.assertIsNone(metrics[key])

    def test_malformed_existing_metrics_are_not_silently_repaired(self) -> None:
        fixture = self._fixture()
        fixture.run["runtime_metrics"] = {**_metrics(), "events": None}
        fixture.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", fixture.run), encoding="utf-8"
        )
        before = fixture.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, harness_transition.main(self._pause_argv(fixture)))
        self.assertEqual(before, fixture.run_path.read_bytes())

    def test_report_only_watchdog_does_not_mutate_observations(self) -> None:
        fixture = self._fixture()
        prior = self._seed_metrics(fixture)
        original = fixture.run_path.read_bytes()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            result = harness_transition.main([
                "--plan", str(fixture.plan_path),
                "--run", str(fixture.run_path),
                "--repo-root", str(fixture.root),
                "watchdog",
            ])

        self.assertEqual(0, result)
        self.assertEqual(original, fixture.run_path.read_bytes())
        self.assertEqual(
            prior, harness_transition.load_run(fixture.run_path)["runtime_metrics"]
        )


class RuntimeObservationSummaryTests(unittest.TestCase):
    def test_null_runtime_metrics_keep_verifier_timings_without_wall_inference(self) -> None:
        run = {"runtime_metrics": None, "verifier_executions": [
            {"verifier_id": "V-1", "execution_key": "key-1", "timings": {"end_to_end_ms": 20}},
            {"verifier_id": "V-2", "execution_key": "key-2", "timings": {"end_to_end_ms": 30}},
        ]}
        before = copy.deepcopy(run)
        summary = inspect_harness_run.summarize_run(Path.cwd(), run)
        self.assertIsNone(summary["runtime_metrics"]["run_wall_time_ms"])
        self.assertIsNone(summary["runtime_metrics"]["critical_path_ms"])
        self.assertEqual([], summary["runtime_metrics"]["phase_events"])
        self.assertEqual(2, len(summary["verifier_timings"]))
        self.assertIn("run_wall=unknown", inspect_harness_run.render_text(summary))
        self.assertEqual(before, run)
        summary["verifier_timings"][0]["timings"]["end_to_end_ms"] = 99
        self.assertEqual(before, run)

    def test_phase_unknowns_and_observed_zero_remain_distinct(self) -> None:
        unknown = {**_event("unknown"), "duration_ms": None}
        zero = {**_event("zero"), "phase": "transition_prepare:resume", "duration_ms": 0}
        run = {"runtime_metrics": {**_metrics(), "events": [unknown, zero]}}
        before = copy.deepcopy(run)
        summary = inspect_harness_run.summarize_run(Path.cwd(), run)
        phases = {row["phase"]: row for row in summary["runtime_metrics"]["phase_events"]}
        self.assertIsNone(phases[unknown["phase"]]["measured_duration_ms"])
        self.assertEqual(1, phases[unknown["phase"]]["unknown_duration_count"])
        self.assertEqual(0, phases[zero["phase"]]["measured_duration_ms"])
        self.assertEqual(0, phases[zero["phase"]]["unknown_duration_count"])
        self.assertIsNone(summary["runtime_metrics"]["run_wall_time_ms"])
        self.assertEqual(before, run)

    def test_phase_sums_do_not_replace_explicit_run_measurements(self) -> None:
        run = {"runtime_metrics": {**_metrics(), "run_wall_time_ms": 42,
                                   "events": [_event("one"), _event("two")]}}
        summary = inspect_harness_run.summarize_run(Path.cwd(), run)["runtime_metrics"]
        self.assertEqual(2000, summary["phase_events"][0]["measured_duration_ms"])
        self.assertEqual(42, summary["run_wall_time_ms"])
        self.assertIsNone(summary["critical_path_ms"])


if __name__ == "__main__":
    unittest.main()
