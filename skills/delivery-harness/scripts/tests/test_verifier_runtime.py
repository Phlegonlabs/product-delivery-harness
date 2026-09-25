#!/usr/bin/env python3
"""Tests for session-only exact-input verifier execution reuse."""

from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor
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

import verifier_runtime  # noqa: E402
from verifier_runtime import (  # noqa: E402
    BATCH_PROTOCOL,
    CACHE_BANNED_LAYERS,
    PROTOCOL,
    VerifierRuntimeError,
    _ContainerResultCache,
    _SnapshotArchiveCache,
    build_execution_key as _build_execution_key,
    execution_retention_binding_errors,
    protected_path_sha256,
    probe_plan_sandboxes,
    run_verifier_batch,
    run_verifier as _run_verifier,
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
    batch/final; harness_manifest.py)."""

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


def container_execution() -> dict[str, object]:
    return {
        "parallel_safe": True,
        "resources": [],
        "isolation": "container",
        "sandbox": {
            "runtime": "docker",
            "image": "fixture@sha256:" + "1" * 64,
            "network": "none",
            "read_only_rootfs": True,
            "no_new_privileges": True,
            "cap_drop": ["ALL"],
            "tmpfs": ["/tmp"],
            "memory": "512m",
            "cpus": "1",
            "pids_limit": "256",
            "user": "65532:65532",
            "pull": "never",
        },
    }


def verifier(counter: Path, *, identifier: str = "focused") -> dict[str, object]:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": counter_command(counter),
        "pass_signal": "exit 0",
        # Legacy batch/final fixtures execute in-process; current task/worker
        # declarations add an explicit container execution policy in their
        # PLAN.  Keep the read-only contract here so guard validation tests
        # reach the intended branch before isolation is checked.
        "read_only": True,
        "execution": container_execution(),
        "cache": {"mode": "session_exact", "environment_keys": ["CI"]},
    }


def sandbox_preflight(declaration: dict[str, object]) -> dict[str, object]:
    execution = declaration["execution"]
    assert isinstance(execution, dict)
    policy = execution["sandbox"]
    assert isinstance(policy, dict)
    executable = Path(sys.executable).resolve()
    return {
        "runtime": policy["runtime"],
        "image": policy["image"],
        "repo_digest": policy["image"],
        "runtime_probe": {
            "executable": str(executable),
            "executable_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "version_output_sha256": "2" * 64,
        },
    }


def run_verifier(
    declaration: dict[str, object],
    verifier_context: dict[str, object],
    **kwargs: object,
) -> dict[str, object]:
    """Test adapter that supplies the required recorded preflight."""

    kwargs.setdefault("sandbox_preflight", sandbox_preflight(declaration))
    return _run_verifier(declaration, verifier_context, **kwargs)


def worker_context() -> dict[str, object]:
    result = cacheable_context()
    result["checkout_role"] = "worker"
    return result


def build_execution_key(
    declaration: dict[str, object],
    verifier_context: dict[str, object],
    **kwargs: object,
) -> tuple[str, dict[str, object]]:
    kwargs.setdefault("sandbox_preflight", sandbox_preflight(declaration))
    return _build_execution_key(declaration, verifier_context, **kwargs)


class VerifierRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.checkout = self.root / "checkout"
        self.cache = self.root / "cache"
        self.checkout.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "integration"], cwd=self.checkout, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.checkout,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Harness Test"],
            cwd=self.checkout,
            check=True,
        )
        fixture = self.checkout / ".fixture"
        fixture.write_text("fixture\n", encoding="utf-8")
        (self.checkout / "subdir").mkdir()
        (self.checkout / "subdir" / ".keep").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.checkout, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.checkout, check=True)
        global SHA_A, SHA_B
        SHA_A = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.checkout, text=True
        ).strip()
        fixture.write_text("fixture-head\n", encoding="utf-8")
        subprocess.run(["git", "add", ".fixture"], cwd=self.checkout, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture head"], cwd=self.checkout, check=True)
        SHA_B = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.checkout, text=True
        ).strip()
        self.environment = dict(os.environ)
        self.environment["CI"] = "true"
        self._container_patch = patch(
            "verifier_runtime._run_container_verifier",
            side_effect=self._fake_container_verifier,
        )
        self._container_patch.start()

    def _fake_container_verifier(
        self,
        _checkout_root: Path,
        snapshot_root: Path,
        declared_cwd: str,
        argv: list[str],
        policy: dict[str, object],
        timeout_seconds: float,
        sandbox_preflight: dict[str, object] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        execution_cwd = (snapshot_root / declared_cwd).resolve()
        environment = dict(os.environ)
        environment["PWD"] = str(execution_cwd)
        for key in ("OLDPWD", "GIT_DIR", "GIT_WORK_TREE"):
            environment.pop(key, None)
        completed = subprocess.run(
            argv,
            cwd=execution_cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        image = str(policy["image"])
        assert isinstance(sandbox_preflight, dict)
        return completed, {
            "runtime": str(policy["runtime"]),
            "runtime_probe": sandbox_preflight["runtime_probe"],
            "image": image,
            "image_probe": sandbox_preflight["repo_digest"],
            "policy": policy,
            "mount": {
                "source": "git_archive",
                "destination": "/workspace",
                "read_only": True,
            },
            "network": "none",
        }

    def tearDown(self) -> None:
        self._container_patch.stop()
        self.temp.cleanup()

    def read_count(self, counter: Path) -> int:
        return int(counter.read_text(encoding="utf-8"))

    def test_container_execution_requires_the_bound_preflight(self) -> None:
        with self.assertRaisesRegex(
            VerifierRuntimeError,
            "exact sandbox preflight entry",
        ):
            _run_verifier(
                verifier(self.root / "counter.txt"),
                context(),
                checkout_root=self.checkout,
                environment=self.environment,
            )

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
            "execution": container_execution(),
            "cache": {"mode": "disabled", "environment_keys": []},
        }
        with self.assertRaisesRegex(VerifierRuntimeError, "must not reference the live checkout"):
            run_verifier(
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

    def test_worker_guard_head_must_match_context_head(self) -> None:
        worker_context = context()
        worker_context.update(
            {
                "layer": "worker",
                "checkout_role": "worker",
                "mission_id": "M1",
                "attempt_id": "A1",
                "lease_id": "L1",
            }
        )
        declaration = verifier(self.root / "counter.txt")
        with self.assertRaisesRegex(VerifierRuntimeError, "expected_head_sha"):
            run_verifier(
                declaration,
                worker_context,
                checkout_root=self.checkout,
                environment=self.environment,
                git_guard={
                    "expected_branch": "integration",
                    "expected_head_sha": SHA_A,
                    "ignored_paths": [],
                },
            )

    def test_worker_command_without_read_only_contract_is_rejected(self) -> None:
        worker_context = context()
        worker_context.update(
            {
                "layer": "worker",
                "checkout_role": "worker",
                "mission_id": "M1",
                "attempt_id": "A1",
                "lease_id": "L1",
            }
        )
        declaration = verifier(self.root / "counter.txt")
        declaration.pop("read_only")
        with self.assertRaisesRegex(VerifierRuntimeError, "read_only declaration"):
            run_verifier(
                declaration,
                worker_context,
                checkout_root=self.checkout,
                environment=self.environment,
                git_guard={
                    "expected_branch": "integration",
                    "expected_head_sha": SHA_B,
                    "ignored_paths": [],
                },
            )

    def test_worker_local_subprocess_is_fail_closed_even_with_snapshot_flag(self) -> None:
        worker_context = context()
        worker_context.update(
            {
                "layer": "worker",
                "checkout_role": "worker",
                "mission_id": "M1",
                "attempt_id": "A1",
                "lease_id": "L1",
            }
        )
        declaration = verifier(self.root / "counter.txt")
        declaration["execution"]["isolation"] = "live"
        with self.assertRaisesRegex(
            VerifierRuntimeError,
            r"execution\.isolation=container",
        ):
            run_verifier(
                declaration,
                worker_context,
                checkout_root=self.checkout,
                environment=self.environment,
                git_guard={
                    "expected_branch": "integration",
                    "expected_head_sha": SHA_B,
                    "ignored_paths": [],
                },
            )

    def test_worker_batch_job_requires_git_guard(self) -> None:
        job = self.batch_job("worker-gate")
        job["context"] = {"layer": "worker", "checkout_role": "worker"}
        with self.assertRaisesRegex(VerifierRuntimeError, "require git_guard"):
            run_verifier_batch([job], max_parallel=1)

    def test_every_verifier_layer_routes_through_container_without_host_sentinel(self) -> None:
        sentinel = self.root / "host-sentinel.txt"
        declaration = verifier(sentinel)
        declaration["cache"] = {"mode": "disabled", "environment_keys": []}
        declaration["argv"] = [
            sys.executable,
            "-c",
            "from pathlib import Path; Path(__import__('sys').argv[1]).write_text('host')",
            str(sentinel),
        ]
        calls: list[str] = []

        def sandbox_only(
            _checkout_root: Path,
            _snapshot_root: Path,
            _declared_cwd: str,
            _argv: list[str],
            policy: dict[str, object],
            _timeout_seconds: float,
            sandbox_preflight: dict[str, object] | None = None,
        ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
            calls.append(str(policy["runtime"]))
            image = str(policy["image"])
            return subprocess.CompletedProcess(
                args=["docker", "run"], returncode=0, stdout="", stderr=""
            ), {
                "runtime": str(policy["runtime"]),
                "runtime_probe": "fixture-runtime",
                "image": image,
                "image_probe": image,
                "policy": policy,
                "mount": {
                    "source": "git_archive",
                    "destination": "/workspace",
                    "read_only": True,
                },
                "network": "none",
            }

        contexts: list[dict[str, object]] = []
        for layer in ("task", "worker"):
            current = context()
            current.update(
                {
                    "layer": layer,
                    "checkout_role": "worker",
                    "mission_id": "M1",
                    "task_id": "M1/T01" if layer == "task" else None,
                    "attempt_id": "A1",
                    "lease_id": "L1",
                }
            )
            contexts.append(current)
        mission = context()
        mission.update({"layer": "mission_integration", "mission_id": "M1"})
        contexts.append(mission)
        contexts.extend(
            [
                context(),
                {**context(), "layer": "final"},
            ]
        )

        with patch("verifier_runtime._run_container_verifier", side_effect=sandbox_only):
            for current in contexts:
                guard = (
                    {
                        "expected_branch": "integration",
                        "expected_head_sha": current["head_sha"],
                        "ignored_paths": [],
                    }
                    if current["layer"] in {"task", "worker"}
                    else None
                )
                result = run_verifier(
                    declaration,
                    current,
                    checkout_root=self.checkout,
                    environment=self.environment,
                    git_guard=guard,
                )
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(
                    result["git_guard_attestation"]["isolation_mode"]
                    if guard is not None
                    else result["key_document"]["execution"]["isolation"],
                    "container",
                )
        self.assertEqual(len(calls), 5)
        self.assertFalse(sentinel.exists())

    def test_sandbox_preflight_proves_runtime_and_exact_repo_digest(self) -> None:
        declaration = verifier(self.root / "unused.txt")
        plan = {"batch_verifiers": [declaration], "final_gates": [], "missions": []}
        image = declaration["execution"]["sandbox"]["image"]
        with patch("verifier_runtime.shutil.which", return_value="docker.exe") as which:
            with patch(
                "verifier_runtime._runtime_trust",
                return_value={
                    "path": "docker.exe",
                    "runtime": "docker",
                    "ownership": "test-machine-policy",
                    "uid": 0,
                    "mode": 0o755,
                    "reparse": False,
                },
            ):
                with patch("verifier_runtime.Path.read_bytes", return_value=b"fixture-runtime"):
                    with patch(
                    "verifier_runtime.subprocess.run",
                    side_effect=[
                        subprocess.CompletedProcess(
                            args=["docker", "version"], returncode=0, stdout="fixture", stderr=""
                        ),
                        subprocess.CompletedProcess(
                            args=["docker", "image", "inspect"],
                            returncode=0,
                            stdout=json.dumps([image]),
                            stderr="",
                        ),
                    ],
                    ) as run:
                        self.assertEqual([], probe_plan_sandboxes(plan))
        which.assert_called_once_with("docker")
        self.assertEqual(run.call_count, 2)

    def test_windows_script_runtime_is_rejected_before_version_probe(self) -> None:
        import verifier_runtime as runtime_module

        declaration = verifier(self.root / "unused.txt")
        with patch.object(runtime_module, "shutil") as shutil_module, patch(
            "verifier_runtime.subprocess.run"
        ) as run:
            shutil_module.which.return_value = str(self.root / "docker.cmd")
            with patch.object(runtime_module.os, "name", "nt"):
                errors = runtime_module.probe_plan_sandboxes(
                    {"batch_verifiers": [declaration], "final_gates": [], "missions": []}
                )
        self.assertTrue(any("native .exe" in error for error in errors), errors)
        run.assert_not_called()

    @unittest.skipUnless(os.name != "nt", "POSIX ownership fixture only")
    def test_runtime_trust_rejects_writable_parent_component(self) -> None:
        import verifier_runtime as runtime_module

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / "docker"
            executable.write_bytes(b"fixture")
            executable.chmod(0o755)
            root.chmod(0o777)
            with patch.object(runtime_module, "_path_within", return_value=True):
                with self.assertRaisesRegex(VerifierRuntimeError, "root-owned and not writable"):
                    runtime_module._runtime_trust(executable, "docker")

    def test_sandbox_runtime_path_switch_is_rejected_before_run(self) -> None:
        patch.stopall()
        from verifier_runtime import _run_container_verifier
        runtime_a = self.root / "runtime-a.exe"
        runtime_b = self.root / "runtime-b.exe"
        runtime_a.write_bytes(b"runtime-a")
        runtime_b.write_bytes(b"runtime-b")
        if os.name != "nt":
            runtime_a.chmod(0o755)
            runtime_b.chmod(0o755)
        policy = container_execution()["sandbox"]
        preflight = {
            "runtime": "docker",
            "image": policy["image"],
            "repo_digest": policy["image"],
            "runtime_probe": {
                "executable": str(runtime_a),
                "executable_sha256": hashlib.sha256(runtime_a.read_bytes()).hexdigest(),
                "version_output_sha256": hashlib.sha256(b"version-a").hexdigest(),
            },
        }
        with patch("verifier_runtime.shutil.which", return_value=str(runtime_b)):
            with self.assertRaisesRegex(VerifierRuntimeError, "executable changed"):
                _run_container_verifier(
                    self.checkout,
                    self.checkout,
                    ".",
                    ["python", "-c", "pass"],
                    policy,
                    5,
                    sandbox_preflight=preflight,
                )

    def test_sandbox_runtime_hash_version_and_repo_digest_drift_fail_closed(self) -> None:
        patch.stopall()
        from verifier_runtime import _run_container_verifier

        runtime = self.root / "runtime.exe"
        original = b"trusted-runtime"
        runtime.write_bytes(original)
        if os.name != "nt":
            runtime.chmod(0o755)
        policy = container_execution()["sandbox"]
        version_output = "version-a"
        preflight = {
            "runtime": "docker",
            "image": policy["image"],
            "repo_digest": policy["image"],
            "runtime_probe": {
                "executable": str(runtime.resolve()),
                "executable_sha256": hashlib.sha256(original).hexdigest(),
                "version_output_sha256": hashlib.sha256(
                    version_output.encode("utf-8")
                ).hexdigest(),
            },
        }

        runtime.write_bytes(b"substituted-runtime")
        with patch("verifier_runtime.shutil.which", return_value=str(runtime)), patch(
            "verifier_runtime.subprocess.run"
        ) as invoked:
            with self.assertRaisesRegex(VerifierRuntimeError, "executable changed"):
                _run_container_verifier(
                    self.checkout,
                    self.checkout,
                    ".",
                    ["python", "-c", "pass"],
                    policy,
                    5,
                    sandbox_preflight=preflight,
                )
            invoked.assert_not_called()

        runtime.write_bytes(original)
        wrong_version = subprocess.CompletedProcess(
            args=[str(runtime), "version"],
            returncode=0,
            stdout="version-b",
            stderr="",
        )
        with patch("verifier_runtime.shutil.which", return_value=str(runtime)), patch(
            "verifier_runtime.subprocess.run", return_value=wrong_version
        ):
            with self.assertRaisesRegex(VerifierRuntimeError, "version output changed"):
                _run_container_verifier(
                    self.checkout,
                    self.checkout,
                    ".",
                    ["python", "-c", "pass"],
                    policy,
                    5,
                    sandbox_preflight=preflight,
                )

        version_ok = subprocess.CompletedProcess(
            args=[str(runtime), "version"],
            returncode=0,
            stdout=version_output,
            stderr="",
        )
        other_repo = "other@" + str(policy["image"]).rsplit("@", 1)[-1]
        inspect_other = subprocess.CompletedProcess(
            args=[str(runtime), "image", "inspect"],
            returncode=0,
            stdout=json.dumps([other_repo]),
            stderr="",
        )
        with patch("verifier_runtime.shutil.which", return_value=str(runtime)), patch(
            "verifier_runtime.subprocess.run",
            side_effect=[version_ok, inspect_other],
        ):
            with self.assertRaisesRegex(VerifierRuntimeError, "RepoDigest changed"):
                _run_container_verifier(
                    self.checkout,
                    self.checkout,
                    ".",
                    ["python", "-c", "pass"],
                    policy,
                    5,
                    sandbox_preflight=preflight,
                )

    def test_container_command_preserves_hidden_cwd_segments(self) -> None:
        patch.stopall()
        from verifier_runtime import _run_container_verifier

        runtime = self.root / "runtime.exe"
        runtime.write_bytes(b"trusted-runtime")
        if os.name != "nt":
            runtime.chmod(0o755)
        policy = container_execution()["sandbox"]
        assert isinstance(policy, dict)
        preflight = {
            "runtime": "docker",
            "image": policy["image"],
            "repo_digest": policy["image"],
            "runtime_probe": {
                "executable": str(runtime.resolve()),
                "executable_sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
                "version_output_sha256": hashlib.sha256(b"version").hexdigest(),
            },
        }
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / ".hidden").mkdir()
        calls: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            if len(command) == 2 and command[1] == "version":
                return subprocess.CompletedProcess(command, 0, "version", "")
            if len(command) > 2 and command[1:3] == ["image", "inspect"]:
                return subprocess.CompletedProcess(
                    command, 0, json.dumps([policy["image"]]), ""
                )
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch("verifier_runtime.shutil.which", return_value=str(runtime)), patch(
            "verifier_runtime.subprocess.run", side_effect=fake_run
        ):
            for declared_cwd, expected in (
                (".github/workflows", "/workspace/.github/workflows"),
                ("./.hidden", "/workspace/.hidden"),
            ):
                calls.clear()
                _run_container_verifier(
                    self.checkout,
                    self.root,
                    declared_cwd,
                    ["python", "-c", "pass"],
                    policy,
                    5,
                    sandbox_preflight=preflight,
                )
                self.assertEqual(len(calls), 3, calls)
                self.assertEqual(calls[0][1], "version")
                self.assertEqual(calls[1][1:3], ["image", "inspect"])
                self.assertEqual(calls[2][1], "run")
                workdir_index = calls[2].index("--workdir")
                self.assertEqual(calls[2][workdir_index + 1], expected)
                self.assertTrue(
                    any(
                        item.startswith("type=bind,src=")
                        and item.endswith(",dst=/workspace,readonly")
                        for item in calls[2]
                    )
                )

    def test_runtime_binding_survives_replace_restore_sentinel_during_run(self) -> None:
        patch.stopall()
        from verifier_runtime import _run_container_verifier

        runtime = self.root / "runtime.exe"
        replacement = self.root / "runtime-replacement.exe"
        sentinel = self.root / "runtime.sentinel"
        original = b"trusted-runtime"
        runtime.write_bytes(original)
        replacement.write_bytes(b"substituted-runtime")
        if os.name != "nt":
            runtime.chmod(0o755)
            replacement.chmod(0o755)
        policy = container_execution()["sandbox"]
        assert isinstance(policy, dict)
        preflight = {
            "runtime": "docker",
            "image": policy["image"],
            "repo_digest": policy["image"],
            "runtime_probe": {
                "executable": str(runtime.resolve()),
                "executable_sha256": hashlib.sha256(original).hexdigest(),
                "version_output_sha256": hashlib.sha256(b"version").hexdigest(),
            },
        }
        commands: list[list[str]] = []
        replacement_denied = False

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal replacement_denied
            commands.append(command)
            if len(command) == 2 and command[1] == "version":
                return subprocess.CompletedProcess(command, 0, "version", "")
            if len(command) > 2 and command[1:3] == ["image", "inspect"]:
                return subprocess.CompletedProcess(
                    command, 0, json.dumps([policy["image"]]), ""
                )
            # POSIX exercises descriptor pinning by replacing the directory
            # entry while the descriptor-backed command is in flight. Windows
            # exercises the native handle's no-delete sharing by observing the
            # expected replacement failure and leaves the original in place.
            try:
                os.replace(runtime, sentinel)
                os.replace(replacement, runtime)
                os.replace(runtime, replacement)
                os.replace(sentinel, runtime)
            except PermissionError:
                replacement_denied = True
                if sentinel.exists():
                    os.replace(sentinel, runtime)
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch("verifier_runtime.shutil.which", return_value=str(runtime)), patch(
            "verifier_runtime.subprocess.run", side_effect=fake_run
        ):
            completed, _attestation = _run_container_verifier(
                self.checkout,
                self.root,
                ".",
                ["python", "-c", "pass"],
                policy,
                5,
                sandbox_preflight=preflight,
            )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(runtime.read_bytes(), original)
        self.assertFalse(sentinel.exists())
        self.assertEqual(len(commands), 3)
        if os.name == "nt":
            self.assertTrue(replacement_denied)
            self.assertEqual(commands[2][0], str(runtime))
        else:
            self.assertTrue(
                commands[2][0].startswith(("/proc/self/fd/", "/dev/fd/"))
            )
            self.assertNotEqual(commands[2][0], str(runtime))

    @unittest.skipUnless(os.name != "nt", "descriptor-backed execution is POSIX-only")
    def test_posix_runtime_descriptor_executes_original_inode(self) -> None:
        from verifier_runtime import _RuntimeExecutableBinding

        runtime = self.root / "runtime.sh"
        runtime.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        runtime.chmod(0o755)
        with _RuntimeExecutableBinding(runtime) as binding:
            completed = subprocess.run(
                [binding.launch_path],
                pass_fds=binding.pass_fds,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

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
            "execution": container_execution(),
            "cache": {"mode": "disabled", "environment_keys": []},
        }
        with self.assertRaisesRegex(VerifierRuntimeError, "must not reference the live checkout"):
            run_verifier(
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
        self.assertEqual(first["cache_status"], "bypassed")
        self.assertEqual(first["cache_reason"], "container_disk_cache_disabled")
        self.assertEqual(worker["cache_status"], "bypassed")
        self.assertEqual(worker["cache_reason"], "container_disk_cache_disabled")
        self.assertEqual(first["execution_key"], worker["execution_key"])
        self.assertEqual(worker["verifier_id"], "mission-focused")
        self.assertEqual(worker["context"]["layer"], "worker")
        self.assertNotIn("verifier_id", worker["key_document"])
        self.assertNotIn("layer", worker["key_document"])
        self.assertNotIn("attempt_id", worker["key_document"])
        self.assertEqual(self.read_count(counter), 2)

    def test_exact_key_invalidates_on_every_immutable_input_axis(self) -> None:
        variants = []

        changed = context()
        changed["head_sha"] = SHA_A
        variants.append(("head", verifier(self.root / "counter.txt"), changed, self.environment))

        changed = context()
        changed["batch_base_sha"] = SHA_B
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
        subdir.mkdir(exist_ok=True)
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
                self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")
        # Every call above executed for real; none could have reused a prior PASS.
        self.assertEqual(self.read_count(counter), len(CACHE_BANNED_LAYERS))

    def test_container_execution_never_reuses_at_banned_layers(self) -> None:
        """Container results are not reused, even for deterministic commands."""

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
        self.assertEqual(result["cache_status"], "bypassed")
        self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")
        self.assertEqual(self.read_count(counter), 2)

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
        self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")
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
            self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")
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
            self.assertEqual(result["cache_status"], "bypassed")
            self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")
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
        self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")

        inside_counter = self.root / "inside.txt"
        result = run_verifier(
            verifier(inside_counter),
            cacheable_context(),
            checkout_root=self.checkout,
            cache_root=self.checkout / ".cache",
            environment=self.environment,
        )
        self.assertEqual(result["cache_reason"], "container_disk_cache_disabled")
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
                    "execution": container_execution(),
                    "cache": {"mode": "disabled", "environment_keys": []},
                },
                context(),
                checkout_root=self.checkout,
                environment=self.environment,
            )
        finally:
            os.chdir(real_cwd)

        resolved_path = key_document["executable_identity"]["path"]
        self.assertTrue(resolved_path.startswith("container:fixture@sha256:"))
        self.assertNotIn(str(self.checkout.resolve()), resolved_path)

    def git_guard(self) -> dict[str, object]:
        return {
            "expected_branch": "integration",
            "expected_head_sha": SHA_B,
            "ignored_paths": [],
        }

    def test_optin_container_pass_reuses_only_in_this_runner(self) -> None:
        counter = self.root / "reuse-counter.txt"
        declaration = verifier(counter)
        declaration["cache"] = {
            "mode": "session_exact",
            "environment_keys": ["CI"],
            "deterministic_local": True,
        }
        cache = _ContainerResultCache()
        trust_calls: list[str] = []

        def fake_trust(**kwargs: object) -> str:
            trust_calls.append("trust")
            return "fixture@sha256:" + "1" * 64

        task_context = worker_context()
        task_context.update({"layer": "task", "task_id": "M1/T1"})
        first = run_verifier(
            declaration,
            task_context,
            checkout_root=self.checkout,
            cache_root=self.cache,
            environment=self.environment,
            git_guard=self.git_guard(),
            container_result_cache=cache,
        )
        second_context = worker_context()
        second_context["attempt_id"] = "A2"
        second_context["lease_id"] = "L2"
        with patch(
            "verifier_runtime._verify_container_runtime_identity",
            side_effect=fake_trust,
        ):
            second = run_verifier(
                declaration,
                second_context,
                checkout_root=self.checkout,
                cache_root=self.cache,
                environment=self.environment,
                git_guard=self.git_guard(),
                reservation={"node_id": "N", "attempt_id": "A2", "nonce": "x"},
                request_sha256="d" * 64,
                container_result_cache=cache,
            )

        self.assertEqual(first["cache_status"], "bypassed")
        self.assertEqual(first["cache_reason"], "same_runner_container_origin")
        self.assertEqual(second["cache_status"], "reused")
        self.assertEqual(second["cache_reason"], "same_runner_container_pass")
        self.assertEqual(1, self.read_count(counter))
        self.assertEqual(1, len(trust_calls))
        self.assertEqual(second["metrics"], {"executed": 0, "reused": 1})
        origin = second["container_reuse_origin"]
        self.assertEqual(origin["verifier_id"], first["verifier_id"])
        self.assertEqual(origin["execution_key"], second["execution_key"])
        self.assertEqual(
            origin["sandbox_attestation"],
            second["sandbox_attestation"],
        )
        self.assertEqual(
            second["git_guard_attestation"]["source_head_sha"], SHA_B
        )
        self.assertNotEqual(
            first["context"]["attempt_id"], second["context"]["attempt_id"]
        )

    def test_container_reuse_refails_when_live_guard_changes(self) -> None:
        counter = self.root / "guarded-reuse.txt"
        declaration = verifier(counter)
        declaration["cache"] = {
            "mode": "session_exact",
            "environment_keys": [],
            "deterministic_local": True,
        }
        cache = _ContainerResultCache()
        run_verifier(
            declaration,
            worker_context(),
            checkout_root=self.checkout,
            environment=self.environment,
            git_guard=self.git_guard(),
            container_result_cache=cache,
        )
        (self.checkout / ".fixture").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(VerifierRuntimeError, "dirty outside ignored paths"):
            run_verifier(
                declaration,
                worker_context(),
                checkout_root=self.checkout,
                environment=self.environment,
                git_guard=self.git_guard(),
                container_result_cache=cache,
            )

    def test_timings_are_observational_and_reuse_has_no_container_command(self) -> None:
        counter = self.root / "timing-counter.txt"
        declaration = verifier(counter)
        declaration["cache"] = {
            "mode": "session_exact",
            "environment_keys": [],
            "deterministic_local": True,
        }
        clock = {"value": 0.0}

        def controlled_clock() -> float:
            clock["value"] += 0.001
            return clock["value"]

        cache = _ContainerResultCache()
        with patch("verifier_runtime.time.perf_counter", side_effect=controlled_clock):
            with patch(
                "verifier_runtime._verify_container_runtime_identity",
                return_value="fixture@sha256:" + "1" * 64,
            ):
                first = run_verifier(
                    declaration,
                    worker_context(),
                    checkout_root=self.checkout,
                    environment=self.environment,
                    git_guard=self.git_guard(),
                    container_result_cache=cache,
                )
                second = run_verifier(
                    declaration,
                    worker_context(),
                    checkout_root=self.checkout,
                    environment=self.environment,
                    git_guard=self.git_guard(),
                    container_result_cache=cache,
                )

        expected = {
            "end_to_end_ms",
            "setup_ms",
            "git_guard_ms",
            "cache_lookup_ms",
            "snapshot_ms",
            "command_ms",
            "postcheck_ms",
        }
        self.assertEqual(expected, set(first["timings"]))
        self.assertEqual(expected, set(second["timings"]))
        self.assertGreater(first["duration_ms"], 0)
        self.assertLess(first["timings"]["command_ms"], first["duration_ms"])
        self.assertEqual(0, second["duration_ms"])
        self.assertEqual(0, second["timings"]["command_ms"])
        self.assertEqual(0, second["timings"]["snapshot_ms"])

    def test_same_batch_snapshot_reads_archive_once_but_extracts_twice(self) -> None:
        counter = self.root / "snapshot-counter.txt"
        declaration = verifier(counter)
        cache = _SnapshotArchiveCache()
        archive_calls: list[str] = []
        snapshot_roots: list[Path] = []
        original_run_git = verifier_runtime.run_git

        def counting_git(root, *args, **kwargs):
            if args and args[0] == "archive":
                archive_calls.append("archive")
            return original_run_git(root, *args, **kwargs)

        original_container = verifier_runtime._run_container_verifier

        def capture_container(
            _checkout: Path,
            snapshot_root: Path,
            *_args: object,
            **_kwargs: object,
        ):
            snapshot_roots.append(snapshot_root)
            return original_container(
                _checkout,
                snapshot_root,
                *_args,
                **_kwargs,
            )

        with (
            patch("verifier_runtime.run_git", counting_git),
            patch(
                "verifier_runtime._run_container_verifier",
                side_effect=capture_container,
            ),
        ):
            for _ in range(2):
                run_verifier(
                    declaration,
                    worker_context(),
                    checkout_root=self.checkout,
                    environment=self.environment,
                    git_guard=self.git_guard(),
                    snapshot_archive_cache=cache,
                )

        self.assertEqual(1, len(archive_calls))
        self.assertEqual(2, len(snapshot_roots))
        self.assertNotEqual(snapshot_roots[0], snapshot_roots[1])

    def test_scheduler_fills_a_slot_while_an_exclusive_job_waits(self) -> None:
        long_started = threading.Event()
        short_done = threading.Event()
        third_started = threading.Event()
        observed_long_active: list[bool] = []
        active: set[str] = set()
        active_lock = threading.Lock()

        def fake_run(verifier: dict[str, object], _context: object, **_kwargs: object) -> dict[str, object]:
            job = verifier["id"]
            with active_lock:
                active.add(job)
            if job == "long-exclusive":
                long_started.set()
                third_started.wait(1)
            elif job == "short-free":
                time.sleep(0.01)
                short_done.set()
            elif job == "third-free":
                short_done.wait(1)
                with active_lock:
                    observed_long_active.append("long-exclusive" in active)
                third_started.set()
            with active_lock:
                active.remove(job)
            return {"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}}

        long_job = self.batch_job("long-exclusive", resources=[{"key": "db", "access": "exclusive"}])
        long_job["reservation"] = {"node_id": "long-exclusive", "attempt_id": "A", "nonce": "n"}
        short_job = self.batch_job("short-free")
        short_job["reservation"] = {"node_id": "short-free", "attempt_id": "A", "nonce": "n"}
        third_job = self.batch_job("third-free")
        third_job["reservation"] = {"node_id": "third-free", "attempt_id": "A", "nonce": "n"}
        with patch("verifier_runtime.run_verifier", side_effect=fake_run):
            result = run_verifier_batch(
                [long_job, short_job, third_job],
                max_parallel=2,
            )

        self.assertEqual("PASS", result["status"])
        self.assertTrue(long_started.is_set())
        self.assertTrue(third_started.is_set())
        self.assertEqual([True], observed_long_active)
        self.assertEqual(2, result["metrics"]["max_parallel"])

    def test_container_execution_does_not_hold_runtime_lock_during_user_command(self) -> None:
        self._container_patch.stop()
        lock_seen_free = threading.Event()
        runtime_lock = verifier_runtime._RUNTIME_EXECUTION_LOCK

        def fake_runtime(*args: object, **kwargs: object):
            acquired: list[bool] = []

            def probe_lock() -> None:
                acquired.append(runtime_lock.acquire(blocking=False))
                if acquired[-1]:
                    runtime_lock.release()

            thread = threading.Thread(target=probe_lock)
            thread.start()
            thread.join(1)
            lock_seen_free.set() if acquired == [True] else None
            return subprocess.CompletedProcess(args[1], 0, "", "")

        declaration = {
            "id": "lock-probe",
            "cwd": ".",
            "argv": ["true"],
            "pass_signal": "exit 0",
            "execution": container_execution(),
            "cache": {"mode": "disabled", "environment_keys": []},
        }
        with (
            patch("verifier_runtime.shutil.which", return_value=str(Path(sys.executable).resolve())),
            patch(
                "verifier_runtime._verify_container_runtime_identity",
                return_value="fixture@sha256:" + "1" * 64,
            ),
            patch("verifier_runtime._run_bound_runtime", side_effect=fake_runtime),
        ):
            try:
                verifier_runtime._run_container_verifier(
                    self.checkout,
                    self.checkout,
                    ".",
                    declaration["argv"],
                    container_execution()["sandbox"],
                    1,
                    sandbox_preflight(declaration),
                )
            finally:
                self._container_patch.start()

        self.assertTrue(lock_seen_free.is_set())

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
            "timings": {
                "end_to_end_ms": 2,
                "setup_ms": 1,
                "git_guard_ms": 0,
                "cache_lookup_ms": 0,
                "snapshot_ms": 1,
                "command_ms": 1,
                "postcheck_ms": 0,
            },
            "container_reuse_origin": {
                "kind": "same_runner",
                "execution_key": "a" * 64,
                "verifier_id": "origin",
                "context_sha256": "d" * 64,
                "stdout_sha256": "b" * 64,
                "stderr_sha256": "c" * 64,
                "sandbox_attestation": {"image": "same"},
            },
        }
        self.assertEqual([], execution_retention_binding_errors(item))
        item["container_reuse_origin"]["execution_key"] = "e" * 64
        errors = execution_retention_binding_errors(item)
        self.assertTrue(any("execution key is rebound" in error for error in errors))
        errors = verifier_runtime.container_reuse_origin_run_errors(
            item,
            {"verifier_executions": []},
        )
        self.assertEqual(
            ["container reuse origin must match exactly one retained same-runner PASS"],
            errors,
        )

    def test_scheduler_returns_error_after_unexpected_worker_exception(self) -> None:
        with patch("verifier_runtime.run_verifier", side_effect=RuntimeError("sentinel")):
            result = run_verifier_batch([self.batch_job("broken")], max_parallel=1)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(["sentinel"], result["results"][0]["result"]["errors"])

    def test_failed_container_origin_releases_waiter_for_fresh_execution(self) -> None:
        declaration = verifier(self.root / "failure-flight.txt")
        declaration["cache"] = {"mode": "session_exact", "environment_keys": [], "deterministic_local": True}
        origin_entered = threading.Event()
        release = threading.Event()
        attempts_lock = threading.Lock()
        flight_acquire_attempts: list[int] = []

        def on_flight_acquire(lock: threading.Lock) -> None:
            with attempts_lock:
                attempt_number = len(flight_acquire_attempts) + 1
                flight_acquire_attempts.append(attempt_number)
            if attempt_number == 2:
                retry_waiting.set()

        class ObservedFlightLock:
            def __init__(self, lock: threading.Lock) -> None:
                self._lock = lock

            def acquire(self, *args: object, **kwargs: object) -> object:
                on_flight_acquire(self._lock)
                return self._lock.acquire(*args, **kwargs)

            def release(self) -> None:
                self._lock.release()

            def __enter__(self) -> "ObservedFlightLock":
                self.acquire()
                return self

            def __exit__(self, *args: object) -> None:
                self.release()

        class ObservedContainerCache(_ContainerResultCache):
            def flight(self, identity: str) -> object:
                return ObservedFlightLock(super().flight(identity))

        cache = ObservedContainerCache()
        retry_waiting = threading.Event()
        calls = []
        original_container = verifier_runtime._run_container_verifier

        def first_fails(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                origin_entered.set()
                self.assertTrue(release.wait(10))
                raise RuntimeError("origin failed")
            return original_container(*args, **kwargs)

        def execute():
            return run_verifier(declaration, worker_context(), checkout_root=self.checkout,
                                environment=self.environment, git_guard=self.git_guard(),
                                container_result_cache=cache)

        pool = ThreadPoolExecutor(max_workers=2)
        with patch("verifier_runtime._run_container_verifier", side_effect=first_fails):
            try:
                first = pool.submit(execute)
                self.assertTrue(origin_entered.wait(10))
                second = pool.submit(execute)

                # The second acquire attempt is observed while the failed
                # origin still owns the flight lock, before release is set.
                self.assertTrue(retry_waiting.wait(10))
                release.set()

                with self.assertRaisesRegex(RuntimeError, "origin failed"):
                    first.result(10)
                result = second.result(10)
            finally:
                release.set()
                pool.shutdown(wait=True, cancel_futures=True)
        self.assertEqual("PASS", result["status"])
        self.assertEqual("bypassed", result["cache_status"])
        self.assertEqual(2, len(calls))

    def test_container_cache_does_not_cross_git_guard_identity(self) -> None:
        counter = self.root / "guard-identity.txt"
        declaration = verifier(counter)
        declaration["cache"] = {"mode": "session_exact", "environment_keys": [], "deterministic_local": True}
        cache = _ContainerResultCache()
        for ignored in ([], ["never-created.txt"]):
            guard = self.git_guard()
            guard["ignored_paths"] = ignored
            result = run_verifier(declaration, worker_context(), checkout_root=self.checkout,
                                  environment=self.environment, git_guard=guard,
                                  container_result_cache=cache)
            self.assertEqual("bypassed", result["cache_status"])
        self.assertEqual(2, self.read_count(counter))

    def test_archive_single_flight_and_failed_origin_retry(self) -> None:
        cache = _SnapshotArchiveCache()
        entered = threading.Event()
        release = threading.Event()
        reads = []

        def read():
            reads.append(1)
            entered.set()
            self.assertTrue(release.wait(3))
            return b"archive"

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(cache.get_or_create, self.checkout, SHA_B, read)
            self.assertTrue(entered.wait(3))
            second = pool.submit(cache.get_or_create, self.checkout, SHA_B, read)
            release.set()
            self.assertEqual(b"archive", first.result(3))
            self.assertEqual(b"archive", second.result(3))
        self.assertEqual([1], reads)
        with self.assertRaisesRegex(RuntimeError, "failed"):
            cache.get_or_create(self.checkout, SHA_A, lambda: (_ for _ in ()).throw(RuntimeError("failed")))
        self.assertEqual(b"retry", cache.get_or_create(self.checkout, SHA_A, lambda: b"retry"))

    def test_container_single_flight_and_origin_evidence_validation(self) -> None:
        counter = self.root / "single-flight.txt"
        declaration = verifier(counter)
        declaration["cache"] = {"mode": "session_exact", "environment_keys": [], "deterministic_local": True}
        cache = _ContainerResultCache()
        started = threading.Event()
        release = threading.Event()
        original_container = verifier_runtime._run_container_verifier

        def blocked_container(*args, **kwargs):
            started.set()
            self.assertTrue(release.wait(5))
            return original_container(*args, **kwargs)

        def execute(candidate):
            return run_verifier(candidate, worker_context(), checkout_root=self.checkout,
                                environment=self.environment, git_guard=self.git_guard(),
                                container_result_cache=cache)

        with patch("verifier_runtime._run_container_verifier", side_effect=blocked_container), patch(
            "verifier_runtime._verify_container_runtime_identity", return_value="fixture@sha256:" + "1" * 64
        ), ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(execute, declaration)
            self.assertTrue(started.wait(5))
            consumer = copy.deepcopy(declaration)
            consumer["id"] = "consumer"
            second_future = pool.submit(execute, consumer)
            release.set()
            first, second = first_future.result(10), second_future.result(10)
        self.assertEqual(1, self.read_count(counter))
        self.assertEqual("reused", second["cache_status"])
        self.assertEqual([], execution_retention_binding_errors(second))
        self.assertEqual([], verifier_runtime.container_reuse_origin_run_errors(second, {"verifier_executions": [first, second]}))
        for mutation in ("missing", "context", "output", "sandbox", "declaration", "fresh"):
            changed = copy.deepcopy(second)
            if mutation == "missing":
                changed.pop("container_reuse_origin")
            elif mutation == "context":
                changed["container_reuse_origin"]["context_sha256"] = "f" * 64
            elif mutation == "output":
                changed["stdout"] += "forged"
            elif mutation == "sandbox":
                changed["container_reuse_origin"]["sandbox_attestation"]["image"] = "forged"
            elif mutation == "declaration":
                changed["verifier"]["cache"]["deterministic_local"] = False
            else:
                changed["cache_status"] = "bypassed"
            with self.subTest(mutation=mutation):
                self.assertTrue(execution_retention_binding_errors(changed) + verifier_runtime.container_reuse_origin_run_errors(changed, {"verifier_executions": [first]}))

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
            "execution": {
                "parallel_safe": parallel_safe,
                "resources": [] if resources is None else resources,
                "isolation": "container",
                "sandbox": container_execution()["sandbox"],
            },
        }
        return {
            "job_id": job_id,
            "verifier": candidate,
            "context": {},
            "checkout_root": str(self.checkout),
            "cache_root": None,
            "timeout_seconds": 5,
            "sandbox_preflight": sandbox_preflight(candidate),
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
        lock = threading.Lock()
        active = 0
        peak = 0

        def fake_run(*args: object, **kwargs: object) -> dict[str, object]:
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.03)
            with lock:
                active -= 1
            return {"protocol": PROTOCOL, "status": "PASS", "metrics": {"executed": 1, "reused": 0}}

        with patch(
            "verifier_runtime.run_verifier",
            side_effect=fake_run,
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
        self.assertEqual(2, peak)

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
