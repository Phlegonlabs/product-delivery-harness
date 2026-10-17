#!/usr/bin/env python3
"""Read and join one retained Deployment source observation."""

from __future__ import annotations

from datetime import datetime, timezone
import ctypes
import ctypes.wintypes as wintypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any


OBSERVATION_SCHEMA = "deployment-source-observation/1"
OBSERVATION_FIELDS = {
    "schema",
    "target",
    "repository",
    "source_ref",
    "resolved_ref",
    "source_sha",
    "artifact",
    "observed_at",
    "readback",
}
READBACK_FIELDS = {"kind", "request", "status", "output"}
OUTPUT_FIELDS = {"repository", "ref", "sha", "artifact"}
MAX_OBSERVATION_BYTES = 1024 * 1024
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
SHA64_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
REPOSITORY_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)+$"
)
PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]|<[^>]+>|\b(?:tbd|todo|placeholder)\b", re.I)
UTF8_SCALAR_RE = re.compile(r"^[\x20-\x7e\t\n\r\u0080-\uffff]*$", re.A)
CREDENTIAL_REQUEST_RE = re.compile(
    r"(?is)"
    r"(?:^|\r?\n)\s*(?:authorization|proxy-authorization|api-key|x-api-key)\s*:"
    r"|\bbearer\s+[a-z0-9._~+/=-]{8,}\b"
    r"|://[^\s/@:]+:[^\s/@]+@"
    r"|(?:^|[;&\s])(?:password|secret|token|api[_-]?key|access[_-]?key)\s*="
)
WINDOWS_DEVICE_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
KNOWN_CREDENTIAL_PATHS = {
    ".env", ".env.local", ".dev.vars", "credentials.json", "credential-store",
    "id_rsa", "id_ed25519", "token.json",
}
ROOT_CREDENTIAL_COMPONENTS = {
    "provider_config.json", "bridge.local.json", ".aws", ".ssh", ".gnupg",
    ".docker", ".kube", ".azure",
}
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class _DuplicateKeyError(ValueError):
    pass


if sys.platform == "win32":
    class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("file_attributes", ctypes.c_ulong),
            ("_creation_time", wintypes.FILETIME),
            ("_access_time", wintypes.FILETIME),
            ("_write_time", wintypes.FILETIME),
            ("volume_serial", ctypes.c_ulong),
            ("size_high", ctypes.c_ulong),
            ("size_low", ctypes.c_ulong),
            ("number_of_links", ctypes.c_ulong),
            ("index_high", ctypes.c_ulong),
            ("index_low", ctypes.c_ulong),
        ]

        @property
        def size(self) -> int:
            return (self.size_high << 32) | self.size_low

        @property
        def index(self) -> int:
            return (self.index_high << 32) | self.index_low

        @property
        def creation_time(self) -> int:
            return (self._creation_time.dwHighDateTime << 32) | self._creation_time.dwLowDateTime

        @property
        def write_time(self) -> int:
            return (self._write_time.dwHighDateTime << 32) | self._write_time.dwLowDateTime


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _timestamp(value: str) -> datetime | None:
    if not RFC3339_RE.fullmatch(value):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _substantive(value: str) -> bool:
    return bool(value.strip()) and PLACEHOLDER_RE.search(value) is None


def _utf8_scalar(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return UTF8_SCALAR_RE.fullmatch(value) is not None


def _has_credential_request(request: str) -> bool:
    return CREDENTIAL_REQUEST_RE.search(request) is not None


def _reject_reference(path_text: str) -> str | None:
    if not path_text or path_text.strip() != path_text:
        return "path is empty or has surrounding spacing"
    if "\\" in path_text or ":" in path_text:
        return "path uses a backslash, drive, URL, or alternate stream separator"
    if path_text.startswith("/") or path_text.startswith("//"):
        return "path is absolute or UNC-like"
    raw = path_text.encode("utf-8", errors="surrogatepass")
    if any(code < 32 or code == 127 for code in raw):
        return "path contains a control character"
    parts = path_text.split("/")
    for part in parts:
        if part in {"", ".", ".."}:
            return "path contains an empty, current, or parent component"
        if part != part.strip() or part.endswith("."):
            return "path contains a dot-space or trailing-dot component"
        lowered = part.casefold()
        device_basename = lowered.split(".", 1)[0]
        if (
            lowered in WINDOWS_DEVICE_NAMES
            or device_basename in WINDOWS_DEVICE_NAMES
            or lowered in KNOWN_CREDENTIAL_PATHS
            or lowered in ROOT_CREDENTIAL_COMPONENTS
            or (
                (lowered.startswith(".env.") or lowered.startswith(".dev.vars."))
                and lowered not in {".env.example", ".env.template"}
            )
        ):
            return "path names a device or known credential path"
    if ".config" in parts and "gcloud" in parts:
        return "path names a known credential path"
    return None


def _is_reparse_metadata(metadata: os.stat_result) -> bool:
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _identity_changed(before: os.stat_result, after: os.stat_result) -> bool:
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    return any(getattr(before, field) != getattr(after, field) for field in fields)


def _directory_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode)


