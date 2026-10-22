"""Real runner output enters mission integration in one guarded transaction."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for directory in (TESTS_DIR, SCRIPTS_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import harness_transition as ht  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
import test_close_wave as cw  # noqa: E402
from harness_core import plan_digest  # noqa: E402
from verifier_runtime import run_verifier  # noqa: E402


class IntegrationResultIngestionTests(unittest.TestCase):
    def setUp(self):
        # Compose setup only; importing or inheriting a TestCase repeats its tests.
        self.fixture = cw.CloseWaveCliTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        fixture = self.fixture
        self.plan = fixture.plan
        declaration = self.plan["missions"][0]["integration_verifiers"][0]
        declaration.update(argv=[sys.executable, "-c", "print('integration verifier executed')"],
                           read_only=True, execution={"isolation": "host", "parallel_safe": False,
                                                      "resources": []})
        second = copy.deepcopy(declaration)
        second["id"] += "-SECOND"
        self.plan["missions"][0]["integration_verifiers"].append(second)
        fixture.plan_path.write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan), encoding="utf-8")
        run = cw.load_run_block(fixture.run_path)
        digest = plan_digest(self.plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for authorization in run["authorizations"].values():
            if isinstance(authorization, dict) and isinstance(authorization.get("scope"), dict):
                authorization["scope"]["plan_digest_sha256"] = digest
        cw.save_run_block(fixture.run_path, run)
        observed = fixture.cli("--repo-root", str(fixture.gitroot), "record-observation")
        self.assertEqual(0, observed.returncode, observed.stderr)
        fixture._seed_sandbox_observation()
        fixture._integrate_m1(record=False, retain_integration=False)
        # RUN and its generated view are the exact protected coordination inputs.
        run = cw.load_run_block(fixture.run_path)
        fixture.run_path = fixture.gitroot / "RUN.md"
        fixture.run_path.write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
        self.run = run
        self.sources = []
        self.results = []
        context = {
            "run_id": run["run_id"], "plan_revision": self.plan["revision"],
            "plan_digest_sha256": digest, "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"], "head_sha": fixture.head,
            "changed_files": [], "trust_domain": "parent_local", "checkout_role": "integration",
            "checkout_dirty": False, "cache_safe": False, "layer": "mission_integration",
            "mission_id": "M1", "task_id": None, "attempt_id": None, "lease_id": None,
        }
        guard = {"expected_branch": "integration", "expected_head_sha": fixture.head,
                 "ignored_paths": sorted(ht._coordination_ignored_paths(fixture.gitroot, fixture.run_path, run))}
        preflight = run["observed"]["host_runtime"]["entries"][0]
        for index, declaration in enumerate(self.plan["missions"][0]["integration_verifiers"]):
            result = run_verifier(declaration, context, checkout_root=fixture.gitroot,
                                  timeout_seconds=15, git_guard=guard, host_preflight=preflight)
            self.assertEqual("PASS", result["status"], result["stderr"])
            self.assertIn("integration verifier executed", result["stdout"])
            path = fixture.root / f"integration-{index}.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            self.sources.append(path)
            self.results.append(result)

    def arguments(self, paths=None):
        fixture = self.fixture
        arguments = ["--plan", str(fixture.plan_path), "--run", str(fixture.run_path),
                     "--repo-root", str(fixture.gitroot), "--session-id", cw.SESSION,
                     "record-integration", "--mission-id", "M1", "--integrated-sha", fixture.head]
        for path in self.sources if paths is None else paths:
            arguments += ["--verifier-result", str(path)]
        return arguments

    def assert_rejected(self, paths=None):
        before = self.fixture.run_path.read_bytes()
        self.assertEqual(2, ht.main(self.arguments(paths)))
        self.assertEqual(before, self.fixture.run_path.read_bytes())

    def test_actual_results_are_retained_with_integration_and_repeat_is_rejected(self):
        self.sources[1].write_text(json.dumps({"verifier_execution": self.results[1]}), encoding="utf-8")
        self.assertEqual(0, ht.main(self.arguments()))
        run = cw.load_run_block(self.fixture.run_path)
        self.assertEqual("integrated", run["mission_states"]["M1"]["phase"])
        self.assertEqual("PASS", run["mission_states"]["M1"]["integration_gate"])
        self.assertEqual("succeeded", run["graph_state"]["node_states"]["N-M1"]["phase"])
        retained = [row for row in run["verifier_executions"] if row["layer"] == "mission_integration"]
        self.assertEqual(2, len(retained))
        self.assertEqual([str(path) for path in self.sources], [row["evidence_paths"][0] for row in retained])
        self.assert_rejected()

    def test_missing_coverage_duplicate_and_replay_preserve_run(self):
        self.assert_rejected(self.sources[:1])
        self.assert_rejected([self.sources[0], self.sources[0], self.sources[1]])
        run = cw.load_run_block(self.fixture.run_path)
        from harness_worker_result_transition import _retained_execution
        record = _retained_execution(run, self.results[0], [str(self.sources[0])])
        run["verifier_executions"].append(record)
        cw.save_run_block(self.fixture.run_path, run)
        # Re-execute after RUN changes; actual output retains its execution key.
        self._refresh_results()
        self.assert_rejected()
        # Omit the already retained proof and use the valid union.
        self.assertEqual(0, ht.main(self.arguments(self.sources[1:])))

    def test_tampered_protocol_context_output_policy_and_guard_are_rejected(self):
        mutations = [
            ("protocol", "harness-verifier-execution-v1"), ("verifier_id", "unknown"),
            ("stdout", None), ("stderr", None), ("status", "FAIL"), ("exit_code", True),
            ("cache_status", "reused"), ("metrics", {"executed": 0, "reused": 1}),
            ("reservation", {}), ("dispatch_attestation", {}), ("container_reuse_origin", {}),
            ("timings", None), ("git_guard_attestation", {}),
        ]
        for field, value in mutations:
            with self.subTest(field=field):
                result = copy.deepcopy(self.results[0]); result[field] = value
                self.sources[0].write_text(json.dumps(result), encoding="utf-8")
                self.assert_rejected()
        for declaration in [self.plan["missions"][0]["worker_verifiers"][0],
                            self.plan["missions"][0]["tasks"][0]["verifiers"][0],
                            self.plan["batch_verifiers"][0], self.plan["final_gates"][0]]:
            with self.subTest(other_route=declaration["id"]):
                result = copy.deepcopy(self.results[0]); result["verifier_id"] = declaration["id"]
                self.sources[0].write_text(json.dumps(result), encoding="utf-8")
                self.assert_rejected()
        for field, value in {
            "run_id": "other", "plan_revision": 999, "plan_digest_sha256": "f" * 64,
            "graph_revision": 999, "batch_base_sha": "f" * 40, "head_sha": "f" * 40,
            "changed_files": ["unreported.py"], "trust_domain": "worker", "checkout_role": "worker",
            "checkout_dirty": True, "cache_safe": True, "layer": "worker", "mission_id": "M2",
            "task_id": "M1/T01", "attempt_id": "A", "lease_id": "L",
        }.items():
            with self.subTest(context=field):
                result = copy.deepcopy(self.results[0]); result["context"][field] = value
                self.sources[0].write_text(json.dumps(result), encoding="utf-8")
                self.assert_rejected()
        for field, value in {
            "checkout_root": str(self.fixture.root), "source_head_sha": "f" * 40,
            "isolation_mode": "container", "tracked_files": {}, "protected_path_sha256": {},
            "protected_path_stats": {}, "git_guard": {"expected_branch": "wrong"},
            "host_execution_attestation": {},
        }.items():
            with self.subTest(guard=field):
                result = copy.deepcopy(self.results[0]); result["git_guard_attestation"][field] = value
                self.sources[0].write_text(json.dumps(result), encoding="utf-8")
                self.assert_rejected()
        for group, field, value in [("verifier", "argv", ["false"]), ("key_document", "host_preflight", {}),
                                    ("key_document", "execution", {}), ("host_execution_attestation", "executable_sha256", "f" * 64)]:
            with self.subTest(group=group, field=field):
                result = copy.deepcopy(self.results[0]); result[group][field] = value
                self.sources[0].write_text(json.dumps(result), encoding="utf-8")
                self.assert_rejected()

    def test_late_source_git_protected_and_plan_races_do_not_write_run(self):
        original_validation = ht.validate_current_plan_run
        for kind in ("source", "protected", "tasks", "tracked", "plan", "run_cas", "branch", "head"):
            with self.subTest(race=kind):
                baseline = self.fixture.run_path.read_bytes()
                original_file = (self.fixture.gitroot / "file.txt").read_bytes()
                original_plan = self.fixture.plan_path.read_bytes()
                def raced(*arguments, **kwargs):
                    errors = original_validation(*arguments, **kwargs)
                    if kind == "source":
                        self.sources[0].write_text(json.dumps(self.results[0]) + " ", encoding="utf-8")
                    elif kind == "protected":
                        self.fixture.run_path.write_bytes(baseline)
                    elif kind == "tracked":
                        (self.fixture.gitroot / "file.txt").write_bytes(original_file)
                    elif kind == "tasks":
                        view = self.fixture.gitroot / "docs/tasks.md"
                        view.write_bytes(view.read_bytes())
                    elif kind == "plan":
                        self.fixture.plan_path.write_bytes(original_plan + b"\n")
                    elif kind == "branch":
                        mf.git(self.fixture.gitroot, "checkout", "-qb", "late-branch")
                    elif kind == "head":
                        mf.git(self.fixture.gitroot, "commit", "--allow-empty", "-qm", "late head")
                    else:
                        self.fixture.run_path.write_bytes(baseline + b"\n")
                    return errors
                with mock.patch.object(ht, "validate_current_plan_run", side_effect=raced):
                    self.assertEqual(2, ht.main(self.arguments()))
                self.assertEqual(baseline + (b"\n" if kind == "run_cas" else b""), self.fixture.run_path.read_bytes())
                self.fixture.run_path.write_bytes(baseline)
                self.fixture.plan_path.write_bytes(original_plan)
                if kind == "branch":
                    mf.git(self.fixture.gitroot, "checkout", "-q", "integration")
                # Re-execute after restoring identities; no synthetic PASS replaces runner output.
                if kind != "head":
                    self._refresh_results()

    def test_commit_boundary_races_do_not_write_run(self):
        # The temporary RUN is already written here; only the recheck can stop the exchange.
        for kind in ("source", "tracked", "tasks", "plan", "branch", "head"):
            with self.subTest(race=kind):
                baseline = self.fixture.run_path.read_bytes()
                original_file = (self.fixture.gitroot / "file.txt").read_bytes()
                original_plan = self.fixture.plan_path.read_bytes()
                def raced(path):
                    if kind == "source":
                        self.sources[0].write_text(json.dumps(self.results[0]) + " ", encoding="utf-8")
                    elif kind == "tracked":
                        (self.fixture.gitroot / "file.txt").write_bytes(original_file)
                    elif kind == "tasks":
                        view = self.fixture.gitroot / "docs/tasks.md"
                        view.write_bytes(view.read_bytes())
                    elif kind == "plan":
                        self.fixture.plan_path.write_bytes(original_plan + b"\n")
                    elif kind == "branch":
                        mf.git(self.fixture.gitroot, "checkout", "-qb", "boundary-branch")
                    else:
                        mf.git(self.fixture.gitroot, "commit", "--allow-empty", "-qm", "boundary head")
                with mock.patch.object(ht, "_run_replace_commit_boundary", side_effect=raced):
                    self.assertEqual(2, ht.main(self.arguments()))
                self.assertEqual(baseline, self.fixture.run_path.read_bytes())
                self.fixture.plan_path.write_bytes(original_plan)
                if kind == "branch":
                    mf.git(self.fixture.gitroot, "checkout", "-q", "integration")
                if kind != "head":
                    self._refresh_results()

    def _refresh_results(self):
        run = cw.load_run_block(self.fixture.run_path)
        for index, declaration in enumerate(self.plan["missions"][0]["integration_verifiers"]):
            result = run_verifier(declaration, self.results[index]["context"], checkout_root=self.fixture.gitroot,
                                  timeout_seconds=15, git_guard=self.results[index]["git_guard_attestation"]["git_guard"],
                                  host_preflight=run["observed"]["host_runtime"]["entries"][0])
            self.assertEqual("PASS", result["status"], result["stderr"])
            self.results[index] = result
            self.sources[index].write_text(json.dumps(result), encoding="utf-8")

    def test_unsafe_result_files_and_dirty_or_wrong_branch_are_rejected(self):
        self.assert_rejected([Path("relative.json")])
        self.assert_rejected([self.fixture.root])
        inside = self.fixture.gitroot / "input.json"
        inside.write_text(json.dumps(self.results[0]), encoding="utf-8")
        self.assert_rejected([inside])
        # Dirty product files and branch drift reject before ingestion.
        mf.git(self.fixture.gitroot, "add", "input.json")
        self.assert_rejected()
        mf.git(self.fixture.gitroot, "checkout", "-qb", "other")
        self.assert_rejected()

    def test_failed_history_survives_a_later_real_pass(self):
        from harness_worker_result_transition import _retained_execution
        run = cw.load_run_block(self.fixture.run_path)
        failed = _retained_execution(run, self.results[0], ["historical failed execution fixture"])
        failed.update(status="FAIL", exit_code=1)
        run["verifier_executions"].append(failed)
        cw.save_run_block(self.fixture.run_path, run)
        self._refresh_results()
        self.assertEqual(0, ht.main(self.arguments()))
        after = cw.load_run_block(self.fixture.run_path)
        self.assertIn(failed, after["verifier_executions"])

    def test_merged_candidate_uses_parent_computed_changed_files(self):
        product = self.fixture.gitroot / "src/a/merge.py"
        product.parent.mkdir(parents=True)
        product.write_text("MERGED = True\n", encoding="utf-8")
        mf.git(self.fixture.gitroot, "add", "src/a/merge.py")
        mf.git(self.fixture.gitroot, "commit", "-qm", "integration candidate")
        self.fixture.head = mf.git(self.fixture.gitroot, "rev-parse", "HEAD")
        for result in self.results:
            result["context"].update(head_sha=self.fixture.head, changed_files=["src/a/merge.py"])
            result["git_guard_attestation"]["git_guard"]["expected_head_sha"] = self.fixture.head
        self._refresh_results()
        self.assertEqual(0, ht.main(self.arguments()))
        after = cw.load_run_block(self.fixture.run_path)
        self.assertEqual(self.fixture.head, after["mission_states"]["M1"]["integrated_sha"])
        self.assertNotEqual(self.fixture.head, after["mission_states"]["M1"]["head_sha"])

    def test_bounded_duplicate_and_nonfinite_json_are_rejected(self):
        for raw in ('{"verifier_id":"a","verifier_id":"b"}', '{"x": NaN}',
                    '{"x": 1e999}', '{"x": -1e999}', '[]'):
            with self.subTest(raw=raw):
                self.sources[0].write_text(raw, encoding="utf-8")
                self.assert_rejected()
        self.sources[0].write_text('{"oversized": true}', encoding="utf-8")
        with mock.patch("harness_integration_results.MAX_RESULT_BYTES", 4):
            self.assert_rejected()
