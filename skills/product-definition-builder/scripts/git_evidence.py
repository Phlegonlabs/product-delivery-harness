#!/usr/bin/env python3
"""Standalone hardened Git reads for Product Definition evidence.

This module intentionally has no dependency on delivery-harness.  Product
Definition is installable on its own, so selected-evidence validation carries
its own small exact-SHA Git boundary.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping


class GitEvidenceError(RuntimeError):
    """Raised when Git metadata can substitute or retarget selected evidence."""


_IDENTITY_ENVIRONMENT = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES_RELATIVE",
    "GIT_SHALLOW_FILE",
    "GIT_NAMESPACE",
    "GIT_REPLACE_REF_BASE",
}
_CONFIG_ENVIRONMENT_PREFIX = "GIT_CONFIG"
_HELPER_ENVIRONMENT = {
    "GIT_SSH_COMMAND",
    "GIT_SSH",
    "GIT_ASKPASS",
    "GIT_PROXY_COMMAND",
    "SSH_ASKPASS",
    "SSH_ASKPASS_REQUIRE",
    "GIT_EXTERNAL_DIFF",
    "GIT_EXEC_PATH",
    "GIT_TERMINAL_PROMPT",
    "GIT_EDITOR",
    "GIT_SEQUENCE_EDITOR",
}


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _has_link_component(path: Path) -> bool:
    current = Path(path)
    while True:
        try:
            if current.is_symlink():
                return True
            if os.name == "nt" and current.exists():
                if getattr(current.stat(), "st_file_attributes", 0) & 0x0400:
                    return True
        except OSError:
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent


def _windows_machine_roots() -> tuple[Path, ...]:
    if os.name != "nt":
        return ()
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetWindowsDirectoryW.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if not length:
            return ()
        windows = Path(buffer.value[:length]).resolve()
        return (windows, (Path(windows.anchor) / "Program Files").resolve())
    except (AttributeError, OSError, ValueError):
        return ()


def _git_executable(environment: Mapping[str, str] | None = None) -> str:
    source = dict(os.environ if environment is None else environment)
    found = shutil.which("git", path=source.get("PATH"))
    if not found:
        raise GitEvidenceError("administrator-installed Git executable is unavailable")
    path = Path(found).resolve(strict=True)
    if _has_link_component(Path(found)) or _within(path, Path.cwd().resolve()):
        raise GitEvidenceError("Git executable must not come from the repository/worktree")
    roots = (Path("/usr"), Path("/bin"), Path("/opt")) if os.name != "nt" else _windows_machine_roots()
    if not any(_within(path, root.resolve()) for root in roots):
        raise GitEvidenceError("Git executable must come from an OS-protected install path")
    path.stat()
    if os.name != "nt":
        for component in (path, *path.parents):
            component_info = component.stat()
            if component_info.st_uid != 0 or component_info.st_mode & 0o022:
                raise GitEvidenceError("Git executable path must be root-owned and not writable by group/other")
    if os.name == "nt" and path.suffix.casefold() != ".exe":
        raise GitEvidenceError("Git executable must be a native .exe on Windows")
    return str(path)


def _environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a clean environment, rejecting caller-controlled repo identity."""

    source = dict(os.environ if environment is None else environment)
    identity = sorted(
        key
        for key in source
        if key.upper() in _IDENTITY_ENVIRONMENT
    )
    if identity:
        raise GitEvidenceError(
            "repository identity environment overrides are forbidden: "
            + ", ".join(identity)
        )
    # Git config injection can select arbitrary files and values.  Selected
    # evidence must not inherit it; remove every case variant, including the
    # numbered key/value protocol.  The Git identity variables above are
    # rejected rather than silently ignored so callers cannot mistake another
    # checkout for the reviewed repository.
    cleaned = {
        key: value
        for key, value in source.items()
        if not key.upper().startswith(_CONFIG_ENVIRONMENT_PREFIX + "_")
        and key.upper() != _CONFIG_ENVIRONMENT_PREFIX
        and key.upper() not in _HELPER_ENVIRONMENT
        and not key.upper().startswith("GIT_SSL_")
    }
    cleaned["GIT_NO_REPLACE_OBJECTS"] = "1"
    return cleaned


def _run(
    root: Path,
    *arguments: str,
    text: bool = True,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [_git_executable(environment), "--no-replace-objects", *arguments],
            cwd=root,
            env=_environment(environment),
            capture_output=True,
            text=text,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitEvidenceError(f"Git evidence read failed: {exc}") from exc


def reject_object_substitution(
    root: Path,
    *,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Reject replace refs and legacy grafts before trusting a revision."""

    root = Path(root).resolve()
    refs = _run(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/replace/",
        environment=environment,
    )
    if refs.returncode != 0:
        raise GitEvidenceError(
            refs.stderr.strip() or "cannot inspect Git replacement refs"
        )
    replacement_refs = [line for line in refs.stdout.splitlines() if line.strip()]
    if replacement_refs:
        raise GitEvidenceError(
            "Git replacement refs are forbidden for selected evidence: "
            + ", ".join(sorted(replacement_refs))
        )
    graft = _run(root, "rev-parse", "--git-path", "info/grafts", environment=environment)
    if graft.returncode != 0 or not graft.stdout.strip():
        raise GitEvidenceError(
            graft.stderr.strip() or "cannot resolve legacy Git graft metadata"
        )
    graft_path = Path(graft.stdout.strip())
    if not graft_path.is_absolute():
        graft_path = (root / graft_path).resolve(strict=False)
    try:
        exists = graft_path.exists() or graft_path.is_symlink()
    except OSError as exc:
        raise GitEvidenceError(f"cannot inspect legacy Git graft metadata: {exc}") from exc
    if exists:
        raise GitEvidenceError(
            f"legacy Git graft metadata is forbidden for selected evidence: {graft_path}"
        )


def verify_revision_path(
    root: Path,
    revision: str,
    relative_path: str,
    *,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Verify an exact commit and path without replacement or identity tricks."""

    root = Path(root).resolve()
    top = _run(root, "rev-parse", "--show-toplevel", environment=environment)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != root:
        raise GitEvidenceError("repo_root is not the exact Git repository root")
    reject_object_substitution(root, environment=environment)
    commit = _run(
        root,
        "cat-file",
        "-e",
        f"{revision}^{{commit}}",
        environment=environment,
    )
    blob = _run(
        root,
        "cat-file",
        "-e",
        f"{revision}:{relative_path}",
        environment=environment,
    )
    if commit.returncode != 0 or blob.returncode != 0:
        raise GitEvidenceError(
            f"repository revision/path is not real: {revision}:{relative_path}"
        )
