#!/usr/bin/env python3
"""Execute host verifiers singly or in a serial batch under the Git guard."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from select_verifiers import VerifierSelectionError, normalize_changed_files
import host_process
from harness_git import (
    GitMetadataError,
    reject_object_substitution,
    run_git,
)


PROTOCOL = "harness-verifier-execution-v2"
BATCH_PROTOCOL = "harness-verifier-batch-v1"
HOST_FINGERPRINT_KEYS = {"system", "machine", "release", "node_sha256"}
HOST_RUNTIME_VERSION_KEYS = {"system", "release", "machine"}
CONTEXT_FIELDS = {
    "run_id",
    "plan_revision",
    "plan_digest_sha256",
    "graph_revision",
    "batch_base_sha",
    "head_sha",
    "changed_files",
    "trust_domain",
    "checkout_role",
    "checkout_dirty",
    "cache_safe",
    "layer",
    "mission_id",
    "task_id",
    "attempt_id",
    "lease_id",
}
GIT_GUARD_FIELDS = {"expected_branch", "expected_head_sha", "ignored_paths"}
RESERVATION_FIELDS = {"node_id", "attempt_id", "nonce"}
BATCH_JOB_FIELDS = {
    "job_id",
    "verifier",
    "context",
    "checkout_root",
    "timeout_seconds",
}
# cache_root is accepted from older requests and ignored; there is no disk cache.
BATCH_JOB_OPTIONAL_FIELDS = {
    "cache_root",
    "git_guard",
    "reservation",
    "request_sha256",
    "sandbox_preflight",
    "host_preflight",
}


class VerifierRuntimeError(ValueError):
    """Raised when verifier execution inputs are unsafe or malformed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def copy_json(value: Any) -> Any:
    """Return a JSON-safe detached copy for retained verifier evidence."""

    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))


def host_runtime_fingerprint() -> dict[str, str]:
    """Return the stable, non-secret host and OS runtime fingerprint."""

    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "release": platform.release(),
        "node_sha256": _sha256_bytes(platform.node().encode("utf-8")),
    }


def host_runtime_version() -> dict[str, str]:
    """Return the OS runtime version observed without running project code."""

    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerifierRuntimeError(f"{label} must be a non-empty string")
    return value


def _require_sha(value: Any, label: str) -> str:
    checked = _require_string(value, label)
    if len(checked) not in {40, 64} or any(char not in "0123456789abcdef" for char in checked):
        raise VerifierRuntimeError(
            f"{label} must be 40 or 64 lowercase hexadecimal characters"
        )
    return checked


