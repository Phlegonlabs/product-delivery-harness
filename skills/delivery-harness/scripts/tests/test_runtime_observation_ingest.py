"""Observed host intervals cannot change execution or approval state."""

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import harness_transition as ht
from harness_manifest import load_run, plan_digest, validate_run
from manifest_fixtures import manifest_markdown
from runtime_observations import append_observation, load_observation
from test_role_dispatch_integration import launch_arguments, mission_reservation


class RuntimeObservationIngestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.plan, self.run, _ = mission_reservation()
        ht._record_launch_observation(self.plan, self.run, launch_arguments())
        ht._acquire_run_lock(self.run, SimpleNamespace(session_id="parent-P", owner=None))
        self.plan_path, self.run_path = self.root / "PLAN.md", self.root / "RUN.md"
        self.plan_path.write_text(manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan), encoding="utf-8")
        self.save()
        self.observation = self.root / "observation.json"
        self.request = {
            "schema": "runtime-observation/1", "run_id": self.run["run_id"],
            "assignment_kind": "mission", "assignment_id": "lease-1", "node_id": "N-M1",
            "attempt_id": "attempt-1", "worker_id": "worker-1", "sample_id": "terminal-1",
            "phase": "dispatch_to_terminal", "status": "complete",
            "started_at": "2026-10-18T10:00:00Z", "completed_at": "2026-10-18T10:01:00Z",
            "duration_ms": 60000, "wait_ms": None, "input_tokens": None,
            "output_tokens": None, "cached_input_tokens": None, "context_bytes": None,
        }

    def save(self):
        self.run_path.write_text(manifest_markdown("## Harness Run State", "harness_run", self.run), encoding="utf-8")

    def call(self, request=None, parent="parent-P", validate=None):
        self.observation.write_text(json.dumps(self.request if request is None else request), encoding="utf-8")
        arguments = ["--plan", str(self.plan_path), "--run", str(self.run_path),
                     "--repo-root", str(self.root), "--session-id", parent,
                     "record-runtime-observation", "--observation", str(self.observation)]
        # Synthetic reservations isolate transaction behavior from live Git and
        # product joins; the complete RUN validator still checks the resulting state.
        validate = validate or (lambda plan, run, **kw: validate_run(plan, run))
        output, error = io.StringIO(), io.StringIO()
        with patch.object(ht, "validate_current_plan_run", side_effect=validate), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = ht.main(arguments)
        return code, output.getvalue(), error.getvalue()

    def test_public_cli_records_observation_without_advancing_work(self):
        original = copy.deepcopy(self.run)
        code, output, error = self.call()
        self.assertEqual(0, code, error)
        self.assertTrue(json.loads(output)["recorded"])
        observed = load_run(self.run_path)
        self.assertEqual(original["workers"], observed["workers"])
        self.assertEqual(original["graph_state"], observed["graph_state"])
        self.assertEqual(original["control"], observed["control"])
        event = observed["runtime_metrics"]["events"][0]
        self.assertEqual("claude_code", event["provider"])
        self.assertEqual(60000, event["duration_ms"])
        self.assertIsNone(event["wait_ms"])
        self.assertIsNone(observed["runtime_metrics"]["run_wall_time_ms"])
        self.assertIsNone(observed["runtime_metrics"]["critical_path_ms"])
        self.assertEqual([], validate_run(self.plan, observed))

    def test_identical_replay_is_byte_identical_even_with_equivalent_timezone(self):
        self.assertEqual(0, self.call()[0])
        before = self.run_path.read_bytes()
        request = dict(self.request, started_at="2026-10-18T03:00:00-07:00",
                       completed_at="2026-10-18T03:01:00-07:00")
        code, output, error = self.call(request)
        self.assertEqual(0, code, error)
        self.assertFalse(json.loads(output)["recorded"])
        self.assertEqual(before, self.run_path.read_bytes())

    def test_conflicting_replay_fails_without_writing(self):
        self.assertEqual(0, self.call()[0])
        before = self.run_path.read_bytes()
        code, _, error = self.call(dict(self.request, duration_ms=1))
        self.assertEqual(2, code)
        self.assertIn("conflicts", error)
        self.assertEqual(before, self.run_path.read_bytes())

    def test_backoff_without_launch_uses_reserved_provider(self):
        self.run["launch_records"] = []
        self.save()
        request = dict(self.request, phase="retry_backoff", sample_id="backoff-1", status="failed")
        self.assertEqual(0, self.call(request)[0])
        self.assertEqual("claude_code", load_run(self.run_path)["runtime_metrics"]["events"][0]["provider"])
        before = self.run_path.read_bytes()
        self.assertEqual(2, self.call()[0])
        self.assertEqual(before, self.run_path.read_bytes())

    def test_terminal_reservation_still_accepts_observed_interval(self):
        # This checks historical assignment lookup, not a fabricated result PASS.
        self.run["workers"][0]["phase"] = "worker_failed"
        self.assertTrue(append_observation(self.plan, self.run, self.request)["recorded"])

    def test_missing_or_foreign_lock_and_wrong_identity_do_not_write(self):
        for field in ("run_id", "assignment_id", "node_id", "attempt_id", "worker_id"):
            with self.subTest(field=field):
                before = self.run_path.read_bytes()
                self.assertEqual(2, self.call(dict(self.request, **{field: "wrong"}))[0])
                self.assertEqual(before, self.run_path.read_bytes())
        before = self.run_path.read_bytes()
        self.assertEqual(2, self.call(parent="foreign")[0])
        self.assertEqual(before, self.run_path.read_bytes())
        self.run.pop("run_lock")
        self.save()
        before = self.run_path.read_bytes()
        self.assertEqual(2, self.call()[0])
        self.assertEqual(before, self.run_path.read_bytes())

    def test_paused_and_cancelled_control_are_preserved(self):
        for state in ("paused", "cancelled"):
            with self.subTest(state=state):
                ht._control(self.run, state, "owner decision")
                self.save()
                before = copy.deepcopy(self.run["control"])
                self.assertEqual(0, self.call(dict(self.request, sample_id=state))[0])
                self.assertEqual(before, load_run(self.run_path)["control"])

    def test_closed_run_is_rejected(self):
        self.run["status"] = "complete"
        before = copy.deepcopy(self.run)
        with self.assertRaisesRegex(ht.ManifestError, "closed RUN"):
            append_observation(self.plan, self.run, self.request)
        self.assertEqual(before, self.run)

    def test_invalid_observation_fields_fail_without_writing(self):
        mutations = [("phase", "queue_estimate"), ("status", "running"), ("duration_ms", True),
                     ("duration_ms", -1), ("sample_id", "prompt body"), ("wait_ms", 1.5),
                     ("started_at", "2026-10-18T10:00:00"), ("completed_at", "2026-10-18T09:59:00Z"),
                     ("completed_at", "0001-01-01T00:00:00+14:00"), ("provider", "forged"),
                     ("critical_path_ms", 1)]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                before = self.run_path.read_bytes()
                self.assertEqual(2, self.call(dict(self.request, **{field: value}))[0])
                self.assertEqual(before, self.run_path.read_bytes())
        self.assertEqual(2, self.call(dict(self.request, input_tokens=1, cached_input_tokens=2))[0])

    def test_reader_rejects_duplicate_json_keys_large_and_invalid_utf8(self):
        for raw in (b'{"schema":1,"schema":2}', b' ' * 65537, b'\xff'):
            self.observation.write_bytes(raw)
            with self.assertRaises(ht.ManifestError):
                load_observation(self.observation)

    def test_reader_rejects_link_input(self):
        self.observation.write_text(json.dumps(self.request), encoding="utf-8")
        link = self.root / "link.json"
        try:
            link.symlink_to(self.observation)
        except OSError:
            self.skipTest("this host cannot create file symlinks")
        with self.assertRaises(ht.ManifestError):
            load_observation(link)

    def test_validation_failure_and_plan_drift_preserve_run_bytes(self):
        before = self.run_path.read_bytes()
        self.assertEqual(2, self.call(validate=lambda *_a, **_kw: ["source is stale"])[0])
        self.assertEqual(before, self.run_path.read_bytes())

        def change_plan(plan, run, **_kw):
            self.plan_path.write_text(self.plan_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            return validate_run(plan, run)

        self.assertEqual(2, self.call(validate=change_plan)[0])
        self.assertEqual(before, self.run_path.read_bytes())

    def test_review_reservation_uses_its_actual_launch(self):
        import test_security_review_result as security_fixture
        from agent_role_bindings import resolve_runtime_binding
        from role_contract_fixtures import native_reviewer_binding

        fixture = security_fixture.SecurityReviewTransitionTests()
        self.addCleanup(fixture.doCleanups)
        plan, run = fixture.state()
        node = next(node for node in plan["graph"]["nodes"] if node["id"] == "N-SECURITY-REVIEW")
        node["runtime"]["worker_role"] = "reviewer"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["version_gate"]["required_harness_version"] = "0.58.0"
        adapter["role_bindings"] = {"reviewer": dict(native_reviewer_binding(), model_provider="generic", model="review-model")}
        run["plan"]["digest_sha256"] = plan_digest(plan)
        worker = run["review_workers"][0]
        worker["runtime_binding"] = resolve_runtime_binding(node, run["runtime_capabilities"])
        ht._record_launch_observation(plan, run, SimpleNamespace(
            assignment_kind="review", assignment_id=node["id"], node_id=node["id"],
            worker_id=worker["worker_id"], attempt_id=worker["attempt_id"], model_provider="generic",
            model="review-model", reasoning_effort="xhigh", worker_session_id="review-session",
            launch_observation="host launch", host_observation="parent readback", fallback_record=None))
        request = dict(self.request, run_id=run["run_id"], assignment_kind="review", assignment_id=node["id"],
                       node_id=node["id"], worker_id=worker["worker_id"], attempt_id=worker["attempt_id"])
        self.assertEqual("generic", append_observation(plan, run, request)["event"]["provider"])


if __name__ == "__main__":
    unittest.main()
