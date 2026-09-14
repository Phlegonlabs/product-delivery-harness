#!/usr/bin/env python3
"""Standalone hardened Git reads for Product Definition evidence.

This module intentionally has no dependency on delivery-harness.  Product
Definition is installable on its own, so selected-evidence validation carries
its own small exact-SHA Git boundary.
"""

from __future__ import annotations

import os
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
            ["git", "--no-replace-objects", *arguments],
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
