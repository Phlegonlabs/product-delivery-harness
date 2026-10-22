"""Current host PASS admission binds real execution to its reserved request."""

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from argparse import Namespace

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import harness_transition as transition  # noqa: E402
import harness_manifest as manifest  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
import verifier_runtime as runtime  # noqa: E402
from test_host_verifier_runtime import host_verifier  # noqa: E402


class CurrentHostAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.repo_temp = tempfile.TemporaryDirectory()
        self.control_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.repo_temp.cleanup)
        self.addCleanup(self.control_temp.cleanup)
        self.root = Path(self.repo_temp.name).resolve()
        self.control = Path(self.control_temp.name).resolve()
        mf.init_repo(self.root, "README.md", default_branch="codex/test")
        base = mf.git(self.root, "rev-parse", "HEAD")
        self.plan = mf.final_candidate_plan(lenses=("backend_code", "security"))
        self.plan["branch_policy"] = {"protocol": "main-preview/1", "kind": "ordinary",
                                      "base_ref": "refs/remotes/origin/main", "base_sha": base}
        self.plan["final_gates"].append(host_verifier())
        self.plan["graph"]["nodes"].append(mf.graph_node("N-HOST", "verifier", "host-check", "local_command", ["pass", "blocked"]))
        self.plan["graph"]["entry_nodes"].append("N-HOST")
        mf.materialize_plan_sources(self.root, self.plan)
        mf.git(self.root, "add", "docs/product")
        mf.git(self.root, "commit", "-qm", "approved sources")
        head = mf.git(self.root, "rev-parse", "HEAD")
        run = mf.valid_run(self.plan)
        mf.authorize_execution(run, [mission["id"] for mission in self.plan["missions"]])
        run.update(status="running", plan_readiness="ready")
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"].update(
            required_harness_version="0.66.0", harness_version="0.66.0")
        run["observed"]["git"].update(parent_worktree_path=str(self.root), parent_branch="codex/test",
                                       parent_head_sha=head, parent_dirty=False)
        run["integration"].update(branch="codex/test", batch_base_sha=head, integration_head_sha=head)
        self.plan_path, self.run_path = self.control / "PLAN.md", self.control / "RUN.md"
        self.request_path, self.result_path = self.control / "request.json", self.control / "result.json"
        self.plan_path.write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan), encoding="utf-8")
        self.run_path.write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
        self.common = ["--plan", str(self.plan_path), "--run", str(self.run_path), "--repo-root", str(self.root), "--session-id", "CURRENT-HOST"]
        self.cli("acquire-run-lock")
        self.cli("reserve-node-attempt", "--node-id", "N-HOST", "--attempt-id", "ATT-HOST", "--request-out", str(self.request_path))
        self.request = json.loads(self.request_path.read_text(encoding="utf-8"))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, runtime.main(["--request", str(self.request_path)]))
        self.result = json.loads(output.getvalue())
        self.assertEqual("PASS", self.result["status"])
        self.record_arguments = ["record-node-result", "--node-id", "N-HOST", "--attempt-id", "ATT-HOST",
                                 "--outcome", "pass", "--evidence", "real host execution", "--verifier-result", str(self.result_path)]

    def cli(self, *arguments, expected=0):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = transition.main([*self.common, *arguments])
        self.assertEqual(expected, code, output.getvalue())
        return output.getvalue()

    @staticmethod
    def rekey(result):
        result["execution_key"] = runtime.execution_key_from_document(result["key_document"])
        result["evidence_key"] = result["execution_key"]

    def test_real_current_host_result_closes_the_reserved_gate(self):
        self.result_path.write_text(json.dumps(self.result), encoding="utf-8")
        self.cli(*self.record_arguments)
        recorded = manifest.load_run(self.run_path)
        self.assertEqual("succeeded", recorded["graph_state"]["node_states"]["N-HOST"]["phase"])
        self.assertEqual("PASS", recorded["final_gate_results"][-1]["status"])
        self.assertEqual([], manifest.validate_run(self.plan, recorded))

    def test_public_record_refuses_incomplete_or_substituted_evidence_without_writes(self):
        for mutation in ("top", "nested", "git", "blank", "executable", "argv", "cwd", "tracked"):
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.result)
                if mutation == "top": result.pop("host_execution_attestation")
                elif mutation == "nested": result["git_guard_attestation"].pop("host_execution_attestation")
                elif mutation == "git": result.pop("git_guard_attestation")
                elif mutation == "blank": result["key_document"]["host_preflight"] = {}
                elif mutation == "executable":
                    result["key_document"]["host_preflight"]["executable_sha256"] = "0" * 64
                    result["host_execution_attestation"]["executable"]["sha256"] = "0" * 64
                    result["git_guard_attestation"]["host_execution_attestation"] = copy.deepcopy(result["host_execution_attestation"])
                elif mutation == "argv":
                    result["key_document"]["argv"][-1] = "print('substituted')"
                    result["verifier"]["argv"] = result["key_document"]["argv"]
                elif mutation == "cwd":
                    result["key_document"]["cwd"] = "docs"
                    result["verifier"]["cwd"] = "docs"
                elif mutation == "tracked": result["git_guard_attestation"]["tracked_files"] = {}
                self.rekey(result)
                self.result_path.write_text(json.dumps(result), encoding="utf-8")
                before = self.run_path.read_bytes()
                self.cli(*self.record_arguments, expected=2)
                self.assertEqual(before, self.run_path.read_bytes())

    def test_formal_missing_host_proof_is_rejected_even_without_a_valid_pin(self):
        result = copy.deepcopy(self.result)
        result.pop("host_execution_attestation")
        result["git_guard_attestation"].pop("host_execution_attestation")
        result["key_document"]["host_preflight"] = {}
        self.rekey(result)
        self.result_path.write_text(json.dumps(result), encoding="utf-8")
        for pin in ("0.66.0", None, "malformed", "0.65.3"):
            with self.subTest(pin=pin):
                run = manifest.load_run(self.run_path)
                run["runtime_capabilities"]["runtime_adapter"]["version_gate"]["required_harness_version"] = pin
                before = copy.deepcopy(run)
                with self.assertRaisesRegex(manifest.ManifestError, "host"):
                    transition._record_node_result(self.plan, run, Namespace(node_id="N-HOST", attempt_id="ATT-HOST",
                        outcome="pass", evidence=["synthetic proof, no execution"], blocker=[],
                        verifier_result=[self.result_path], repo_root=self.root, run=self.run_path))
                self.assertEqual(before, run)

    def test_retained_current_evidence_and_historical_optional_payloads(self):
        self.result_path.write_text(json.dumps(self.result), encoding="utf-8")
        self.cli(*self.record_arguments)
        baseline = manifest.load_run(self.run_path)
        for pin in ("0.66.0", None, "malformed", "0.65.3"):
            with self.subTest(pin=pin):
                run = copy.deepcopy(baseline)
                run["runtime_capabilities"]["runtime_adapter"]["version_gate"]["required_harness_version"] = pin
                retained = run["verifier_executions"][-1]
                retained.pop("host_execution_attestation")
                retained["git_guard_attestation"].pop("host_execution_attestation")
                errors = []
                manifest._validate_verifier_executions(errors, self.plan, run)
                self.assertEqual(pin != "0.65.3", any("host_execution_attestation" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
