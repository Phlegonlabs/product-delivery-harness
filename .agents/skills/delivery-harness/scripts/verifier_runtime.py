#!/usr/bin/env python3
"""Execute local verifiers singly or in resource-safe batches."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

from select_verifiers import VerifierSelectionError, normalize_changed_files


PROTOCOL = "harness-verifier-execution-v2"
BATCH_PROTOCOL = "harness-verifier-batch-v1"
# Integration, batch, and final gates refuse cache reuse by default, in PLAN
# validation (harness_core.py's cache_allowed=False) and again here.
#
# This is no longer defense in depth against a hand-built request. A verifier
# may attest `cache.deterministic_local: true` to reuse at these layers, and
# that flag travels inside the same request this check would otherwise guard.
# A caller who hand-builds a final-layer request can therefore assert its way
# past the ban. The real protection is PLAN validation of a declared verifier;
# what remains here is a default for anything that did not make the claim.
CACHE_BANNED_LAYERS = {"mission_integration", "batch", "final"}
CACHE_ENTRY_FIELDS = {
    "protocol",
    "execution_key",
    "status",
    "exit_code",
    "stdout",
    "stderr",
    "executable_identity",
}
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
    "cache_root",
    "timeout_seconds",
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


def _normalized_branch(value: str) -> str:
    return value.removeprefix("refs/heads/")


def _git_output(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=text,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise VerifierRuntimeError(
            f"git {' '.join(arguments)} failed while checking verifier checkout"
        )
    return completed.stdout


def _git_guard_snapshot(
    checkout_root: Path, guard: dict[str, Any]
) -> dict[str, tuple[int, int, int] | None]:
    """Prove the requested committed checkout and fingerprint tracked files."""

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
    fingerprint: dict[str, tuple[int, int, int] | None] = {}
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
            fingerprint[relative] = (
                file_stat.st_size,
                file_stat.st_mtime_ns,
                file_stat.st_mode,
            )
    return fingerprint


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
        # A verifier that declares no execution block also claims no resource.
        # Two such verifiers cannot contend, so batching them is safe and is the
        # common case (lint, typecheck, unit tests). Anything that binds a port,
        # database, or other shared resource must declare it, and may still set
        # parallel_safe: false explicitly to force serial execution.
        return {"parallel_safe": True, "resources": []}
    if not isinstance(value, dict) or set(value) != {"parallel_safe", "resources"}:
        raise VerifierRuntimeError(
            "verifier.execution must contain exactly parallel_safe and resources"
        )
    if not isinstance(value["parallel_safe"], bool):
        raise VerifierRuntimeError("verifier.execution.parallel_safe must be boolean")
    resources = value["resources"]
    if not isinstance(resources, list):
        raise VerifierRuntimeError("verifier.execution.resources must be an array")
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
    }


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
    cwd = _resolve_cwd(checkout_root, declared_cwd)
    executable = _resolve_executable(argv[0], cwd, environment)
    identity = executable_identity(executable)
    execution = _execution_policy(verifier)

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
    if verifier.get("execution") is not None:
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
) -> tuple[str, dict[str, Any]]:
    effective_environment = os.environ if environment is None else environment
    _, _, normalized_verifier, key_inputs = _validated_inputs(
        verifier,
        context,
        checkout_root,
        effective_environment,
    )
    return _key_document(normalized_verifier, key_inputs)


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


def _cache_path(cache_root: Path, execution_key: str) -> Path:
    return cache_root / PROTOCOL / f"{execution_key}.json"


def _load_cache_entry(
    path: Path,
    execution_key: str,
    expected_executable_identity: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, "cache_entry_missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "cache_entry_malformed"
    if not isinstance(value, dict) or set(value) != CACHE_ENTRY_FIELDS:
        return None, "cache_entry_malformed"
    if (
        value.get("protocol") != PROTOCOL
        or value.get("execution_key") != execution_key
        or value.get("status") != "PASS"
        or value.get("exit_code") != 0
        or not isinstance(value.get("stdout"), str)
        or not isinstance(value.get("stderr"), str)
        or value.get("executable_identity") != expected_executable_identity
    ):
        return None, "cache_entry_invalid"
    return value, "exact_input_hit"


def _write_cache_entry(path: Path, entry: dict[str, Any]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(entry, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
    except FileExistsError:
        return False
    return True


def run_verifier(
    verifier: dict[str, Any],
    context: dict[str, Any],
    *,
    checkout_root: Path,
    cache_root: Path | None = None,
    timeout_seconds: float = 120.0,
    environment: Mapping[str, str] | None = None,
    git_guard: dict[str, Any] | None = None,
    reservation: dict[str, Any] | None = None,
    request_sha256: str | None = None,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise VerifierRuntimeError("timeout_seconds must be positive")
    effective_environment = dict(os.environ if environment is None else environment)
    cwd, argv, normalized_verifier, key_inputs = _validated_inputs(
        verifier,
        context,
        checkout_root,
        effective_environment,
    )
    execution_key, key_document = _key_document(normalized_verifier, key_inputs)
    checked_reservation = _validated_reservation(reservation)
    dispatch_attestation = None
    if checked_reservation is not None:
        if git_guard is None or not isinstance(request_sha256, str) or (
            len(request_sha256) != 64
            or any(char not in "0123456789abcdef" for char in request_sha256)
        ):
            raise VerifierRuntimeError(
                "a reserved verifier requires git_guard and the canonical request SHA-256"
            )
        dispatch_attestation = {
            "request_sha256": request_sha256,
            "checkout_root": str(checkout_root.resolve()),
            "git_guard": json.loads(json.dumps(git_guard)),
        }
    guard_snapshot = (
        _git_guard_snapshot(checkout_root.resolve(), git_guard)
        if git_guard is not None
        else None
    )
    cache_mode = normalized_verifier["cache"]["mode"]
    cache_status = "bypassed"
    cache_reason = "cache_disabled"
    cache_path: Path | None = None
    can_reuse = cache_mode == "session_exact"
    if (
        can_reuse
        and key_inputs["context"]["layer"] in CACHE_BANNED_LAYERS
        and not normalized_verifier["cache"].get("deterministic_local", False)
    ):
        can_reuse = False
        cache_reason = "layer_not_cacheable"
    elif can_reuse and normalized_verifier["pass_signal"] != "exit 0":
        can_reuse = False
        cache_reason = "pass_signal_not_cacheable"
    elif can_reuse and not key_inputs["context"]["cache_safe"]:
        can_reuse = False
        cache_reason = "not_declared_deterministic_local"
    elif can_reuse and key_inputs["context"]["checkout_dirty"]:
        can_reuse = False
        cache_reason = "checkout_dirty"
    elif can_reuse and cache_root is None:
        can_reuse = False
        cache_reason = "cache_root_missing"
    elif can_reuse:
        root = cache_root.resolve()
        checkout = checkout_root.resolve()
        try:
            root.relative_to(checkout)
        except ValueError:
            cache_path = _cache_path(root, execution_key)
            entry, cache_reason = _load_cache_entry(
                cache_path,
                execution_key,
                key_document["executable_identity"],
            )
            if entry is not None:
                return {
                    "protocol": PROTOCOL,
                    "verifier_id": normalized_verifier["id"],
                    "status": "PASS",
                    "exit_code": 0,
                    "stdout": entry["stdout"],
                    "stderr": entry["stderr"],
                    "execution_key": execution_key,
                    "evidence_key": execution_key,
                    "verifier": normalized_verifier,
                    "context": key_inputs["context"],
                    "key_document": key_document,
                    "cache_status": "reused",
                    "cache_reason": cache_reason,
                    "duration_ms": 0,
                    "metrics": {"executed": 0, "reused": 1},
                    **(
                        {"reservation": checked_reservation}
                        if checked_reservation is not None
                        else {}
                    ),
                    **(
                        {"dispatch_attestation": dispatch_attestation}
                        if dispatch_attestation is not None
                        else {}
                    ),
                }
            cache_status = "miss"
        else:
            can_reuse = False
            cache_reason = "cache_root_inside_checkout"

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=effective_environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        status = "PASS" if completed.returncode == 0 else "FAIL"
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        status = "TIMEOUT"
        exit_code = None
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
    except OSError as exc:
        status = "ERROR"
        exit_code = None
        stdout = ""
        stderr = str(exc)
    if git_guard is not None:
        try:
            after_snapshot = _git_guard_snapshot(checkout_root.resolve(), git_guard)
            if after_snapshot != guard_snapshot:
                raise VerifierRuntimeError(
                    "tracked verifier inputs changed while the command was running"
                )
        except VerifierRuntimeError as exc:
            status = "ERROR"
            exit_code = None
            stderr = (stderr + "\n" if stderr else "") + str(exc)
    duration_ms = max(0, round((time.perf_counter() - started) * 1000))

    if status == "PASS" and can_reuse and cache_path is not None:
        entry = {
            "protocol": PROTOCOL,
            "execution_key": execution_key,
            "status": "PASS",
            "exit_code": 0,
            "stdout": stdout,
            "stderr": stderr,
            "executable_identity": key_document["executable_identity"],
        }
        if _write_cache_entry(cache_path, entry):
            cache_status = "stored"
            cache_reason = "successful_exact_execution"
        elif cache_reason == "cache_entry_missing":
            cache_reason = "cache_entry_race"

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
        "cache_status": cache_status,
        "cache_reason": cache_reason,
        "duration_ms": duration_ms,
        "metrics": {"executed": 1, "reused": 0},
        **(
            {"reservation": checked_reservation}
            if checked_reservation is not None
            else {}
        ),
        **(
            {"dispatch_attestation": dispatch_attestation}
            if dispatch_attestation is not None
            else {}
        ),
    }


def _execution_policies_conflict(
    left: dict[str, Any], right: dict[str, Any]
) -> bool:
    if not left["parallel_safe"] or not right["parallel_safe"]:
        return True
    left_resources = {item["key"]: item["access"] for item in left["resources"]}
    right_resources = {item["key"]: item["access"] for item in right["resources"]}
    return any(
        "exclusive" in {left_resources[key], right_resources[key]}
        for key in set(left_resources) & set(right_resources)
    )


def run_verifier_batch(
    jobs: list[dict[str, Any]],
    *,
    max_parallel: int,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Execute explicitly parallel-safe verifier jobs in deterministic waves."""

    if not isinstance(jobs, list) or not jobs:
        raise VerifierRuntimeError("jobs must be a non-empty array")
    if (
        not isinstance(max_parallel, int)
        or isinstance(max_parallel, bool)
        or max_parallel <= 0
    ):
        raise VerifierRuntimeError("max_parallel must be a positive integer")

    prepared: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    job_ids: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict) or set(job) != BATCH_JOB_FIELDS:
            raise VerifierRuntimeError(
                "each job must contain exactly job_id, verifier, context, checkout_root, "
                "cache_root, and timeout_seconds"
            )
        job_id = _require_string(job["job_id"], "job.job_id")
        if job_id in job_ids:
            raise VerifierRuntimeError("job.job_id must be unique")
        job_ids.add(job_id)
        if not isinstance(job["verifier"], dict):
            raise VerifierRuntimeError("job.verifier must be an object")
        if not isinstance(job["context"], dict):
            raise VerifierRuntimeError("job.context must be an object")
        checkout_root = _require_string(job["checkout_root"], "job.checkout_root")
        if job["cache_root"] is not None:
            _require_string(job["cache_root"], "job.cache_root")
        timeout_seconds = job["timeout_seconds"]
        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or timeout_seconds <= 0
        ):
            raise VerifierRuntimeError("job.timeout_seconds must be positive")
        prepared.append(
            (
                job_id,
                {**job, "checkout_root": checkout_root},
                _execution_policy(job["verifier"]),
            )
        )

    waves: list[list[tuple[str, dict[str, Any], dict[str, Any]]]] = []
    for prepared_job in sorted(prepared, key=lambda item: item[0]):
        for wave in waves:
            if len(wave) < max_parallel and all(
                not _execution_policies_conflict(prepared_job[2], existing[2])
                for existing in wave
            ):
                wave.append(prepared_job)
                break
        else:
            waves.append([prepared_job])

    def execute(job: dict[str, Any]) -> dict[str, Any]:
        try:
            return run_verifier(
                job["verifier"],
                job["context"],
                checkout_root=Path(job["checkout_root"]),
                cache_root=(
                    Path(job["cache_root"])
                    if job["cache_root"] is not None
                    else None
                ),
                timeout_seconds=float(job["timeout_seconds"]),
                environment=environment,
            )
        except (OSError, ValueError, VerifierRuntimeError) as exc:
            return {"protocol": PROTOCOL, "status": "ERROR", "errors": [str(exc)]}

    started = time.perf_counter()
    results_by_id: dict[str, dict[str, Any]] = {}
    for wave in waves:
        with ThreadPoolExecutor(max_workers=len(wave)) as executor:
            futures = {
                executor.submit(execute, job): job_id for job_id, job, _ in wave
            }
            for future in as_completed(futures):
                results_by_id[futures[future]] = future.result()
    duration_ms = max(0, round((time.perf_counter() - started) * 1000))
    results = [
        {"job_id": job_id, "result": results_by_id[job_id]}
        for job_id in sorted(results_by_id)
    ]
    passed = all(item["result"].get("status") == "PASS" for item in results)
    return {
        "protocol": BATCH_PROTOCOL,
        "status": "PASS" if passed else "FAIL",
        "results": results,
        "metrics": {
            "duration_ms": duration_ms,
            "waves": len(waves),
            "max_parallel": max(len(wave) for wave in waves),
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
                cache_root=(
                    Path(request["cache_root"])
                    if request.get("cache_root") is not None
                    else None
                ),
                timeout_seconds=float(request.get("timeout_seconds", 120.0)),
                git_guard=request.get("git_guard"),
                reservation=request.get("reservation"),
                request_sha256=request_sha256,
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
    raise SystemExit(main())