def _posix_refused_link(exception: OSError) -> bool:
    return exception.errno in (errno.ELOOP, getattr(errno, "ENOTDIR", errno.ELOOP))


def _read_bounded_regular_posix(
    root: Path,
    parts: tuple[str, ...],
    label: str,
    _race_probe=None,
) -> tuple[bytes, str, list[str]]:
    if sys.platform == "win32":
        return b"", "", [f"{label}: safe descriptor binding is unavailable"]
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    leaf_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptors: list[int] = []
    leaf_fd = None
    try:
        descriptors.append(os.open(root.parts[0], directory_flags))
        for part in root.parts[1:]:
            descriptors.append(
                os.open(part, directory_flags, dir_fd=descriptors[-1])
            )
            metadata = os.fstat(descriptors[-1])
            if not stat.S_ISDIR(metadata.st_mode) or _is_reparse_metadata(metadata):
                return b"", "", [
                    f"{label}: retained evidence path contains a symlink or reparse point"
                ]

        for part in parts[:-1]:
            descriptors.append(
                os.open(part, directory_flags, dir_fd=descriptors[-1])
            )
            metadata = os.fstat(descriptors[-1])
            if not stat.S_ISDIR(metadata.st_mode) or _is_reparse_metadata(metadata):
                return b"", "", [
                    f"{label}: retained evidence path contains a symlink or reparse point"
                ]

        if _race_probe is not None:
            _race_probe("before-read", Path(root.parts[0]).joinpath(*root.parts[1:], *parts))
        parent_before = os.fstat(descriptors[-1])
        leaf_fd = os.open(parts[-1], leaf_flags, dir_fd=descriptors[-1])
        leaf_before = os.fstat(leaf_fd)
        if not stat.S_ISREG(leaf_before.st_mode):
            return b"", "", [f"{label}: retained evidence is not a regular file"]
        if leaf_before.st_size > MAX_OBSERVATION_BYTES:
            return b"", "", [f"{label}: retained evidence exceeds 1 MiB"]
        if _race_probe is not None:
            _race_probe("after-open", Path(root.parts[0]).joinpath(*root.parts[1:], *parts))
        content = b""
        while len(content) <= MAX_OBSERVATION_BYTES:
            chunk = os.read(
                leaf_fd,
                min(65536, MAX_OBSERVATION_BYTES + 1 - len(content)),
            )
            if not chunk:
                break
            content += chunk
        leaf_after = os.fstat(leaf_fd)
        if _race_probe is not None:
            _race_probe("after-read", Path(root.parts[0]).joinpath(*root.parts[1:], *parts))
        parent_after = os.fstat(descriptors[-1])
        if _identity_changed(leaf_before, leaf_after):
            return b"", "", [f"{label}: retained evidence changed while it was read"]
        if _directory_identity(parent_before) != _directory_identity(parent_after):
            return b"", "", [f"{label}: retained evidence parent changed while it was read"]
        parent_reopened_fd = _posix_open_relative_directory(
            descriptors[0],
            tuple(root.parts[1:] + parts[:-1]),
            directory_flags,
        )
        try:
            parent_reopened = os.fstat(parent_reopened_fd)
        finally:
            os.close(parent_reopened_fd)
        if _directory_identity(parent_before) != _directory_identity(parent_reopened):
            return b"", "", [
                f"{label}: retained evidence parent changed while it was read"
            ]
        os.close(leaf_fd)
        leaf_fd = None
    except (OSError, ValueError) as exception:
        if isinstance(exception, OSError) and _posix_refused_link(exception):
            return b"", "", [
                f"{label}: retained evidence path contains a symlink or reparse point"
            ]
        return b"", "", [f"{label}: retained evidence cannot be read safely"]
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        if leaf_fd is not None:
            os.close(leaf_fd)

    if len(content) > MAX_OBSERVATION_BYTES:
        return b"", "", [f"{label}: retained evidence exceeds 1 MiB"]
    return content, hashlib.sha256(content).hexdigest(), []


