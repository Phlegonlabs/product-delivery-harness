import contextlib
import builtins
import copy
import hashlib
import io
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_eval_acceptance as checker
import manifest_fixtures as mf
from eval_delivery_fixtures import fixture, encoded, prd
from test_delivery_acceptance import execution
from eval_verification import QUALITY_ASSERTIONS, HANDOFF_ASSERTIONS


class EvalMissingParserTests(unittest.TestCase):
    def test_cli_missing_sibling_returns_json_failure_without_traceback(self):
        output = io.StringIO()
        with patch.dict(sys.modules, {"eval_verification": None}), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(checker.__file__, run_name="__main__")
        self.assertEqual(1, result.exception.code)
        self.assertEqual("FAIL", json.loads(output.getvalue())["status"])

    def test_cli_broken_sibling_returns_json_failure_without_traceback(self):
        original = builtins.__import__
        for error in (OSError, SyntaxError):
            def unavailable(name, *arguments, **options):
                if name == "eval_verification":
                    raise error("broken sibling")
                return original(name, *arguments, **options)

            output = io.StringIO()
            with self.subTest(error=error), patch("builtins.__import__", side_effect=unavailable), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as result:
                    runpy.run_path(checker.__file__, run_name="__main__")
                self.assertEqual(1, result.exception.code)
                self.assertEqual("FAIL", json.loads(output.getvalue())["status"])


class EvalAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        mf.init_repo(self.root, "README.md")
        self.policy, files, self.contract, _, report, _ = fixture()
        artifact_name = getattr(self, "artifact_in_evidence", None)
        if artifact_name:
            old = self.policy["delivery"][artifact_name]
            new = "docs/verification/evidence/implementation/" + getattr(self, "artifact_filename", Path(old).name)
            self.policy["delivery"][artifact_name] = new
            for name in ("setup_argv", "full_argv"):
                self.policy["delivery"][name] = [new if arg == old else arg for arg in self.policy["delivery"][name]]
            if getattr(self, "direct_runner", False):
                self.policy["delivery"]["full_argv"] = [new, "--full"]
            self.contract.update(prd_sha256=hashlib.sha256(prd(self.policy).encode()).hexdigest(),
                                 policy_sha256=checker.ep.policy_digest(self.policy), delivery=copy.deepcopy(self.policy["delivery"]))
            report.update(prd_sha256=self.contract["prd_sha256"], policy_sha256=self.contract["policy_sha256"],
                          contract_sha256=hashlib.sha256(encoded(self.contract)).hexdigest())
            report["artifacts"].pop(old)
            report["artifacts"][new] = hashlib.sha256(("Delivered " + new).encode()).hexdigest()
            for name in ("setup", "full"):
                report["provenance"][name]["argv"] = copy.deepcopy(self.policy["delivery"][name + "_argv"])
        self.write(".gitattributes", b"* -text -filter\n")
        self.prd_path = "docs/product/PRD.md"
        self.contract_path = "docs/verification/eval-contract.json"
        self.delivery_path = "docs/verification/delivery-acceptance.json"
        self.results_path = "docs/verification/delivery-results.json"
        self.write(self.prd_path, prd(self.policy).encode())
        self.write(self.contract_path, encoded(self.contract))
        for path, raw in files.items():
            self.write(path, raw)
        for name in ("runner", "grader", "lockfile", "runbook"):
            path = self.policy["delivery"][name]
            if not (name == artifact_name and getattr(self, "defer_artifact", False)):
                self.write(path, ("Delivered " + path).encode())
        self.delivery = {"schema": "delivery-acceptance/1", "prd_sha256": self.contract["prd_sha256"], "tests": []}
        self.register = {"schema": "delivery-results/1", "candidate_sha": "", "results": []}
        self.reports = {}
        for purpose, assertions in (("quality", QUALITY_ASSERTIONS), ("handoff", HANDOFF_ASSERTIONS)):
            declared = self.policy[purpose]
            context = execution()
            context["assertions"] = {name: "Frozen eval policy verified by deterministic checker" for name in sorted(assertions)}
            scenario = {"id": declared["scenario_id"], "execution": context,
                        "platform": "cli", "auth_mode": "none", "environment": "local",
                        "build": {"build_id": "fixture-eval-1", "config_digest": "b" * 64}, "fixtures": []}
            if getattr(self, "production_eval_row", None) == purpose:
                scenario["environment"] = "production"
            self.delivery["tests"].append({"test_id": declared["test_id"], "scenarios": [scenario]})
            current = copy.deepcopy(report)
            current.update(purpose=purpose, run_id=purpose + "-run-1", execution=context)
            current["provenance"]["job_id"] = "job-" + purpose + "-1"
            self.reports[purpose] = current
            self.register["results"].append({"test_id": declared["test_id"], "scenario_id": scenario["id"],
                **{name: scenario[name] for name in ("execution", "platform", "auth_mode", "environment", "build")},
                "status": "pass", "assertion_results": {name: "pass" for name in assertions},
                "fixture_cleanup": "not_required", "evidence": {"path": declared["report"], "sha256": ""}})
            if getattr(self, "production_eval_row", None) == purpose:
                self.register["results"][-1].update(
                    status="blocked", assertion_results={name: "blocked" for name in assertions})
        if artifact_name:
            scenario = copy.deepcopy(self.delivery["tests"][0]["scenarios"][0])
            scenario["id"] = "implementation-evidence"
            scenario["execution"]["assertions"] = {"artifact-check": "Delivered implementation is retained"}
            self.delivery["tests"][0]["scenarios"].append(scenario)
            row = copy.deepcopy(self.register["results"][0])
            row.update(scenario_id=scenario["id"], execution=scenario["execution"],
                       assertion_results={"artifact-check": "pass"},
                       evidence={"path": self.policy["delivery"][artifact_name], "sha256": ""})
            self.register["results"].append(row)
        if getattr(self, "production_smoke", False):
            # A production scenario cannot run before landing; its blocked row defers.
            smoke = copy.deepcopy(self.delivery["tests"][0]["scenarios"][0])
            smoke.update(id="prod-smoke", environment="production", platform="web", auth_mode="real")
            self.delivery["tests"][0]["scenarios"].append(smoke)
            raw = b"not run: production smoke runs after the main landing\n"
            smoke_evidence = "docs/verification/evidence/prod-smoke.txt"
            self.write(smoke_evidence, raw)
            row = copy.deepcopy(self.register["results"][0])
            row.update(scenario_id="prod-smoke", environment="production", platform="web", auth_mode="real",
                       status="blocked", assertion_results={name: "blocked" for name in row["assertion_results"]},
                       evidence={"path": smoke_evidence, "sha256": hashlib.sha256(raw).hexdigest()})
            self.register["results"].append(row)
        self.write(self.delivery_path, encoded(self.delivery))
        self.h1 = self.commit("product candidate")
        self.register["candidate_sha"] = self.h1
        for report in self.reports.values():
            report["candidate_sha"] = self.h1
            report["provenance"]["checkout_sha"] = self.h1
        if artifact_name and getattr(self, "defer_artifact", False):
            path = self.policy["delivery"][artifact_name]
            self.write(path, ("Delivered " + path).encode())
        self.save_reports()
        self.h2 = self.commit("directly registered evidence")

    def write(self, path, raw):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def commit(self, message):
        mf.git(self.root, "add", "-A")
        executable = getattr(self, "h1_runner_executable", None)
        if message == "product candidate" and executable is not None:
            path = self.policy["delivery"]["runner"]
            (self.root / path).chmod(0o755 if executable else 0o644)
            mf.git(self.root, "update-index", "--chmod=" + ("+x" if executable else "-x"), "--", path)
        mf.git(self.root, "commit", "-qm", message)
        return mf.git(self.root, "rev-parse", "HEAD")

    def save_reports(self):
        for purpose, report in self.reports.items():
            path = self.policy[purpose]["report"]
            raw = encoded(report)
            self.write(path, raw)
            for row in self.register["results"]:
                if (row["test_id"], row["scenario_id"]) == (self.policy[purpose]["test_id"], self.policy[purpose]["scenario_id"]):
                    row["evidence"]["sha256"] = hashlib.sha256(raw).hexdigest()
        if getattr(self, "artifact_in_evidence", None):
            row = self.register["results"][-1]
            row["evidence"]["sha256"] = hashlib.sha256((self.root / row["evidence"]["path"]).read_bytes()).hexdigest()
        self.write(self.results_path, encoded(self.register))

    def invoke(self, overrides=None):
        values = {"--repo-root": str(self.root), "--prd": self.prd_path,
            "--prd-sha256": self.contract["prd_sha256"], "--contract": self.contract_path,
            "--contract-sha256": hashlib.sha256(encoded(self.contract)).hexdigest(),
            "--delivery-contract": self.delivery_path,
            "--delivery-contract-sha256": hashlib.sha256(encoded(self.delivery)).hexdigest(), "--results": self.results_path}
        values.update(overrides or {})
        argv = [value for pair in values.items() for value in pair] + ["--candidate-from-head"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = checker.main(argv)
        return code, json.loads(output.getvalue())

    def test_deferred_list_names_only_the_blocked_production_rows(self):
        code, result = self.invoke()
        expected = ["TEST-001/prod-smoke"] if getattr(self, "production_smoke", False) else []
        self.assertEqual((0, expected), (code, result["production_smoke_deferred"]))

    def test_h1_h2_full_quality_and_handoff_pass(self):
        code, result = self.invoke()
        self.assertEqual((0, []), (code, result["errors"]))
        self.assertEqual(self.h1, result["candidate_sha"])
        self.assertEqual(self.h2, result["checked_head_sha"])
        self.assertEqual(8, result["reports"]["handoff"]["planned_trials"])

    def test_frozen_inputs_cannot_be_replaced(self):
        code, result = self.invoke({"--prd-sha256": "f" * 64})
        self.assertEqual(1, code)
        self.assertIn("frozen", str(result))

    def test_git_timeout_returns_json_failure_at_entry_and_final_recheck(self):
        self.assertEqual(0, self.invoke()[0])
        original = checker.run_git
        for phase in ("entry", "final"):
            status_calls = []

            def bounded_git(root, *command, **options):
                if command[0] == "status":
                    status_calls.append(command)
                if phase == "entry" or (command[0] == "status" and len(status_calls) == 2):
                    raise subprocess.TimeoutExpired(["git", *command], 10)
                return original(root, *command, **options)

            with self.subTest(phase=phase), patch.object(checker, "run_git", side_effect=bounded_git):
                code, result = self.invoke()
            self.assertEqual((1, "FAIL"), (code, result["status"]))
            self.assertIn("unreadable eval evidence", str(result["errors"]))
            if phase == "final":
                self.assertEqual(2, len(status_calls))

    def test_timestamp_overflow_returns_json_failure_in_both_reports(self):
        original = copy.deepcopy(self.reports)
        self.assertEqual(0, self.invoke()[0])
        for purpose, value in (("quality", "0001-01-01T00:00:00+01:00"),
                               ("handoff", "9999-12-31T23:00:00-02:00")):
            with self.subTest(purpose=purpose):
                self.reports = copy.deepcopy(original)
                self.reports[purpose]["started_at"] = value
                self.save_reports()
                self.commit("invalid timestamp evidence")
                code, result = self.invoke()
                self.assertEqual((1, "FAIL"), (code, result["status"]))
                self.assertIn("invalid report timestamp", str(result["errors"]))

    def test_protected_tree_git_failure_returns_json_fail(self):
        self.assertEqual(0, self.invoke()[0])
        original = checker.run_git
        for failure in ("exit", "timeout"):
            def unavailable_tree(root, *command, **options):
                if command[:2] == ("--literal-pathspecs", "diff"):
                    if failure == "timeout":
                        raise subprocess.TimeoutExpired(["git", *command], 30)
                    return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"unavailable")
                return original(root, *command, **options)

            with self.subTest(failure=failure), patch.object(checker, "run_git", side_effect=unavailable_tree):
                code, result = self.invoke()
            self.assertEqual((1, "FAIL"), (code, result["status"]))
            self.assertTrue(result["errors"])

    def test_changed_uncommitted_report_and_product_after_h1_fail(self):
        self.write(self.policy["quality"]["report"], b"{}")
        self.assertEqual(1, self.invoke()[0])
        self.save_reports()
        self.write(self.policy["delivery"]["runner"], b"new runner version")
        self.commit("runner repair")
        code, result = self.invoke()
        self.assertEqual(1, code)
        self.assertTrue(any(word in str(result) for word in ("bytes", "candidate", "context")))

    def test_same_trial_report_cannot_satisfy_handoff(self):
        self.reports["handoff"]["run_id"] = self.reports["quality"]["run_id"]
        self.save_reports()
        self.commit("invalid handoff evidence")
        self.assertEqual(1, self.invoke()[0])

    def test_missing_handoff_or_assertion_join_fails(self):
        self.register["results"].pop()
        self.save_reports()
        self.commit("missing handoff")
        self.assertEqual(1, self.invoke()[0])

    def test_prohibited_outcome_in_handoff_is_recomputed(self):
        self.reports["handoff"]["trials"][0]["assertion_results"]["no-side-effect"] = "fail"
        self.save_reports()
        self.commit("prohibited outcome")
        code, result = self.invoke()
        self.assertEqual(1, code)
        self.assertIn("prohibited", str(result))

    def test_unregistered_outside_root_and_transitive_trace_rejected(self):
        self.register["results"][0]["evidence"]["path"] = "evals/cases.jsonl"
        self.write(self.results_path, encoded(self.register))
        self.commit("invalid evidence root")
        self.assertEqual(1, self.invoke()[0])

    def test_moving_head_and_exact_byte_guards(self):
        with patch.object(checker.acceptance, "_head_sha", side_effect=[self.h2, "f" * 40]):
            code, result = self.invoke()
        self.assertEqual(1, code)
        self.assertIn("HEAD changed", str(result))
        with patch.object(checker.acceptance, "_committed_file_errors", return_value=["bytes differ from HEAD"]):
            self.assertEqual(1, self.invoke()[0])

    def test_symlink_secret_and_duplicate_json_fail(self):
        for path in ("../outside.json", ".env", "evals/auth-token.json"):
            self.assertEqual(1, self.invoke({"--contract": path})[0])
        path = self.policy["quality"]["report"]
        self.write(path, b'{"schema":1,"schema":2}')
        self.commit("duplicate evidence keys")
        self.assertEqual(1, self.invoke()[0])


