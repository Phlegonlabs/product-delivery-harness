#!/usr/bin/env python3
"""Execute explicitly containerized verifiers singly or in resource-safe batches."""

from __future__ import annotations

import argparse
import ctypes
import io
import tarfile
import tempfile
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import nullcontext
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from select_verifiers import VerifierSelectionError, normalize_changed_files
from harness_core import (
    HOST_FINGERPRINT_KEYS,
    HOST_RUNTIME_VERSION_KEYS,
    normalize_sandbox_policy,
)
from harness_git import (
    GitMetadataError,
    reject_object_substitution,
    run_git,
    windows_machine_roots,
    windows_parent_user_writable,
)


PROTOCOL = "harness-verifier-execution-v2"
BATCH_PROTOCOL = "harness-verifier-batch-v1"
# Container reuse is batch-local and opt-in, with fresh consumer attestations.
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
BATCH_JOB_OPTIONAL_FIELDS = {
    "git_guard",
    "reservation",
    "request_sha256",
    "sandbox_preflight",
    "host_preflight",
}


class VerifierRuntimeError(ValueError):
    """Raised when verifier execution inputs are unsafe or malformed."""


# Serialize runtime probes, not user commands. Each invocation holds its own
# descriptor (POSIX) or delete/write-denying handle (Windows) and rechecks the
# preflight hash before launch so path replacement cannot retarget execution.
_RUNTIME_EXECUTION_LOCK = threading.RLock()