def _posix_open_relative_directory(anchor_fd: int, parts: tuple[str, ...], flags: int) -> int:
    fd = anchor_fd
    opened = None
    try:
        for part in parts:
            opened = os.open(part, flags, dir_fd=fd)
            if fd != anchor_fd:
                os.close(fd)
            fd = opened
        return fd
    except (OSError, ValueError):
        if opened is not None and opened != fd:
            os.close(opened)
        raise


def _valid_handle(handle: int | None) -> bool:
    return handle is not None and handle != INVALID_HANDLE_VALUE


def _windows_kernel():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CreateFileW.argtypes = (
        ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
    )
    kernel.GetFileInformationByHandle.argtypes = (
        ctypes.c_void_p, ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION),
    )
    kernel.GetFileInformationByHandleEx.argtypes = (
        ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong,
    )
    kernel.ReadFile.argtypes = (
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p,
    )
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def _windows_info(kernel: ctypes.WinDLL, handle: int) -> _BY_HANDLE_FILE_INFORMATION | None:
    info = _BY_HANDLE_FILE_INFORMATION()
    if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
        return None
    return info


def _windows_identity(info: _BY_HANDLE_FILE_INFORMATION) -> tuple:
    return (
        info.volume_serial, info.index, info.size,
        info.creation_time, info.write_time, info.file_attributes,
    )


def _windows_open(
    kernel: ctypes.WinDLL,
    path: Path,
    *,
    directory: bool,
    read: bool,
    share: int = 7,
):
    desired = 0x80 if not read else 0x80000000
    flags = 0x00200000
    flags |= 0x02000000
    if not directory and not read:
        flags |= 0x80
    return kernel.CreateFileW(
        str(path), desired, share, None, 3, flags, None
    )


def _read_bounded_regular_windows(
    root: Path,
    parts: tuple[str, ...],
    label: str,
    _race_probe=None,
) -> tuple[bytes, str, list[str]]:
    failure = [f"{label}: safe native descriptor binding is unavailable"]
    open_failure = [f"{label}: retained evidence cannot be read safely"]
    if sys.platform != "win32":
        return b"", "", failure
    handles: list[int] = []
    kernel = None
    try:
        kernel = _windows_kernel()
        root_path = Path(os.path.abspath(root))
        if root_path.drive.startswith("\\\\"):
            return b"", "", [f"{label}: UNC repository roots are not safe evidence roots"]
        chain_paths = [root_path]
        chain_paths.extend(
            root_path.joinpath(*parts[:index])
            for index in range(1, len(parts))
        )
        for chain_path in chain_paths:
            handle = _windows_open(
                kernel, chain_path, directory=True, read=False, share=3
            )
            if not _valid_handle(handle):
                return b"", "", open_failure
            handles.append(handle)
            info = _windows_info(kernel, handle)
            if info is None:
                return b"", "", failure
            if info.file_attributes & 0x400 or not info.file_attributes & 0x10:
                return b"", "", [f"{label}: retained evidence root contains a link or reparse point"]
        parent_before = _windows_info(kernel, handles[-1])
        if parent_before is None:
            return b"", "", failure

        leaf_path = root_path.joinpath(*parts)
        leaf_handle = _windows_open(kernel, leaf_path, directory=False, read=False)
        if not _valid_handle(leaf_handle):
            return b"", "", open_failure
        handles.append(leaf_handle)
        leaf_before = _windows_info(kernel, leaf_handle)
        if leaf_before is None:
            return b"", "", failure
        if leaf_before.file_attributes & 0x400:
            return b"", "", [f"{label}: retained evidence path contains a link or reparse point"]
        if leaf_before.file_attributes & 0x10:
            return b"", "", [f"{label}: retained evidence is not a regular file"]
        if leaf_before.size > MAX_OBSERVATION_BYTES:
            return b"", "", [f"{label}: retained evidence exceeds 1 MiB"]
        if _race_probe is not None:
            _race_probe("after-open", leaf_path)
        read_handle = _windows_open(kernel, leaf_path, directory=False, read=True)
        if not _valid_handle(read_handle):
            return b"", "", open_failure
        handles.append(read_handle)
        if _race_probe is not None:
            _race_probe("after-open", leaf_path)

        content = b""
        remaining = MAX_OBSERVATION_BYTES + 1
        while remaining:
            request = min(65536, remaining)
            buffer = ctypes.create_string_buffer(65536)
            count = ctypes.c_ulong(0)
            if not kernel.ReadFile(
                read_handle, buffer, request, ctypes.byref(count), None
            ):
                return b"", "", open_failure
            if not count.value:
                break
            content += buffer.raw[:count.value]
            remaining -= count.value
        leaf_after = _windows_info(kernel, leaf_handle)
        if leaf_after is None or _windows_identity(leaf_before) != _windows_identity(leaf_after):
            return b"", "", [f"{label}: retained evidence changed while it was read"]
        if _race_probe is not None:
            _race_probe("after-read", leaf_path)

        if parent_before is None:
            return b"", "", failure
        parent_handle = _windows_open(kernel, leaf_path.parent, directory=True, read=False)
        if not _valid_handle(parent_handle):
            return b"", "", open_failure
        handles.append(parent_handle)
        parent_after = _windows_info(kernel, parent_handle)
        if parent_before is None or parent_after is None:
            return b"", "", failure
        if parent_before.volume_serial != parent_after.volume_serial or parent_before.index != parent_after.index:
            return b"", "", [f"{label}: retained evidence parent changed while it was read"]
        root_before = _windows_info(kernel, handles[0])
        if root_before is None:
            return b"", "", failure
        root_handle = _windows_open(kernel, chain_paths[0], directory=True, read=False, share=3)
        if not _valid_handle(root_handle):
            return b"", "", open_failure
        handles.append(root_handle)
        root_after = _windows_info(kernel, root_handle)
        if root_after is None:
            return b"", "", failure
        if root_before.volume_serial != root_after.volume_serial or root_before.index != root_after.index:
            return b"", "", [f"{label}: retained evidence root changed while it was read"]
    except (OSError, ValueError):
        return b"", "", failure
    finally:
        for handle in reversed(handles):
            if kernel is not None and _valid_handle(handle):
                kernel.CloseHandle(handle)

    if len(content) > MAX_OBSERVATION_BYTES:
        return b"", "", [f"{label}: retained evidence exceeds 1 MiB"]
    return content, hashlib.sha256(content).hexdigest(), []


