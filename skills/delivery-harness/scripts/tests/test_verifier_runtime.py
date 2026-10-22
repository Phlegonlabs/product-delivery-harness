#!/usr/bin/env python3
"""Tests for the host-only verifier runtime: policy, keys, guard and serial batches."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import verifier_runtime  # noqa: E402
from verifier_runtime import (  # noqa: E402
    BATCH_PROTOCOL,
    PROTOCOL,
    VerifierRuntimeError,
    build_execution_key,
    execution_retention_binding_errors,
    host_runtime_fingerprint,
    host_runtime_version,
    observe_plan_host_runtimes,
    protected_path_sha256,
    run_verifier,
    run_verifier_batch,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST = "c" * 64
NO_SANDBOX = "sandbox_preflight is not supported"


def context() -> dict[str, object]:
    return {
        "run_id": "RUN-TEST",
        "plan_revision": 1,
        "plan_digest_sha256": DIGEST,
        "graph_revision": 1,
        "batch_base_sha": SHA_A,
        "head_sha": SHA_B,
        "changed_files": ["src/feature.py"],
        "trust_domain": "parent_local",
        "checkout_role": "integration",
        "checkout_dirty": False,
        "cache_safe": True,
        "layer": "batch",
        "mission_id": None,
        "task_id": None,
        "attempt_id": None,
        "lease_id": None,
    }


def worker_context(**changes: object) -> dict[str, object]:
    result = context()
    result.update(layer="worker", checkout_role="worker", mission_id="M1",
                  attempt_id="A1", lease_id="L1")
    result.update(changes)
    return result


def verifier(source: str = "raise SystemExit(0)", *, identifier: str = "focused") -> dict[str, object]:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": [sys.executable, "-c", source],
        "pass_signal": "exit 0",
        "read_only": True,
        "execution": {"parallel_safe": False, "resources": [], "isolation": "host"},
        "cache": {"mode": "disabled", "environment_keys": []},
    }


class VerifierRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.checkout = self.root / "checkout"
        self.checkout.mkdir()
        self.git("init", "-q", "-b", "integration")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Harness Test")
        (self.checkout / "subdir").mkdir()
        (self.checkout / "subdir" / ".keep").write_text("fixture\n", encoding="utf-8")
        (self.checkout / "tracked.txt").write_text("original\n", encoding="utf-8")
        (self.checkout / "docs" / "goal").mkdir(parents=True)
        (self.checkout / "docs" / "goal" / "RUN.md").write_text("authorized: false\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        (self.checkout / "tracked.txt").write_text("head\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-qm", "head")
        self.head = self.git("rev-parse", "HEAD")
        self.environment = dict(os.environ)

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=self.checkout, check=True, capture_output=True, text=True
        ).stdout.strip()

    def ctx(self, **changes: object) -> dict[str, object]:
        result = context()
        result.update(batch_base_sha=self.base, head_sha=self.head, changed_files=[], cache_safe=False)
        result.update(changes)
        return result

    def guard(self, **changes: object) -> dict[str, object]:
        result = {"expected_branch": "integration", "expected_head_sha": self.head, "ignored_paths": []}
        result.update(changes)
        return result

    def preflight(self, declaration: dict[str, object]) -> dict[str, object]:
        entries, errors = observe_plan_host_runtimes({"final_gates": [declaration]}, self.checkout)
        self.assertEqual([], errors)
        return entries[0]

    def run_host(self, declaration: dict[str, object], verifier_context: dict[str, object], **kwargs: object):
        values = {"checkout_root": self.checkout, "environment": self.environment,
                  "git_guard": self.guard(), "host_preflight": self.preflight(declaration)}
        values.update(kwargs)
        return run_verifier(declaration, verifier_context, **values)

    def key(self, declaration: dict[str, object], verifier_context: dict[str, object]) -> str:
        return build_execution_key(
            declaration, verifier_context, checkout_root=self.checkout,
            environment=self.environment, host_preflight=self.preflight(declaration),
        )[0]

    def batch_job(self, job_id: str) -> dict[str, object]:
        return {"job_id": job_id, "verifier": verifier(identifier=job_id), "context": {},
                "checkout_root": str(self.checkout), "cache_root": None, "timeout_seconds": 5}

    def test_sandbox_preflight_is_rejected_with_one_message(self) -> None:
        declaration = verifier()
        preflight = {"runtime": "docker"}
        with self.assertRaisesRegex(VerifierRuntimeError, NO_SANDBOX):
            self.run_host(declaration, self.ctx(), sandbox_preflight=preflight)
        with self.assertRaisesRegex(VerifierRuntimeError, NO_SANDBOX):
            build_execution_key(declaration, self.ctx(), checkout_root=self.checkout,
                                host_preflight=self.preflight(declaration), sandbox_preflight=preflight)
        job = self.batch_job("V1")
        job["sandbox_preflight"] = preflight
        result = run_verifier_batch([job], max_parallel=1)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["results"][0]["result"]["errors"]))
        self.assertRegex(result["results"][0]["result"]["errors"][0], NO_SANDBOX)
        request = self.root / "request.json"
        request.write_text(json.dumps({
            "verifier": declaration, "context": self.ctx(), "checkout_root": str(self.checkout),
            "git_guard": self.guard(), "sandbox_preflight": preflight,
        }), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = verifier_runtime.main(["--request", str(request)])
        self.assertEqual(2, code)
        self.assertRegex(json.loads(output.getvalue())["errors"][0], NO_SANDBOX)

    def test_container_and_unknown_isolation_are_rejected(self) -> None:
        container = verifier()
        container["execution"] = {"parallel_safe": True, "resources": [], "isolation": "container",
                                  "sandbox": {"runtime": "docker", "image": "fixture@sha256:" + "1" * 64}}
        with self.assertRaisesRegex(VerifierRuntimeError, "must contain parallel_safe/resources/isolation"):
            run_verifier(container, self.ctx(), checkout_root=self.checkout, git_guard=self.guard())
        for isolation in ("container", "live"):
            declaration = verifier()
            declaration["execution"]["isolation"] = isolation
            with self.subTest(isolation=isolation), self.assertRaisesRegex(
                VerifierRuntimeError, r"execution\.isolation must be host"
            ):
                run_verifier(declaration, self.ctx(), checkout_root=self.checkout, git_guard=self.guard())
        with self.assertRaisesRegex(VerifierRuntimeError, r"isolation=host"):
            run_verifier({**verifier(), "execution": None}, self.ctx(), checkout_root=self.checkout,
                         git_guard=self.guard())

    def test_worker_guard_head_must_match_context_head(self) -> None:
        with self.assertRaisesRegex(VerifierRuntimeError, "expected_head_sha"):
            self.run_host(verifier(), worker_context(head_sha=self.head, batch_base_sha=self.base),
                          git_guard=self.guard(expected_head_sha=SHA_A))

    def test_worker_command_without_read_only_contract_is_rejected(self) -> None:
        declaration = verifier()
        declaration.pop("read_only")
        with self.assertRaisesRegex(VerifierRuntimeError, "read_only declaration"):
            self.run_host(declaration, worker_context(head_sha=self.head, batch_base_sha=self.base))

    def test_worker_batch_job_requires_git_guard(self) -> None:
        job = self.batch_job("worker-gate")
        job["context"] = {"layer": "worker", "checkout_role": "worker"}
        with self.assertRaisesRegex(VerifierRuntimeError, "require git_guard"):
            run_verifier_batch([job], max_parallel=1)

    def test_git_guard_rejects_tracked_file_changes_restored_during_execution(self) -> None:
        tracked = self.checkout / "tracked.txt"
        source = (
            "import os,pathlib,sys;"
            "p=pathlib.Path(sys.argv[1]);original=p.read_text();"
            "p.write_text('temporary\\n');p.write_text(original);"
            "s=p.stat();os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1000000000))"
        )
        declaration = verifier(source)
        declaration["argv"].append(str(tracked))
        result = self.run_host(declaration, self.ctx())
        self.assertEqual("ERROR", result["status"])
        self.assertIn("changed while the command was running", result["stderr"])

    def test_git_guard_rejects_changes_to_an_ignored_coordination_file(self) -> None:
        run_path = self.checkout / "docs" / "goal" / "RUN.md"
        source = (
            "import os,pathlib,sys;"
            "p=pathlib.Path(sys.argv[1]);original=p.read_bytes();"
            "p.write_text('authorized: true\\n');p.write_bytes(original);"
            "s=p.stat();os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1000000000))"
        )
        declaration = verifier(source)
        declaration["argv"].append(str(run_path))
        result = self.run_host(
            declaration,
            self.ctx(),
            git_guard=self.guard(ignored_paths=["docs/goal/RUN.md"]),
            reservation={"node_id": "N-FINAL", "attempt_id": "ATT-FINAL", "nonce": "n" * 64},
            request_sha256="d" * 64,
        )
        self.assertEqual("ERROR", result["status"])
        self.assertIn("changed while the command was running", result["stderr"])
        self.assertEqual("d" * 64, result["dispatch_attestation"]["request_sha256"])

    def test_protected_path_hashes_reject_path_escape(self) -> None:
        with self.assertRaisesRegex(VerifierRuntimeError, "repository-relative"):
            protected_path_sha256(self.checkout, ["../RUN.md"])
        with self.assertRaisesRegex(VerifierRuntimeError, "repository-relative"):
            protected_path_sha256(self.checkout, ["C:/outside/RUN.md"])

    def test_protected_path_hashes_reject_ancestor_link_escape(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "RUN.md").write_text("outside\n", encoding="utf-8")
        linked = self.checkout / "linked"
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(linked), str(outside)],
                capture_output=True, text=True, check=False,
            )
            if completed.returncode != 0:
                self.skipTest(f"directory junction unavailable: {completed.stderr}")
        else:
            linked.symlink_to(outside, target_is_directory=True)
        try:
            with self.assertRaisesRegex(VerifierRuntimeError, "escapes the checkout"):
                protected_path_sha256(self.checkout, ["linked/RUN.md"])
        finally:
            if os.name == "nt":
                linked.rmdir()
            else:
                linked.unlink()

    def test_exact_key_changes_on_every_immutable_input_axis(self) -> None:
        baseline = self.key(verifier(), self.ctx())
        self.assertEqual(baseline, self.key(verifier(identifier="renamed"), self.ctx(layer="final")))
        changed_argv = verifier()
        changed_argv["argv"].append("different-argv")
        changed_cwd = verifier()
        changed_cwd["cwd"] = "subdir"
        variants = {
            "head": (verifier(), self.ctx(head_sha=SHA_A)),
            "base": (verifier(), self.ctx(batch_base_sha=SHA_B)),
            "plan": (verifier(), self.ctx(plan_digest_sha256="f" * 64)),
            "files": (verifier(), self.ctx(changed_files=["src/other.py"])),
            "trust": (verifier(), self.ctx(trust_domain="worker_local")),
            "role": (verifier(), self.ctx(checkout_role="worker")),
            "argv": (changed_argv, self.ctx()),
            "cwd": (changed_cwd, self.ctx()),
        }
        for label, (declaration, verifier_context) in variants.items():
            with self.subTest(axis=label):
                self.assertNotEqual(baseline, self.key(declaration, verifier_context))

    def test_layer_associations_reject_detached_or_spurious_ids(self) -> None:
        invalid_contexts = [
            {**context(), "layer": "task", "mission_id": "M1", "task_id": "T1"},
            {**context(), "layer": "worker", "mission_id": "M1", "task_id": "T1",
             "attempt_id": "A1", "lease_id": "L1"},
            {**context(), "mission_id": "M1"},
        ]
        for invalid in invalid_contexts:
            with self.subTest(layer=invalid["layer"]), self.assertRaises(VerifierRuntimeError):
                self.key(verifier(), invalid)

    def test_dot_slash_argv0_resolves_against_verifier_cwd_not_real_process_cwd(self) -> None:
        mission = self.checkout / "workspace"
        mission.mkdir()
        (mission / "probe.sh").write_text("mission\n", encoding="utf-8")
        decoy = self.root / "decoy"
        decoy.mkdir()
        (decoy / "probe.sh").write_text("decoy - much longer content\n", encoding="utf-8")
        declaration = {**verifier(), "cwd": "workspace", "argv": ["./probe.sh"]}
        preflight = {
            "isolation": "host", "argv0": "./probe.sh",
            "executable": str((mission / "probe.sh").resolve()),
            "executable_sha256": hashlib.sha256(b"mission\n").hexdigest(),
            "runtime_version": host_runtime_version(), "host": host_runtime_fingerprint(),
        }
        real_cwd = os.getcwd()
        os.chdir(decoy)
        try:
            _, key_document = build_execution_key(
                declaration, self.ctx(), checkout_root=self.checkout,
                environment=self.environment, host_preflight=preflight,
            )
        finally:
            os.chdir(real_cwd)
        resolved = key_document["executable_identity"]["path"]
        self.assertEqual(os.path.normcase(str((mission / "probe.sh").resolve())), resolved)

    def test_retention_binding_rejects_rebound_reuse_evidence(self) -> None:
        item = {
            "status": "PASS", "exit_code": 0, "cache_status": "reused",
            "cache_reason": "same_runner_container_pass",
            "verifier": {"cache": {"mode": "session_exact", "deterministic_local": True},
                         "read_only": True, "pass_signal": "exit 0"},
            "context": {"layer": "worker", "cache_safe": True, "checkout_dirty": False},
            "execution_key": "a" * 64,
            "stdout_sha256": "b" * 64,
            "stderr_sha256": "c" * 64,
            "sandbox_attestation": {"image": "same"},
            "timings": {"end_to_end_ms": 2, "setup_ms": 1, "git_guard_ms": 0, "cache_lookup_ms": 0,
                        "snapshot_ms": 1, "command_ms": 1, "postcheck_ms": 0},
            "container_reuse_origin": {
                "kind": "same_runner", "execution_key": "a" * 64, "verifier_id": "origin",
                "context_sha256": "d" * 64, "stdout_sha256": "b" * 64, "stderr_sha256": "c" * 64,
                "sandbox_attestation": {"image": "same"},
            },
        }
        self.assertEqual([], execution_retention_binding_errors(item))
        item["container_reuse_origin"]["execution_key"] = "e" * 64
        errors = execution_retention_binding_errors(item)
        self.assertTrue(any("execution key is rebound" in error for error in errors))
        self.assertEqual(
            ["container reuse origin must match exactly one retained same-runner PASS"],
            verifier_runtime.container_reuse_origin_run_errors(item, {"verifier_executions": []}),
        )

    def test_batch_runs_jobs_one_at_a_time_in_job_id_order(self) -> None:
        lock = threading.Lock()
        state = {"active": 0, "peak": 0, "order": []}

        def fake_run(verifier_declaration: dict[str, object], *args: object, **kwargs: object):
            with lock:
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
                state["order"].append(verifier_declaration["id"])
            with lock:
                state["active"] -= 1
            return {"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}}

        with patch("verifier_runtime.run_verifier", side_effect=fake_run):
            result = run_verifier_batch([self.batch_job("V2"), self.batch_job("V1")], max_parallel=4)
        self.assertEqual(BATCH_PROTOCOL, result["protocol"])
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["metrics"]["max_parallel"])
        self.assertEqual(2, result["metrics"]["executed"])
        self.assertEqual(1, state["peak"])
        self.assertEqual(["V1", "V2"], state["order"])
        self.assertEqual(["V1", "V2"], [item["job_id"] for item in result["results"]])

    def test_batch_returns_error_after_unexpected_exception(self) -> None:
        with patch("verifier_runtime.run_verifier", side_effect=RuntimeError("sentinel")):
            result = run_verifier_batch([self.batch_job("broken")], max_parallel=1)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(["sentinel"], result["results"][0]["result"]["errors"])

    def test_batch_job_cache_root_is_optional_and_ignored(self) -> None:
        without_root = self.batch_job("V1")
        without_root.pop("cache_root")
        with_root = self.batch_job("V2")
        with_root["cache_root"] = str(self.root / "cache")
        with patch(
            "verifier_runtime.run_verifier",
            return_value={"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}},
        ) as run:
            result = run_verifier_batch([without_root, with_root], max_parallel=1)
        self.assertEqual("PASS", result["status"])
        for call in run.call_args_list:
            self.assertNotIn("cache_root", call.kwargs)
        self.assertFalse((self.root / "cache").exists())

    def test_batch_validates_each_job_policy_before_running(self) -> None:
        bad = self.batch_job("V1")
        bad["verifier"]["execution"]["isolation"] = "container"
        with patch("verifier_runtime.run_verifier") as run:
            with self.assertRaisesRegex(VerifierRuntimeError, "must be host"):
                run_verifier_batch([self.batch_job("V0"), bad], max_parallel=1)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