class EvalProtectedArtifactTests(unittest.TestCase):
    def test_registered_runner_mode_change_fails_with_unchanged_blob(self):
        for executable in (True, False):
            with self.subTest(h1_executable=executable):
                case = EvalAcceptanceTests("test_h1_h2_full_quality_and_handoff_pass")
                case.artifact_in_evidence = "runner"
                case.artifact_filename = "run[1].py"
                case.direct_runner = True
                case.h1_runner_executable = executable
                try:
                    case.setUp()
                    self.assertEqual(0, case.invoke()[0])
                    path = case.policy["delivery"]["runner"]
                    before = mf.git(case.root, "ls-tree", case.h1, "--", path).split()
                    (case.root / path).chmod(0o644 if executable else 0o755)
                    mf.git(case.root, "update-index", "--chmod=" + ("-x" if executable else "+x"), "--", path)
                    changed = case.commit("change only directly registered runner mode")
                    after = mf.git(case.root, "ls-tree", changed, "--", path).split()
                    self.assertNotEqual(before[0], after[0])
                    self.assertEqual(before[2], after[2])
                    self.assertEqual("", mf.git(case.root, "status", "--porcelain", "--untracked-files=all"))
                    code, result = case.invoke()
                    self.assertEqual((1, "FAIL"), (code, result["status"]))
                    self.assertTrue(any("tested candidate H1" in error and path in error for error in result["errors"]), result)
                finally:
                    case.doCleanups()

    def test_registered_implementation_cannot_change_after_h1(self):
        for name in ("runner", "grader", "lockfile", "runbook"):
            with self.subTest(artifact=name):
                case = EvalAcceptanceTests("test_h1_h2_full_quality_and_handoff_pass")
                case.artifact_in_evidence = name
                try:
                    case.setUp()
                    self.assertEqual(0, case.invoke()[0])
                    path = case.policy["delivery"][name]
                    changed = b"Changed after tested H1\n"
                    case.write(path, changed)
                    for report in case.reports.values():
                        report["artifacts"][path] = hashlib.sha256(changed).hexdigest()
                    case.save_reports()
                    case.commit("change directly registered implementation after H1")
                    code, result = case.invoke()
                    self.assertEqual((1, "FAIL"), (code, result["status"]))
                    self.assertTrue(any("tested candidate H1" in error and path in error for error in result["errors"]), result)
                finally:
                    case.doCleanups()

    def test_registered_implementation_must_exist_at_h1(self):
        for name in ("runner", "grader", "lockfile", "runbook"):
            with self.subTest(artifact=name):
                case = EvalAcceptanceTests("test_h1_h2_full_quality_and_handoff_pass")
                case.artifact_in_evidence = name
                case.defer_artifact = True
                try:
                    case.setUp()
                    code, result = case.invoke()
                    self.assertEqual((1, "FAIL"), (code, result["status"]))
                    path = case.policy["delivery"][name]
                    self.assertTrue(any("tested candidate H1" in error and path in error for error in result["errors"]), result)
                finally:
                    case.doCleanups()