def _hash_runtime_fd(file_descriptor: int) -> str:
    """Hash a held runtime descriptor without reopening its mutable path."""

    try:
        original_offset = os.lseek(file_descriptor, 0, os.SEEK_CUR)
        os.lseek(file_descriptor, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        while True:
            chunk = os.read(file_descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        os.lseek(file_descriptor, original_offset, os.SEEK_SET)
    except OSError as exc:
        raise VerifierRuntimeError(
            f"cannot hash bound sandbox runtime executable: {exc}"
        ) from exc
    return digest.hexdigest()


class _RuntimeExecutableBinding:
    """Bind one runtime executable to the process that will invoke it.

    On POSIX, the child receives the inherited descriptor and executes through
    ``/proc/self/fd`` (or ``/dev/fd``), which pins the opened inode even if its
    directory entry is replaced.  Windows has no portable descriptor path, so
    a native ``CreateFileW`` handle is held without delete/write sharing while
    the path is executed.  Both routes fail closed when the platform cannot
    provide the required binding.
    """

    def __init__(self, executable: Path) -> None:
        self.executable = executable
        self.file_descriptor: int | None = None
        self.handle: int | None = None
        self.launch_path = str(executable)
        self.pass_fds: tuple[int, ...] = ()
        self._close_handle: Any = None

    def __enter__(self) -> "_RuntimeExecutableBinding":
        if os.name == "nt":
            self._open_windows_handle()
            return self
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(str(self.executable), flags)
        except OSError as exc:
            raise VerifierRuntimeError(
                f"cannot bind sandbox runtime executable: {exc}"
            ) from exc
        try:
            descriptor_stat = os.fstat(descriptor)
        except OSError as exc:
            os.close(descriptor)
            raise VerifierRuntimeError(
                f"cannot inspect bound sandbox runtime executable: {exc}"
            ) from exc
        if not stat.S_ISREG(descriptor_stat.st_mode):
            os.close(descriptor)
            raise VerifierRuntimeError(
                "sandbox runtime executable must be a regular file"
            )
        if not descriptor_stat.st_mode & (
            stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        ):
            os.close(descriptor)
            raise VerifierRuntimeError(
                "sandbox runtime executable must have an execute bit"
            )
        candidates = (f"/proc/self/fd/{descriptor}", f"/dev/fd/{descriptor}")
        launch_path = next((candidate for candidate in candidates if Path(candidate).exists()), None)
        if launch_path is None:
            os.close(descriptor)
            raise VerifierRuntimeError(
                "sandbox runtime executable requires a descriptor-backed launch path"
            )
        self.file_descriptor = descriptor
        self.launch_path = launch_path
        self.pass_fds = (descriptor,)
        return self

    def _open_windows_handle(self) -> None:
        win_dll = getattr(ctypes, "WinDLL", None)
        if win_dll is None:
            raise VerifierRuntimeError(
                "sandbox runtime executable requires native Windows handle protection"
            )
        kernel32 = win_dll("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        # GENERIC_READ | GENERIC_EXECUTE; share read only.  In particular,
        # omitting FILE_SHARE_DELETE prevents os.replace()/rename from
        # retargeting the path while this handle is held.  OPEN_REPARSE_POINT
        # lets us inspect the opened entry before accepting it; a reparse
        # point is rejected instead of silently following a mutable link.
        handle = create_file(
            str(self.executable),
            0x80000000 | 0x20000000,
            0x00000001,
            None,
            3,  # OPEN_EXISTING
            0x00000080 | 0x00200000,  # FILE_ATTRIBUTE_NORMAL | OPEN_REPARSE_POINT
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle is None or handle == invalid:
            error = ctypes.get_last_error()
            raise VerifierRuntimeError(
                f"cannot bind sandbox runtime executable handle (winerror {error})"
            )
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        get_attributes = kernel32.GetFileAttributesW
        get_attributes.argtypes = [ctypes.c_wchar_p]
        get_attributes.restype = ctypes.c_uint32
        attributes = get_attributes(str(self.executable))
        if attributes == 0xFFFFFFFF or attributes & 0x00000010 or attributes & 0x00000400:
            close_handle(handle)
            raise VerifierRuntimeError(
                "sandbox runtime executable must be a non-reparse regular file"
            )
        get_final_path = kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
        get_final_path.restype = ctypes.c_uint32
        buffer_size = 512
        final_path = ""
        while buffer_size <= 32768:
            buffer = ctypes.create_unicode_buffer(buffer_size)
            length = get_final_path(handle, buffer, buffer_size, 0)
            if length == 0:
                break
            if length < buffer_size - 1:
                final_path = buffer.value
                break
            buffer_size *= 2
        if not final_path:
            close_handle(handle)
            raise VerifierRuntimeError(
                "cannot resolve bound sandbox runtime executable handle"
            )
        normalized_final = final_path.removeprefix("\\\\?\\").casefold()
        normalized_expected = str(self.executable.resolve()).casefold()
        if normalized_final != normalized_expected:
            close_handle(handle)
            raise VerifierRuntimeError(
                "sandbox runtime executable handle path differs from preflight path"
            )
        self.handle = int(handle)
        self._close_handle = close_handle

    def sha256(self) -> str:
        if self.file_descriptor is not None:
            return _hash_runtime_fd(self.file_descriptor)
        try:
            return _sha256_bytes(self.executable.read_bytes())
        except OSError as exc:
            raise VerifierRuntimeError(
                f"cannot hash bound sandbox runtime executable: {exc}"
            ) from exc

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        if self.file_descriptor is not None:
            os.close(self.file_descriptor)
            self.file_descriptor = None
        if self.handle is not None and self._close_handle is not None:
            self._close_handle(ctypes.c_void_p(self.handle))
            self.handle = None


def _run_bound_runtime(
    binding: _RuntimeExecutableBinding,
    arguments: list[str],
    *,
    env: Mapping[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Invoke a runtime through its held descriptor/handle binding."""

    command = [binding.launch_path, *arguments]
    options: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "env": env,
        "check": False,
        "timeout": timeout,
    }
    if binding.pass_fds and os.name != "nt":
        options["pass_fds"] = binding.pass_fds
    return subprocess.run(command, **options)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


class _SnapshotArchiveCache:
    """Cache immutable archive bytes for one verifier batch only."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], bytes] = {}
        self._flights: dict[tuple[str, str], Any] = {}
        self._lock = threading.Lock()

    @staticmethod
    def key(checkout_root: Path, head_sha: str) -> tuple[str, str]:
        return os.path.normcase(str(checkout_root.resolve())), head_sha

    def get_or_create(
        self,
        checkout_root: Path,
        head_sha: str,
        read_archive: Any,
    ) -> bytes:
        key = self.key(checkout_root, head_sha)
        with self._lock:
            flight = self._flights.setdefault(key, threading.Lock())
        with flight:
            if key not in self._entries:
                self._entries[key] = read_archive()
            return self._entries[key]


class _ContainerResultCache:
    """Trust one runner invocation's PASSes; never persist or import them."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._flights: dict[str, Any] = {}
        self._lock = threading.Lock()

    def flight(self, identity: str) -> Any:
        with self._lock:
            return self._flights.setdefault(identity, threading.Lock())

    def get(self, execution_key: str) -> dict[str, Any] | None:
        with self._lock:
            return copy_json(self._entries.get(execution_key))

    def store(self, identity: str, entry: dict[str, Any]) -> None:
        with self._lock:
            self._entries.setdefault(identity, copy_json(entry))


def _runtime_trust(executable: Path, runtime: str) -> dict[str, Any]:
    """Return machine-bound proof for a native sandbox runtime executable.

    A hash alone is not an authority boundary: a user-writable directory can
    replace a same-hash or same-name executable between preflight and launch.
    The accepted roots below are administrator-managed OS locations.  The
    descriptor/handle binding still protects the final execution window.
    """

    try:
        canonical = executable.resolve(strict=True)
        info = canonical.stat()
    except OSError as exc:
        raise VerifierRuntimeError(f"sandbox runtime executable is unavailable: {executable}") from exc
    if not canonical.is_file() or executable.is_symlink():
        raise VerifierRuntimeError("sandbox runtime executable must be a non-reparse regular file")
    for component in (canonical, *canonical.parents):
        try:
            if component.is_symlink() or getattr(component.stat(), "st_file_attributes", 0) & 0x0400:
                raise VerifierRuntimeError("sandbox runtime path contains a symlink or reparse point")
        except OSError as exc:
            raise VerifierRuntimeError(f"cannot inspect sandbox runtime path: {exc}") from exc
    try:
        canonical.relative_to(Path.cwd().resolve())
    except ValueError:
        pass
    else:
        raise VerifierRuntimeError("sandbox runtime executable must not come from the current repository/worktree")
    if os.name == "nt":
        if canonical.suffix.casefold() != ".exe":
            raise VerifierRuntimeError("Windows sandbox runtime executable must be a canonical native .exe")
        roots = list(windows_machine_roots())
        if not any(_path_within(canonical, root) for root in roots):
            raise VerifierRuntimeError("sandbox runtime executable must come from an administrator-installed Windows path")
        # File ACEs can permit writes even when the parent directory is protected.
        if windows_parent_user_writable(canonical):
            raise VerifierRuntimeError("sandbox runtime file is user-writable")
        if windows_parent_user_writable(canonical.parent):
            raise VerifierRuntimeError("sandbox runtime parent is user-writable")
    else:
        allowed_roots = (Path("/usr").resolve(), Path("/bin").resolve(), Path("/opt").resolve())
        if not any(_path_within(canonical, root) for root in allowed_roots):
            raise VerifierRuntimeError("sandbox runtime executable must come from an administrator-installed POSIX path")
        for component in (canonical, *canonical.parents):
            component_info = component.stat()
            if component_info.st_uid != 0 or component_info.st_mode & 0o022:
                raise VerifierRuntimeError(
                    "sandbox runtime path must be root-owned and not writable by group/other: "
                    + str(component)
                )
    return {
        "path": str(canonical),
        "runtime": runtime,
        "ownership": "administrator-managed",
        "uid": int(getattr(info, "st_uid", -1)),
        "mode": int(info.st_mode & 0o777),
        "reparse": False,
    }


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


def sandbox_host_fingerprint() -> dict[str, str]:
    """Return non-sensitive host identity used to invalidate stale probes."""

    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "node_sha256": _sha256_bytes(platform.node().encode("utf-8")),
    }


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


def _validated_sandbox_preflight(
    policy: dict[str, Any], value: Any
) -> dict[str, Any]:
    """Validate and normalize the exact observation bound to execution."""

    if not isinstance(value, dict) or set(value) != {
        "runtime",
        "image",
        "repo_digest",
        "runtime_probe",
    }:
        raise VerifierRuntimeError(
            "container execution requires the exact sandbox preflight entry"
        )
    if value.get("runtime") != policy.get("runtime"):
        raise VerifierRuntimeError("sandbox preflight runtime does not match policy")
    if value.get("image") != policy.get("image"):
        raise VerifierRuntimeError("sandbox preflight image does not match policy")
    image = value["image"]
    repo_digest = value.get("repo_digest")
    if (
        not isinstance(repo_digest, str)
        or re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", repo_digest) is None
        or not repo_digest.endswith("@" + image.rsplit("@", 1)[-1])
    ):
        raise VerifierRuntimeError(
            "sandbox preflight RepoDigest does not attest the pinned image"
        )
    probe = value.get("runtime_probe")
    if not isinstance(probe, dict) or not {
        "executable",
        "executable_sha256",
        "version_output_sha256",
    }.issubset(probe) or set(probe) - {
        "executable",
        "executable_sha256",
        "version_output_sha256",
        "trust",
    }:
        raise VerifierRuntimeError("sandbox preflight runtime identity is malformed")
    executable = probe.get("executable")
    if not isinstance(executable, str) or not executable or not Path(executable).is_absolute():
        raise VerifierRuntimeError(
            "sandbox preflight executable must be a canonical absolute path"
        )
    canonical = str(Path(executable).resolve())
    if os.path.normcase(executable) != os.path.normcase(canonical):
        raise VerifierRuntimeError(
            "sandbox preflight executable must be a canonical absolute path"
        )
    if os.name == "nt" and Path(canonical).suffix.casefold() != ".exe":
        raise VerifierRuntimeError(
            "Windows sandbox runtime executable must be a canonical native .exe"
        )
    for key in ("executable_sha256", "version_output_sha256"):
        digest = probe.get(key)
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise VerifierRuntimeError(
                f"sandbox preflight runtime_probe.{key} must be a lowercase SHA-256"
            )
    normalized = copy_json(value)
    normalized["runtime_probe"]["executable"] = canonical
    if "trust" in probe and not isinstance(probe["trust"], dict):
        raise VerifierRuntimeError("sandbox preflight runtime trust proof is malformed")
    return normalized


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
            "verifier.execution is required; runtime verifier requests must declare isolation=container or host"
        )
    isolation = value.get("isolation") if isinstance(value, dict) else None
    if (
        isinstance(value, dict)
        and {"parallel_safe", "resources", "isolation"} <= set(value)
        and isolation not in {"container", "host"}
    ):
        raise VerifierRuntimeError(
            "runtime verifier execution requires execution.isolation=container"
        )
    container_keys = {"parallel_safe", "resources", "isolation", "sandbox"}
    host_keys = {"parallel_safe", "resources", "isolation"}
    allowed_keys = container_keys if isolation == "container" else host_keys
    if not isinstance(value, dict) or not {"parallel_safe", "resources", "isolation"} <= set(value) or not set(value) <= allowed_keys:
        required_shape = (
            "parallel_safe/resources/isolation/sandbox"
            if isolation == "container"
            else "parallel_safe/resources/isolation"
        )
        raise VerifierRuntimeError(
            f"verifier.execution must contain {required_shape}"
        )
    if not isinstance(value["parallel_safe"], bool):
        raise VerifierRuntimeError("verifier.execution.parallel_safe must be boolean")
    resources = value["resources"]
    if not isinstance(resources, list):
        raise VerifierRuntimeError("verifier.execution.resources must be an array")
    isolation = value["isolation"]
    if isolation not in {"container", "host"}:
        raise VerifierRuntimeError(
            "runtime verifier execution requires explicit execution.isolation=container or host"
        )
    if isolation == "container" and not isinstance(value.get("sandbox"), dict):
        raise VerifierRuntimeError("container verifier execution requires sandbox policy")
    if isolation == "host" and value["parallel_safe"] is not False:
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
        "isolation": isolation,
        **(
            {"sandbox": normalize_sandbox_policy(value["sandbox"])}
            if isolation == "container"
            else {}
        ),
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


def observe_plan_sandboxes(
    plan: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Probe every unique declared runtime/image and retain exact evidence."""

    observations: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for path, verifier in _plan_verifier_declarations(plan):
        try:
            policy = _execution_policy(verifier)
        except VerifierRuntimeError as exc:
            errors.append(f"{path}: {exc}")
            continue
        if policy["isolation"] == "host":
            continue
        sandbox = policy["sandbox"]
        runtime = str(sandbox["runtime"])
        image = str(sandbox["image"])
        key = (runtime, image)
        if key in seen:
            continue
        seen.add(key)
        executable = shutil.which(runtime)
        if executable is None:
            errors.append(
                f"{path}: sandbox runtime {runtime!r} is unavailable; record an unavailable preflight and defer the gate"
            )
            continue
        if os.name == "nt" and Path(executable).suffix.casefold() != ".exe":
            errors.append(f"{path}: Windows sandbox runtime must resolve to a native .exe, not a script wrapper")
            continue
        try:
            trust = _runtime_trust(Path(executable), runtime)
        except VerifierRuntimeError as exc:
            errors.append(f"{path}: {exc}")
            continue
        executable = trust["path"]
        probe_env = {"PATH": os.environ.get("PATH", "")}
        if os.name == "nt" and os.environ.get("SystemRoot"):
            probe_env["SystemRoot"] = os.environ["SystemRoot"]
        try:
            version = subprocess.run(
                [executable, "version"],
                capture_output=True,
                text=True,
                env=probe_env,
                check=False,
                timeout=30,
            )
            if version.returncode != 0:
                errors.append(f"{path}: sandbox runtime {runtime!r} probe failed")
                continue
            inspect = subprocess.run(
                [executable, "image", "inspect", "--format", "{{json .RepoDigests}}", image],
                capture_output=True,
                text=True,
                env=probe_env,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{path}: sandbox preflight failed: {exc}")
            continue
        if inspect.returncode != 0 or not inspect.stdout.strip():
            errors.append(f"{path}: pinned image {image!r} is unavailable or unverified")
            continue
        try:
            repo_digests = json.loads(inspect.stdout)
        except json.JSONDecodeError:
            errors.append(f"{path}: sandbox image probe returned invalid RepoDigests JSON")
            continue
        pinned_digest = image.rsplit("@", 1)[-1]
        if not isinstance(repo_digests, list) or any(not isinstance(item, str) for item in repo_digests):
            errors.append(f"{path}: sandbox image probe returned malformed RepoDigests")
        elif not any(item.endswith("@" + pinned_digest) for item in repo_digests):
            errors.append(f"{path}: sandbox image probe did not attest the pinned digest")
        else:
            matched = next(
                item for item in repo_digests if item.endswith("@" + pinned_digest)
            )
            try:
                executable_sha256 = _sha256_bytes(Path(executable).read_bytes())
            except OSError as exc:
                errors.append(f"{path}: cannot hash sandbox runtime executable: {exc}")
                continue
            version_output_sha256 = _sha256_bytes(version.stdout.encode("utf-8"))
            observations.append(
                {
                    "runtime": runtime,
                    "image": image,
                    "repo_digest": matched,
                    "runtime_probe": {
                        "executable": executable,
                        "executable_sha256": executable_sha256,
                        "version_output_sha256": version_output_sha256,
                        "trust": trust,
                    },
                }
            )
    return observations, sorted(set(errors))


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


def probe_plan_sandboxes(plan: Mapping[str, Any]) -> list[str]:
    """Read-only preflight for every declared verifier image/runtime."""

    _observations, errors = observe_plan_sandboxes(plan)
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
    cwd = checkout_root.resolve()
    if execution["isolation"] == "container":
        image = execution["sandbox"]["image"]
        identity = {
            "path": f"container:{image}:{argv[0]}",
            "size": 0,
            "mtime_ns": 0,
            "device": 0,
            "inode": 0,
        }
    else:
        cwd = _resolve_cwd(checkout_root.resolve(), declared_cwd)
        identity = executable_identity(
            _resolve_executable(argv[0], cwd, environment)
        )
    read_only = verifier.get("read_only", False)
    if not isinstance(read_only, bool):
        raise VerifierRuntimeError("verifier.read_only must be boolean")

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
    if execution["isolation"] == "host" and (
        cache["mode"] != "disabled" or deterministic_local
    ):
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
    effective_environment = os.environ if environment is None else environment
    _, _, normalized_verifier, key_inputs = _validated_inputs(
        verifier,
        context,
        checkout_root,
        effective_environment,
    )
    execution_key, key_document = _key_document(normalized_verifier, key_inputs)
    execution = normalized_verifier.get("execution", {})
    if execution.get("isolation") == "container":
        policy = normalized_verifier["execution"].get("sandbox")
        if not isinstance(policy, dict):
            raise VerifierRuntimeError("container sandbox policy is malformed")
        checked = _validated_sandbox_preflight(policy, sandbox_preflight)
        key_document["sandbox_preflight"] = copy_json(checked)
        execution_key = execution_key_from_document(key_document)
    elif sandbox_preflight is not None:
        raise VerifierRuntimeError(
            "sandbox_preflight is valid only for container execution"
        )
    if execution.get("isolation") == "host":
        if host_preflight is None:
            raise VerifierRuntimeError("host execution requires host_preflight")
        key_document["host_preflight"] = copy_json(
            _validated_host_preflight(host_preflight)
        )
        if host_preflight["argv0"] != normalized_verifier["argv"][0]:
            raise VerifierRuntimeError("host preflight argv0 differs from the declaration")
        execution_key = execution_key_from_document(key_document)
    elif host_preflight is not None:
        raise VerifierRuntimeError(
            "host_preflight is valid only for host execution"
        )
    return execution_key, key_document


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


def _materialize_git_snapshot(
    checkout_root: Path,
    head_sha: str,
    declared_cwd: str,
    argv: list[str],
    archive_cache: _SnapshotArchiveCache | None = None,
) -> tuple[tempfile.TemporaryDirectory[str], Path, list[str]]:
    """Materialize an immutable Git tree outside the worker checkout."""

    checkout = checkout_root.resolve()
    try:
        reject_object_substitution(checkout)
    except GitMetadataError as exc:
        raise VerifierRuntimeError(str(exc)) from exc
    for index, argument in enumerate(argv):
        if not isinstance(argument, str):
            continue
        candidate = Path(argument)
        if candidate.is_absolute():
            try:
                candidate.resolve().relative_to(checkout)
            except ValueError:
                continue
            raise VerifierRuntimeError(
                f"snapshot verifier argv[{index}] must not reference the live checkout"
            )
    def read_archive() -> bytes:
        try:
            result = run_git(
                checkout,
                "archive",
                "--format=tar",
                head_sha,
                text=False,
                check=False,
                timeout=60,
            )
        except GitMetadataError as exc:
            raise VerifierRuntimeError(str(exc)) from exc
        if result.returncode != 0:
            detail = result.stderr.decode(errors="replace").strip()
            raise VerifierRuntimeError(
                f"cannot materialize git snapshot: {detail}"
            )
        assert isinstance(result.stdout, bytes)
        return result.stdout

    if archive_cache is None:
        archive = read_archive()
    else:
        archive = archive_cache.get_or_create(checkout, head_sha, read_archive)
    temporary = tempfile.TemporaryDirectory(prefix="harness-verifier-snapshot-")
    snapshot_root = Path(temporary.name).resolve()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
            for member in bundle.getmembers():
                if member.issym() or member.islnk() or member.isdev() or not (
                    member.isdir() or member.isfile()
                ):
                    raise VerifierRuntimeError(
                        "git snapshot contains a link, device, FIFO, or unsupported archive member"
                    )
                target = (snapshot_root / member.name).resolve()
                try:
                    target.relative_to(snapshot_root)
                except ValueError as exc:
                    raise VerifierRuntimeError(
                        "git snapshot contains a path outside the snapshot root"
                    ) from exc
            bundle.extractall(snapshot_root)
    except Exception:
        temporary.cleanup()
        raise
    snapshot_cwd = (snapshot_root / declared_cwd).resolve()
    try:
        snapshot_cwd.relative_to(snapshot_root)
    except ValueError as exc:
        temporary.cleanup()
        raise VerifierRuntimeError("snapshot verifier cwd escapes the snapshot") from exc
    if not snapshot_cwd.is_dir():
        temporary.cleanup()
        raise VerifierRuntimeError("snapshot verifier cwd does not exist")
    snapshot_argv = list(argv)
    first = Path(snapshot_argv[0])
    if snapshot_argv[0].startswith("./"):
        snapshot_argv[0] = str((snapshot_cwd / first).resolve())
    elif not first.is_absolute() and first.parent != Path("."):
        snapshot_argv[0] = str((snapshot_root / first).resolve())
    return temporary, snapshot_cwd, snapshot_argv


def _snapshot_environment(
    environment: Mapping[str, str], checkout_root: Path, snapshot_cwd: Path
) -> dict[str, str]:
    """Remove live-checkout path leaks before running a snapshot verifier."""

    checkout = checkout_root.resolve()
    result = dict(environment)
    result["PWD"] = str(snapshot_cwd)
    for key in ("OLDPWD", "GIT_DIR", "GIT_WORK_TREE"):
        result.pop(key, None)
    for key in ("PYTHONPATH", "NODE_PATH"):
        value = result.get(key)
        if not isinstance(value, str):
            continue
        kept: list[str] = []
        for entry in value.split(os.pathsep):
            if not entry:
                continue
            try:
                Path(entry).resolve().relative_to(checkout)
            except ValueError:
                kept.append(entry)
        if kept:
            result[key] = os.pathsep.join(kept)
        else:
            result.pop(key, None)
    return result


def _verify_container_runtime_identity(
    *,
    bound_executable: Path,
    runtime: str,
    checked_preflight: dict[str, Any],
) -> str:
    """Freshly verify executable and image trust without running user code."""

    runtime_probe = checked_preflight["runtime_probe"]
    with _RUNTIME_EXECUTION_LOCK:
        executable = shutil.which(runtime)
        if executable is None:
            raise VerifierRuntimeError(
                f"container sandbox runtime {runtime!r} is unavailable; run the sandbox preflight again and defer the gate"
            )
        if os.path.normcase(str(Path(executable).resolve())) != os.path.normcase(
            str(bound_executable)
        ):
            raise VerifierRuntimeError(
                "sandbox runtime executable changed since preflight"
            )
        recorded_trust = runtime_probe.get("trust")
        if recorded_trust is not None:
            observed_trust = _runtime_trust(bound_executable, runtime)
            if observed_trust != recorded_trust:
                raise VerifierRuntimeError(
                    "sandbox runtime machine trust proof changed since preflight"
                )
        with _RuntimeExecutableBinding(bound_executable) as binding:
            if binding.sha256() != runtime_probe["executable_sha256"]:
                raise VerifierRuntimeError(
                    "sandbox runtime executable changed since preflight"
                )
            probe_env = {"PATH": os.environ.get("PATH", "")}
            if os.name == "nt" and os.environ.get("SystemRoot"):
                probe_env["SystemRoot"] = os.environ["SystemRoot"]
            probe = _run_bound_runtime(
                binding,
                ["version"],
                env=probe_env,
                timeout=30,
            )
            if probe.returncode != 0:
                raise VerifierRuntimeError("container sandbox runtime probe failed")
            if _sha256_bytes(probe.stdout.encode("utf-8")) != runtime_probe[
                "version_output_sha256"
            ]:
                raise VerifierRuntimeError(
                    "sandbox runtime version output changed since preflight"
                )
            image = checked_preflight["image"]
            inspect = _run_bound_runtime(
                binding,
                [
                    "image",
                    "inspect",
                    "--format",
                    "{{json .RepoDigests}}",
                    image,
                ],
                env=probe_env,
                timeout=60,
            )
            if inspect.returncode != 0 or not inspect.stdout.strip():
                raise VerifierRuntimeError(
                    "pinned container image is unavailable or unverified"
                )
            pinned_digest = image.rsplit("@", 1)[-1]
            try:
                repo_digests = json.loads(inspect.stdout)
            except json.JSONDecodeError as exc:
                raise VerifierRuntimeError(
                    "container image probe returned invalid RepoDigests JSON"
                ) from exc
            if not isinstance(repo_digests, list) or any(
                not isinstance(item, str) for item in repo_digests
            ):
                raise VerifierRuntimeError(
                    "container image probe returned malformed RepoDigests"
                )
            matched_repo_digest = next(
                (item for item in repo_digests if item.endswith("@" + pinned_digest)),
                None,
            )
            if matched_repo_digest is None:
                raise VerifierRuntimeError(
                    "container image probe did not attest the pinned digest"
                )
            if checked_preflight["repo_digest"] != matched_repo_digest:
                raise VerifierRuntimeError(
                    "container image RepoDigest changed since preflight"
                )
            if binding.sha256() != runtime_probe["executable_sha256"]:
                raise VerifierRuntimeError(
                    "sandbox runtime executable changed immediately before execution"
                )
        return matched_repo_digest


def _container_attestation(
    runtime: str,
    image: str,
    matched_repo_digest: str,
    checked_preflight: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "runtime": runtime,
        "runtime_probe": copy_json(checked_preflight["runtime_probe"]),
        "image": image,
        "image_probe": matched_repo_digest,
        "policy": copy_json(policy),
        "mount": {
            "source": "git_archive",
            "destination": "/workspace",
            "read_only": True,
        },
        "network": "none",
    }


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


def _run_container_verifier(
    checkout_root: Path,
    snapshot_root: Path,
    declared_cwd: str,
    argv: list[str],
    policy: dict[str, Any],
    timeout_seconds: float,
    sandbox_preflight: dict[str, Any],
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """Run a verifier under an explicit, machine-probed container policy."""

    runtime = policy.get("runtime")
    image = policy.get("image")
    if runtime not in {"docker", "podman"} or not isinstance(image, str):
        raise VerifierRuntimeError("container sandbox policy is malformed")
    checked_preflight = _validated_sandbox_preflight(policy, sandbox_preflight)
    runtime_probe = checked_preflight["runtime_probe"]
    bound_executable = Path(runtime_probe["executable"])
    matched_repo_digest = _verify_container_runtime_identity(
        bound_executable=bound_executable,
        runtime=runtime,
        checked_preflight=checked_preflight,
    )
    # ``Path.as_posix`` in _validated_inputs normalizes one leading ``./``.
    # Keep every other leading dot and slash exactly: a hidden directory must
    # remain ``/workspace/.hidden``.
    normalized_cwd = Path(declared_cwd).as_posix()
    workdir = "/workspace" if normalized_cwd == "." else f"/workspace/{normalized_cwd}"
    arguments = [
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        f"--user={policy['user']}",
        f"--memory={policy['memory']}",
        f"--cpus={policy['cpus']}",
        f"--pids-limit={policy['pids_limit']}",
        "--mount",
        f"type=bind,src={snapshot_root},dst=/workspace,readonly",
    ]
    for tmpfs in policy["tmpfs"]:
        arguments.extend(["--tmpfs", str(tmpfs)])
    arguments.extend(["--workdir", workdir, image, *argv])
    with _RuntimeExecutableBinding(bound_executable) as binding:
        if binding.sha256() != runtime_probe["executable_sha256"]:
            raise VerifierRuntimeError(
                "sandbox runtime executable changed immediately before execution"
            )
        completed = _run_bound_runtime(
            binding,
            arguments,
            env={"PATH": os.environ.get("PATH", ""), **(
                {"SystemRoot": os.environ["SystemRoot"]}
                if os.name == "nt" and os.environ.get("SystemRoot")
                else {}
            )},
            timeout=timeout_seconds,
        )
        if binding.sha256() != runtime_probe["executable_sha256"]:
            raise VerifierRuntimeError(
                "sandbox runtime executable changed during execution"
            )
    return completed, {
        "runtime": runtime,
        "runtime_probe": copy_json(runtime_probe),
        "image": image,
        "image_probe": matched_repo_digest,
        "policy": copy_json(policy),
        "mount": {"source": "git_archive", "destination": "/workspace", "read_only": True},
        "network": "none",
    }


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


def _container_reuse_allowed(
    *,
    container_mode: bool,
    normalized_verifier: dict[str, Any],
    context: dict[str, Any],
    git_guard: dict[str, Any] | None,
) -> bool:
    cache = normalized_verifier["cache"]
    return bool(
        container_mode
        and cache["mode"] == "session_exact"
        and cache.get("deterministic_local") is True
        and normalized_verifier["pass_signal"] == "exit 0"
        and context["layer"] in {"task", "worker"}
        and context["checkout_role"] == "worker"
        and context["cache_safe"] is True
        and context["checkout_dirty"] is False
        and git_guard is not None
    )


def _host_cache_allowed(normalized_verifier: Mapping[str, Any]) -> bool:
    cache = normalized_verifier["cache"]
    return bool(
        cache["mode"] == "disabled"
        and cache.get("environment_keys") == []
        and cache.get("deterministic_local", False) is False
    )


TIMING_FIELDS = {
    "end_to_end_ms",
    "setup_ms",
    "git_guard_ms",
    "cache_lookup_ms",
    "snapshot_ms",
    "command_ms",
    "postcheck_ms",
}
REUSE_ORIGIN_FIELDS = {
    "kind",
    "execution_key",
    "verifier_id",
    "context_sha256",
    "stdout_sha256",
    "stderr_sha256",
    "sandbox_attestation",
}


def _output_digest(item: Mapping[str, Any], name: str) -> Any:
    value = item.get(name)
    return _sha256_bytes(value.encode("utf-8")) if isinstance(value, str) else item.get(name + "_sha256")


def execution_retention_binding_errors(item: Mapping[str, Any]) -> list[str]:
    """Validate optional observational and same-runner reuse bindings."""

    errors: list[str] = []
    timings = item.get("timings")
    if timings is not None:
        if not isinstance(timings, dict) or set(timings) != TIMING_FIELDS:
            errors.append("timings must contain the exact observational fields")
        else:
            for key, value in timings.items():
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    errors.append(f"timings.{key} must be a non-negative integer")
    origin = item.get("container_reuse_origin")
    container_reuse = item.get("cache_status") == "reused" and (
        item.get("cache_reason") == "same_runner_container_pass"
        or isinstance(item.get("sandbox_attestation"), dict)
    )
    if container_reuse and origin is None:
        errors.append("container reuse requires an explicit origin")
    if origin is not None:
        if not container_reuse or item.get("status") != "PASS" or item.get("exit_code") != 0:
            errors.append("container reuse origin requires a reused PASS")
        verifier = item.get("verifier", {})
        context = item.get("context", {})
        cache = verifier.get("cache") if isinstance(verifier, dict) else None
        if not isinstance(verifier, dict) or not isinstance(context, dict) or not (
            isinstance(cache, dict)
            and cache.get("mode") == "session_exact"
            and cache.get("deterministic_local") is True
            and verifier.get("read_only") is True
            and verifier.get("pass_signal") == "exit 0"
            and context.get("layer") in {"task", "worker"}
            and context.get("cache_safe") is True
            and context.get("checkout_dirty") is False
        ):
            errors.append("container reuse requires an opted-in read-only task/worker declaration")
        if not isinstance(origin, dict) or set(origin) != REUSE_ORIGIN_FIELDS:
            errors.append("container reuse origin has an incomplete binding")
        else:
            for key in (
                "execution_key",
                "context_sha256",
                "stdout_sha256",
                "stderr_sha256",
            ):
                digest = origin.get(key)
                if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                    errors.append(
                        f"container reuse origin.{key} must be a SHA-256 digest"
                    )
            if origin.get("kind") != "same_runner":
                errors.append("container reuse origin kind must be same_runner")
            if not isinstance(origin.get("verifier_id"), str) or not origin["verifier_id"]:
                errors.append("container reuse origin.verifier_id must be non-empty")
            if not isinstance(origin.get("sandbox_attestation"), dict):
                errors.append("container reuse origin sandbox attestation is missing")
            if isinstance(item.get("execution_key"), str) and origin.get(
                "execution_key"
            ) != item.get("execution_key"):
                errors.append("container reuse origin execution key is rebound")
            stdout_digest = _output_digest(item, "stdout")
            if isinstance(stdout_digest, str) and origin.get("stdout_sha256") != stdout_digest:
                errors.append("container reuse origin stdout is rebound")
            stderr_digest = _output_digest(item, "stderr")
            if isinstance(stderr_digest, str) and origin.get("stderr_sha256") != stderr_digest:
                errors.append("container reuse origin stderr is rebound")
            sandbox = item.get("sandbox_attestation")
            if isinstance(sandbox, dict) and origin.get("sandbox_attestation") != sandbox:
                errors.append("container reuse origin sandbox identity is rebound")
    return errors


def container_reuse_origin_run_errors(
    item: Mapping[str, Any], run: Mapping[str, Any]
) -> list[str]:
    """Bind a retained reuse result to one real origin execution in RUN."""

    origin = item.get("container_reuse_origin")
    if origin is None:
        return []
    if not isinstance(origin, dict):
        return ["container reuse origin is malformed"]
    executions = run.get("verifier_executions")
    if not isinstance(executions, list):
        return ["container reuse origin has no retained RUN executions"]
    matches = set()
    for candidate in executions:
        if not isinstance(candidate, dict) or candidate is item:
            continue
        if (
            candidate.get("execution_key") == origin.get("execution_key")
            and candidate.get("verifier_id") == origin.get("verifier_id")
            and candidate.get("status") == "PASS"
            and candidate.get("exit_code") == 0
            and isinstance(candidate.get("context"), dict)
            and candidate["context"].get("layer") in {"task", "worker"}
            and _sha256_bytes(_canonical_json(candidate["context"])) == origin.get("context_sha256")
            and candidate.get("cache_status") == "bypassed"
            and candidate.get("cache_reason") == "same_runner_container_origin"
            and candidate.get("sandbox_attestation")
            == origin.get("sandbox_attestation")
            and candidate.get("container_reuse_origin") is None
            and _output_digest(candidate, "stdout") == origin.get("stdout_sha256")
            and _output_digest(candidate, "stderr") == origin.get("stderr_sha256")
            and candidate.get("git_guard_attestation") == item.get("git_guard_attestation")
        ):
            matches.add((candidate["execution_key"], candidate["verifier_id"], origin["context_sha256"]))
    if len(matches) != 1:
        return ["container reuse origin must match exactly one retained same-runner PASS"]
    return []


def _valid_container_cache_entry(
    value: Any, execution_key: str
) -> bool:
    required = {
        "execution_key",
        "status",
        "stdout",
        "stderr",
        "verifier_id",
        "context",
        "sandbox_attestation",
    }
    return (
        isinstance(value, dict)
        and set(value) == required
        and value["execution_key"] == execution_key
        and value["status"] == "PASS"
        and isinstance(value["stdout"], str)
        and isinstance(value["stderr"], str)
        and isinstance(value["verifier_id"], str)
        and bool(value["verifier_id"])
        and isinstance(value["context"], dict)
        and isinstance(value["sandbox_attestation"], dict)
    )


def _timings(
    start: float, current: float, **fields: int
) -> dict[str, int]:
    values = {
        key: max(0, value) for key, value in fields.items()
    }
    values["end_to_end_ms"] = max(
        0,
        round((current - start) * 1000),
    )
    return values


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
    sandbox_preflight: dict[str, Any] | None = None,
    host_preflight: dict[str, Any] | None = None,
    snapshot_archive_cache: _SnapshotArchiveCache | None = None,
    container_result_cache: _ContainerResultCache | None = None,
) -> dict[str, Any]:
    entry_started = time.perf_counter()
    if timeout_seconds <= 0:
        raise VerifierRuntimeError("timeout_seconds must be positive")
    effective_environment = dict(os.environ if environment is None else environment)
    setup_started = time.perf_counter()
    cwd, argv, normalized_verifier, key_inputs = _validated_inputs(
        verifier,
        context,
        checkout_root,
        effective_environment,
    )
    execution_policy = normalized_verifier.get("execution", {})
    container_mode = execution_policy.get("isolation") == "container"
    host_mode = execution_policy.get("isolation") == "host"
    container_policy = execution_policy.get("sandbox")
    checked_sandbox_preflight: dict[str, Any] | None = None
    if container_mode:
        if not isinstance(container_policy, dict):
            raise VerifierRuntimeError("container sandbox policy is malformed")
        checked_sandbox_preflight = _validated_sandbox_preflight(
            container_policy,
            sandbox_preflight,
        )
    elif sandbox_preflight is not None:
        raise VerifierRuntimeError(
            "sandbox_preflight is valid only for container execution"
        )
    checked_host_preflight: dict[str, Any] | None = None
    if host_mode:
        checked_host_preflight = _validated_host_preflight(host_preflight)
    elif host_preflight is not None:
        raise VerifierRuntimeError(
            "host_preflight is valid only for host execution"
        )
    execution_key, key_document = _key_document(normalized_verifier, key_inputs)
    if checked_sandbox_preflight is not None:
        key_document["sandbox_preflight"] = copy_json(checked_sandbox_preflight)
        execution_key = execution_key_from_document(key_document)
    if checked_host_preflight is not None:
        if checked_host_preflight["argv0"] != argv[0]:
            raise VerifierRuntimeError("host preflight argv0 differs from declaration")
        key_document["host_preflight"] = copy_json(checked_host_preflight)
        execution_key = execution_key_from_document(key_document)
    if host_mode and git_guard is None:
        raise VerifierRuntimeError("host verifier requests require a live git_guard")
    checked_reservation = _validated_reservation(reservation)
    context_layer = key_inputs["context"].get("layer")
    context_role = key_inputs["context"].get("checkout_role")
    if (
        context_layer in {"task", "worker"}
        and context_role == "worker"
        and git_guard is None
    ):
        raise VerifierRuntimeError(
            "current task/worker verifier requests require a live git_guard"
        )
    if (
        context_layer in {"task", "worker"}
        and context_role == "worker"
        and normalized_verifier.get("read_only") is not True
    ):
        raise VerifierRuntimeError(
            "current task/worker verifier commands require an explicit read_only declaration"
        )
    if git_guard is not None:
        if not isinstance(git_guard, dict) or git_guard.get("expected_head_sha") != key_inputs["context"].get("head_sha"):
            raise VerifierRuntimeError(
                "git_guard.expected_head_sha must equal context.head_sha"
            )
    worker_guarded_mode = context_layer in {"task", "worker"} and context_role == "worker"
    if worker_guarded_mode and not (container_mode or host_mode):
        raise VerifierRuntimeError(
            "current task/worker verifier commands require explicit container or host isolation"
        )
    if host_mode and not _host_cache_allowed(normalized_verifier):
        raise VerifierRuntimeError("host verifier execution requires disabled cache")
    dispatch_attestation = None
    git_guard_attestation = None
    sandbox_attestation = None
    host_attestation: dict[str, Any] | None = None
    if checked_reservation is not None:
        if git_guard is None or not isinstance(request_sha256, str) or (
            len(request_sha256) != 64
            or any(char not in "0123456789abcdef" for char in request_sha256)
        ):
            raise VerifierRuntimeError(
                "a reserved verifier requires git_guard and the canonical request SHA-256"
            )
    guard_started = time.perf_counter()
    guard_snapshot = (
        _git_guard_snapshot(checkout_root.resolve(), git_guard)
        if git_guard is not None
        else None
    )
    guard_ms = max(0, round((time.perf_counter() - guard_started) * 1000))
    setup_ms = max(0, round((guard_started - setup_started) * 1000))
    if git_guard is not None:
        assert isinstance(guard_snapshot, dict)
        git_guard_attestation = {
            "checkout_root": str(checkout_root.resolve()),
            "git_guard": json.loads(json.dumps(git_guard)),
            "isolation_mode": execution_policy["isolation"],
            "source_head_sha": key_inputs["context"]["head_sha"],
            "tracked_files": copy_json(guard_snapshot["tracked_files"]),
            "protected_path_sha256": dict(guard_snapshot["protected_path_sha256"]),
            "protected_path_stats": copy_json(guard_snapshot["protected_path_stats"]),
        }
    if checked_reservation is not None:
        assert isinstance(guard_snapshot, dict)
        dispatch_attestation = {
            "request_sha256": request_sha256,
            "checkout_root": str(checkout_root.resolve()),
            "git_guard": json.loads(json.dumps(git_guard)),
            "protected_path_sha256": dict(
                guard_snapshot["protected_path_sha256"]
            ),
        }
    # Bind reuse to the live checkout and protected inputs as well as the
    # immutable command key. A waiter must recheck the guard after acquiring
    # the flight lock; failed origins leave no reusable entry.
    container_reuse_allowed = _container_reuse_allowed(
        container_mode=container_mode,
        normalized_verifier=normalized_verifier,
        context=key_inputs["context"],
        git_guard=git_guard,
    )
    coalesce = container_result_cache is not None and container_reuse_allowed
    cache_identity = ""
    if coalesce:
        cache_identity = _sha256_bytes(_canonical_json({
            "execution_key": execution_key,
            "checkout_root": os.path.normcase(str(checkout_root.resolve())),
            "git_guard": git_guard,
            "guard_snapshot": guard_snapshot,
        }))
    flight = container_result_cache.flight(cache_identity) if coalesce else nullcontext()
    with flight:
        if coalesce and _git_guard_snapshot(
            checkout_root.resolve(), git_guard
        ) != guard_snapshot:
            raise VerifierRuntimeError("verifier inputs changed while waiting for execution")
        cache_started = time.perf_counter()
        if container_reuse_allowed and container_result_cache is not None:
            cached = container_result_cache.get(cache_identity)
            if cached is not None:
                if not _valid_container_cache_entry(cached, execution_key):
                    container_result_cache = None
                else:
                    matched_repo_digest = _verify_container_runtime_identity(
                        bound_executable=Path(
                            checked_sandbox_preflight["runtime_probe"]["executable"]
                        ),
                        runtime=container_policy["runtime"],
                        checked_preflight=checked_sandbox_preflight,
                    )
                    sandbox_attestation = _container_attestation(
                        container_policy["runtime"],
                        container_policy["image"],
                        matched_repo_digest,
                        checked_sandbox_preflight,
                        container_policy,
                    )
                    if git_guard_attestation is not None:
                        git_guard_attestation["sandbox_attestation"] = copy_json(
                            sandbox_attestation
                        )
                    if git_guard is not None:
                        if _git_guard_snapshot(
                            checkout_root.resolve(), git_guard
                        ) != guard_snapshot:
                            raise VerifierRuntimeError(
                                "tracked or protected verifier inputs changed while reusing a same-runner result"
                            )
                    return {
                        "protocol": PROTOCOL,
                        "verifier_id": normalized_verifier["id"],
                        "status": "PASS",
                        "exit_code": 0,
                        "stdout": cached["stdout"],
                        "stderr": cached["stderr"],
                        "execution_key": execution_key,
                        "evidence_key": execution_key,
                        "verifier": normalized_verifier,
                        "context": key_inputs["context"],
                        "key_document": key_document,
                        "cache_status": "reused",
                        "cache_reason": "same_runner_container_pass",
                        "duration_ms": 0,
                        "metrics": {"executed": 0, "reused": 1},
                        "container_reuse_origin": {
                            "kind": "same_runner",
                            "execution_key": execution_key,
                            "verifier_id": cached["verifier_id"],
                            "context_sha256": _sha256_bytes(
                                _canonical_json(cached["context"])
                            ),
                            "stdout_sha256": _sha256_bytes(
                                cached["stdout"].encode("utf-8")
                            ),
                            "stderr_sha256": _sha256_bytes(
                                cached["stderr"].encode("utf-8")
                            ),
                            "sandbox_attestation": copy_json(
                                cached["sandbox_attestation"]
                            ),
                        },
                        "timings": _timings(
                            entry_started,
                            time.perf_counter(),
                            setup_ms=setup_ms,
                            git_guard_ms=guard_ms,
                            cache_lookup_ms=max(
                                0,
                                round((time.perf_counter() - cache_started) * 1000),
                            ),
                            snapshot_ms=0,
                            command_ms=0,
                            postcheck_ms=0,
                        ),
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
                        **(
                            {"git_guard_attestation": git_guard_attestation}
                            if git_guard_attestation is not None
                            else {}
                        ),
                        **(
                            {"sandbox_attestation": sandbox_attestation}
                            if sandbox_attestation is not None
                            else {}
                        ),
                    }
        cache_mode = normalized_verifier["cache"]["mode"]
        cache_status = "bypassed"
        cache_reason = "cache_disabled"
        cache_path: Path | None = None
        can_reuse = cache_mode == "session_exact"
        if container_mode and can_reuse:
            can_reuse = False
            cache_reason = "container_disk_cache_disabled"
        if host_mode and cache_mode == "session_exact":
            can_reuse = False
            cache_reason = "host_cache_disabled"
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
                    cache_lookup_ms = max(
                        0,
                        round((time.perf_counter() - cache_started) * 1000),
                    )
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
                        "timings": _timings(
                            entry_started,
                            time.perf_counter(),
                            setup_ms=setup_ms,
                            git_guard_ms=guard_ms,
                            cache_lookup_ms=cache_lookup_ms,
                            snapshot_ms=0,
                            command_ms=0,
                            postcheck_ms=0,
                        ),
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
                        **(
                            {"git_guard_attestation": git_guard_attestation}
                            if git_guard_attestation is not None
                            else {}
                        ),
                    }
                cache_status = "miss"
            else:
                can_reuse = False
                cache_reason = "cache_root_inside_checkout"
        cache_lookup_ms = max(
            0,
            round((time.perf_counter() - cache_started) * 1000),
        )

        snapshot_temp: tempfile.TemporaryDirectory[str] | None = None
        execution_cwd = cwd
        execution_argv = ([checked_host_preflight["executable"], *argv[1:]] if host_mode else argv)
        execution_environment = effective_environment
        snapshot_started = time.perf_counter()
        if container_mode:
            snapshot_temp, execution_cwd, execution_argv = _materialize_git_snapshot(
                checkout_root,
                key_inputs["context"]["head_sha"],
                normalized_verifier["cwd"],
                argv,
                archive_cache=snapshot_archive_cache,
            )
            execution_environment = _snapshot_environment(
                effective_environment, checkout_root, execution_cwd
            )
        snapshot_ms = max(
            0,
            round((time.perf_counter() - snapshot_started) * 1000),
        )
        started = time.perf_counter()
        try:
            if container_mode:
                assert snapshot_temp is not None
                completed, sandbox_attestation = _run_container_verifier(
                    checkout_root,
                    Path(snapshot_temp.name),
                    normalized_verifier["cwd"],
                    argv,
                    container_policy,
                    timeout_seconds,
                    sandbox_preflight=checked_sandbox_preflight,
                )
            else:
                if host_mode:
                    assert checked_host_preflight is not None
                    _verify_host_runtime_identity(
                        argv[0],
                        execution_cwd,
                        execution_environment,
                        checked_host_preflight,
                    )
                completed = subprocess.run(
                    execution_argv,
                    cwd=execution_cwd,
                    env=execution_environment,
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
        finally:
            command_ms = max(0, round((time.perf_counter() - started) * 1000))
            if snapshot_temp is not None:
                snapshot_temp.cleanup()
        postcheck_started = time.perf_counter()
        if git_guard is not None:
            try:
                after_snapshot = _git_guard_snapshot(checkout_root.resolve(), git_guard)
                if after_snapshot != guard_snapshot:
                    raise VerifierRuntimeError(
                        "tracked or protected verifier inputs changed while the command was running"
                    )
            except VerifierRuntimeError as exc:
                status = "ERROR"
                exit_code = None
                stderr = (stderr + "\n" if stderr else "") + str(exc)
        postcheck_ms = max(
            0,
            round((time.perf_counter() - postcheck_started) * 1000),
        )
        if git_guard_attestation is not None and sandbox_attestation is not None:
            git_guard_attestation["sandbox_attestation"] = copy_json(sandbox_attestation)
        if host_mode:
            assert checked_host_preflight is not None
            try:
                executable, executable_sha256 = _verify_host_runtime_identity(
                    argv[0],
                    execution_cwd,
                    execution_environment,
                    checked_host_preflight,
                )
                host_attestation = _host_attestation(
                    execution_cwd,
                    executable,
                    executable_sha256,
                )
                if git_guard_attestation is not None:
                    git_guard_attestation["host_execution_attestation"] = copy_json(
                        host_attestation
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

        if (
            status == "PASS"
            and container_reuse_allowed
            and container_result_cache is not None
            and sandbox_attestation is not None
        ):
            container_result_cache.store(
                cache_identity,
                {
                    "execution_key": execution_key,
                    "status": "PASS",
                    "stdout": stdout,
                    "stderr": stderr,
                    "verifier_id": normalized_verifier["id"],
                    "context": copy_json(key_inputs["context"]),
                    "sandbox_attestation": copy_json(sandbox_attestation),
                }
            )
        if container_mode:
            cache_status = "bypassed"
            cache_reason = (
                "same_runner_container_origin"
                if container_reuse_allowed
                else "container_disk_cache_disabled"
            )
        elif host_mode:
            cache_status = "bypassed"
            cache_reason = "host_cache_disabled"

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
            "timings": _timings(
                entry_started,
                time.perf_counter(),
                setup_ms=setup_ms,
                git_guard_ms=guard_ms,
                cache_lookup_ms=cache_lookup_ms,
                snapshot_ms=snapshot_ms,
                command_ms=command_ms,
                postcheck_ms=postcheck_ms,
            ),
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
            **(
                {"git_guard_attestation": git_guard_attestation}
                if git_guard_attestation is not None
                else {}
            ),
            **(
                {"sandbox_attestation": sandbox_attestation}
                if sandbox_attestation is not None
                else {}
            ),
            **(
                {"host_execution_attestation": host_attestation}
                if host_attestation is not None
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
    """Execute verifier jobs by filling free slots with eligible work."""

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
        if not isinstance(job, dict) or not BATCH_JOB_FIELDS.issubset(job) or not set(job).issubset(
            BATCH_JOB_FIELDS | BATCH_JOB_OPTIONAL_FIELDS
        ):
            raise VerifierRuntimeError(
                "each job must contain exactly job_id, verifier, context, checkout_root, "
                "cache_root, and timeout_seconds; task/worker jobs also require git_guard"
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

    prepared.sort(key=lambda item: item[0])
    # Report the old deterministic conflict/capacity grouping for consumers.
    # Execution below no longer waits at those boundaries.
    compatibility_waves: list[list[tuple[str, dict[str, Any], dict[str, Any]]]] = []
    for prepared_job in prepared:
        for wave in compatibility_waves:
            if len(wave) < max_parallel and all(
                not _execution_policies_conflict(prepared_job[2], existing[2])
                for existing in wave
            ):
                wave.append(prepared_job)
                break
        else:
            compatibility_waves.append([prepared_job])
    snapshot_archive_cache = _SnapshotArchiveCache()
    container_result_cache = _ContainerResultCache()

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
                git_guard=job.get("git_guard"),
                reservation=job.get("reservation"),
                request_sha256=job.get("request_sha256"),
                sandbox_preflight=job.get("sandbox_preflight"),
                host_preflight=job.get("host_preflight"),
                snapshot_archive_cache=snapshot_archive_cache,
                container_result_cache=container_result_cache,
            )
        except (OSError, ValueError, VerifierRuntimeError) as exc:
            return {"protocol": PROTOCOL, "status": "ERROR", "errors": [str(exc)]}

    started = time.perf_counter()
    results_by_id: dict[str, dict[str, Any]] = {}
    pending = list(prepared)
    active: dict[Any, tuple[str, dict[str, Any]]] = {}
    serial_waves = len(compatibility_waves)
    peak_parallel = 0
    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        while pending or active:
            for candidate in list(pending):
                if len(active) >= max_parallel:
                    break
                if any(
                    _execution_policies_conflict(candidate[2], policy)
                    for _, policy in active.values()
                ):
                    continue
                job_id, job, policy = candidate
                active[executor.submit(execute, job)] = (job_id, policy)
                pending.remove(candidate)
                peak_parallel = max(peak_parallel, len(active))
            if not active:
                raise VerifierRuntimeError("verifier scheduler made no progress")
            completed, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in completed:
                job_id, _ = active.pop(future)
                try:
                    results_by_id[job_id] = future.result()
                except Exception as exc:
                    results_by_id[job_id] = {
                        "protocol": PROTOCOL, "status": "ERROR", "errors": [str(exc)]
                    }
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
            "waves": serial_waves,
            "max_parallel": peak_parallel,
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
    raise SystemExit(main())
