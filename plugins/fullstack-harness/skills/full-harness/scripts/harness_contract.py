#!/usr/bin/env python3
"""Stable identity for the installed Harness contract.

The digest covers runtime-facing skill files while ignoring tests and generated
Python caches. Text line endings are normalized so a Windows install and its
packaged copy identify the same contract.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


SKILL_NAMES = (
    "full-harness",
    "fullstack-harness-codex",
    "fullstack-harness-claude-code",
    "fullstack-harness-pi",
    "prd-builder",
    "product-design-builder",
)
IGNORED_PARTS = {"__pycache__", "tests"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def _skills_root(script: Path | None = None) -> Path:
    origin = (script or Path(__file__)).resolve()
    skill_dir = origin.parent.parent
    return skill_dir.parent


def contract_digest(skills_root: str | Path | None = None) -> str:
    root = Path(skills_root).resolve() if skills_root is not None else _skills_root()
    digest = hashlib.sha256()
    for skill_name in SKILL_NAMES:
        skill_root = root / skill_name
        if not skill_root.is_dir():
            continue
        for path in sorted(item for item in skill_root.rglob("*") if item.is_file()):
            relative = path.relative_to(root)
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            if path.suffix.lower() in IGNORED_SUFFIXES:
                continue
            data = path.read_bytes()
            try:
                data = data.decode("utf-8").replace("\r\n", "\n").encode("utf-8")
            except UnicodeDecodeError:
                pass
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(data)
            digest.update(b"\0")
    return digest.hexdigest()


if __name__ == "__main__":
    print(contract_digest())