class EvalAcceptanceTestsWithProductionSmoke(EvalAcceptanceTests):
    """The eval gate runs before landing, so a blocked production row defers here too."""

    production_smoke = True

    def test_blocked_production_row_is_deferred_before_landing(self):
        code, result = self.invoke()
        self.assertEqual((0, []), (code, result["errors"]))
        self.assertEqual([self.policy["quality"]["test_id"] + "/prod-smoke"],
                         result["production_smoke_deferred"])


class _DeclaredEvalRowMixin:
    """A policy's quality or handoff row never defers, even as a production row."""

    production_eval_row = None

    def test_declared_eval_row_cannot_be_deferred(self):
        code, result = self.invoke()
        declared = self.policy[self.production_eval_row]
        self.assertEqual(1, code)
        self.assertIn(
            f"required eval row {declared['test_id']}/{declared['scenario_id']} "
            "cannot be deferred as production smoke",
            result["errors"])


class QualityRowNotDeferredTests(_DeclaredEvalRowMixin, EvalAcceptanceTests):
    production_eval_row = "quality"


class HandoffRowNotDeferredTests(_DeclaredEvalRowMixin, EvalAcceptanceTests):
    production_eval_row = "handoff"


for _case in (QualityRowNotDeferredTests, HandoffRowNotDeferredTests):
    # Only the mixin's test belongs to these fixtures; hide the inherited ones.
    for _name in dir(EvalAcceptanceTests):
        if _name.startswith("test_"):
            setattr(_case, _name, None)


if __name__ == "__main__":
    unittest.main()
