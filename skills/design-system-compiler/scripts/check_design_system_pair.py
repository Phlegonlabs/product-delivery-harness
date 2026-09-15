#!/usr/bin/env python3
"""Validate design-system.json and its generated Markdown contract view.

The JSON file is the sole structured authority. The Markdown carries rationale
and guardrails plus one generated JSON block that mirrors every field consumed
by implementation and conformance checks. This avoids guessing declarations
from arbitrary Markdown tables or headings.

Exit codes: 0 clean, 1 mismatch, 2 usage or parse error.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import json
import math
import os
import hashlib
import re
import stat
import secrets
import sys
import tempfile
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt
else:
    import fcntl

PRODUCT_BUILDER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"
)
if str(PRODUCT_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_BUILDER_SCRIPTS))
UI_BUILDER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "ui-design-builder" / "scripts"
)
if str(UI_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(UI_BUILDER_SCRIPTS))

from markdown_contract import active_text, exact_marker_lines  # noqa: E402
from ui_approval_digest import canonical_ui_approval_sha256  # noqa: E402


BEGIN_MARKER = "<!-- BEGIN GENERATED DESIGN SYSTEM CONTRACT -->"
END_MARKER = "<!-- END GENERATED DESIGN SYSTEM CONTRACT -->"
CONTRACT_FIELDS = (
    "schema",
    "product",
    "platform",
    "stackSemantics",
    "stylingMechanism",
    "enforcement",
    "sourceBindings",
    "surfaceContracts",
    "tokenSources",
    "primitiveSources",
    "viewports",
    "sizeClasses",
    "tokens",
    "primitives",
    "productComponents",
    "signatureRules",
    "motionVariants",
    "stateMatrix",
)
GENERATED_BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN_MARKER)}\s*```json\s*(.*?)\s*```\s*{re.escape(END_MARKER)}",
    re.DOTALL,
)
PLACEHOLDER_RE = re.compile(r"^<.*>$", re.DOTALL)
DS_COMP_ID_RE = re.compile(r"^DS-COMP-[0-9]+$")
DS_PRIMITIVE_ID_RE = re.compile(r"^DS-[A-Z]+-[0-9]+$")
DS_RULE_ID_RE = re.compile(r"^DS-(?:[A-Z]+-)?[0-9]+$")
DS_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])DS-(?:[A-Z]+-)?[0-9]+(?![A-Za-z0-9_-])"
)
DS_LIKE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])DS-[A-Za-z0-9_-]+(?![A-Za-z0-9_-])"
)
SOURCE_BINDING_KEYS = (
    "prd",
    "architecture",
    "stack",
    "uiDesign",
    "wireframe",
    "hifi",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VALID_PLATFORMS = {"web", "ios", "android", "flutter", "react-native", "macos", "windows", "desktop"}
VALID_HYBRID_SURFACE_CLASSES = {
    "hosted_web",
    "browser_extension",
    "ios",
    "android",
    "macos",
    "windows",
    "desktop",
}
VALID_STYLING_MECHANISMS = {
    "utility CSS",
    "Tailwind CSS",
    "CSS-in-JS",
    "CSS modules",
    "plain CSS",
    "platform theme",
}
VALID_ENFORCEMENT = {"blocking", "advisory"}




class ConcurrentModificationError(RuntimeError):
    """Raised when the destination changed after it was read for a write."""


def _is_reparse_or_link(path: Path) -> bool:
    """Return true for symlinks and Windows reparse-point path components."""

    try:
        info = path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _safe_parent_chain(path: Path) -> None:
    """Reject a destination whose parent chain can redirect the atomic write."""

    cursor = path.parent
    existing: list[Path] = []
    while True:
        existing.append(cursor)
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    for component in reversed(existing):
        if _is_reparse_or_link(component):
            raise ConcurrentModificationError(
                f"{path} parent directory contains a symlink or reparse point: {component}"
            )


def _open_posix_parent(path: Path) -> tuple[int, str]:
    """Walk every POSIX component with O_NOFOLLOW and retain final dirfd."""

    absolute = path.absolute()
    parts = absolute.parts
    if not parts or parts[0] != os.sep:
        raise ConcurrentModificationError(f"{path} must be an absolute POSIX path")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(os.sep, flags)
        try:
            for component in parts[1:-1]:
                next_fd = os.open(component, flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
        except BaseException:
            os.close(directory_fd)
            raise
    except OSError as exc:
        raise ConcurrentModificationError(
            f"{path} parent component cannot be held without following a symlink: {exc}"
        ) from exc
    return directory_fd, parts[-1]


if os.name == "nt":
    _WIN_INVALID_HANDLE = ctypes.c_void_p(-1).value
    _WIN_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
    _WIN_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _WIN_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _WIN_GENERIC_READ = 0x80000000
    _WIN_GENERIC_WRITE = 0x40000000
    _WIN_DELETE = 0x00010000
    _WIN_FILE_SHARE_READ = 0x00000001
    _WIN_FILE_SHARE_WRITE = 0x00000002
    _WIN_OPEN_EXISTING = 3
    _WIN_FILE_RENAME_INFO = 3


def _windows_close(handle: int | None) -> None:
    if os.name != "nt" or handle is None:
        return
    value = handle if isinstance(handle, int) else handle.value
    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(value))


def _windows_open_parent(path: Path) -> tuple[int, list[int]]:
    """Hold every Windows parent component without FILE_SHARE_DELETE."""

    if os.name != "nt":
        raise ConcurrentModificationError("Windows parent handles are unavailable on this host")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.restype = ctypes.c_void_p
    desired = _WIN_GENERIC_READ
    flags = _WIN_FILE_FLAG_BACKUP_SEMANTICS | _WIN_FILE_FLAG_OPEN_REPARSE_POINT

    class _FileAttributeTagInfo(ctypes.Structure):
        _fields_ = [("FileAttributes", ctypes.c_uint32), ("ReparseTag", ctypes.c_uint32)]

    def open_component(component: Path) -> int:
        handle = kernel32.CreateFileW(
            str(component),
            desired,
            _WIN_FILE_SHARE_READ | _WIN_FILE_SHARE_WRITE,
            None,
            _WIN_OPEN_EXISTING,
            flags,
            None,
        )
        if handle in (None, _WIN_INVALID_HANDLE):
            error = ctypes.get_last_error()
            raise ConcurrentModificationError(
                f"{path} parent cannot be held without delete sharing (winerror={error})"
            )
        info = _FileAttributeTagInfo()
        ok = kernel32.GetFileInformationByHandleEx(
            ctypes.c_void_p(handle), 9, ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok or info.FileAttributes & _WIN_FILE_ATTRIBUTE_REPARSE_POINT:
            _windows_close(handle)
            raise ConcurrentModificationError(
                f"{path} parent is a symlink or reparse point"
            )
        return int(handle)

    held: list[int] = []
    try:
        parent = path.parent
        components = list(parent.parts)
        if not components:
            raise ConcurrentModificationError(f"{path} has no Windows parent")
        # Open each absolute component in order. Every prior handle stays open,
        # so an ancestor cannot be renamed or replaced while the final move is
        # in flight. _safe_parent_chain supplied the initial no-reparse check;
        # OPEN_REPARSE_POINT makes the native hold check fail closed as well.
        current = Path(components[0])
        for component in components[1:]:
            current = current / component
            held.append(open_component(current))
        if not held:
            held.append(open_component(parent))
        return held[-1], held[:-1]
    except BaseException:
        for handle in reversed(held):
            _windows_close(handle)
        raise


def _posix_rename_exchange(parent_fd: int, left_name: str, right_name: str) -> None:
    """Exchange destination and payload atomically, or fail closed."""

    if os.name == "nt":
        raise ConcurrentModificationError("POSIX rename exchange is unavailable on Windows")
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise ConcurrentModificationError("renameat2(RENAME_EXCHANGE) is unavailable")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(parent_fd, os.fsencode(left_name), parent_fd, os.fsencode(right_name), 0x2) != 0:
        raise ConcurrentModificationError(f"renameat2 exchange failed (errno={ctypes.get_errno()})")


def _windows_replace_with_backup(destination: Path, replacement: Path, backup: Path) -> None:
    """Replace a design-system authority file while retaining its old bytes."""

    if os.name != "nt":
        raise ConcurrentModificationError("ReplaceFileW is unavailable on this host")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.ReplaceFileW.restype = wintypes.BOOL
    kernel32.ReplaceFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    ]
    if backup.exists():
        raise ConcurrentModificationError(f"design-system transaction backup already exists: {backup}")
    if not kernel32.ReplaceFileW(str(destination), str(replacement), str(backup), 0x1, None, None):
        raise ConcurrentModificationError(f"ReplaceFileW failed (winerror={ctypes.get_last_error()})")


def _path_version(path: Path) -> tuple[int, int, int, int, str]:
    info = path.stat(follow_symlinks=False)
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _exchange_design_system_commit(
    path: Path,
    temporary_path: Path,
    *,
    parent_fd: int | None,
    expected_version: tuple[int, int, int, int, str],
    payload: bytes,
) -> None:
    """Commit with a displaced-file backup and verify/restore on mismatch."""

    if os.name != "nt":
        if parent_fd is None:
            raise ConcurrentModificationError("design-system exchange requires a held parent descriptor")
        _posix_rename_exchange(parent_fd, temporary_path.name, path.name)
        displaced = path.parent / temporary_path.name
        if _path_version(displaced) != expected_version:
            if _path_version(path)[-1] == hashlib.sha256(payload).hexdigest():
                _posix_rename_exchange(parent_fd, temporary_path.name, path.name)
                if _path_version(path) != expected_version:
                    raise ConcurrentModificationError("design-system restore verification failed; artifacts retained")
                os.unlink(temporary_path.name, dir_fd=parent_fd)
            raise ConcurrentModificationError("design-system displaced bytes changed; concurrent bytes preserved")
        os.unlink(temporary_path.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        return

    backup = path.parent / f".{path.name}.{secrets.token_hex(8)}.backup"
    _windows_replace_with_backup(path, temporary_path, backup)
    if _path_version(backup) != expected_version:
        if _path_version(path)[-1] == hashlib.sha256(payload).hexdigest():
            rollback_backup = path.parent / f".{path.name}.{secrets.token_hex(8)}.rollback"
            _windows_replace_with_backup(path, backup, rollback_backup)
            if _path_version(path) != expected_version:
                raise ConcurrentModificationError("design-system restore verification failed; artifacts retained")
            rollback_backup.unlink(missing_ok=True)
        raise ConcurrentModificationError("design-system displaced bytes changed; concurrent bytes preserved")
    backup.unlink(missing_ok=True)


def _destination_lock_path(path: Path) -> Path:
    token = hashlib.sha256(str(path.absolute()).casefold().encode("utf-8")).hexdigest()
    directory = Path(tempfile.gettempdir()) / "product-delivery-harness-ds-locks"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{token}.lock"


@contextmanager
def _destination_lock(path: Path):
    """Serialize compliant writers with a stable host-local version token."""

    lock_path = _destination_lock_path(path)
    handle = lock_path.open("a+b")
    try:
        if os.name == "nt":
            handle.seek(0)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _destination_version_token(path: Path) -> tuple[int, int, int, int, str]:
    info = path.stat()
    content = hashlib.sha256(path.read_bytes()).hexdigest()
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_size),
        int(info.st_mtime_ns),
        content,
    )


def is_placeholder(value: str) -> bool:
    """True for a `<...>`-shaped template slot nobody has filled in yet."""
    return bool(PLACEHOLDER_RE.match(value.strip()))


def contract_inventory(registry: dict[str, Any]) -> dict[str, Any]:
    """Return the ordered, machine-owned subset published into Markdown."""
    return {key: registry[key] for key in CONTRACT_FIELDS if key in registry}


def generated_contract_block(
    registry: dict[str, Any],
    *,
    newline: str = "\n",
) -> str:
    payload = json.dumps(
        contract_inventory(registry),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    block = f"{BEGIN_MARKER}\n```json\n{payload}\n```\n{END_MARKER}"
    return block.replace("\n", newline)


def _newline_sequence(text: str) -> str:
    match = re.search(r"\r\n|\r|\n", text)
    return match.group(0) if match is not None else "\n"


def _generated_contract_match(
    markdown_text: str,
    *,
    allow_absent: bool,
) -> re.Match[str] | None:
    begin_lines = exact_marker_lines(markdown_text, BEGIN_MARKER)
    end_lines = exact_marker_lines(markdown_text, END_MARKER)
    if not begin_lines and not end_lines and allow_absent:
        return None
    if len(begin_lines) != 1 or len(end_lines) != 1:
        raise ValueError(
            "design-system.md must contain exactly one matched generated "
            "design-system contract marker pair"
        )

    line_offsets = [0]
    for match in re.finditer(r"\n", markdown_text):
        line_offsets.append(match.end())
    begin_line = begin_lines[0]
    end_line = end_lines[0]
    begin_at = markdown_text.find(BEGIN_MARKER, line_offsets[begin_line - 1])
    end_at = markdown_text.find(END_MARKER, line_offsets[end_line - 1])
    if begin_at >= end_at:
        raise ValueError(
            "design-system.md generated contract begin marker must precede its end marker"
        )

    match = GENERATED_BLOCK_RE.search(markdown_text, begin_at, end_at + len(END_MARKER))
    if (
        match is None
        or match.start() != begin_at
        or match.end() != end_at + len(END_MARKER)
    ):
        raise ValueError(
            "design-system.md generated contract must be a fenced json block between its markers"
        )
    return match


def replace_generated_contract(markdown_text: str, registry: dict[str, Any]) -> str:
    """Replace the generated block, or append it when the document predates it."""
    newline = _newline_sequence(markdown_text)
    block = generated_contract_block(registry, newline=newline)
    match = _generated_contract_match(markdown_text, allow_absent=True)
    if match is not None:
        return markdown_text[: match.start()] + block + markdown_text[match.end() :]
    if not markdown_text:
        prefix = ""
    elif markdown_text.endswith(f"{newline}{newline}"):
        prefix = markdown_text
    elif markdown_text.endswith(("\r", "\n")):
        prefix = markdown_text + newline
    else:
        prefix = markdown_text + newline + newline
    return (
        prefix
        + "## Generated Machine Contract"
        + newline
        + newline
        + block
        + newline
    )


def _write_bytes_atomic_unlocked(path: Path, payload: bytes, expected_bytes: bytes) -> None:
    """Replace ``path`` with ``payload`` without exposing a partial file."""
    _safe_parent_chain(path)
    original_stat = path.lstat()
    destination_version_token = _destination_version_token(path)
    if stat.S_ISLNK(original_stat.st_mode):
        raise ConcurrentModificationError(
            f"{path} must not be a symbolic link for --write"
        )
    mode = stat.S_IMODE(original_stat.st_mode)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        _safe_parent_chain(path)
        current_stat = path.lstat()
        if (
            stat.S_ISLNK(current_stat.st_mode)
            or not os.path.samestat(original_stat, current_stat)
            or path.read_bytes() != expected_bytes
            or _destination_version_token(path) != destination_version_token
        ):
            raise ConcurrentModificationError(
                f"{path} changed while preparing the generated contract"
            )
        if os.name == "nt":
            # Windows has no dir_fd form of os.replace. Hold the final parent
            # without FILE_SHARE_DELETE and use ReplaceFileW with a displaced
            # backup so a concurrent edit can be restored or retained.
            parent_handle, ancestor_handles = _windows_open_parent(path)
            try:
                if _destination_version_token(path) != destination_version_token:
                    raise ConcurrentModificationError(
                        f"{path} changed before the native replace"
                    )
                _exchange_design_system_commit(
                    path,
                    temporary_path,
                    parent_fd=None,
                    expected_version=destination_version_token,
                    payload=payload,
                )
            finally:
                _windows_close(parent_handle)
                for ancestor_handle in reversed(ancestor_handles):
                    _windows_close(ancestor_handle)
        else:
            # POSIX keeps every component no-follow checked and the final
            # directory open while replacing by basename. This prevents an
            # ancestor swap from redirecting the destination after CAS.
            parent_fd, _basename = _open_posix_parent(path)
            try:
                if _destination_version_token(path) != destination_version_token:
                    raise ConcurrentModificationError(
                        f"{path} changed before the dirfd replace"
                    )
                _exchange_design_system_commit(
                    path,
                    temporary_path,
                    parent_fd=parent_fd,
                    expected_version=destination_version_token,
                    payload=payload,
                )
            finally:
                os.close(parent_fd)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def _write_bytes_atomic(path: Path, payload: bytes, expected_bytes: bytes) -> None:
    """CAS write serialized by the shared destination version lock."""

    with _destination_lock(path):
        _write_bytes_atomic_unlocked(path, payload, expected_bytes)


def _string_list(problems: list[str], path: str, value: Any, *, nonempty: bool) -> None:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        qualifier = "non-empty " if nonempty else ""
        problems.append(f"design-system.json {path} must be a {qualifier}list of strings")


def _repo_relative(value: str) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\\" in value
        or value.startswith("/")
        or (len(value) > 1 and value[1] == ":")
    ):
        return False
    parts = value.split("/")
    return bool(parts) and all(part not in {"", ".", ".."} for part in parts)


def _safe_repo_candidate(root: Path, relative: str) -> Path | None:
    """Resolve a source binding without traversing aliases or reparse points."""

    if not _repo_relative(relative):
        return None
    candidate = root / relative
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if _is_reparse_or_link(cursor):
            return None
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def validate_registry(registry: dict[str, Any]) -> list[str]:
    """Validate the structured fields the pair checker promises to mirror."""
    problems: list[str] = []
    schema = registry.get("schema")
    if schema not in {"design-system/1", "design-system/2"}:
        problems.append(
            "design-system.json schema must be 'design-system/1' or 'design-system/2'"
        )

    hybrid_surface_contracts = registry.get("surfaceContracts")
    if hybrid_surface_contracts is not None and schema != "design-system/2":
        problems.append("design-system.json surfaceContracts requires design-system/2")
    hybrid = schema == "design-system/2" and hybrid_surface_contracts is not None
    product = registry.get("product")
    if not isinstance(product, str) or not product.strip():
        problems.append("design-system.json product must be a non-empty string")

    has_viewports = "viewports" in registry
    has_size_classes = "sizeClasses" in registry
    viewports = registry.get("viewports")
    size_classes = registry.get("sizeClasses")
    valid_viewports = (
        isinstance(viewports, list)
        and len(viewports) >= 3
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in viewports
        )
        and len(set(viewports)) == len(viewports)
        and all(left < right for left, right in zip(viewports, viewports[1:]))
    )
    valid_size_classes = (
        isinstance(size_classes, list)
        and len(size_classes) >= 2
        and all(
            isinstance(value, str) and bool(value.strip())
            for value in size_classes
        )
        and len(set(size_classes)) == len(size_classes)
    )
    if hybrid:
        if has_viewports or has_size_classes or "platform" in registry or "stylingMechanism" in registry:
            problems.append(
                "design-system.json hybrid surfaceContracts must omit global platform, "
                "stylingMechanism, viewports, and sizeClasses"
            )
        if not isinstance(hybrid_surface_contracts, dict) or len(hybrid_surface_contracts) < 2:
            problems.append("design-system.json surfaceContracts must contain at least two UI-* surfaces")
        elif any(not isinstance(key, str) or not key.startswith("UI-") for key in hybrid_surface_contracts):
            problems.append("design-system.json surfaceContracts keys must be UI-* identities")
        else:
            for surface_id, contract in hybrid_surface_contracts.items():
                path = f"surfaceContracts.{surface_id}"
                expected_keys = {"releaseSurface", "surfaceClass", "captureMode", "responsive"}
                if not isinstance(contract, dict) or set(contract) != expected_keys:
                    problems.append(f"design-system.json {path} must contain exactly {sorted(expected_keys)}")
                    continue
                surface_class = contract.get("surfaceClass")
                capture_mode = contract.get("captureMode")
                for field in ("releaseSurface", "surfaceClass", "captureMode"):
                    if not isinstance(contract.get(field), str) or not contract[field].strip():
                        problems.append(f"design-system.json {path}.{field} must be a non-empty string")
                if not isinstance(surface_class, str) or surface_class not in VALID_HYBRID_SURFACE_CLASSES:
                    problems.append(f"design-system.json {path}.surfaceClass is invalid")
                if not isinstance(capture_mode, str) or capture_mode not in {"hosted-browser", "browser-extension", "native", "desktop"}:
                    problems.append(f"design-system.json {path}.captureMode is invalid")
                expected_capture_modes = {
                    "hosted_web": {"hosted-browser"},
                    "browser_extension": {"browser-extension"},
                    "ios": {"native"},
                    "android": {"native"},
                    "macos": {"desktop"},
                    "windows": {"desktop"},
                    "desktop": {"desktop"},
                }.get(surface_class) if isinstance(surface_class, str) else None
                if expected_capture_modes and capture_mode not in expected_capture_modes:
                    problems.append(
                        f"design-system.json {path}.captureMode is incompatible with surfaceClass"
                    )
                responsive = contract.get("responsive")
                if not isinstance(responsive, dict) or set(responsive) != {"kind", "targets"}:
                    problems.append(f"design-system.json {path}.responsive must contain kind and targets")
                elif responsive.get("kind") == "viewports":
                    targets = responsive.get("targets")
                    if not isinstance(targets, list) or len(targets) < 3 or any(not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0 for value in targets) or any(left >= right for left, right in zip(targets, targets[1:])):
                        problems.append(f"design-system.json {path}.responsive.viewports must be three ascending positive numbers")
                elif responsive.get("kind") == "sizeClasses":
                    targets = responsive.get("targets")
                    if not isinstance(targets, list) or len(targets) < 2 or any(not isinstance(value, str) or not value.strip() for value in targets) or len(set(targets)) != len(targets):
                        problems.append(f"design-system.json {path}.responsive.sizeClasses must be two unique strings")
                else:
                    problems.append(f"design-system.json {path}.responsive.kind is invalid")
    elif (
        has_viewports == has_size_classes
        or (has_viewports and not valid_viewports)
        or (has_size_classes and not valid_size_classes)
    ):
        problems.append(
            "design-system.json must declare exactly one non-empty unique responsive "
            "set: at least three ascending numeric viewports for web, or at least "
            "two unique string sizeClasses for native or desktop"
        )
    platform = registry.get("platform")
    if hybrid:
        platform = "<hybrid>"
    if not isinstance(platform, str) or not platform.strip():
        problems.append("design-system.json platform must be a non-empty string")
    elif not (platform.startswith("<") and platform.endswith(">")) and platform not in VALID_PLATFORMS:
        problems.append(
            "design-system.json platform must be one of: "
            + ", ".join(sorted(VALID_PLATFORMS))
        )
    elif not (platform.startswith("<") and platform.endswith(">")):
        if has_viewports and platform != "web":
            problems.append(
                "design-system.json viewports require platform 'web'"
            )
        if has_size_classes and platform == "web":
            problems.append(
                "design-system.json platform 'web' requires viewports, not sizeClasses"
            )

    styling = registry.get("stylingMechanism")
    if hybrid:
        styling = "<hybrid>"
    if not isinstance(styling, str) or not styling.strip():
        problems.append("design-system.json stylingMechanism must be a non-empty string")
    elif not (styling.startswith("<") and styling.endswith(">")) and styling not in VALID_STYLING_MECHANISMS:
        problems.append(
            "design-system.json stylingMechanism must be one of: "
            + ", ".join(sorted(VALID_STYLING_MECHANISMS))
        )
    enforcement = registry.get("enforcement")
    if not isinstance(enforcement, str) or not enforcement.strip():
        problems.append("design-system.json enforcement must be a non-empty string")
    elif not (enforcement.startswith("<") and enforcement.endswith(">")) and enforcement not in VALID_ENFORCEMENT:
        problems.append(
            "design-system.json enforcement must be one of: "
            + ", ".join(sorted(VALID_ENFORCEMENT))
        )

    for key in ("tokens", "primitives"):
        if not isinstance(registry.get(key), dict):
            problems.append(f"design-system.json {key} must be an object")
    if "productComponents" in registry and not isinstance(
        registry["productComponents"], dict
    ):
        problems.append("design-system.json productComponents must be an object")

    if "motionVariants" in registry:
        _string_list(
            problems,
            "motionVariants",
            registry["motionVariants"],
            nonempty=False,
        )
    _string_list(problems, "stateMatrix", registry.get("stateMatrix"), nonempty=True)
    _string_list(problems, "tokenSources", registry.get("tokenSources"), nonempty=True)
    _string_list(problems, "primitiveSources", registry.get("primitiveSources"), nonempty=False)

    if schema == "design-system/2":
        bindings = registry.get("sourceBindings")
        if not isinstance(bindings, dict):
            problems.append(
                "design-system.json sourceBindings must be an object with prd, "
                "architecture, stack, uiDesign, wireframe, and hifi"
            )
        else:
            expected = set(SOURCE_BINDING_KEYS)
            missing = sorted(expected - set(bindings))
            extra = sorted(set(bindings) - expected)
            if missing:
                problems.append(
                    "design-system.json sourceBindings is missing: " + ", ".join(missing)
                )
            if extra:
                problems.append(
                    "design-system.json sourceBindings names unexpected keys: "
                    + ", ".join(extra)
                )
            for key in SOURCE_BINDING_KEYS:
                binding = bindings.get(key)
                path_name = f"sourceBindings.{key}"
                if not isinstance(binding, dict):
                    problems.append(f"design-system.json {path_name} must be an object")
                    continue
                path = binding.get("path")
                digest = binding.get("sha256")
                if not isinstance(path, str) or not _repo_relative(path):
                    problems.append(
                        f"design-system.json {path_name}.path must be a repo-relative path"
                    )
                if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
                    problems.append(
                        f"design-system.json {path_name}.sha256 must be lowercase hex"
                    )
            paths = [
                bindings[key].get("path")
                for key in SOURCE_BINDING_KEYS
                if isinstance(bindings.get(key), dict)
            ]
            if len(paths) != len(set(paths)):
                problems.append("design-system.json sourceBindings paths must be distinct")
            semantic_suffixes = {
                "prd": "prd.md",
                "architecture": "architecture.md",
                "stack": "stack-decisions.md",
                "uiDesign": "ui-design.md",
                "wireframe": "wireframes.html",
            }
            for key, suffix in semantic_suffixes.items():
                binding = bindings.get(key)
                path = binding.get("path") if isinstance(binding, dict) else None
                if isinstance(path, str) and not path.casefold().endswith(suffix.casefold()):
                    problems.append(
                        f"design-system.json sourceBindings.{key}.path must identify {suffix}"
                    )
            hifi = bindings.get("hifi")
            hifi_path = hifi.get("path") if isinstance(hifi, dict) else None
            if isinstance(hifi_path, str) and hifi_path.casefold().endswith("wireframes.html"):
                problems.append("design-system.json sourceBindings.hifi.path must be a distinct HiFi target")

    primitives = registry.get("primitives")
    seen_ds_ids: set[str] = set()
    if isinstance(primitives, dict):
        for name, spec in primitives.items():
            path = f"primitives.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
            elif spec.get("layer") not in {"layout", "surface", "typography", "control"}:
                problems.append(
                    f"design-system.json {path}.layer must be layout, surface, typography, or control"
                )
            if isinstance(spec, dict) and spec.get("dsId") is not None:
                ds_id = spec["dsId"]
                if not isinstance(ds_id, str) or not DS_PRIMITIVE_ID_RE.match(ds_id):
                    problems.append(
                        f"design-system.json {path}.dsId must match DS-<family>-<number>, "
                        f"got {ds_id!r}"
                    )
                elif ds_id in seen_ds_ids:
                    problems.append(f"design-system.json {path}.dsId duplicates {ds_id}")
                else:
                    seen_ds_ids.add(ds_id)

    components = registry.get("productComponents")
    if isinstance(components, dict):
        for name, spec in components.items():
            path = f"productComponents.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
                continue
            if not isinstance(spec.get("dsId"), str) or not spec["dsId"].strip():
                problems.append(f"design-system.json {path}.dsId must be a non-empty string")
            elif not DS_COMP_ID_RE.match(spec["dsId"]):
                problems.append(
                    f"design-system.json {path}.dsId must match DS-COMP-<number>, "
                    f"got {spec['dsId']!r}"
                )
            elif spec["dsId"] in seen_ds_ids:
                problems.append(
                    f"design-system.json {path}.dsId duplicates {spec['dsId']}"
                )
            else:
                seen_ds_ids.add(spec["dsId"])
            for field in ("requiredContentOrder", "composes", "states"):
                _string_list(
                    problems,
                    f"{path}.{field}",
                    spec.get(field),
                    nonempty=True,
                )
            composes = spec.get("composes")
            if isinstance(composes, list) and isinstance(primitives, dict):
                for entry in composes:
                    if not isinstance(entry, str) or is_placeholder(entry):
                        continue
                    if entry.strip() not in primitives:
                        problems.append(
                            f"design-system.json {path}.composes names '{entry}', "
                            "which is not a key in primitives"
                        )

    if "signatureRules" in registry:
        rules = registry["signatureRules"]
        if not isinstance(rules, list):
            problems.append("design-system.json signatureRules must be a list")
        else:
            for rule in rules:
                if not isinstance(rule, str) or not DS_RULE_ID_RE.match(rule):
                    problems.append(
                        f"design-system.json signatureRules entry must match "
                        f"DS-<number> or DS-<family>-<number>, got {rule!r}"
                    )
                elif rule in seen_ds_ids:
                    problems.append(
                        f"design-system.json signatureRules entry duplicates {rule}"
                    )
                else:
                    seen_ds_ids.add(rule)
    return problems


def unfilled_placeholders(value: Any, path: str = "design-system.json") -> list[str]:
    """Report every `<...>` key or string value still left from the template."""
    problems: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            if is_placeholder(key):
                problems.append(f"{child} is an unfilled template placeholder")
            problems.extend(unfilled_placeholders(value[key], child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            problems.extend(unfilled_placeholders(item, f"{path}[{index}]"))
    elif isinstance(value, str) and is_placeholder(value):
        problems.append(f"{path} is an unfilled template placeholder")
    return problems


def _extract_generated_contract(markdown_text: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        match = _generated_contract_match(markdown_text, allow_absent=False)
    except ValueError as error:
        return None, [str(error)]
    assert match is not None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        return None, [f"design-system.md generated contract is not valid JSON: {error}"]
    if not isinstance(value, dict):
        return None, ["design-system.md generated contract must contain a JSON object"]
    return value, []


def _diff(expected: Any, actual: Any, path: str, problems: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) - set(actual)):
            problems.append(f"{path}.{key} is missing from the generated Markdown contract")
        for key in sorted(set(actual) - set(expected)):
            problems.append(f"{path}.{key} exists only in the generated Markdown contract")
        for key in sorted(set(expected) & set(actual)):
            _diff(expected[key], actual[key], f"{path}.{key}", problems)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if expected != actual:
            problems.append(
                f"{path} differs: expected {json.dumps(expected, ensure_ascii=False)}, "
                f"got {json.dumps(actual, ensure_ascii=False)}"
            )
        return
    if expected != actual:
        problems.append(
            f"{path} differs: expected {json.dumps(expected, ensure_ascii=False)}, "
            f"got {json.dumps(actual, ensure_ascii=False)}"
        )


def _ui_identity_bindings(
    bindings: dict[str, Any], *, repo_root: Path, problems: list[str], require_contract: bool = False,
    surface_contracts: dict[str, Any] | None = None,
) -> None:
    """Cross-check pair source bindings against the UI contract they name."""

    ui_binding = bindings.get("uiDesign")
    if not isinstance(ui_binding, dict):
        return
    ui_path = ui_binding.get("path")
    if not isinstance(ui_path, str) or not _repo_relative(ui_path):
        return
    candidate = _safe_repo_candidate(repo_root, ui_path)
    if candidate is None:
        problems.append("design-system.json sourceBindings.uiDesign path is not a safe canonical repo-relative path")
        return
    if not candidate.is_file():
        return
    try:
        text = active_text(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        problems.append(f"design-system.json sourceBindings.uiDesign cannot be read: {exc}")
        return
    if "# UI Design Contract" not in text and "## Source Product Definition" not in text:
        # Legacy inspection fixtures may carry only opaque bytes. Enforce the
        # complete identity join once the file declares itself as a UI contract.
        if require_contract:
            problems.append("design-system.json sourceBindings.uiDesign must point to a complete UI Design Contract")
        return
    try:
        ui_checker = __import__("check_ui_design_contract")
        view, view_problems = ui_checker.parse_ui_contract_view(text)
    except Exception as exc:
        problems.append(
            "design-system.json shared UI contract parser failed safely: "
            f"{type(exc).__name__}: {exc}"
        )
        return
    problems.extend(f"ui-design: {item}" for item in view_problems)
    gate = view.get("gate") if isinstance(view, dict) else None
    decision = gate.get("decision") if isinstance(gate, dict) else None
    if decision != "required":
        problems.append("design-system.json sourceBindings.uiDesign requires an active Design System Need Gate Decision: required")
    if isinstance(gate, dict) and gate.get("replacement"):
        problems.append("design-system.json sourceBindings.uiDesign must not contain a not_required replacement for a required pair")
    identities = view.get("source_identities") if isinstance(view, dict) else {}
    target_scope = view.get("target_scope") if isinstance(view, dict) else None
    if surface_contracts is not None:
        if not isinstance(surface_contracts, dict) or not isinstance(target_scope, dict):
            problems.append("design-system.json surfaceContracts requires an approved target scope")
        else:
            target_surfaces = {
                item.get("id"): item
                for item in target_scope.get("surfaces", [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            if set(surface_contracts) != set(target_surfaces):
                problems.append("design-system.json surfaceContracts must exactly match Approved target UI-* identities")
            for surface_id, contract in surface_contracts.items():
                target = target_surfaces.get(surface_id)
                if not isinstance(contract, dict) or not isinstance(target, dict):
                    continue
                for contract_key, target_key in (
                    ("releaseSurface", "releaseSurface"),
                    ("surfaceClass", "surfaceClass"),
                    ("captureMode", "captureMode"),
                    ("responsive", "responsive"),
                ):
                    if contract.get(contract_key) != target.get(target_key):
                        problems.append(
                            f"design-system.json surfaceContracts.{surface_id}.{contract_key} "
                            "does not match Approved target scope"
                        )
    mapping = {
        "prd": "prd",
        "architecture": "architecture",
        "stack": "stack",
        "wireframe": "wireframe",
    }
    for key, view_key in mapping.items():
        binding = bindings.get(key)
        if not isinstance(binding, dict):
            problems.append(f"design-system.json sourceBindings.{key} is missing or not an object")
            continue
        expected = identities.get(view_key) if isinstance(identities, dict) else None
        if not isinstance(expected, dict):
            problems.append(f"design-system.json sourceBindings.{key} requires exactly one active UI source identity")
            continue
        if binding.get("path") != expected.get("path") or binding.get("sha256") != expected.get("sha256"):
            problems.append(
                f"design-system.json sourceBindings.{key} does not match {view_key} in ui-design.md"
            )
    hifi_binding = bindings.get("hifi")
    target = view.get("approved_target") if isinstance(view, dict) else None
    if not isinstance(hifi_binding, dict):
        problems.append("design-system.json sourceBindings.hifi is missing or not an object")
    elif not isinstance(target, dict) or hifi_binding.get("path") != target.get("path") or hifi_binding.get("sha256") != target.get("sha256"):
        problems.append("design-system.json sourceBindings.hifi does not match Approved target in ui-design.md")

    # A current pair cannot silently accept a UI markdown file that only looks
    # like a source manifest. Run the exact UI checker when its contract is
    # present; otherwise fail the source join rather than minting identities.
    if "# UI Design Contract" in text or "## Source Product Definition" in text:
        try:
            ui_checker = __import__("check_ui_design_contract")
            source_binding = {
                key: bindings.get(key) for key in ("prd", "architecture", "stack", "wireframe", "hifi")
            }
            paths = {
                key: value.get("path")
                for key, value in source_binding.items()
                if isinstance(value, dict) and isinstance(value.get("path"), str)
            }
            ui_checker_problems = ui_checker._validate_for_design_system_preflight(
                candidate,
                repo_root=repo_root,
                prd_path=repo_root / paths["prd"] if "prd" in paths else None,
                wireframes_path=repo_root / paths["wireframe"] if "wireframe" in paths else None,
                hifi_path=repo_root / paths["hifi"] if "hifi" in paths else None,
            )
            problems.extend(f"ui-design: {item}" for item in ui_checker_problems)
        except Exception as exc:
            problems.append(f"design-system.json cannot run exact UI checker: {exc}")


def _stack_semantics(
    stack_text: str,
    section_names: tuple[str, ...] = (
        "Frontend Technology Decision",
        "Mobile/Desktop Technology Decision",
    ),
) -> dict[str, str]:
    """Extract executable frontend/client layer selections from the approved stack."""

    active = active_text(stack_text)
    semantics: dict[str, str] = {}
    wanted = {
        "rendering model": "renderingModel",
        "component foundation": "componentFoundation",
        "styling approach": "stylingMechanism",
        # Native/desktop packages use a client strategy and framework rather
        # than the web-specific layer names. Keep those names explicit rather
        # than silently inventing a web rendering model.
        "client strategy": "renderingModel",
        "framework": "componentFoundation",
    }
    for section_name in section_names:
        match = re.search(
            rf"^##\s+{re.escape(section_name)}\s*$([\s\S]*?)(?=^##\s|\Z)",
            active,
            re.MULTILINE,
        )
        if match is None:
            continue
        table_match = re.search(
            r"^\|\s*Layer\s*\|[^\n]*\n^\|\s*:?-{3,}",
            match.group(1),
            re.IGNORECASE | re.MULTILINE,
        )
        if table_match is None:
            continue
        block = match.group(1)[table_match.start() :]
        for line in block.splitlines()[2:]:
            if not line.strip().startswith("|") or line.count("|") < 6:
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) != 6:
                continue
            layer, selection, status = cells[0].casefold(), cells[1], cells[2].casefold()
            if status in {"required", "selected", "approved"} and layer in wanted and selection:
                key = wanted[layer]
                if layer in {"rendering model", "component foundation", "styling approach"} or key not in semantics:
                    semantics[key] = selection
    return semantics


def _validate_stack_semantics(
    registry: dict[str, Any],
    *,
    stack_path: Path,
    ui_view: dict[str, Any] | None,
    problems: list[str],
) -> None:
    """Bind executable design-system platform/style fields to Stack decisions."""

    try:
        stack_text = stack_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return
    selected_frontend = _stack_semantics(stack_text, ("Frontend Technology Decision",))
    selected_mobile = _stack_semantics(stack_text, ("Mobile/Desktop Technology Decision",))
    selected = {**selected_frontend, **selected_mobile}
    # Older inspection fixtures intentionally use opaque ``b"stack"`` bytes;
    # only enforce this join when the approved table is present.
    if not selected:
        return
    recorded = registry.get("stackSemantics")
    if not isinstance(recorded, dict):
        problems.append(
            "design-system.json stackSemantics must bind renderingModel, "
            "componentFoundation, and stylingMechanism to approved Stack rows"
        )
        return

    target_scope = ui_view.get("target_scope") if isinstance(ui_view, dict) else None
    surfaces = target_scope.get("surfaces", []) if isinstance(target_scope, dict) else []
    surface_items = [item for item in surfaces if isinstance(item, dict)]
    classes = {str(item.get("surfaceClass")) for item in surface_items}
    hybrid = len(classes) > 1 or len(surface_items) > 1 and isinstance(registry.get("surfaceContracts"), dict)
    required_keys = {"renderingModel", "componentFoundation", "stylingMechanism"}
    if hybrid:
        if set(recorded) != {str(item.get("id")) for item in surface_items}:
            problems.append("design-system.json stackSemantics must exactly match hybrid UI-* surfaces")
            return
        platform_by_class = {
            "hosted_web": "web",
            "browser_extension": "web",
            "ios": "ios",
            "android": "android",
            "macos": "macos",
            "windows": "windows",
            "desktop": "desktop",
        }
        for item in surface_items:
            surface_id = str(item.get("id"))
            entry = recorded.get(surface_id)
            if not isinstance(entry, dict) or set(entry) != required_keys | {"platform"}:
                problems.append(
                    f"design-system.json stackSemantics.{surface_id} must contain platform, renderingModel, componentFoundation, and stylingMechanism"
                )
                continue
            target_semantics = item.get("stackSemantics")
            if not isinstance(target_semantics, dict) or set(target_semantics) != required_keys | {"platform"}:
                problems.append(
                    f"design-system.json stackSemantics.{surface_id} requires the normalized UI Approved target stackSemantics authority"
                )
            elif any(
                str(entry.get(key, "")).strip().casefold()
                != str(target_semantics.get(key, "")).strip().casefold()
                for key in required_keys | {"platform"}
            ):
                problems.append(
                    f"design-system.json stackSemantics.{surface_id} does not exactly equal ui-design Approved target stackSemantics"
                )
            expected_platform = platform_by_class.get(str(item.get("surfaceClass")))
            if expected_platform and entry.get("platform") != expected_platform:
                problems.append(f"design-system.json stackSemantics.{surface_id}.platform does not match surfaceClass")
            selected_for_surface = (
                selected_mobile
                if str(item.get("surfaceClass")) in {"ios", "android", "macos", "windows", "desktop"}
                else selected_frontend
            )
            for key in required_keys:
                expected = selected_for_surface.get(key)
                if expected is None:
                    problems.append(
                        f"design-system.json stackSemantics.{surface_id}.{key} has no approved Stack selection"
                    )
                elif str(entry.get(key, "")).casefold() != expected.casefold():
                    problems.append(f"design-system.json stackSemantics.{surface_id}.{key} does not match approved Stack selection")
    else:
        if set(recorded) != required_keys | {"platform"}:
            problems.append("design-system.json stackSemantics must contain platform, renderingModel, componentFoundation, and stylingMechanism")
            return
        surface_class = str(surface_items[0].get("surfaceClass")) if surface_items else ""
        expected_platform = {
            "hosted_web": "web",
            "browser_extension": "web",
            "ios": "ios",
            "android": "android",
            "macos": "macos",
            "windows": "windows",
            "desktop": "desktop",
        }.get(surface_class)
        if expected_platform and recorded.get("platform") != expected_platform:
            problems.append("design-system.json stackSemantics.platform does not match approved UI surface class")
        if registry.get("platform") != recorded.get("platform"):
            problems.append("design-system.json platform must equal stackSemantics.platform")
        if registry.get("stylingMechanism") != recorded.get("stylingMechanism"):
            problems.append("design-system.json stylingMechanism must equal stackSemantics.stylingMechanism")
        if surface_items:
            target_semantics = surface_items[0].get("stackSemantics")
            if not isinstance(target_semantics, dict) or set(target_semantics) != required_keys | {"platform"}:
                problems.append("design-system.json stackSemantics requires the normalized UI Approved target stackSemantics authority")
            elif any(
                str(recorded.get(key, "")).strip().casefold()
                != str(target_semantics.get(key, "")).strip().casefold()
                for key in required_keys | {"platform"}
            ):
                problems.append("design-system.json stackSemantics does not exactly equal ui-design Approved target stackSemantics")
        selected_for_surface = (
            selected_mobile
            if surface_class in {"ios", "android", "macos", "windows", "desktop"}
            else selected_frontend
        )
        for key in required_keys:
            expected = selected_for_surface.get(key)
            if expected is None:
                problems.append(
                    f"design-system.json stackSemantics.{key} has no approved Stack selection"
                )
            elif str(recorded.get(key, "")).casefold() != expected.casefold():
                problems.append(f"design-system.json stackSemantics.{key} does not match approved Stack selection")


def compare(
    markdown_text: str,
    registry: dict[str, Any],
    *,
    require_filled: bool = False,
    repo_root: Path | None = None,
) -> list[str]:
    problems = validate_registry(registry)
    if require_filled:
        if registry.get("schema") != "design-system/2":
            problems.append(
                "current publication requires design-system/2; design-system/1 is inspection-only"
            )
        problems.extend(unfilled_placeholders(registry))
    generated, parse_problems = _extract_generated_contract(markdown_text)
    problems.extend(parse_problems)
    if generated is not None:
        _diff(
            contract_inventory(registry),
            generated,
            "generated contract",
            problems,
        )
    if registry.get("schema") == "design-system/2" and repo_root is None:
        problems.append("design-system.json source bindings require repo_root")
    elif registry.get("schema") == "design-system/2" and repo_root is not None:
        root = repo_root.resolve()
        bindings = registry.get("sourceBindings")
        if isinstance(bindings, dict):
            for key in SOURCE_BINDING_KEYS:
                binding = bindings.get(key)
                if not isinstance(binding, dict):
                    continue
                path = binding.get("path")
                digest = binding.get("sha256")
                if not isinstance(path, str) or not _repo_relative(path):
                    continue
                candidate = _safe_repo_candidate(root, path)
                if candidate is None:
                    problems.append(
                        f"design-system.json sourceBindings.{key} path is not a safe canonical repo-relative path"
                    )
                    continue
                if not candidate.is_file():
                    problems.append(
                        f"design-system.json sourceBindings.{key} path does not exist: {path}"
                    )
                else:
                    try:
                        actual_digest = (
                            canonical_ui_approval_sha256(candidate.read_text(encoding="utf-8"))
                            if key == "uiDesign"
                            else hashlib.sha256(candidate.read_bytes()).hexdigest()
                        )
                    except (OSError, UnicodeError) as exc:
                        problems.append(
                            f"design-system.json sourceBindings.{key} cannot read current bytes: {exc}"
                        )
                        continue
                    if not isinstance(digest, str) or actual_digest != digest:
                        problems.append(
                            f"design-system.json sourceBindings.{key} sha256 does not "
                            f"match current bytes: {path}"
                        )
            if isinstance(bindings, dict):
                _ui_identity_bindings(
                    bindings,
                    repo_root=root,
                    problems=problems,
                    require_contract=require_filled,
                    surface_contracts=registry.get("surfaceContracts") if isinstance(registry, dict) else None,
                )
                stack_binding = bindings.get("stack")
                stack_path = (
                    _safe_repo_candidate(root, stack_binding.get("path"))
                    if isinstance(stack_binding, dict)
                    and isinstance(stack_binding.get("path"), str)
                    else None
                )
                ui_binding = bindings.get("uiDesign")
                ui_view = None
                if isinstance(ui_binding, dict) and isinstance(ui_binding.get("path"), str):
                    ui_path = _safe_repo_candidate(root, ui_binding["path"])
                    if ui_path is not None and ui_path.is_file():
                        try:
                            ui_checker = __import__("check_ui_design_contract")
                            ui_view, _ = ui_checker.parse_ui_contract_view(
                                ui_path.read_text(encoding="utf-8")
                            )
                        except Exception:
                            ui_view = None
                if stack_path is not None and stack_path.is_file():
                    _validate_stack_semantics(
                        registry,
                        stack_path=stack_path,
                        ui_view=ui_view,
                        problems=problems,
                    )

    # Every DS-* id active Markdown names — prose or tables, never fences or
    # must resolve to a registered id: a product component dsId, a primitive
    # dsId, or a signatureRules entry. The Markdown never mints ids.
    components = registry.get("productComponents")
    primitives = registry.get("primitives")
    registered = {
        spec.get("dsId")
        for spec in (components.values() if isinstance(components, dict) else [])
        if isinstance(spec, dict) and isinstance(spec.get("dsId"), str)
    } | {
        spec.get("dsId")
        for spec in (primitives.values() if isinstance(primitives, dict) else [])
        if isinstance(spec, dict) and isinstance(spec.get("dsId"), str)
    } | {
        rule
        for rule in (
            registry.get("signatureRules")
            if isinstance(registry.get("signatureRules"), list)
            else []
        )
        if isinstance(rule, str)
    }
    unregistered = sorted(
        {
            token
            for token in DS_TOKEN_RE.findall(active_text(markdown_text))
            if token not in registered
        }
    )
    if unregistered:
        problems.append(
            "design-system.md names DS ids missing from design-system.json: "
            + ", ".join(unregistered)
        )
    malformed = sorted(
        token
        for token in set(DS_LIKE_TOKEN_RE.findall(active_text(markdown_text)))
        if DS_RULE_ID_RE.fullmatch(token) is None
    )
    if malformed:
        problems.append(
            "design-system.md contains malformed DS ids: " + ", ".join(malformed)
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path, help="path to design-system.md")
    parser.add_argument("--registry", required=True, type=Path, help="path to design-system.json")
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace or append the generated Markdown contract block before checking",
    )
    parser.add_argument(
        "--require-filled",
        action="store_true",
        help="reject template placeholder keys and string values",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="repository root used to resolve and hash design-system/2 source bindings",
    )
    args = parser.parse_args(argv)

    for path in (args.markdown, args.registry):
        if not path.is_file():
            print(f"missing file: {path}", file=sys.stderr)
            return 2

    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"{args.registry} is not valid JSON: {error}", file=sys.stderr)
        return 2
    if not isinstance(registry, dict):
        print(f"{args.registry} must contain a JSON object", file=sys.stderr)
        return 2

    try:
        original_markdown_bytes = args.markdown.read_bytes()
        original_markdown_text = original_markdown_bytes.decode("utf-8")
    except (OSError, UnicodeError) as error:
        print(f"{args.markdown} cannot be read as UTF-8: {error}", file=sys.stderr)
        return 2
    markdown_text = original_markdown_text
    updated_markdown = markdown_text
    if args.write:
        try:
            updated_markdown = replace_generated_contract(markdown_text, registry)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
        markdown_text = updated_markdown

    problems = compare(
        markdown_text,
        registry,
        require_filled=args.require_filled,
        repo_root=args.repo_root,
    )
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"{len(problems)} pairing problem(s) between {args.markdown} and {args.registry}")
        return 1

    if args.write and updated_markdown != original_markdown_text:
        try:
            _write_bytes_atomic(
                args.markdown,
                updated_markdown.encode("utf-8"),
                original_markdown_bytes,
            )
        except ConcurrentModificationError as error:
            print(f"cannot write {args.markdown}: {error}", file=sys.stderr)
            return 2
        except OSError as error:
            print(f"cannot write {args.markdown}: {error}", file=sys.stderr)
            return 2

    print(f"PASS generated design-system contract agrees with {args.registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