def _safe_regular_bytes(
    repo_root: Path,
    relative_path: str,
    label: str,
) -> tuple[bytes, str, list[str]]:
    path_error = _reject_reference(relative_path)
    if path_error:
        return b"", "", [f"{label}: retained evidence {path_error}"]
    parts = tuple(part for part in relative_path.split("/") if part)
    absolute_root = Path(os.path.abspath(repo_root))
    if os.name == "nt":
        return _read_bounded_regular_windows(absolute_root, parts, label)
    return _read_bounded_regular_posix(absolute_root, parts, label)


def _load_json(
    content: bytes,
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        text = content.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, TypeError):
        return None, [f"{label}: retained evidence is not strict UTF-8 JSON"]
    if not isinstance(value, dict):
        return None, [f"{label}: retained observation must be a JSON object"]
    return value, []


def load_retained_observation(
    *,
    repo_root: Path,
    reference: str,
    expected_hash: str,
    expected_repository: str,
    target: str,
    source_ref: str,
    resolved_ref: str,
    source_sha: str,
    artifact: str,
    checked_at: datetime | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Load one bounded retained observation and return it with findings."""

    label = f"target {target}"
    match = re.fullmatch(
        r"file:(?P<path>[^@]+)@sha256:(?P<hash>[0-9a-f]{64})",
        reference,
    )
    if match is None:
        return None, [
            f"{label}: authority evidence must use "
            "file:<relative-path>@sha256:<64 lowercase hex>"
        ]
    if match.group("hash") != expected_hash:
        return None, [f"{label}: authority evidence digest is malformed"]

    content, actual_hash, findings = _safe_regular_bytes(
        repo_root,
        match.group("path"),
        label,
    )
    if findings:
        return None, findings
    if actual_hash != expected_hash:
        return None, [f"{label}: retained evidence hash does not match authority evidence"]

    observation, json_findings = _load_json(content, label)
    findings.extend(json_findings)
    if observation is None:
        return None, findings
    if set(observation) != OBSERVATION_FIELDS:
        findings.append(f"{label}: retained observation fields are not exactly closed")
        return None, findings

    scalar_fields = (
        "schema", "target", "repository", "source_ref", "resolved_ref",
        "source_sha", "artifact", "observed_at",
    )
    strings: dict[str, str] = {}
    for field in scalar_fields:
        value = observation[field]
        if not isinstance(value, str):
            findings.append(
                f"{label}: retained observation {field} must be a string"
            )
        elif not _utf8_scalar(value):
            findings.append(
                f"{label}: retained observation {field} must be valid UTF-8 "
                "scalar text"
            )
        else:
            strings[field] = value
    if len(strings) != len(scalar_fields):
        return None, findings

    readback = observation["readback"]
    if not isinstance(readback, dict):
        findings.append(f"{label}: retained readback must be an object")
        return None, findings
    if set(readback) != READBACK_FIELDS:
        findings.append(f"{label}: retained readback fields are not exactly closed")
        return None, findings

    readback_strings: dict[str, str] = {}
    for field in ("kind", "request", "output"):
        value = readback[field]
        if not isinstance(value, str):
            findings.append(f"{label}: retained readback {field} must be a string")
        elif not _utf8_scalar(value):
            findings.append(
                f"{label}: retained readback {field} must be valid UTF-8 "
                "scalar text"
            )
        else:
            readback_strings[field] = value
    status = readback["status"]
    if isinstance(status, bool) or not isinstance(status, int):
        findings.append(f"{label}: retained readback status must be an integer")
    if len(readback_strings) != 3 or isinstance(status, bool) or not isinstance(
        status, int
    ):
        return None, findings

    output_text = readback["output"]
    output: dict[str, Any] | None = None
    try:
        output_value = json.loads(
            output_text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
        )
    except (ValueError, TypeError):
        output_value = None
    if not isinstance(output_value, dict) or set(output_value) != OUTPUT_FIELDS:
        findings.append(f"{label}: retained output fields are not exactly closed")
    else:
        output_strings: dict[str, str] = {}
        for field in OUTPUT_FIELDS:
            value = output_value[field]
            if not isinstance(value, str):
                findings.append(
                    f"{label}: retained output {field} must be a string"
                )
            elif not _utf8_scalar(value):
                findings.append(
                    f"{label}: retained output {field} must be valid UTF-8 "
                    "scalar text"
                )
            else:
                output_strings[field] = value
        if len(output_strings) == len(OUTPUT_FIELDS):
            output = output_value

    if observation["schema"] != OBSERVATION_SCHEMA:
        findings.append(f"{label}: retained observation schema must be {OBSERVATION_SCHEMA}")
    if observation["target"] != target:
        findings.append(f"{label}: retained observation target differs from deployment")
    if not REPOSITORY_RE.fullmatch(observation["repository"]):
        findings.append(f"{label}: retained repository identity is malformed")
    elif observation["repository"] != expected_repository:
        findings.append(f"{label}: retained repository differs from expected context")
    if observation["source_ref"] != source_ref:
        findings.append(f"{label}: retained source ref differs from deployment")
    if observation["resolved_ref"] != resolved_ref:
        findings.append(f"{label}: retained resolved ref differs from expected context")
    if not SHA40_RE.fullmatch(observation["source_sha"]):
        findings.append(f"{label}: retained source SHA must be full lowercase hex")
    elif observation["source_sha"] != source_sha:
        findings.append(f"{label}: retained source SHA differs from deployment")
    if observation["artifact"] != artifact:
        findings.append(f"{label}: retained artifact differs from deployment")

    observed_at = _timestamp(observation["observed_at"])
    if observed_at is None:
        findings.append(f"{label}: retained observation time must be RFC3339 with a timezone")
    elif observed_at > datetime.now(timezone.utc):
        findings.append(f"{label}: retained observation time cannot be in the future")
    elif checked_at is not None and observed_at > checked_at:
        findings.append(f"{label}: retained observation is newer than deployment checked time")

    kind = readback["kind"]
    request = readback["request"]
    if kind not in {"command", "provider"}:
        findings.append(f"{label}: retained readback kind must be command or provider")
    if not isinstance(request, str) or not _substantive(request):
        findings.append(f"{label}: retained readback request must be substantive")
    if _has_credential_request(request):
        findings.append(
            f"{label}: retained readback request contains credential-bearing syntax"
        )
    if isinstance(status, bool) or not isinstance(status, int):
        findings.append(f"{label}: retained readback status must be an integer")
    elif kind == "command" and status != 0:
        findings.append(f"{label}: retained command readback status must be zero")
    elif kind == "provider" and not 200 <= status <= 299:
        findings.append(f"{label}: retained provider readback status must be HTTP 2xx")

    if output is not None:
        if output["repository"] != observation["repository"]:
            findings.append(f"{label}: retained output repository differs from observation")
        if output["ref"] != observation["resolved_ref"]:
            findings.append(f"{label}: retained output ref differs from observation")
        if output["sha"] != observation["source_sha"]:
            findings.append(f"{label}: retained output SHA differs from observation")
        if output["artifact"] != observation["artifact"]:
            findings.append(f"{label}: retained output artifact differs from observation")

    if findings:
        return None, findings
    return observation, []


if __name__ == "__main__":
    raise SystemExit(2)
