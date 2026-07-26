#!/usr/bin/env python3
"""Tests for session-only exact-input verifier execution reuse."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from verifier_runtime import (  # noqa: E402
    PROTOCOL,
    VerifierRuntimeError,
    build_execution_key,
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

    def test_exact_pass_reuses_only_the_same_verifier_declaration(self) -> None:
        counter = self.root / "counter.txt"
        first = run_verifier(
            verifier(counter),
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        second = run_verifier(
            verifier(counter),
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        relabeled = run_verifier(
            verifier(counter, identifier="mission-focused"),
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["cache_status"], "stored")
        self.assertEqual(second["cache_status"], "reused")
        self.assertEqual(first["execution_key"], second["execution_key"])
        self.assertEqual(relabeled["verifier_id"], "mission-focused")
        self.assertNotEqual(first["execution_key"], relabeled["execution_key"])
        self.assertEqual(relabeled["cache_status"], "stored")
        self.assertEqual(self.read_count(counter), 2)

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

    def test_dirty_checkout_bypasses_existing_pass(self) -> None:
        counter = self.root / "counter.txt"
        run_verifier(
            verifier(counter),
            context(),
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
        )
        dirty = context()
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
                context(),
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
            context(),
            checkout_root=self.checkout,
            environment=self.environment,
        )
        cache_path = self.cache / PROTOCOL / f"{execution_key}.json"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text("not json\n", encoding="utf-8")

        for _ in range(2):
            result = run_verifier(
                candidate,
                context(),
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
        unsafe = context()
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
            context(),
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


if __name__ == "__main__":
    unittest.main()
