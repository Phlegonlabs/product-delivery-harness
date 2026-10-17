#!/usr/bin/env python3
"""Stable identity for the installed Harness contract.

The digest covers runtime-facing skill files while ignoring tests directories,
CI timing data, and generated caches. Text line endings are normalized so a
Windows install and its packaged copy identify the same contract.
"""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any

from harness_schema import run_required_harness_version, version_at_least


SKILL_NAMES = (
    "delivery-harness",
    "product-definition-builder",
    "ui-design-builder",
    "design-system-compiler",
    "code-security-review",
    "product-activation",
    "seo-growth-review",
)
CACHE_PARTS = {"__pycache__", ".pytest_cache"}
DEV_ONLY_DIRECTORY = "tests"
IGNORED_SUFFIXES = {".pyc", ".pyo"}
IGNORED_FILE_NAMES = {"ci-test-timings.json", "requirements-test.txt"}
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
            if path.name in CACHE_PARTS:
                continue
            info = _plain_stat(path)
            if stat.S_ISDIR(info.st_mode):
                # DEV_ONLY_DIRECTORY excludes directories named "tests"; a
                # regular file with that name is shipped content and is kept.
                if path.name == DEV_ONLY_DIRECTORY:
                    continue
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                # The compiled-cache suffix and IGNORED_FILE_NAMES describe
                # shipped files, not directories: a directory with such a name
                # is ordinary content and must still be walked. The suffix is
                # matched over the whole file name, so a file named exactly
                # ".pyc" is a cache file just like "module.pyc".
                if (
                    path.name.lower().endswith(tuple(IGNORED_SUFFIXES))
                    or path.name in IGNORED_FILE_NAMES
                ):
                    continue
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
            if (
                any(part in CACHE_PARTS for part in relative.parts)
                or DEV_ONLY_DIRECTORY in relative.parts[:-1]
                or path.name in IGNORED_FILE_NAMES
                or path.name.lower().endswith(tuple(IGNORED_SUFFIXES))
            ):
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


CONTRACT_ADOPTION_CHECK_KEYS = {"digest", "matched", "reading_evidence"}


def contract_adoption_check_errors(
    run: dict[str, Any],
    check: Any,
    *,
    blocked: bool = False,
    optional: bool = False,
) -> list[str]:
    """Check a worker's or reviewer's own contract-adoption report.

    The report is required when the RUN has an adopted contract (so the
    directive or review packet carried it) and the RUN requires Harness 0.55.1
    or later; older RUNs may omit it. A report must never appear without an
    adopted contract. Pass ``blocked=True`` for a blocked review: it may omit
    the report, or report a mismatch with ``matched`` false so the observed
    digest is kept. Pass ``optional=True`` for a result the parent may record
    without child output: it may omit the report, but one it supplies is
    checked in full.
    """

    runtime = run.get("runtime_capabilities") if isinstance(run, dict) else None
    adapter = runtime.get("runtime_adapter") if isinstance(runtime, dict) else None
    gate = adapter.get("version_gate") if isinstance(adapter, dict) else None
    adoption = (
        gate.get("contract_adoption")
        if isinstance(gate, dict) and gate.get("status") == "adopted"
        else None
    )
    if check is None:
        if (
            not blocked
            and not optional
            and isinstance(adoption, dict)
            and version_at_least(run_required_harness_version(run), (0, 55, 1))
        ):
            return ["is required because the dispatch carried contract_adoption"]
        return []
    if not isinstance(adoption, dict):
        return ["is not allowed without an adopted runtime contract"]
    if not isinstance(check, dict) or set(check) != CONTRACT_ADOPTION_CHECK_KEYS:
        return ["must be an object with exactly digest, matched, and reading_evidence"]
    errors = []
    digest = check["digest"]
    same = digest == adoption.get("contract_digest_sha256")
    if not isinstance(digest, str) or not digest:
        errors.append("digest must be a non-empty string")
    elif blocked:
        if check["matched"] is not same:
            errors.append("matched must be true exactly when digest equals the adopted digest")
    else:
        if not same:
            errors.append("digest does not match the adopted contract digest")
        if check["matched"] is not True:
            errors.append("matched must be true")
    reading = check["reading_evidence"]
    # A child that stopped on a mismatch may not have read the contract.
    may_be_empty = blocked and check["matched"] is False
    if (
        not isinstance(reading, list)
        or (not reading and not may_be_empty)
        or any(not isinstance(item, str) or not item.strip() for item in reading)
    ):
        errors.append("reading_evidence must be a non-empty list of non-empty strings")
    elif reading and reading == adoption.get("reading_evidence"):
        errors.append("reading_evidence must be the child's own reading, not the parent receipt")
    return errors


def contract_adoption_check_evidence(check: Any) -> list[str]:
    """Attempt-log lines that retain a validated contract-adoption report."""

    if not isinstance(check, dict):
        return []
    label = "digest" if check["matched"] is True else "mismatch"
    return [f"contract_adoption_{label}:{check['digest']}"] + [
        f"contract_adoption_reading:{item}" for item in check["reading_evidence"]
    ]


if __name__ == "__main__":
    print(contract_digest())
