#!/usr/bin/env python3
"""Tests for session-only exact-input verifier execution reuse."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verifier_runtime import (  # noqa: E402
    BATCH_PROTOCOL,
    CACHE_BANNED_LAYERS,
    PROTOCOL,
    VerifierRuntimeError,
    build_execution_key,
    protected_path_sha256,
    run_verifier_batch,
    run_verifier,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST = "c" * 64


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


def cacheable_context() -> dict[str, object]:
    """A worker-layer context: the only shape session_exact caching is ever
    reachable from through a validated PLAN (cache_allowed=False for
    integration/batch/final; harness_manifest.py)."""

    context_document = context()
    context_document.update(
        {
            "layer": "worker",
            "mission_id": "M1",
            "task_id": None,
            "attempt_id": "A1",
            "lease_id": "L1",
        }
    )
    return context_document


def counter_command(counter: Path, *, exit_code: int = 0, delay: float = 0) -> list[str]:
    source = (
        "import pathlib,sys,time;"
        "p=pathlib.Path(sys.argv[1]);"
        "n=int(p.read_text()) if p.exists() else 0;"
        "p.write_text(str(n+1));"
        "time.sleep(float(sys.argv[2]));"
        "raise SystemExit(int(sys.argv[3]))"
    )
    return [sys.executable, "-c", source, str(counter), str(delay), str(exit_code)]


def verifier(counter: Path, *, identifier: str = "focused") -> dict[str, object]:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": counter_command(counter),
        "pass_signal": "exit 0",
        "cache": {"mode": "session_exact", "environment_keys": ["CI"]},
    }


class VerifierRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.checkout = self.root / "checkout"
        self.cache = self.root / "cache"
        self.checkout.mkdir()
        self.environment = dict(os.environ)
        self.environment["CI"] = "true"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read_count(self, counter: Path) -> int:
        return int(counter.read_text(encoding="utf-8"))

    def test_git_guard_rejects_tracked_file_changes_restored_during_execution(self) -> None:
        subprocess.run(
            ["git", "init", "-q", "-b", "integration"],
            cwd=self.checkout,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.checkout,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.checkout,
            check=True,
        )
        tracked = self.checkout / "tracked.txt"
        tracked.write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=self.checkout, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "base"], cwd=self.checkout, check=True
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        guarded_context = context()
        guarded_context.update(
            {
                "batch_base_sha": head,
                "head_sha": head,
                "changed_files": [],
                "cache_safe": False,
            }
        )
        source = (
            "import os,pathlib,sys;"
            "p=pathlib.Path(sys.argv[1]);"
            "original=p.read_text();"
            "p.write_text('temporary\\n');"
            "p.write_text(original);"
            "s=p.stat();os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1000000000))"
        )
        declaration = {
            "id": "guarded",
            "cwd": ".",
            "argv": [sys.executable, "-c", source, str(tracked)],
            "pass_signal": "exit 0",
            "cache": {"mode": "disabled", "environment_keys": []},
        }
        result = run_verifier(
            declaration,
            guarded_context,
            checkout_root=self.checkout,
            environment=self.environment,
            git_guard={
                "expected_branch": "integration",
                "expected_head_sha": head,
                "ignored_paths": [],
            },
        )

        self.assertEqual("ERROR", result["status"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("verifier inputs changed", result["stderr"])

    def test_git_guard_rejects_changes_to_an_ignored_coordination_file(self) -> None:
        subprocess.run(
            ["git", "init", "-q", "-b", "integration"],
            cwd=self.checkout,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.checkout,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.checkout,
            check=True,
        )
        run_path = self.checkout / "docs" / "goal" / "RUN.md"
        run_path.parent.mkdir(parents=True)
        run_path.write_text("authorized: false\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.checkout, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "base"], cwd=self.checkout, check=True
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.checkout,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        guarded_context = context()
        guarded_context.update(
            {
                "batch_base_sha": head,
                "head_sha": head,
                "changed_files": [],
                "cache_safe": False,
            }
        )
        declaration = {
            "id": "guarded-run",
            "cwd": ".",
            "argv": [
                sys.executable,
                "-c",
                (
                    "import os,pathlib,sys;"
                    "p=pathlib.Path(sys.argv[1]);original=p.read_bytes();"
                    "p.write_text('authorized: true\\n');p.write_bytes(original);"
                    "s=p.stat();os.utime(p,ns=(s.st_atime_ns,s.st_mtime_ns+1000000000))"
                ),
                str(run_path),
            ],
            "pass_signal": "exit 0",
            "cache": {"mode": "disabled", "environment_keys": []},
        }
        expected_protected_hash = hashlib.sha256(run_path.read_bytes()).hexdigest()

        result = run_verifier(
            declaration,
            guarded_context,
            checkout_root=self.checkout,
            environment=self.environment,
            git_guard={
                "expected_branch": "integration",
                "expected_head_sha": head,
                "ignored_paths": ["docs/goal/RUN.md"],
            },
            reservation={
                "node_id": "N-FINAL",
                "attempt_id": "ATT-FINAL",
                "nonce": "n" * 64,
            },
            request_sha256="d" * 64,
        )

        self.assertEqual("ERROR", result["status"])
        self.assertIsNone(result["exit_code"])
        self.assertIn("verifier inputs changed", result["stderr"])
        self.assertEqual(
            expected_protected_hash,
            result["dispatch_attestation"]["protected_path_sha256"][
                "docs/goal/RUN.md"
            ],
        )

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
                [
                    "cmd",
                    "/c",
                    "mklink",
                    "/J",
                    str(linked),
                    str(outside),
                ],
                capture_output=True,
                text=True,
                check=False,
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

    def test_exact_pass_reuses_equivalent_task_and_worker_declarations(self) -> None:
        counter = self.root / "counter.txt"
        task_context = cacheable_context()
        task_context.update(
            {
                "layer": "task",
                "task_id": "M1/T01",
                "attempt_id": "ATT-TASK-1",
                "lease_id": "LEASE-TASK-1",
            }
        )
        first = run_verifier(
            verifier(counter, identifier="task-focused"),
            task_context,
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        worker = run_verifier(
            verifier(counter, identifier="mission-focused"),
            cacheable_context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["cache_status"], "stored")
        self.assertEqual(worker["cache_status"], "reused")
        self.assertEqual(first["execution_key"], worker["execution_key"])
        self.assertEqual(worker["verifier_id"], "mission-focused")
        self.assertEqual(worker["context"]["layer"], "worker")
        self.assertNotIn("verifier_id", worker["key_document"])
        self.assertNotIn("layer", worker["key_document"])
        self.assertNotIn("attempt_id", worker["key_document"])
        self.assertEqual(self.read_count(counter), 1)

    def test_exact_key_invalidates_on_every_immutable_input_axis(self) -> None:
        variants = []

        changed = context()
        changed["head_sha"] = "d" * 40
        variants.append(("head", verifier(self.root / "counter.txt"), changed, self.environment))

        changed = context()
        changed["batch_base_sha"] = "e" * 40
        variants.append(("base", verifier(self.root / "counter.txt"), changed, self.environment))

        changed = context()
        changed["plan_digest_sha256"] = "f" * 64
        variants.append(("plan", verifier(self.root / "counter.txt"), changed, self.environment))

        changed = context()
        changed["changed_files"] = ["src/other.py"]
        variants.append(("files", verifier(self.root / "counter.txt"), changed, self.environment))

        changed = context()
        changed["trust_domain"] = "worker_local"
        variants.append(("trust", verifier(self.root / "counter.txt"), changed, self.environment))

        changed = context()
        changed["checkout_role"] = "worker"
        variants.append(("role", verifier(self.root / "counter.txt"), changed, self.environment))

        changed_verifier = verifier(self.root / "counter.txt")
        changed_verifier["argv"] = [*changed_verifier["argv"], "different-argv"]
        variants.append(("argv", changed_verifier, context(), self.environment))

        environment = dict(self.environment)
        environment["CI"] = "false"
        variants.append(("environment", verifier(self.root / "counter.txt"), context(), environment))

        subdir = self.checkout / "subdir"
        subdir.mkdir()
        changed_verifier = verifier(self.root / "counter.txt")
        changed_verifier["cwd"] = "subdir"
        variants.append(("cwd", changed_verifier, context(), self.environment))

        baseline = run_verifier(
            verifier(self.root / "counter.txt"),
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        baseline_key = baseline["execution_key"]
        for label, candidate_verifier, candidate_context, candidate_environment in variants:
            with self.subTest(axis=label):
                result = run_verifier(
                    candidate_verifier,
                    candidate_context,
                    checkout_root=self.checkout,
                    cache_root=self.cache,
                    environment=candidate_environment,
                )
                self.assertEqual(result["status"], "PASS")
                self.assertNotEqual(result["execution_key"], baseline_key)
                self.assertEqual(result["metrics"]["executed"], 1)
        self.assertEqual(self.read_count(self.root / "counter.txt"), 1 + len(variants))

    def test_layer_associations_reject_detached_or_spurious_ids(self) -> None:
        candidate = verifier(self.root / "counter.txt")
        invalid_contexts = []

        task = context()
        task.update({"layer": "task", "mission_id": "M1", "task_id": "T1"})
        invalid_contexts.append(task)

        worker = context()
        worker.update(
            {
                "layer": "worker",
                "mission_id": "M1",
                "task_id": "T1",
                "attempt_id": "A1",
                "lease_id": "L1",
            }
        )
        invalid_contexts.append(worker)

        final = context()
        final["mission_id"] = "M1"
        invalid_contexts.append(final)

        for invalid in invalid_contexts:
            with self.subTest(layer=invalid["layer"]):
                with self.assertRaises(VerifierRuntimeError):
                    build_execution_key(
                        candidate,
                        invalid,
                        checkout_root=self.checkout,
                        environment=self.environment,
                    )

    def test_banned_layers_never_reuse_even_with_a_hand_built_context(self) -> None:
        """PLAN validation already refuses session_exact for these layers
        (harness_core.py cache_allowed=False), which is unreachable through a
        validated PLAN. A direct run_verifier call with a hand-built context
        dict bypasses that PLAN-time gate, so the runtime must refuse too."""

        counter = self.root / "counter.txt"
        for layer in sorted(CACHE_BANNED_LAYERS):
            with self.subTest(layer=layer):
                banned = context()
                banned["layer"] = layer
                if layer == "mission_integration":
                    banned["mission_id"] = "M1"
                result = run_verifier(
                    verifier(counter),
                    banned,
                    checkout_root=self.checkout,
                    cache_root=self.cache,
                    environment=self.environment,
                )
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["cache_status"], "bypassed")
                self.assertEqual(result["cache_reason"], "layer_not_cacheable")
        # Every call above executed for real; none could have reused a prior PASS.
        self.assertEqual(self.read_count(counter), len(CACHE_BANNED_LAYERS))

    def test_deterministic_local_attestation_reuses_at_banned_layers(self) -> None:
        """The ban keys on layer, but the property that matters is the command's
        nature. A verifier that attests it is a pure local deterministic command
        may reuse an exact-input PASS at those layers."""

        counter = self.root / "counter.txt"
        attested = verifier(counter)
        attested["cache"] = {
            "mode": "session_exact",
            "environment_keys": ["CI"],
            "deterministic_local": True,
        }
        banned = context()
        banned["layer"] = "batch"
        for _ in range(2):
            result = run_verifier(
                attested,
                banned,
                checkout_root=self.checkout,
                cache_root=self.cache,
                environment=self.environment,
            )
            self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["cache_status"], "reused")
        # The second call reused the first; the command ran exactly once.
        self.assertEqual(self.read_count(counter), 1)

    def test_dirty_checkout_bypasses_existing_pass(self) -> None:
        counter = self.root / "counter.txt"
        run_verifier(
            verifier(counter),
            cacheable_context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        dirty = cacheable_context()
        dirty["checkout_dirty"] = True
        result = run_verifier(
            verifier(counter),
            dirty,
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        self.assertEqual(result["cache_status"], "bypassed")
        self.assertEqual(result["cache_reason"], "checkout_dirty")
        self.assertEqual(self.read_count(counter), 2)

    def test_failure_timeout_and_missing_cache_root_never_reuse(self) -> None:
        failure_counter = self.root / "failure.txt"
        failing = verifier(failure_counter)
        failing["argv"] = counter_command(failure_counter, exit_code=1)
        first = run_verifier(
            failing,
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        second = run_verifier(
            failing,
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        self.assertEqual((first["status"], second["status"]), ("FAIL", "FAIL"))
        self.assertEqual(self.read_count(failure_counter), 2)

        timeout_counter = self.root / "timeout.txt"
        slow = verifier(timeout_counter)
        slow["argv"] = counter_command(timeout_counter, delay=0.2)
        first = run_verifier(
            slow,
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            timeout_seconds=0.01,
            environment=self.environment,
        )
        second = run_verifier(
            slow,
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            timeout_seconds=0.01,
            environment=self.environment,
        )
        self.assertEqual((first["status"], second["status"]), ("TIMEOUT", "TIMEOUT"))

        uncached_counter = self.root / "uncached.txt"
        for _ in range(2):
            result = run_verifier(
                verifier(uncached_counter),
                cacheable_context(),
                checkout_root=self.checkout,
                cache_root=None,
                environment=self.environment,
            )
            self.assertEqual(result["cache_reason"], "cache_root_missing")
        self.assertEqual(self.read_count(uncached_counter), 2)

    def test_corrupt_cache_never_hits_or_gets_overwritten(self) -> None:
        counter = self.root / "counter.txt"
        candidate = verifier(counter)
        execution_key, _ = build_execution_key(
            candidate,
            cacheable_context(),
            checkout_root=self.checkout,
            environment=self.environment,
        )
        cache_path = self.cache / PROTOCOL / f"{execution_key}.json"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text("not json\n", encoding="utf-8")

        for _ in range(2):
            result = run_verifier(
                candidate,
                cacheable_context(),
                checkout_root=self.checkout,
                cache_root=self.cache,
                environment=self.environment,
            )
            self.assertEqual(result["cache_status"], "miss")
            self.assertEqual(result["cache_reason"], "cache_entry_malformed")
        self.assertEqual(self.read_count(counter), 2)
        self.assertEqual(cache_path.read_text(encoding="utf-8"), "not json\n")

    def test_non_deterministic_or_inside_checkout_cache_is_bypassed(self) -> None:
        counter = self.root / "counter.txt"
        unsafe = cacheable_context()
        unsafe["cache_safe"] = False
        result = run_verifier(
            verifier(counter),
            unsafe,
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        self.assertEqual(result["cache_reason"], "not_declared_deterministic_local")

        inside_counter = self.root / "inside.txt"
        result = run_verifier(
            verifier(inside_counter),
            cacheable_context(),
            checkout_root=self.checkout,
            cache_root=self.checkout / ".cache",
            environment=self.environment,
        )
        self.assertEqual(result["cache_reason"], "cache_root_inside_checkout")
        self.assertFalse((self.checkout / ".cache").exists())

    def test_dot_slash_argv0_resolves_against_verifier_cwd_not_real_process_cwd(
        self,
    ) -> None:
        mission = self.checkout / "workspace"
        mission.mkdir()
        (mission / "probe.sh").write_text("mission\n", encoding="utf-8")

        decoy_dir = self.root / "decoy"
        decoy_dir.mkdir()
        (decoy_dir / "probe.sh").write_text("decoy - much longer content\n", encoding="utf-8")

        real_cwd = os.getcwd()
        os.chdir(decoy_dir)
        try:
            _, key_document = build_execution_key(
                {
                    "id": "dot-slash-probe",
                    "cwd": "workspace",
                    "argv": ["./probe.sh"],
                    "pass_signal": "exit 0",
                    "cache": {"mode": "disabled", "environment_keys": []},
                },
                context(),
                checkout_root=self.checkout,
                environment=self.environment,
            )
        finally:
            os.chdir(real_cwd)

        resolved_path = key_document["executable_identity"]["path"]
        self.assertEqual(
            Path(resolved_path),
            (mission / "probe.sh").resolve(),
        )
        self.assertEqual(
            key_document["executable_identity"]["size"],
            (mission / "probe.sh").stat().st_size,
        )

    def batch_job(
        self,
        job_id: str,
        *,
        parallel_safe: bool = True,
        resources: list[dict[str, str]] | None = None,
        include_execution: bool = True,
    ) -> dict[str, object]:
        candidate = {
            "id": job_id,
            "cwd": ".",
            "argv": [sys.executable, "-c", "raise SystemExit(0)"],
            "pass_signal": "exit 0",
        }
        if include_execution:
            candidate["execution"] = {
                "parallel_safe": parallel_safe,
                "resources": [] if resources is None else resources,
            }
        return {
            "job_id": job_id,
            "verifier": candidate,
            "context": {},
            "checkout_root": str(self.checkout),
            "cache_root": None,
            "timeout_seconds": 5,
        }

    def test_parallel_batch_runs_independent_opted_in_verifiers_together(self) -> None:
        lock = threading.Lock()
        active = 0
        peak = 0

        def fake_run(*args: object, **kwargs: object) -> dict[str, object]:
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with lock:
                active -= 1
            return {"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}}

        with patch("verifier_runtime.run_verifier", side_effect=fake_run):
            result = run_verifier_batch(
                [self.batch_job("V2"), self.batch_job("V1")],
                max_parallel=2,
            )

        self.assertEqual(result["protocol"], BATCH_PROTOCOL)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["metrics"]["waves"], 1)
        self.assertEqual(result["metrics"]["max_parallel"], 2)
        self.assertEqual(peak, 2)
        self.assertEqual([item["job_id"] for item in result["results"]], ["V1", "V2"])

    def test_parallel_batch_serializes_exclusive_resource_conflicts(self) -> None:
        resource = [{"key": "database:test", "access": "exclusive"}]
        with patch(
            "verifier_runtime.run_verifier",
            return_value={"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}},
        ):
            result = run_verifier_batch(
                [
                    self.batch_job("V1", resources=resource),
                    self.batch_job("V2", resources=resource),
                ],
                max_parallel=2,
            )

        self.assertEqual(result["metrics"]["waves"], 2)
        self.assertEqual(result["metrics"]["max_parallel"], 1)

    def test_parallel_batch_groups_unmarked_verifiers(self) -> None:
        # A verifier with no execution block claims no resource, so it cannot
        # contend with another that also claims none. They share one wave.
        with patch(
            "verifier_runtime.run_verifier",
            return_value={"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}},
        ):
            result = run_verifier_batch(
                [
                    self.batch_job("V1", include_execution=False),
                    self.batch_job("V2", include_execution=False),
                ],
                max_parallel=2,
            )

        self.assertEqual(result["metrics"]["waves"], 1)
        self.assertEqual(result["metrics"]["max_parallel"], 2)

    def test_parallel_batch_serializes_explicit_opt_out(self) -> None:
        # Declaring parallel_safe: false still forces serial execution.
        with patch(
            "verifier_runtime.run_verifier",
            return_value={"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}},
        ):
            result = run_verifier_batch(
                [
                    self.batch_job("V1", parallel_safe=False),
                    self.batch_job("V2", include_execution=False),
                ],
                max_parallel=2,
            )

        self.assertEqual(result["metrics"]["waves"], 2)


if __name__ == "__main__":
    unittest.main()
