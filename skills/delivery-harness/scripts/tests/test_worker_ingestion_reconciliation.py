#!/usr/bin/env python3
"""Focused tests for guarded stale-head result reconciliation."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for entry in (str(TESTS_DIR), str(SCRIPTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import worker_ingestion_fixture as fixture
import harness_transition
from harness_core import ManifestError
from harness_manifest import load_run, validate_current_plan_run
from harness_contract import contract_adoption_check_errors
from harness_worker_ingestion_proof import KIND, validate_reconciliation


class WorkerIngestionReconciliationTests(unittest.TestCase):
    def test_real_original_ingestion_is_rejected_with_sole_diagnostic(self):
        fx = fixture.build_original_failure()
        self.addCleanup(fx.temp.cleanup)
        self.addCleanup(fx.skills_temp.cleanup)
        state = fx.run["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("failed", state["phase"])
        self.assertEqual("retryable_failure", state["last_outcome"])
        self.assertEqual(2, state["attempts"])
        self.assertEqual("A-M01-002", state["last_attempt_id"])
        self.assertEqual("worker_failed", fx.run["mission_states"]["M1"]["phase"])
        self.assertEqual(3, len(fx.verifier_paths))
        self.assertEqual(fx.head, fx.worker_result["head_sha"])

    def test_real_closed_wave_recovery_after_contract_adoption(self):
        fx = fixture.build_original_failure()
        self.addCleanup(fx.temp.cleanup)
        self.addCleanup(fx.skills_temp.cleanup)
        before = fixture.prepare_recovery(fx)
        run_bytes = fx.run_path.read_bytes()
        tasks_path = fx.root / "docs/tasks.md"
        tasks_bytes = tasks_path.read_bytes()
        flags = fixture.recovery_flags(fx)

        def invoke():
            return fixture.transition(
                "--plan", str(fx.plan_path), "--run", str(fx.run_path),
                "--repo-root", str(fx.root), "--session-id", "parent-session",
                "reconcile-worker-ingestion", *flags, script=fx.active_script)

        # Each mutation is isolated. Refusal must leave both canonical files
        # byte-identical to the inputs, including the invalid supplied RUN.
        mutations = {
            "extra blocker": lambda r: r["mission_states"]["M1"]["blockers"].append("another failure"),
            "replacement wave": lambda r: r["active_wave"].update(wave_id="WAVE-OTHER"),
            "new lease": lambda r: r["workers"][-1].update(lease_id="L-NEW"),
            "new plan": lambda r: r["plan"].update(revision=99),
            "new base": lambda r: r["workers"][-1].update(batch_base_sha=fx.head),
            "new attempt": lambda r: r["graph_state"]["node_states"]["N-M1"].update(last_attempt_id="A-NEW"),
            "no receipt": lambda r: r["workers"][-1].pop("result_receipt"),
            "legacy": lambda r: r.update(schema_version=10),
            "unrelated adoption": lambda r: r["runtime_capabilities"]["runtime_adapter"]["version_gate"]
                ["contract_adoption_history"][0].update(owner_source="unrelated receipt"),
            "reserved reviewer": lambda r: r["review_workers"].append({"phase": "leased"}),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(before)
                mutate(changed)
                fx.run_path.write_text(fixture.mf.manifest_markdown(
                    "## Harness Run State", "harness_run", changed), encoding="utf-8")
                invalid_bytes = fx.run_path.read_bytes()
                result = invoke()
                self.assertNotEqual(0, result.returncode, result.stdout)
                self.assertEqual(invalid_bytes, fx.run_path.read_bytes())
                self.assertEqual(tasks_bytes, tasks_path.read_bytes())
                fx.run_path.write_bytes(run_bytes)

        for path, change in (
            (fx.original_run_path, lambda raw: raw + b"\nchanged original\n"),
            (fx.report_path, lambda raw: raw.replace(b"Synthetic docs fixture", b"Different docs fixture")),
            (fx.receipt_path, lambda raw: raw.replace(b"host-session-2", b"wrong-session")),
            (fx.node_path, lambda raw: raw.replace(b'"succeeded"', b'"failed"')),
            (fx.verifier_paths[0], lambda raw: raw.replace(b'"PASS"', b'"FAIL"')),
        ):
            with self.subTest(path=path.name):
                saved = path.read_bytes()
                path.write_bytes(change(saved))
                try:
                    result = invoke()
                    self.assertNotEqual(0, result.returncode, result.stdout)
                    self.assertEqual(run_bytes, fx.run_path.read_bytes())
                    self.assertEqual(tasks_bytes, tasks_path.read_bytes())
                finally:
                    path.write_bytes(saved)

        arguments = ["--plan", str(fx.plan_path), "--run", str(fx.run_path),
                     "--repo-root", str(fx.root), "--session-id", "parent-session",
                     "reconcile-worker-ingestion", *flags]
        plan_bytes = fx.plan_path.read_bytes()
        original_bytes = fx.original_run_path.read_bytes()
        real_ensure_plan = harness_transition._ensure_plan_unchanged
        real_replace = harness_transition._replace_run_document
        real_observe = harness_transition.verify_worker_observation

        def race_plan(path, expected):
            fx.plan_path.write_bytes(plan_bytes + b"\nconcurrent plan note\n")
            real_ensure_plan(path, expected)

        def race_run(path, run, **kwargs):
            fx.run_path.write_bytes(run_bytes + b"\nconcurrent run note\n")
            real_replace(path, run, **kwargs)

        def race_source(observed):
            real_observe(observed)
            fx.original_run_path.write_bytes(original_bytes + b"\nconcurrent source note\n")

        def race_branch(observed):
            real_observe(observed)
            fixture.mf.git(fx.worker_root, "checkout", "-q", "-b", "feature/m1-race")

        for label, target, replacement in (
            ("PLAN CAS", "_ensure_plan_unchanged", race_plan),
            ("RUN CAS", "_replace_run_document", race_run),
            ("source CAS", "verify_worker_observation", race_source),
            ("worker branch CAS", "verify_worker_observation", race_branch),
        ):
            with self.subTest(race=label):
                try:
                    parsed = harness_transition.build_parser().parse_args(arguments)
                    with patch.object(harness_transition, target, replacement):
                        with self.assertRaises(ManifestError):
                            harness_transition._transition_under_lock(
                                parsed, fx.plan, expected_plan_text=fx.plan_path.read_text(encoding="utf-8"))
                    expected_run = run_bytes + b"\nconcurrent run note\n" if label == "RUN CAS" else run_bytes
                    self.assertEqual(expected_run, fx.run_path.read_bytes())
                    self.assertEqual(tasks_bytes, tasks_path.read_bytes())
                    if label == "PLAN CAS":
                        self.assertEqual(plan_bytes + b"\nconcurrent plan note\n", fx.plan_path.read_bytes())
                    if label == "source CAS":
                        self.assertEqual(original_bytes + b"\nconcurrent source note\n", fx.original_run_path.read_bytes())
                finally:
                    fx.plan_path.write_bytes(plan_bytes)
                    fx.run_path.write_bytes(run_bytes)
                    fx.original_run_path.write_bytes(original_bytes)
                    fixture.mf.git(fx.worker_root, "checkout", "-q", "feature/m1")

        result = invoke()
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        after = load_run(fx.run_path)
        self.assertEqual([], validate_current_plan_run(fx.plan, after, repo_root=fx.root))
        state = after["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("running", state["phase"])
        self.assertIsNone(state["last_outcome"])
        self.assertEqual(2, state["attempts"])
        self.assertEqual("A-M01-002", state["last_attempt_id"])
        self.assertEqual("worker_passed", after["mission_states"]["M1"]["phase"])
        self.assertEqual(before["active_wave"], after["active_wave"])
        self.assertEqual(before["closed_waves"], after["closed_waves"])
        self.assertEqual(before["authorizations"], after["authorizations"])
        self.assertEqual(before["runtime_capabilities"], after["runtime_capabilities"])
        old_dispatch = next(row for row in before["attempt_log"] if row["attempt_id"] == "A-M01-002")
        self.assertIn(old_dispatch, after["attempt_log"])
        for task_id, state in before["task_states"].items():
            self.assertEqual(state["attempts"], after["task_states"][task_id]["attempts"])
        for task in fx.worker_result["task_results"]:
            self.assertEqual("mission_recorded", after["task_states"][task["task_id"]]["phase"])
        self.assertEqual(3, len(after["verifier_executions"]))
        audits = [row for row in after["attempt_log"] if row["kind"] == KIND]
        self.assertEqual(1, len(audits))
        self.assertEqual(fx.digest_s3, audits[0][KIND]["original_adoption"]["contract_digest_sha256"])
        self.assertEqual(fx.digest_s4, after["runtime_capabilities"]["runtime_adapter"]
                         ["version_gate"]["contract_adoption"]["contract_digest_sha256"])
        selection = fixture.cli(fx.skills_s4 / "delivery-harness/scripts/select_ready_nodes.py",
                                "--plan", str(fx.plan_path), "--run", str(fx.run_path),
                                "--repo-root", str(fx.root))
        self.assertEqual(0, selection.returncode, selection.stderr + selection.stdout)
        selected = json.loads(selection.stdout)
        directive = next(row for row in selected["dispatchable_nodes"]
                         if row.get("review", {}).get("mission_ids") == ["M1"])
        self.assertEqual(fx.digest_s4, directive["contract_adoption"]["contract_digest_sha256"])
        self.assertTrue(contract_adoption_check_errors(after, fx.worker_result["contract_adoption_check"]))
        # Audit fields are a machine contract, not an unchecked explanation.
        for key in ("head_sha", "failed_dispatch_sha256", "original_adoption_sha256", "launch_record_sha256"):
            changed = copy.deepcopy(after)
            audit = next(row for row in changed["attempt_log"] if row["kind"] == KIND)
            audit[KIND][key] = "0" * len(audit[KIND][key])
            self.assertTrue(validate_current_plan_run(fx.plan, changed, repo_root=fx.root), key)
        historical = copy.deepcopy(after)
        historical["mission_states"]["M1"].update(phase="integrated", integrated_sha=fx.head)
        historical["graph_state"]["node_states"]["N-M1"].update(phase="succeeded", last_outcome="pass")
        historical["run_lock"]["session_id"] = "a-later-parent-session"
        audit = next(row for row in historical["attempt_log"] if row["kind"] == KIND)
        self.assertEqual([], validate_reconciliation(fx.plan, historical, audit))
        accepted_bytes = fx.run_path.read_bytes()
        self.assertNotEqual(0, invoke().returncode)
        self.assertEqual(accepted_bytes, fx.run_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
