#!/usr/bin/env python3
"""Hardened Git subprocess helpers for authority-bearing repository reads."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Mapping


class GitMetadataError(RuntimeError):
    """Raised when local Git metadata can substitute immutable objects."""


def git_environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment that disables Git object replacement."""

    result = dict(os.environ if environment is None else environment)
    forbidden = {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_SHALLOW_FILE",
        "GIT_NAMESPACE",
        "GIT_REPLACE_REF_BASE",
    }
    # Environment names are case-insensitive on Windows.  Remove aliases by
    # normalized name so a caller cannot retain ``git_dir`` beside ``GIT_DIR``.
    result = {key: value for key, value in result.items() if key.upper() not in forbidden}
    result["GIT_NO_REPLACE_OBJECTS"] = "1"
    return result


def git_argv(*arguments: str) -> list[str]:
    """Build a Git argv that reads raw object identities."""

    return ["git", "--no-replace-objects", *arguments]


def run_git(
    root: Path,
    *arguments: str,
    capture_output: bool = True,
    text: bool = True,
    timeout: float = 30,
    check: bool = False,
    environment: Mapping[str, str] | None = None,
    input: str | bytes | None = None,
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess[Any]:
    """Run Git with replacement objects disabled."""

    return subprocess.run(
        git_argv(*arguments),
        cwd=root,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        check=check,
        env=git_environment(environment),
        input=input,
        encoding=encoding,
        errors=errors,
    )


def reject_object_substitution(root: Path) -> None:
    """Reject replace refs and legacy graft metadata in one repository.

    ``--no-replace-objects`` already makes each hardened read use the raw
    object. Rejecting the metadata as well prevents a caller from mistaking a
    clean worktree for a clean object database before a validation or side
    effect.
    """

    resolved = Path(root).resolve()
    try:
        refs = run_git(
            resolved,
            "for-each-ref",
            "--format=%(refname)",
            "refs/replace/",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitMetadataError(f"cannot inspect Git replacement refs: {exc}") from exc
    if refs.returncode != 0:
        raise GitMetadataError(
            refs.stderr.strip() or "cannot inspect Git replacement refs"
        )
    replacement_refs = [line for line in refs.stdout.splitlines() if line.strip()]
    if replacement_refs:
        raise GitMetadataError(
            "Git replacement refs are forbidden for exact-SHA validation: "
            + ", ".join(sorted(replacement_refs))
        )

    try:
        graft = run_git(resolved, "rev-parse", "--git-path", "info/grafts")
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitMetadataError(
            f"cannot resolve legacy Git graft metadata: {exc}"
        ) from exc
    if graft.returncode != 0 or not graft.stdout.strip():
        raise GitMetadataError(
            graft.stderr.strip() or "cannot resolve legacy Git graft metadata"
        )
    graft_path = Path(graft.stdout.strip())
    if not graft_path.is_absolute():
        graft_path = (resolved / graft_path).resolve(strict=False)
    try:
        graft_exists = graft_path.exists() or graft_path.is_symlink()
    except OSError as exc:
        raise GitMetadataError(
            f"cannot inspect legacy Git graft metadata: {exc}"
        ) from exc
    if graft_exists:
        raise GitMetadataError(
            f"legacy Git graft metadata is forbidden for exact-SHA validation: {graft_path}"
        )
