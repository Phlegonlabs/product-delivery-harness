"""Adoption preserves real recovered S3 and exact-head S4 review history."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
for directory in (TESTS_DIR, TESTS_DIR.parent):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import worker_ingestion_fixture as fixture  # noqa: E402
import harness_transition as ht  # noqa: E402
from harness_core import ManifestError  # noqa: E402
from harness_manifest import load_run, validate_current_plan_run, preintegration_review_errors  # noqa: E402
from harness_contract import contract_adoption_check_errors  # noqa: E402


class RuntimeContractQuiescenceTests(unittest.TestCase):
    def test_recovered_worker_and_real_review_receipt_allow_only_quiet_adoption(self):
        fx = fixture.build_original_failure()
        self.addCleanup(fx.temp.cleanup)
        self.addCleanup(fx.skills_temp.cleanup)
        fixture.prepare_recovery(fx)
        fixture._command(fx, "reconcile-worker-ingestion", *fixture.recovery_flags(fx))
        fixture._command(fx, "reserve-review-dispatch", "--node-id", "N-REVIEW-M1",
                         "--worker-id", "RW-S4", "--attempt-id", "RA-S4")
        reserved = load_run(fx.run_path)
        review = next(row for row in reserved["review_workers"] if row["worker_id"] == "RW-S4")
        binding = review["runtime_binding"]
        fixture._command(fx, "record-launch-observation", "--assignment-kind", "review",
                         "--assignment-id", "N-REVIEW-M1", "--node-id", "N-REVIEW-M1",
                         "--worker-id", "RW-S4", "--attempt-id", "RA-S4",
                         "--model-provider", binding["model_provider"], "--model", binding["model"] or "synthetic-review-model",
                         "--reasoning-effort", binding["reasoning_effort"] or "xhigh",
                         "--worker-session-id", "synthetic-review-s4",
                         "--launch-observation", "synthetic terminal review fixture; no real model call",
                         "--host-observation", "test-owned returned review source")
        check = {"digest": fx.digest_s4, "matched": True,
                 "reading_evidence": ["Synthetic S4 reviewer reads its fixed fixture contract."]}
        check_path = fixture._write_json(fx.evidence / "review-check.json", check)
        payload = {"outcome": "pass", "findings": [], "security_result": None,
                   "contract_adoption_check": check}
        receipt_path = fixture._receipt_files(fx, payload, "synthetic-review-s4", "review-s4")
        reserved = load_run(fx.run_path)
        review_arguments = ["--lineage", "REVIEW-M1", "--attempt-id", "RA-S4",
                            "--worker-id", "RW-S4", "--mission-id", "M1", "--result", "pass",
                            "--evidence", "synthetic exact-head review fixture",
                            "--contract-adoption-check", str(check_path), "--result-receipt", str(receipt_path)]
        fixture._command(fx, "record-review-attempt", *review_arguments)
        before = load_run(fx.run_path)
        self.assertEqual([], validate_current_plan_run(fx.plan, before, repo_root=fx.root))
        self.assertEqual([], preintegration_review_errors(fx.plan, before, "M1"))
        self.assertEqual("running", before["graph_state"]["node_states"]["N-M1"]["phase"])
        self.assertEqual("worker_passed", before["workers"][-1]["phase"])
        self.assertEqual("worker_passed", before["review_workers"][-1]["phase"])
        baseline = fx.run_path.read_bytes()
        source_paths = [fx.original_run_path, fx.node_path, fx.report_path, fx.receipt_path, receipt_path, check_path,
                        *fx.verifier_paths]
        for receipt_file in (fx.receipt_path, receipt_path):
            source_paths.append(Path(json.loads(receipt_file.read_text(encoding="utf-8"))["source_ref"]))
        source_bytes = {path: path.read_bytes() for path in source_paths}
        adopted_digest = "d" * 64
        arguments = ["--plan", str(fx.plan_path), "--run", str(fx.run_path), "--repo-root", str(fx.root),
                     "--session-id", "parent-session", "adopt-runtime-contract",
                     "--owner-source", "synthetic owner approved exact replacement digest",
                     "--reading-evidence", "terminal source refs: host-session-2 and synthetic-review-s4; owned command trees exited",
                     "--expected-contract-digest", adopted_digest]

        mutations = {
            "active wave": lambda r: r["active_wave"].update(status="active"),
            "proposed wave": lambda r: r["active_wave"].update(status="proposed"),
            "live worker": lambda r: r["workers"][-1].update(phase="worker_running"),
            "leased worker": lambda r: r["workers"][-1].update(phase="leased"),
            "live reviewer": lambda r: r["review_workers"][-1].update(phase="worker_running"),
            "leased reviewer": lambda r: r["review_workers"][-1].update(phase="leased"),
            "reserved node": lambda r: r["attempt_log"].append({"attempt_id": "RESERVED", "kind": "node_attempt", "result": "reserved"}),
            "other running node": lambda r: r["graph_state"]["node_states"]["N-REVIEW-M1"].update(phase="running"),
            "worker mismatch": lambda r: r["mission_states"]["M1"].update(worker_id="wrong"),
            "lease mismatch": lambda r: r["mission_states"]["M1"].update(lease_id="wrong"),
            "attempt mismatch": lambda r: r["graph_state"]["node_states"]["N-M1"].update(last_attempt_id="wrong"),
            "head mismatch": lambda r: r["workers"][-1].update(worker_head_sha="f" * 40),
            "failed mission": lambda r: r["mission_states"]["M1"].update(phase="worker_failed"),
            "missing review": lambda r: r.update(review_workers=[]),
            "stale review": lambda r: r["review_workers"][-1].update(reviewed_sha="f" * 40),
            "failed review": lambda r: r["review_workers"][-1].update(outcome="fix_required"),
            "review findings": lambda r: r["review_workers"][-1].update(findings=["blocking finding"]),
            "review attempt": lambda r: r["graph_state"]["node_states"]["N-REVIEW-M1"].update(last_attempt_id="wrong"),
            "review graph": lambda r: r["review_workers"][-1].update(graph_revision=999),
            "missing worker receipt": lambda r: r["workers"][-1].pop("result_receipt"),
            "missing review receipt": lambda r: r["review_workers"][-1].pop("result_receipt"),
            "missing launch": lambda r: r.update(launch_records=[]),
            "missing verifier": lambda r: r.update(verifier_executions=[]),
            "known loaded identity": lambda r: r["runtime_capabilities"]["runtime_adapter"]["version_gate"].update(loaded_contract_digest="a" * 64),
            "restart required": lambda r: r["runtime_capabilities"]["runtime_adapter"]["version_gate"].update(status="restart_required"),
            "version mismatch": lambda r: r["runtime_capabilities"]["runtime_adapter"]["version_gate"].update(required_harness_version="999.0.0"),
            "foreign lock": lambda r: r["run_lock"].update(session_id="another-parent"),
            "complete": lambda r: r.update(status="complete"),
            "cancelled": lambda r: r["control"].update(desired_state="cancelled"),
        }
        with patch.object(ht, "contract_digest", return_value=adopted_digest):
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    changed = copy.deepcopy(before); mutate(changed)
                    fx.run_path.write_text(fixture.mf.manifest_markdown("## Harness Run State", "harness_run", changed), encoding="utf-8")
                    unchanged = fx.run_path.read_bytes()
                    self.assertEqual(2, ht.main(arguments))
                    self.assertEqual(unchanged, fx.run_path.read_bytes())
            fx.run_path.write_bytes(baseline)
            for omitted in ("--owner-source", "--reading-evidence"):
                missing = list(arguments); at = missing.index(omitted); del missing[at:at+2]
                with self.assertRaises(SystemExit) as stopped:
                    ht.main(missing)
                self.assertEqual(2, stopped.exception.code)
                self.assertEqual(baseline, fx.run_path.read_bytes())
            wrong = list(arguments); wrong[-1] = "e" * 64
            self.assertEqual(2, ht.main(wrong))
            self.assertEqual(baseline, fx.run_path.read_bytes())
            self.assertEqual(0, ht.main(arguments))
            after = load_run(fx.run_path)
            after_bytes = fx.run_path.read_bytes()
            self.assertEqual(2, ht.main(arguments))
            self.assertEqual(after_bytes, fx.run_path.read_bytes())
        self.assertEqual([], validate_current_plan_run(fx.plan, after, repo_root=fx.root))
        for key in ("workers", "review_workers", "graph_state", "task_states", "mission_states", "integration", "authorizations", "active_wave", "closed_waves", "verifier_executions", "launch_records"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(before["attempt_log"], after["attempt_log"][:-1])
        self.assertIn(f"integration_pending mission=M1 node=N-M1 head={fx.head}", after["attempt_log"][-1]["evidence"])
        old_gate = before["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        new_gate = after["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        self.assertEqual([*old_gate["contract_adoption_history"], old_gate["contract_adoption"]], new_gate["contract_adoption_history"])
        for path, raw in source_bytes.items():
            self.assertEqual(raw, path.read_bytes(), path.name)
        self.assertTrue(contract_adoption_check_errors(after, fx.worker_result["contract_adoption_check"]))
        self.assertTrue(contract_adoption_check_errors(after, check))
        # Exercise fresh recording's unchanged digest guard with its real reserved
        # review fixture. This is an isolated validator input, not a RUN adoption.
        fresh = copy.deepcopy(reserved)
        fresh["runtime_capabilities"]["runtime_adapter"]["version_gate"] = copy.deepcopy(new_gate)
        parsed = ht.build_parser().parse_args(["--plan", str(fx.plan_path), "--run", str(fx.run_path),
                                              "--repo-root", str(fx.root), "record-review-attempt", *review_arguments])
        with self.assertRaisesRegex(ManifestError, "adoption|digest"):
            ht._record_review_attempt(fx.plan, fresh, parsed)
        self.assertEqual(reserved["review_workers"][-1]["phase"], fresh["review_workers"][-1]["phase"])
        # Role-policy changes retain their stricter, separate quiet boundary.
        from agent_role_policy_updates import update_role_bindings, policy_digest
        roles = before["runtime_capabilities"]["runtime_adapter"]["role_bindings"]
        policy_path = fixture._write_json(fx.evidence / "unchanged-role-policy.json", roles)
        with self.assertRaisesRegex(ManifestError, "quiescent|running|quiet"):
            update_role_bindings(fx.plan, copy.deepcopy(before), type("Args", (), {
                "repo_root": fx.root, "session_id": "parent-session", "owner_source": "owner",
                "policy": policy_path, "expected_role_bindings_sha256": policy_digest(roles),
                "update_id": "blocked-running-mission",
            })())
        duplicate_plan = copy.deepcopy(fx.plan)
        duplicate_plan["graph"]["nodes"].append(copy.deepcopy(next(node for node in fx.plan["graph"]["nodes"] if node["id"] == "N-M1")))
        self.assertIsNone(ht._quiescent_integration_pending(duplicate_plan, before, "N-M1"))


if __name__ == "__main__":
    unittest.main()