def _validated_host_preflight(value: Any) -> dict[str, Any]:
    """Validate and normalize the host identity bound to host execution."""

    required = {
        "isolation",
        "argv0",
        "executable",
        "executable_sha256",
        "runtime_version",
        "host",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise VerifierRuntimeError(
            "host execution requires the exact host preflight entry"
        )
    if value.get("isolation") != "host":
        raise VerifierRuntimeError("host preflight isolation differs from policy")
    _require_string(value.get("argv0"), "host preflight.argv0")
    executable = value.get("executable")
    if not isinstance(executable, str) or not executable or not Path(executable).is_absolute():
        raise VerifierRuntimeError(
            "host preflight executable must be a canonical absolute path"
        )
    canonical = str(Path(executable).resolve())
    if os.path.normcase(executable) != os.path.normcase(canonical):
        raise VerifierRuntimeError(
            "host preflight executable must be a canonical absolute path"
        )
    if re.fullmatch(r"[0-9a-f]{64}", str(value.get("executable_sha256", ""))) is None:
        raise VerifierRuntimeError(
            "host preflight executable_sha256 must be a lowercase SHA-256"
        )
    version = value.get("runtime_version")
    if not isinstance(version, dict) or set(version) != HOST_RUNTIME_VERSION_KEYS or any(
        not isinstance(version.get(key), str) for key in HOST_RUNTIME_VERSION_KEYS
    ):
        raise VerifierRuntimeError("host preflight runtime_version is malformed")
    host = value.get("host")
    if not isinstance(host, dict) or set(host) != HOST_FINGERPRINT_KEYS or any(
        not isinstance(host.get(key), str) for key in HOST_FINGERPRINT_KEYS
    ):
        raise VerifierRuntimeError("host preflight host fingerprint is malformed")
    normalized = copy_json(value)
    normalized["executable"] = canonical
    return normalized


def _reject_sandbox_preflight(value: Any) -> None:
    if value is not None:
        raise VerifierRuntimeError(
            "sandbox_preflight is not supported; verifiers run with execution.isolation=host"
        )


def _normalized_branch(value: str) -> str:
    return value.removeprefix("refs/heads/")


def _git_output(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    try:
        completed = run_git(root, *arguments, text=text, check=False, timeout=30)
    except GitMetadataError as exc:
        raise VerifierRuntimeError(str(exc)) from exc
    if completed.returncode != 0:
        raise VerifierRuntimeError(
            f"git {' '.join(arguments)} failed while checking verifier checkout"
        )
    return completed.stdout


def protected_path_sha256(
    checkout_root: Path, relative_paths: list[str]
) -> dict[str, str | None]:
    """Hash allowed-dirty files without letting them escape the checkout."""

    if not isinstance(relative_paths, list) or any(
        not isinstance(relative, str)
        or not relative
        or relative.startswith(("/", "\\"))
        or "\\" in relative
        or ".." in relative.split("/")
        or ":" in relative.split("/", 1)[0]
        for relative in relative_paths
    ):
        raise VerifierRuntimeError(
            "protected paths must be repository-relative POSIX paths"
        )
    root = checkout_root.resolve()
    protected: dict[str, str | None] = {}
    for relative in sorted(set(relative_paths)):
        path = root / relative
        if path.is_symlink():
            raise VerifierRuntimeError(
                f"git_guard protected path must not be a symlink: {relative}"
            )
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise VerifierRuntimeError(
                f"git_guard protected path escapes the checkout: {relative}"
            ) from exc
        try:
            value = resolved.read_bytes()
        except FileNotFoundError:
            protected[relative] = None
        except (IsADirectoryError, OSError) as exc:
            raise VerifierRuntimeError(
                f"cannot read git_guard protected path {relative}: {exc}"
            ) from exc
        else:
            protected[relative] = _sha256_bytes(value)
    return protected


def _protected_path_stats(
    checkout_root: Path, relative_paths: list[str]
) -> dict[str, list[int] | None]:
    """Fingerprint protected file identity so write-then-restore is visible."""

    root = checkout_root.resolve()
    stats: dict[str, list[int] | None] = {}
    for relative in sorted(set(relative_paths)):
        path = root / relative
        if path.is_symlink():
            raise VerifierRuntimeError(
                f"git_guard protected path must not be a symlink: {relative}"
            )
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise VerifierRuntimeError(
                f"git_guard protected path escapes the checkout: {relative}"
            ) from exc
        try:
            value = resolved.lstat()
        except FileNotFoundError:
            stats[relative] = None
        else:
            stats[relative] = [
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
                value.st_mode,
            ]
    return stats


def _git_guard_snapshot(
    checkout_root: Path, guard: dict[str, Any]
) -> dict[str, Any]:
    """Prove the requested committed checkout and fingerprint tracked files."""

    try:
        reject_object_substitution(checkout_root)
    except GitMetadataError as exc:
        raise VerifierRuntimeError(str(exc)) from exc
    if not isinstance(guard, dict) or set(guard) != GIT_GUARD_FIELDS:
        raise VerifierRuntimeError(
            "git_guard must contain expected_branch, expected_head_sha, and ignored_paths"
        )
    expected_branch = _require_string(
        guard["expected_branch"], "git_guard.expected_branch"
    )
    expected_head = _require_sha(
        guard["expected_head_sha"], "git_guard.expected_head_sha"
    )
    ignored = guard["ignored_paths"]
    if not isinstance(ignored, list) or any(
        not isinstance(path, str)
        or not path
        or path.startswith(("/", "\\"))
        or "\\" in path
        or ".." in path.split("/")
        for path in ignored
    ):
        raise VerifierRuntimeError(
            "git_guard.ignored_paths must be repository-relative POSIX paths"
        )
    ignored_set = set(ignored)
    branch = str(_git_output(checkout_root, "rev-parse", "--abbrev-ref", "HEAD")).strip()
    if branch == "HEAD" or _normalized_branch(branch) != _normalized_branch(
        expected_branch
    ):
        raise VerifierRuntimeError("verifier checkout branch differs from git_guard")
    head = str(_git_output(checkout_root, "rev-parse", "HEAD")).strip()
    if head != expected_head:
        raise VerifierRuntimeError("verifier checkout HEAD differs from git_guard")
    status_args = ["status", "--porcelain", "--untracked-files=all", "--", "."]
    status_args.extend(
        f":(exclude,top,literal){path}" for path in sorted(ignored_set)
    )
    if str(_git_output(checkout_root, *status_args)).strip():
        raise VerifierRuntimeError("verifier checkout is dirty outside ignored paths")

    raw_paths = _git_output(checkout_root, "ls-files", "-z", text=False)
    assert isinstance(raw_paths, bytes)
    fingerprint: dict[str, dict[str, Any] | None] = {}
    for raw_path in raw_paths.split(b"\0"):
        if not raw_path:
            continue
        relative = os.fsdecode(raw_path).replace("\\", "/")
        if relative in ignored_set:
            continue
        try:
            file_stat = (checkout_root / relative).lstat()
        except FileNotFoundError:
            fingerprint[relative] = None
        else:
            try:
                content_sha256 = _sha256_bytes((checkout_root / relative).read_bytes())
            except OSError as exc:
                raise VerifierRuntimeError(
                    f"cannot hash tracked verifier input {relative}: {exc}"
                ) from exc
            fingerprint[relative] = {
                "stat": [
                    file_stat.st_dev,
                    file_stat.st_ino,
                    file_stat.st_size,
                    file_stat.st_mtime_ns,
                    file_stat.st_ctime_ns,
                    file_stat.st_mode,
                ],
                "sha256": content_sha256,
            }
    return {
        "tracked_files": fingerprint,
        "protected_path_sha256": protected_path_sha256(
            checkout_root, sorted(ignored_set)
        ),
        "protected_path_stats": _protected_path_stats(
            checkout_root, sorted(ignored_set)
        ),
    }


def _validated_reservation(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != RESERVATION_FIELDS:
        raise VerifierRuntimeError(
            "reservation must contain node_id, attempt_id, and nonce"
        )
    return {
        key: _require_string(value[key], f"reservation.{key}")
        for key in ("node_id", "attempt_id", "nonce")
    }


def _resolve_cwd(checkout_root: Path, declared_cwd: Any) -> Path:
    cwd = Path(_require_string(declared_cwd, "verifier.cwd"))
    if cwd.is_absolute():
        raise VerifierRuntimeError("verifier.cwd must be repository-relative")
    root = checkout_root.resolve()
    resolved = (root / cwd).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise VerifierRuntimeError("verifier.cwd escapes the checkout root") from exc
    if not resolved.is_dir():
        raise VerifierRuntimeError("verifier.cwd must resolve to an existing directory")
    return resolved


def _resolve_executable(argv0: str, cwd: Path, environment: Mapping[str, str]) -> Path:
    candidate = Path(argv0)
    if argv0.startswith("./"):
        resolved = (cwd / candidate).resolve()
        if resolved.is_file():
            return resolved
    elif candidate.parent != Path("."):
        resolved = candidate if candidate.is_absolute() else cwd / candidate
        resolved = resolved.resolve()
        if resolved.is_file():
            return resolved
    found = shutil.which(argv0, path=environment.get("PATH"))
    if found is None:
        raise VerifierRuntimeError(f"executable {argv0!r} is unavailable")
    return Path(found).resolve()


def host_executable_identity(
    argv0: str, cwd: Path, environment: Mapping[str, str]
) -> dict[str, Any]:
    """Resolve and hash a declared host executable without invoking it."""

    executable = _resolve_executable(argv0, cwd, environment)
    try:
        info = executable.lstat()
    except OSError as exc:
        raise VerifierRuntimeError(
            f"host executable {argv0!r} is unavailable: {exc}"
        ) from exc
    if not executable.is_file():
        raise VerifierRuntimeError(
            f"host executable {argv0!r} must be a regular file"
        )
    if os.name == "nt":
        if executable.suffix.casefold() not in {".exe", ".com"}:
            raise VerifierRuntimeError(
                "Windows host executable must be a native .exe or .com, not a shell wrapper"
            )
        if getattr(info, "st_file_attributes", 0) & 0x0400:
            raise VerifierRuntimeError(
                "Windows host executable must not be a reparse point"
            )
    elif not info.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        raise VerifierRuntimeError(
            f"host executable {argv0!r} must have an execute bit"
        )
    try:
        digest = _sha256_bytes(executable.read_bytes())
    except OSError as exc:
        raise VerifierRuntimeError(
            f"cannot hash host executable {argv0!r}: {exc}"
        ) from exc
    return {
        "executable": str(executable),
        "executable_sha256": digest,
    }


def executable_identity(executable: Path) -> dict[str, Any]:
    stat = executable.stat()
    return {
        "path": os.path.normcase(str(executable)),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "device": stat.st_dev,
        "inode": stat.st_ino,
    }


def _environment_digests(
    keys: list[str], environment: Mapping[str, str]
) -> dict[str, str]:
    return {
        key: _sha256_bytes(environment.get(key, "").encode("utf-8"))
        for key in sorted(keys)
    }


def _execution_policy(verifier: dict[str, Any]) -> dict[str, Any]:
    value = verifier.get("execution")
    if value is None:
        raise VerifierRuntimeError(
            "verifier.execution is required; runtime verifier requests must declare isolation=host"
        )
    if not isinstance(value, dict) or set(value) != {"parallel_safe", "resources", "isolation"}:
        raise VerifierRuntimeError(
            "verifier.execution must contain parallel_safe/resources/isolation"
        )
    if value["isolation"] != "host":
        raise VerifierRuntimeError(
            "verifier.execution.isolation must be host; container isolation is not supported"
        )
    if not isinstance(value["parallel_safe"], bool):
        raise VerifierRuntimeError("verifier.execution.parallel_safe must be boolean")
    resources = value["resources"]
    if not isinstance(resources, list):
        raise VerifierRuntimeError("verifier.execution.resources must be an array")
    if value["parallel_safe"] is not False:
        raise VerifierRuntimeError("host verifier execution requires parallel_safe=false")
    normalized_resources: list[dict[str, str]] = []
    resource_keys: set[str] = set()
    for resource in resources:
        if not isinstance(resource, dict) or set(resource) != {"key", "access"}:
            raise VerifierRuntimeError(
                "each verifier.execution resource must contain exactly key and access"
            )
        key = _require_string(resource["key"], "verifier.execution.resources[].key")
        if key in resource_keys:
            raise VerifierRuntimeError("verifier.execution resource keys must be unique")
        resource_keys.add(key)
        access = resource["access"]
        if access not in {"shared_read", "exclusive"}:
            raise VerifierRuntimeError(
                "verifier.execution resource access must be shared_read or exclusive"
            )
        normalized_resources.append({"key": key, "access": access})
    return {
        "parallel_safe": value["parallel_safe"],
        "resources": sorted(normalized_resources, key=lambda item: item["key"]),
        "isolation": "host",
    }


def _plan_verifier_declarations(plan: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    declarations: list[tuple[str, dict[str, Any]]] = []
    for group in ("batch_verifiers", "final_gates"):
        values = plan.get(group, [])
        if isinstance(values, list):
            declarations.extend(
                (f"plan.{group}[{index}]", verifier)
                for index, verifier in enumerate(values)
                if isinstance(verifier, dict)
            )
    missions = plan.get("missions", [])
    if isinstance(missions, list):
        for mission_index, mission in enumerate(missions):
            if not isinstance(mission, dict):
                continue
            for group in ("worker_verifiers", "integration_verifiers"):
                values = mission.get(group, [])
                if isinstance(values, list):
                    declarations.extend(
                        (
                            f"plan.missions[{mission_index}].{group}[{index}]",
                            verifier,
                        )
                        for index, verifier in enumerate(values)
                        if isinstance(verifier, dict)
                    )
            tasks = mission.get("tasks", [])
            if isinstance(tasks, list):
                for task_index, task in enumerate(tasks):
                    if not isinstance(task, dict):
                        continue
                    values = task.get("verifiers", [])
                    if isinstance(values, list):
                        declarations.extend(
                            (
                                f"plan.missions[{mission_index}].tasks[{task_index}].verifiers[{index}]",
                                verifier,
                            )
                            for index, verifier in enumerate(values)
                            if isinstance(verifier, dict)
                        )
    return declarations


def observe_plan_host_runtimes(
    plan: Mapping[str, Any],
    checkout_root: Path,
    environment: Mapping[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Observe hashed host executables without invoking project code."""

    effective_environment = os.environ if environment is None else environment
    observations: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    root = checkout_root.resolve()
    for path, verifier in _plan_verifier_declarations(plan):
        try:
            policy = _execution_policy(verifier)
            if policy["isolation"] != "host":
                continue
            declared_cwd = Path(_require_string(verifier.get("cwd"), "verifier.cwd")).as_posix()
            argv = verifier.get("argv")
            if (
                not isinstance(argv, list)
                or not argv
                or any(not isinstance(item, str) or not item for item in argv)
            ):
                raise VerifierRuntimeError("verifier.argv must be a non-empty string array")
            cwd = _resolve_cwd(root, declared_cwd)
            identity = host_executable_identity(argv[0], cwd, effective_environment)
        except (OSError, ValueError, VerifierRuntimeError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        key = (argv[0], identity["executable"], identity["executable_sha256"])
        if key in seen:
            continue
        seen.add(key)
        observations.append(
            {
                "isolation": "host",
                "argv0": argv[0],
                **identity,
                "runtime_version": host_runtime_version(),
                "host": host_runtime_fingerprint(),
            }
        )
    return observations, sorted(set(errors))


def probe_plan_host_runtimes(
    plan: Mapping[str, Any],
    checkout_root: Path,
    environment: Mapping[str, str] | None = None,
) -> list[str]:
    """Read-only host executable preflight."""

    _observations, errors = observe_plan_host_runtimes(plan, checkout_root, environment)
    return errors


def _validated_inputs(
    verifier: dict[str, Any],
    context: dict[str, Any],
    checkout_root: Path,
    environment: Mapping[str, str],
) -> tuple[Path, list[str], dict[str, Any], dict[str, Any]]:
    unknown = set(context) - CONTEXT_FIELDS
    missing = CONTEXT_FIELDS - set(context)
    if unknown or missing:
        parts = []
        if missing:
            parts.append("missing context keys: " + ", ".join(sorted(missing)))
        if unknown:
            parts.append("unknown context keys: " + ", ".join(sorted(unknown)))
        raise VerifierRuntimeError("; ".join(parts))

    _require_string(context["run_id"], "context.run_id")
    if not isinstance(context["plan_revision"], int) or isinstance(
        context["plan_revision"], bool
    ):
        raise VerifierRuntimeError("context.plan_revision must be an integer")
    _require_sha(context["plan_digest_sha256"], "context.plan_digest_sha256")
    if context["graph_revision"] is not None and not isinstance(
        context["graph_revision"], int
    ):
        raise VerifierRuntimeError("context.graph_revision must be null or an integer")
    _require_sha(context["batch_base_sha"], "context.batch_base_sha")
    _require_sha(context["head_sha"], "context.head_sha")
    if not isinstance(context["changed_files"], list):
        raise VerifierRuntimeError("context.changed_files must be an array")
    try:
        changed_files = normalize_changed_files(context["changed_files"])
    except VerifierSelectionError as exc:
        raise VerifierRuntimeError(str(exc)) from exc
    _require_string(context["trust_domain"], "context.trust_domain")
    _require_string(context["checkout_role"], "context.checkout_role")
    layer = _require_string(context["layer"], "context.layer")
    if layer not in {"task", "worker", "mission_integration", "batch", "final"}:
        raise VerifierRuntimeError("context.layer is unsupported")
    for key in ("mission_id", "task_id", "attempt_id", "lease_id"):
        value = context[key]
        if value is not None:
            _require_string(value, f"context.{key}")
    for key in ("checkout_dirty", "cache_safe"):
        if not isinstance(context[key], bool):
            raise VerifierRuntimeError(f"context.{key} must be boolean")
    if context["layer"] == "task" and any(
        context[key] is None for key in ("mission_id", "task_id", "attempt_id", "lease_id")
    ):
        raise VerifierRuntimeError(
            "task verifier context requires mission_id, task_id, attempt_id, and lease_id"
        )
    if context["layer"] == "worker" and (
        any(context[key] is None for key in ("mission_id", "attempt_id", "lease_id"))
        or context["task_id"] is not None
    ):
        raise VerifierRuntimeError(
            "worker verifier context requires mission_id, attempt_id, lease_id, and null task_id"
        )
    if context["layer"] == "mission_integration" and (
        context["mission_id"] is None
        or any(context[key] is not None for key in ("task_id", "attempt_id", "lease_id"))
    ):
        raise VerifierRuntimeError(
            "mission_integration verifier context requires mission_id and null task/attempt/lease IDs"
        )
    if context["layer"] in {"batch", "final"} and any(
        context[key] is not None
        for key in ("mission_id", "task_id", "attempt_id", "lease_id")
    ):
        raise VerifierRuntimeError(
            f"{context['layer']} verifier context requires null mission/task/attempt/lease IDs"
        )

    verifier_id = _require_string(verifier.get("id"), "verifier.id")
    pass_signal = _require_string(verifier.get("pass_signal"), "verifier.pass_signal")
    argv = verifier.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or any(not isinstance(item, str) or not item for item in argv)
    ):
        raise VerifierRuntimeError("verifier.argv must be a non-empty string array")
    declared_cwd = Path(_require_string(verifier.get("cwd"), "verifier.cwd")).as_posix()
    execution = _execution_policy(verifier)
    declared_path = Path(declared_cwd)
    if declared_path.is_absolute() or ".." in declared_path.parts:
        raise VerifierRuntimeError("verifier cwd must be repository-relative")
    cwd = _resolve_cwd(checkout_root.resolve(), declared_cwd)
    identity = executable_identity(_resolve_executable(argv[0], cwd, environment))
    read_only = verifier.get("read_only", False)
    if not isinstance(read_only, bool):
        raise VerifierRuntimeError("verifier.read_only must be boolean")
    if "acceptance_test_ids" in verifier:
        raw_acceptance_test_ids = verifier["acceptance_test_ids"]
        if (
            not isinstance(raw_acceptance_test_ids, list)
            or not raw_acceptance_test_ids
            or any(
                not isinstance(item, str) or not item.startswith("TEST-")
                for item in raw_acceptance_test_ids
            )
            or len(raw_acceptance_test_ids) != len(set(raw_acceptance_test_ids))
        ):
            raise VerifierRuntimeError(
                "verifier.acceptance_test_ids must be a nonempty unique TEST-* string array"
            )
        acceptance_test_ids = sorted(raw_acceptance_test_ids)
    else:
        acceptance_test_ids = None

    cache = verifier.get("cache")
    if cache is None:
        cache = {"mode": "disabled", "environment_keys": []}
    if not isinstance(cache, dict) or not {"mode", "environment_keys"} <= set(cache) or not set(
        cache
    ) <= {"mode", "environment_keys", "deterministic_local"}:
        raise VerifierRuntimeError(
            "verifier.cache must contain mode and environment_keys, and may add deterministic_local"
        )
    deterministic_local = cache.get("deterministic_local", False)
    if not isinstance(deterministic_local, bool):
        raise VerifierRuntimeError("verifier.cache.deterministic_local must be boolean")
    if cache["mode"] not in {"disabled", "session_exact"}:
        raise VerifierRuntimeError("verifier.cache.mode is unsupported")
    if cache["mode"] != "disabled" or deterministic_local:
        raise VerifierRuntimeError("host verifier execution requires disabled cache")
    environment_keys = cache["environment_keys"]
    if (
        not isinstance(environment_keys, list)
        or any(not isinstance(key, str) or not key for key in environment_keys)
        or len(environment_keys) != len(set(environment_keys))
    ):
        raise VerifierRuntimeError(
            "verifier.cache.environment_keys must be a unique string array"
        )

    normalized_verifier = {
        "id": verifier_id,
        "cwd": declared_cwd,
        "argv": argv,
        "pass_signal": pass_signal,
        "cache": cache,
    }
    if "read_only" in verifier:
        normalized_verifier["read_only"] = read_only
    if acceptance_test_ids is not None:
        normalized_verifier["acceptance_test_ids"] = acceptance_test_ids
    normalized_verifier["execution"] = execution
    normalized_context = {**context, "changed_files": changed_files}
    return cwd, argv, normalized_verifier, {
        "context": normalized_context,
        "executable_identity": identity,
        "environment_digests": _environment_digests(environment_keys, environment),
    }


def execution_key_from_document(key_document: dict[str, Any]) -> str:
    """Recompute the immutable execution key from a retained parent result."""

    return _sha256_bytes(_canonical_json(key_document))


def build_execution_key(
    verifier: dict[str, Any],
    context: dict[str, Any],
    *,
    checkout_root: Path,
    environment: Mapping[str, str] | None = None,
    sandbox_preflight: dict[str, Any] | None = None,
    host_preflight: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    _reject_sandbox_preflight(sandbox_preflight)
    effective_environment = os.environ if environment is None else environment
    _, _, normalized_verifier, key_inputs = _validated_inputs(
        verifier,
        context,
        checkout_root,
        effective_environment,
    )
    _, key_document = _key_document(normalized_verifier, key_inputs)
    if host_preflight is None:
        raise VerifierRuntimeError("host execution requires host_preflight")
    key_document["host_preflight"] = copy_json(
        _validated_host_preflight(host_preflight)
    )
    if host_preflight["argv0"] != normalized_verifier["argv"][0]:
        raise VerifierRuntimeError("host preflight argv0 differs from the declaration")
    return execution_key_from_document(key_document), key_document


def _key_document(
    normalized_verifier: dict[str, Any], key_inputs: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    # Logical gate labels belong to retained evidence, not execution identity.
    # Omitting verifier/layer/mission/task/attempt/lease attribution lets an
    # equivalent opted-in task and worker check reuse one exact execution while
    # each gate still records its own verifier ID and context in the result.
    key_document = {
        "protocol": PROTOCOL,
        "run_id": key_inputs["context"]["run_id"],
        "plan_revision": key_inputs["context"]["plan_revision"],
        "plan_digest_sha256": key_inputs["context"]["plan_digest_sha256"],
        "graph_revision": key_inputs["context"]["graph_revision"],
        "batch_base_sha": key_inputs["context"]["batch_base_sha"],
        "head_sha": key_inputs["context"]["head_sha"],
        "changed_files_digest": _sha256_bytes(
            _canonical_json(key_inputs["context"]["changed_files"])
        ),
        "trust_domain": key_inputs["context"]["trust_domain"],
        "checkout_role": key_inputs["context"]["checkout_role"],
        "checkout_dirty": key_inputs["context"]["checkout_dirty"],
        "cache_safe": key_inputs["context"]["cache_safe"],
        "cwd": normalized_verifier["cwd"],
        "argv": normalized_verifier["argv"],
        "pass_signal": normalized_verifier["pass_signal"],
        "read_only": normalized_verifier.get("read_only", False),
        "execution": copy_json(normalized_verifier["execution"]),
        "cache_mode": normalized_verifier["cache"]["mode"],
        "environment_keys": sorted(normalized_verifier["cache"]["environment_keys"]),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "executable_identity": key_inputs["executable_identity"],
        "environment_digests": key_inputs["environment_digests"],
    }
    return execution_key_from_document(key_document), key_document


def _host_attestation(
    cwd: Path,
    executable: Path,
    executable_sha256: str,
) -> dict[str, Any]:
    return {
        "isolation": "host",
        "cwd": str(cwd.resolve()),
        "host": host_runtime_fingerprint(),
        "runtime_version": host_runtime_version(),
        "executable": {
            "path": str(executable.resolve()),
            "sha256": executable_sha256,
        },
    }


def _verify_host_runtime_identity(
    argv0: str,
    cwd: Path,
    environment: Mapping[str, str],
    checked_preflight: dict[str, Any],
) -> tuple[Path, str]:
    """Freshly verify the resolved host executable before or after invocation."""

    identity = host_executable_identity(argv0, cwd, environment)
    if checked_preflight["host"] != host_runtime_fingerprint() or checked_preflight["runtime_version"] != host_runtime_version():
        raise VerifierRuntimeError("host identity changed since preflight")
    executable = Path(identity["executable"])
    if os.path.normcase(str(executable.resolve())) != os.path.normcase(
        str(Path(checked_preflight["executable"]))
    ):
        raise VerifierRuntimeError("host executable path changed since preflight")
    if identity["executable_sha256"] != checked_preflight["executable_sha256"]:
        raise VerifierRuntimeError("host executable changed since preflight")
    return executable, identity["executable_sha256"]


def _host_cache_allowed(normalized_verifier: Mapping[str, Any]) -> bool:
    cache = normalized_verifier["cache"]
    return bool(
        cache["mode"] == "disabled"
        and cache.get("environment_keys") == []
        and cache.get("deterministic_local", False) is False
    )


def execution_retention_binding_errors(
    item: Mapping[str, Any], *, require_host_evidence: bool = False,
) -> list[str]:
    """Check host identity; current PASS evidence requires both attestations."""
    errors: list[str] = []
    duration = item.get("duration_ms")
    if duration is not None and (not isinstance(duration, int) or isinstance(duration, bool) or duration < 0):
        errors.append("duration_ms must be a non-negative integer")
    attestation = item.get("host_execution_attestation")
    if attestation is None:
        return errors + (["current host PASS requires host_execution_attestation"] if require_host_evidence else [])
    document = item.get("key_document")
    preflight = document.get("host_preflight") if isinstance(document, dict) else None
    try:
        checked = _validated_host_preflight(preflight)
    except VerifierRuntimeError as exc:
        return errors + [str(exc)]
    if not isinstance(attestation, dict) or set(attestation) != {"isolation", "cwd", "host", "runtime_version", "executable"}:
        return errors + ["host execution must retain the complete host attestation"]
    if attestation["isolation"] != "host":
        errors.append("host attestation isolation differs from the declaration")
    for name in ("host", "runtime_version"):
        if attestation[name] != checked[name]:
            errors.append(f"host attestation {name} differs from preflight")
    if attestation["executable"] != {"path": checked["executable"], "sha256": checked["executable_sha256"]}:
        errors.append("host attestation executable differs from preflight")
    identity = document.get("executable_identity")
    if require_host_evidence and (not isinstance(identity, dict)
            or identity.get("path") != os.path.normcase(checked["executable"])):
        errors.append("execution executable identity differs from host preflight")
    argv = document.get("argv")
    if not isinstance(argv, list) or not argv or argv[0] != checked["argv0"]:
        errors.append("host preflight argv0 differs from the declared command")
    guard = item.get("git_guard_attestation")
    if require_host_evidence:
        required = {"checkout_root", "git_guard", "isolation_mode", "source_head_sha", "tracked_files",
                    "protected_path_sha256", "protected_path_stats", "host_execution_attestation"}
        if not isinstance(guard, dict) or set(guard) != required:
            errors.append("current host PASS requires complete git_guard_attestation")
        elif guard["host_execution_attestation"] != attestation:
            errors.append("nested host_execution_attestation differs from host execution")
        elif guard["isolation_mode"] != "host":
            errors.append("Git attestation isolation differs from host execution")
    root = guard.get("checkout_root") if isinstance(guard, dict) else None
    cwd = document.get("cwd")
    if isinstance(root, str) and isinstance(cwd, str):
        if attestation["cwd"] != str((Path(root) / cwd).resolve()):
            errors.append("host attestation cwd differs from the declared checkout cwd")
    return errors


def run_verifier(
    verifier: dict[str, Any],
    context: dict[str, Any],
    *,
    checkout_root: Path,
    timeout_seconds: float = 120.0,
    environment: Mapping[str, str] | None = None,
    git_guard: dict[str, Any] | None = None,
    reservation: dict[str, Any] | None = None,
    request_sha256: str | None = None,
    sandbox_preflight: dict[str, Any] | None = None,
    host_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise VerifierRuntimeError("timeout_seconds must be positive")
    _reject_sandbox_preflight(sandbox_preflight)
    effective_environment = dict(os.environ if environment is None else environment)
    cwd, argv, normalized_verifier, key_inputs = _validated_inputs(
        verifier,
        context,
        checkout_root,
        effective_environment,
    )
    checked_host_preflight = _validated_host_preflight(host_preflight)
    _, key_document = _key_document(normalized_verifier, key_inputs)
    if checked_host_preflight["argv0"] != argv[0]:
        raise VerifierRuntimeError("host preflight argv0 differs from declaration")
    key_document["host_preflight"] = copy_json(checked_host_preflight)
    execution_key = execution_key_from_document(key_document)
    if git_guard is None:
        raise VerifierRuntimeError("host verifier requests require a live git_guard")
    if not _host_cache_allowed(normalized_verifier):
        raise VerifierRuntimeError("host verifier execution requires disabled cache")
    checked_reservation = _validated_reservation(reservation)
    context_layer = key_inputs["context"].get("layer")
    context_role = key_inputs["context"].get("checkout_role")
    if (
        context_layer in {"task", "worker"}
        and context_role == "worker"
        and normalized_verifier.get("read_only") is not True
    ):
        raise VerifierRuntimeError(
            "current task/worker verifier commands require an explicit read_only declaration"
        )
    if not isinstance(git_guard, dict) or git_guard.get("expected_head_sha") != key_inputs["context"].get("head_sha"):
        raise VerifierRuntimeError(
            "git_guard.expected_head_sha must equal context.head_sha"
        )
    if checked_reservation is not None and (
        not isinstance(request_sha256, str)
        or len(request_sha256) != 64
        or any(char not in "0123456789abcdef" for char in request_sha256)
    ):
        raise VerifierRuntimeError(
            "a reserved verifier requires git_guard and the canonical request SHA-256"
        )
    guard_snapshot = _git_guard_snapshot(checkout_root.resolve(), git_guard)
    git_guard_attestation = {
        "checkout_root": str(checkout_root.resolve()),
        "git_guard": json.loads(json.dumps(git_guard)),
        "isolation_mode": "host",
        "source_head_sha": key_inputs["context"]["head_sha"],
        "tracked_files": copy_json(guard_snapshot["tracked_files"]),
        "protected_path_sha256": dict(guard_snapshot["protected_path_sha256"]),
        "protected_path_stats": copy_json(guard_snapshot["protected_path_stats"]),
    }
    dispatch_attestation = None
    if checked_reservation is not None:
        dispatch_attestation = {
            "request_sha256": request_sha256,
            "checkout_root": str(checkout_root.resolve()),
            "git_guard": json.loads(json.dumps(git_guard)),
            "protected_path_sha256": dict(guard_snapshot["protected_path_sha256"]),
        }

    execution_argv = [checked_host_preflight["executable"], *argv[1:]]
    started = time.perf_counter()
    try:
        _verify_host_runtime_identity(
            argv[0],
            cwd,
            effective_environment,
            checked_host_preflight,
        )
        host_result = host_process.run_process_tree(
            execution_argv,
            cwd=cwd,
            environment=effective_environment,
            timeout_seconds=timeout_seconds,
        )
        if host_result.timeout:
            raise subprocess.TimeoutExpired(
                execution_argv,
                timeout_seconds,
                output=host_result.stdout,
                stderr=host_result.stderr,
            )
        status = "PASS" if host_result.exit_code == 0 else "FAIL"
        exit_code = host_result.exit_code
        stdout = host_result.stdout
        stderr = host_result.stderr
    except subprocess.TimeoutExpired as exc:
        status = "TIMEOUT"
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    except host_process.HostProcessError as exc:
        status = "ERROR"
        exit_code = None
        stdout = exc.stdout
        stderr = (exc.stderr + "\n" if exc.stderr else "") + str(exc)
    except OSError as exc:
        status = "ERROR"
        exit_code = None
        stdout = ""
        stderr = str(exc)
    try:
        if _git_guard_snapshot(checkout_root.resolve(), git_guard) != guard_snapshot:
            raise VerifierRuntimeError(
                "tracked or protected verifier inputs changed while the command was running"
            )
    except VerifierRuntimeError as exc:
        status = "ERROR"
        exit_code = None
        stderr = (stderr + "\n" if stderr else "") + str(exc)
    host_attestation = None
    try:
        executable, executable_sha256 = _verify_host_runtime_identity(
            argv[0],
            cwd,
            effective_environment,
            checked_host_preflight,
        )
        host_attestation = _host_attestation(cwd, executable, executable_sha256)
        git_guard_attestation["host_execution_attestation"] = copy_json(
            host_attestation
        )
    except VerifierRuntimeError as exc:
        status = "ERROR"
        exit_code = None
        stderr = (stderr + "\n" if stderr else "") + str(exc)
    duration_ms = max(0, round((time.perf_counter() - started) * 1000))
    return {
        "protocol": PROTOCOL,
        "verifier_id": normalized_verifier["id"],
        "status": status,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "execution_key": execution_key,
        "evidence_key": execution_key,
        "verifier": normalized_verifier,
        "context": key_inputs["context"],
        "key_document": key_document,
        "cache_status": "bypassed",
        "cache_reason": "host_cache_disabled",
        "duration_ms": duration_ms,
        "metrics": {"executed": 1, "reused": 0},
        **({"reservation": checked_reservation} if checked_reservation is not None else {}),
        **(
            {"dispatch_attestation": dispatch_attestation}
            if dispatch_attestation is not None
            else {}
        ),
        "git_guard_attestation": git_guard_attestation,
        **(
            {"host_execution_attestation": host_attestation}
            if host_attestation is not None
            else {}
        ),
    }


def run_verifier_batch(
    jobs: list[dict[str, Any]],
    *,
    max_parallel: int,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute host verifier jobs one at a time, ordered by job id.

    Host verifiers require ``parallel_safe=false``, so no two can overlap.
    ``max_parallel`` is validated to keep the request shape and reported as 1.
    """

    if not isinstance(jobs, list) or not jobs:
        raise VerifierRuntimeError("jobs must be a non-empty array")
    if (
        not isinstance(max_parallel, int)
        or isinstance(max_parallel, bool)
        or max_parallel <= 0
    ):
        raise VerifierRuntimeError("max_parallel must be a positive integer")

    prepared: list[tuple[str, dict[str, Any]]] = []
    job_ids: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict) or not BATCH_JOB_FIELDS.issubset(job) or not set(job).issubset(
            BATCH_JOB_FIELDS | BATCH_JOB_OPTIONAL_FIELDS
        ):
            raise VerifierRuntimeError(
                "each job must contain exactly job_id, verifier, context, checkout_root, "
                "and timeout_seconds; task/worker jobs also require git_guard"
            )
        job_id = _require_string(job["job_id"], "job.job_id")
        if job_id in job_ids:
            raise VerifierRuntimeError("job.job_id must be unique")
        job_ids.add(job_id)
        if not isinstance(job["verifier"], dict):
            raise VerifierRuntimeError("job.verifier must be an object")
        if not isinstance(job["context"], dict):
            raise VerifierRuntimeError("job.context must be an object")
        if (
            job["context"].get("layer") in {"task", "worker"}
            and job["context"].get("checkout_role") == "worker"
            and not isinstance(job.get("git_guard"), dict)
        ):
            raise VerifierRuntimeError(
                "task/worker verifier batch jobs require git_guard"
            )
        checkout_root = _require_string(job["checkout_root"], "job.checkout_root")
        timeout_seconds = job["timeout_seconds"]
        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise VerifierRuntimeError("job.timeout_seconds must be positive")
        _execution_policy(job["verifier"])
        prepared.append((job_id, {**job, "checkout_root": checkout_root}))

    prepared.sort(key=lambda item: item[0])
    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    for job_id, job in prepared:
        try:
            result = run_verifier(
                job["verifier"],
                job["context"],
                checkout_root=Path(job["checkout_root"]),
                timeout_seconds=float(job["timeout_seconds"]),
                environment=environment,
                git_guard=job.get("git_guard"),
                reservation=job.get("reservation"),
                request_sha256=job.get("request_sha256"),
                sandbox_preflight=job.get("sandbox_preflight"),
                host_preflight=job.get("host_preflight"),
            )
        except Exception as exc:
            result = {"protocol": PROTOCOL, "status": "ERROR", "errors": [str(exc)]}
        results.append({"job_id": job_id, "result": result})
    duration_ms = max(0, round((time.perf_counter() - started) * 1000))
    passed = all(item["result"].get("status") == "PASS" for item in results)
    return {
        "protocol": BATCH_PROTOCOL,
        "status": "PASS" if passed else "FAIL",
        "results": results,
        "metrics": {
            "duration_ms": duration_ms,
            "max_parallel": 1,
            "executed": sum(
                item["result"].get("metrics", {}).get("executed", 0) for item in results
            ),
            "reused": sum(
                item["result"].get("metrics", {}).get("reused", 0) for item in results
            ),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one local verifier or one resource-safe verifier batch."
    )
    parser.add_argument("--request", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise VerifierRuntimeError("request must be a JSON object")
        if "jobs" in request:
            result = run_verifier_batch(
                request["jobs"],
                max_parallel=request.get("max_parallel", 1),
            )
        else:
            request_sha256 = _sha256_bytes(_canonical_json(request))
            result = run_verifier(
                request["verifier"],
                request["context"],
                checkout_root=Path(request["checkout_root"]),
                timeout_seconds=float(request.get("timeout_seconds", 120.0)),
                git_guard=request.get("git_guard"),
                reservation=request.get("reservation"),
                request_sha256=request_sha256,
                sandbox_preflight=request.get("sandbox_preflight"),
                host_preflight=request.get("host_preflight"),
            )
    except (KeyError, OSError, ValueError, VerifierRuntimeError) as exc:
        print(
            json.dumps(
                {"protocol": PROTOCOL, "status": "ERROR", "errors": [str(exc)]},
                sort_keys=True,
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
