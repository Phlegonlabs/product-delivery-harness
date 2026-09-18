#!/usr/bin/env python3
"""Stable identity for the installed Harness contract.

The digest covers runtime-facing skill files while ignoring tests and generated
Python caches. Text line endings are normalized so a Windows install and its
packaged copy identify the same contract.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path


SKILL_NAMES = (
    "delivery-harness",
    "product-definition-builder",
    "ui-design-builder",
    "design-system-compiler",
    "code-security-review",
    "product-activation",
    "seo-growth-review",
)
IGNORED_PARTS = {"__pycache__", "tests"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_BUNDLE_BYTES = 128 * 1024 * 1024
MAX_ENTRIES = 10000


def _plain_stat(path: Path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("linked skill paths are not supported")
    return info


def _contract_files(skill_root: Path):
    pending = [skill_root]
    files = []
    entries = 0
    while pending:
        directory = pending.pop()
        if not stat.S_ISDIR(_plain_stat(directory).st_mode):
            raise ValueError("skill root must be a plain directory")
        for path in directory.iterdir():
            entries += 1
            if entries > MAX_ENTRIES:
                raise ValueError("skill tree exceeds entry limit")
            if path.name in IGNORED_PARTS or path.suffix.lower() in IGNORED_SUFFIXES:
                continue
            info = _plain_stat(path)
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                files.append(path)
            else:
                raise ValueError("skill artifact must be a regular file")
    return sorted(files)


def _bounded_bytes(path: Path):
    before = _plain_stat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError("skill artifact exceeds file limit or is not regular")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError("skill artifact changed before observation")
        data = stream.read(MAX_FILE_BYTES + 1)
    after = _plain_stat(path)
    if len(data) > MAX_FILE_BYTES or (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("skill artifact changed during observation")
    return data


def _skills_root(script: Path | None = None) -> Path:
    origin = (script or Path(__file__)).resolve()
    skill_dir = origin.parent.parent
    return skill_dir.parent


def contract_digest(skills_root: str | Path | None = None) -> str:
    supplied = Path(skills_root).absolute() if skills_root is not None else _skills_root()
    for component in (supplied, *supplied.parents):
        _plain_stat(component)
    root = supplied.resolve()
    digest = hashlib.sha256()
    total_bytes = 0
    for skill_name in SKILL_NAMES:
        skill_root = root / skill_name
        if not skill_root.is_dir():
            raise FileNotFoundError(
                f"required bundled skill directory is absent: {skill_root}"
            )
        for path in _contract_files(skill_root):
            relative = path.relative_to(root)
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            if path.suffix.lower() in IGNORED_SUFFIXES:
                continue
            data = _bounded_bytes(path)
            total_bytes += len(data)
            if total_bytes > MAX_BUNDLE_BYTES:
                raise ValueError("skill bundle exceeds total byte limit")
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
