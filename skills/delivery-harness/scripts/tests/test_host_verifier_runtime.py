"""Exercise real host commands, source guards, and retained host identity."""

from __future__ import annotations

import copy
import contextlib
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import manifest_fixtures as mf
import verifier_runtime as vr
import harness_transition as transition
from harness_manifest import load_run, plan_digest, validate_run
from harness_core import host_execution_binding_errors
from test_verifier_runtime import context


def host_verifier(source="print('host works')", cwd="."):
    return {
        "id": "host-check", "cwd": cwd,
        "argv": [sys.executable, "-c", source], "pass_signal": "exit 0",
        "read_only": True,
        "execution": {"isolation": "host", "parallel_safe": False, "resources": []},
        "cache": {"mode": "disabled", "environment_keys": []},
    }


class HostVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        mf.init_repo(self.root, "README.md", default_branch="integration")
        (self.root / ".gitignore").write_text("build/\n", encoding="utf-8")
        (self.root / "app").mkdir()
        (self.root / "app/input.txt").write_text("input\n", encoding="utf-8")
        (self.root / "tracked.txt").write_text("safe\n", encoding="utf-8")
        mf.git(self.root, "add", ".")
        mf.git(self.root, "commit", "-qm", "host fixture")
        self.head = mf.git(self.root, "rev-parse", "HEAD")
        self.context = context()
        self.context.update(head_sha=self.head, batch_base_sha=self.head, changed_files=[], cache_safe=False)
        self.guard = {"expected_branch": "integration", "expected_head_sha": self.head, "ignored_paths": []}

    def preflight(self, declaration):
        entries, errors = vr.observe_plan_host_runtimes({"final_gates": [declaration]}, self.root)
        self.assertEqual([], errors)
        self.assertEqual(1, len(entries))
        return entries[0]

    def execute(self, declaration, **kwargs):
        values = {"checkout_root": self.root, "git_guard": self.guard,
                  "host_preflight": self.preflight(declaration)}
        values.update(kwargs)
        return vr.run_verifier(declaration, self.context, **values)

    def test_actual_command_uses_declared_cwd_without_container_or_archive(self):
        declaration = host_verifier("from pathlib import Path; print(Path('input.txt').read_text())", "app")
        with patch.object(vr, "_run_container_verifier", side_effect=AssertionError("container invoked")), \
             patch.object(vr, "_materialize_git_snapshot", side_effect=AssertionError("archive invoked")):
            result = self.execute(declaration)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(str(self.root / "app"), result["host_execution_attestation"]["cwd"])
        self.assertEqual(result["host_execution_attestation"], result["git_guard_attestation"]["host_execution_attestation"])
        self.assertEqual([], vr.execution_retention_binding_errors(result))
        self.assertEqual([], host_execution_binding_errors(result["key_document"]["host_preflight"],
                         result["host_execution_attestation"], result["key_document"], str(self.root)))

    def delayed_mutation_command(self, delay, *, timeout=False, inherit_output=False):
        path = self.root / "tracked.txt"
        child_source = (
            "from pathlib import Path; import time; "
            "Path('build/child-ready').touch(); "
            f"time.sleep({delay}); Path({str(path)!r}).write_text('mutated')\n"
        )
        parent_body = "print('parent-exit')"
        if timeout:
            parent_body = "import time; time.sleep(5); print('parent-exit')"
        output_args = "" if inherit_output else "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, "
        parent_source = (
            "import subprocess, sys, time; from pathlib import Path; "
            "Path('build').mkdir(exist_ok=True); "
            "subprocess.Popen([sys.executable, '-c', "
            f"{child_source!r}], stdin=subprocess.DEVNULL, "
            + output_args + "close_fds=True)\n"
            "while not Path('build/child-ready').exists(): time.sleep(.005)\n"
            "print('child-ready', flush=True)\n" + parent_body
        )
        return host_verifier(parent_source)

    def test_host_only_preflight_does_not_launch_any_process(self):
        declaration = host_verifier()
        with patch.object(vr.subprocess, "run", side_effect=AssertionError("process invoked")):
            self.assertEqual(([], []), vr.observe_plan_sandboxes({"final_gates": [declaration]}))
            self.preflight(declaration)

    @unittest.skipUnless(sys.platform == "win32", "uses the Windows job mechanism")
    def test_windows_job_terminates_descendant_after_parent_success(self):
        declaration = self.delayed_mutation_command(0.75)
        result = self.execute(declaration)
        self.assertEqual("PASS", result["status"])
        time.sleep(1.0)
        self.assertEqual("safe\n", (self.root / "tracked.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(sys.platform == "win32", "uses the Windows job mechanism")
    def test_windows_job_terminates_descendant_on_timeout(self):
        declaration = self.delayed_mutation_command(2, timeout=True)
        result = self.execute(declaration, timeout_seconds=1)
        self.assertEqual("TIMEOUT", result["status"])
        self.assertIn("child-ready", result["stdout"])
        time.sleep(2.25)
        self.assertEqual("safe\n", (self.root / "tracked.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(sys.platform.startswith("linux") or sys.platform == "darwin",
                         "uses the POSIX process-group mechanism")
    def test_posix_group_terminates_descendant_after_parent_success(self):
        declaration = self.delayed_mutation_command(0.75)
        result = self.execute(declaration)
        self.assertEqual("PASS", result["status"])
        time.sleep(1.0)
        self.assertEqual("safe\n", (self.root / "tracked.txt").read_text(encoding="utf-8"))

    @unittest.skipUnless(sys.platform.startswith("linux") or sys.platform == "darwin",
                         "uses the POSIX process-group mechanism")
    def test_posix_group_terminates_descendant_on_timeout(self):
        declaration = self.delayed_mutation_command(2, timeout=True)
        result = self.execute(declaration, timeout_seconds=1)
        self.assertEqual("TIMEOUT", result["status"])
        self.assertIn("child-ready", result["stdout"])
        time.sleep(2.25)
        self.assertEqual("safe\n", (self.root / "tracked.txt").read_text(encoding="utf-8"))

    def test_inherited_output_does_not_delay_descendant_cleanup(self):
        result = self.execute(self.delayed_mutation_command(0.75, inherit_output=True))
        self.assertEqual("PASS", result["status"])
        self.assertIn("child-ready", result["stdout"])
        time.sleep(1.0)
        self.assertEqual("safe\n", (self.root / "tracked.txt").read_text(encoding="utf-8"))

    def test_cleanup_failure_cannot_pass(self):
        cleanup = "_wait_job_empty" if sys.platform == "win32" else "_terminate_group"
        with patch.object(vr.host_process, cleanup,
                          side_effect=vr.host_process.HostProcessError("cleanup failed")):
            result = self.execute(host_verifier())
        self.assertEqual("ERROR", result["status"])
        self.assertIn("cleanup failed", result["stderr"])

    def test_host_stdout_stderr_and_exit_code_are_preserved(self):
        result = self.execute(host_verifier(
            "import sys; print('stdout marker'); "
            "sys.stderr.write('stderr marker'); raise SystemExit(3)"
        ))
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(3, result["exit_code"])
        self.assertEqual("stdout marker\n", result["stdout"])
        self.assertEqual("stderr marker", result["stderr"])

    @unittest.skipUnless(sys.platform == "win32", "forces a Windows job setup failure")
    def test_windows_containment_setup_failure_fails_closed(self):
        declaration = host_verifier()
        with patch.object(vr.host_process._kernel32, "AssignProcessToJobObject",
                          return_value=False) as assign:
            result = self.execute(declaration)
        self.assertEqual("ERROR", result["status"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("Windows process-tree setup failure", result["stderr"])
        assign.assert_called_once()

    def test_fail_and_timeout_are_not_pass(self):
        for source, timeout, expected in [("raise SystemExit(7)", 5, "FAIL"), ("import time; time.sleep(3)", .1, "TIMEOUT")]:
            with self.subTest(expected=expected):
                self.assertEqual(expected, self.execute(host_verifier(source), timeout_seconds=timeout)["status"])

    def test_ignored_build_outputs_allowed_and_never_cached(self):
        declaration = host_verifier("from pathlib import Path; p=Path('build/count'); p.parent.mkdir(exist_ok=True); p.write_text(str(int(p.read_text())+1 if p.exists() else 1))")
        for _ in range(2):
            result = self.execute(declaration)
            self.assertEqual("PASS", result["status"])
        self.assertEqual("2", (self.root / "build/count").read_text())

    def test_tracked_source_mutation_is_rejected(self):
        result = self.execute(host_verifier("from pathlib import Path; Path('README.md').write_text('changed')"))
        self.assertEqual("ERROR", result["status"])

    def test_git_branch_mutation_is_rejected(self):
        result = self.execute(host_verifier("import subprocess; subprocess.run(['git','checkout','-b','unexpected'],check=True)"))
        self.assertEqual("ERROR", result["status"])

    def test_guard_and_exact_preflight_required(self):
        declaration = host_verifier()
        for changes, message in [({"git_guard": None}, "git_guard"), ({"host_preflight": None}, "preflight")]:
            with self.subTest(message=message), self.assertRaisesRegex(vr.VerifierRuntimeError, message):
                self.execute(declaration, **changes)
        for key, value in [("argv0", "different-command"), ("executable_sha256", "0" * 64), ("isolation", "container")]:
            preflight = self.preflight(declaration)
            preflight[key] = value
            with self.subTest(key=key), self.assertRaises(vr.VerifierRuntimeError):
                self.execute(declaration, host_preflight=preflight)

    def test_retained_wrong_cwd_and_command_are_rejected(self):
        result = self.execute(host_verifier())
        attestation = copy.deepcopy(result["host_execution_attestation"])
        attestation["cwd"] = str(self.root / "wrong")
        issues = host_execution_binding_errors(result["key_document"]["host_preflight"], attestation, result["key_document"], str(self.root))
        self.assertTrue(any("cwd differs" in item for item in issues))
        document = copy.deepcopy(result["key_document"])
        document["argv"][0] = "other"
        issues = host_execution_binding_errors(document["host_preflight"], result["host_execution_attestation"], document, str(self.root))
        self.assertTrue(any("argv0 differs" in item for item in issues))

    def test_host_cache_parallel_and_malformed_resources_refused(self):
        for field, value in [("cache", {"mode": "session_exact", "environment_keys": []}),
                             ("execution", {"isolation": "host", "parallel_safe": True, "resources": []}),
                             ("execution", {"isolation": "host", "parallel_safe": False, "resources": [{"key": "db", "access": "write"}]})]:
            declaration = host_verifier()
            declaration[field] = value
            with self.subTest(value=value), self.assertRaises(vr.VerifierRuntimeError):
                vr.run_verifier(declaration, self.context, checkout_root=self.root, git_guard=self.guard)

    def test_independent_worktrees_can_execute_host_checks_concurrently(self):
        second = self.root.parent / (self.root.name + "-worker")
        mf.git(self.root, "worktree", "add", "-b", "worker", str(second))
        self.addCleanup(lambda: mf.git(self.root, "worktree", "remove", "--force", str(second)))
        # Each process waits for the other checkout's marker. Serial execution times out.
        def run(root, other, branch):
            source = ("from pathlib import Path; import sys,time; "
                      "p=Path('build/ready'); p.parent.mkdir(exist_ok=True); p.touch(); "
                      "other=Path(sys.argv[1]); deadline=time.monotonic()+5\n"
                      "while not other.exists() and time.monotonic()<deadline: time.sleep(.02)\n"
                      "assert other.exists(), 'peer was not dispatched concurrently'")
            declaration = host_verifier(source)
            declaration["argv"].append(str(other / "build/ready"))
            entries, errors = vr.observe_plan_host_runtimes({"final_gates": [declaration]}, root)
            self.assertEqual([], errors)
            return vr.run_verifier(declaration, self.context, checkout_root=root, host_preflight=entries[0],
                                   git_guard={**self.guard, "expected_branch": branch})
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(run, self.root, second, "integration")
            other = executor.submit(run, second, self.root, "worker")
            self.assertEqual("PASS", first.result()["status"])
            self.assertEqual("PASS", other.result()["status"])

    def test_host_observe_reserve_execute_record_and_retained_tamper_rejection(self):
        plan = mf.valid_plan()
        for _, declaration in vr._plan_verifier_declarations(plan):
            declaration.update({**host_verifier(), "id": declaration["id"]})
        gate_id = plan["final_gates"][0]["id"]
        plan["graph"]["nodes"].append({"id": "N-HOST", "kind": "verifier", "ref": gate_id,
            "executor": "local_command", "allowed_outcomes": ["pass", "blocked"], "max_attempts": 1, "runtime": None})
        plan["graph"]["entry_nodes"].append("N-HOST")
        for source in plan["sources"]:
            payload = f"# Test {source['kind']}\n".encode()
            path = self.root / source["location"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            source["content_sha256"] = hashlib.sha256(payload).hexdigest()
        mf.git(self.root, "add", "docs/product")
        mf.git(self.root, "commit", "-qm", "contracts")
        head = mf.git(self.root, "rev-parse", "HEAD")
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        run.update(status="running", plan_readiness="ready")
        run["integration"].update(branch="integration", batch_base_sha=head, integration_head_sha=head)
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["execution_authorization_scope"]["plan_digest_sha256"] = plan_digest(plan)
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)
            plan_path, run_path = control / "PLAN.md", control / "RUN.md"
            request_path, result_path = control / "request.json", control / "result.json"
            plan_path.write_text(mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan), encoding="utf-8")
            run_path.write_text(mf.manifest_markdown("## Harness Run State", "harness_run", run), encoding="utf-8")
            common = ["--plan", str(plan_path), "--run", str(run_path), "--repo-root", str(self.root), "--session-id", "HOST-TEST"]
            def step(*args):
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    code = transition.main([*common, *args])
                self.assertEqual(0, code, output.getvalue())
            step("acquire-run-lock")
            with patch.object(vr, "_run_container_verifier", side_effect=AssertionError("container invoked")):
                step("record-observation", "--available-worker-slots", "2", "--isolation-capacity", "2", "--capacity-evidence", "fixture capacity")
                step("reserve-node-attempt", "--node-id", "N-HOST", "--attempt-id", "ATT-HOST", "--request-out", str(request_path))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = vr.main(["--request", str(request_path)])
                self.assertEqual(0, code, output.getvalue())
            result_path.write_text(output.getvalue(), encoding="utf-8")
            result = json.loads(output.getvalue())
            self.assertEqual("PASS", result["status"])
            step("record-node-result", "--node-id", "N-HOST", "--attempt-id", "ATT-HOST", "--outcome", "pass", "--evidence", "host passed", "--verifier-result", str(result_path))
            recorded = load_run(run_path)
            self.assertEqual("succeeded", recorded["graph_state"]["node_states"]["N-HOST"]["phase"])
            self.assertEqual([], validate_run(plan, recorded))
            recorded["observed"]["host_runtime"]["entries"][0]["executable_sha256"] = "0" * 64
            self.assertTrue(any("host_preflight" in issue for issue in validate_run(plan, recorded)))


if __name__ == "__main__":
    unittest.main()
