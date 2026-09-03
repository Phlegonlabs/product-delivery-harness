"""Shared manifest fixtures for Harness command-line tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def manifest_markdown(
    heading: str, wrapper: str, value: dict[str, object]
) -> str:
    encoded = json.dumps({wrapper: value}, sort_keys=True, indent=2)
    return f"# Harness fixture\n\n{heading}\n\n```json\n{encoded}\n```\n"


def git(root: Path, *args: str) -> str:
    """Run git in `root`; raise with stderr on failure; return stripped stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed in {root}:\n{result.stderr}"
        )
    return result.stdout.strip()


def init_repo(root: Path, *files: str, default_branch: str = "main") -> str:
    """Create a committed repo with one commit per named file; return the head."""

    git(root, "init", "-q", "-b", default_branch)
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Harness Test")
    for name in files:
        (root / name).write_text(f"{name} base\n", encoding="utf-8")
        git(root, "add", name)
        git(root, "commit", "-qm", f"add {name}")
    return git(root, "rev-parse", "HEAD")
