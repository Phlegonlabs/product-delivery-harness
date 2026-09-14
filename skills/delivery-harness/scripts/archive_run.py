#!/usr/bin/env python3
"""Archive a completed run's coordination set under docs/goal/archived/.

The script refuses anything but a completed run whose PLAN/RUN pair
passes full manifest validation with every final gate PASS, lists every
exact move first (dry run by default), and moves — never deletes — the
coordination set into one timestamped archive directory. It performs no Git
ref or commit writes; hardened Git metadata/blob reads stay read-only from the
parent's perspective, and committing the archival remains with the parent
under its ordinary create_local_commits authorization.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_plan, load_run  # noqa: E402
from harness_git import (  # noqa: E402
    GitMetadataError,
    git_environment,
    git_executable,
    reject_object_substitution,
    run_git,
)
from harness_manifest import plan_digest  # noqa: E402
from harness_manifest import validate_current_plan_run  # noqa: E402
from harness_schema import archive_first_required  # noqa: E402

GOAL_DIR = Path("docs/goal")
REQUIRED_FILES = ("PLAN.md", "RUN.md")
OPTIONAL_FILES = ("DECISIONS.md", "REFINEMENT_BACKLOG.md")
OPTIONAL_DIRS = ("evidence",)
OPTIONAL_OUTSIDE = ("docs/tasks.md",)
DOCUMENTS_PATH = Path("docs/DOCUMENTS.md")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAIN_REF_RE = re.compile(
    r"^(?:refs/heads/main|refs/remotes/[A-Za-z0-9._-]+/main)$"
)
DOCUMENTS_ROW = (
    "| `docs/goal/archived/` | `docs/goal/archived/` | run closeout | "
    "harness parent | moved coordination set plus closed "
    "ARCHIVE_RECEIPT.json (never delete) | "
)
ARCHIVE_RECEIPT_NAME = "ARCHIVE_RECEIPT.json"
ARCHIVE_RECEIPT_PROTOCOL = "harness-archive-receipt-v1"
ARCHIVE_RECEIPT_KEYS = {
    "protocol", "run_id", "plan_id", "plan_revision", "plan_digest_sha256",
    "candidate_c", "branch", "branch_ref", "expected_main", "main_ref", "stamp",
    "archive_path", "moves", "documents_before_sha256", "documents_after_sha256",
    "anchor_path", "anchor_path_sha256", "anchor_nonce", "receipt_sha256",
}
ARCHIVE_ANCHOR_NAME = "ARCHIVE_ANCHOR"
ARCHIVE_JOURNAL_NAME = ".ARCHIVE_TRANSACTION.json"
ARCHIVE_JOURNAL_PROTOCOL = "harness-archive-transaction-v1"
ARCHIVE_ANCHOR_PROTOCOL = "harness-archive-anchor-v1"
ARCHIVE_ANCHOR_KEYS = {
    "protocol", "anchor_path", "anchor_path_sha256", "anchor_nonce", "receipt_sha256",
    "run_id", "plan_id", "plan_revision", "plan_digest_sha256", "candidate_c",
    "branch", "branch_ref", "expected_main", "main_ref", "stamp", "archive_path",
    "source_inventory", "moves_sha256", "anchor_sha256", "created_at",
}

_LAST_DOCUMENT_WRITE_STATE: dict[str, object] | None = None
_ACTIVE_DOCUMENT_LOCK: "_DocumentLock | None" = None


class _DocumentLock:
    """Stable cross-process lock for one checkout's DOCUMENTS transaction."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        token = hashlib.sha256(str(self.root).encode("utf-8")).hexdigest()[:32]
        self.path = Path(tempfile.gettempdir()) / f"product-delivery-harness-documents-{token}.lock"
        self.fd: int | None = None
        self._reentrant = False

    def acquire(self) -> None:
        global _ACTIVE_DOCUMENT_LOCK
        if _ACTIVE_DOCUMENT_LOCK is not None:
            if _ACTIVE_DOCUMENT_LOCK.root != self.root:
                raise OSError("another DOCUMENTS transaction is active in this process")
            self._reentrant = True
            return
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_EX)
            _ACTIVE_DOCUMENT_LOCK = self
        except Exception:
            os.close(self.fd)
            self.fd = None
            raise

    def release(self) -> None:
        global _ACTIVE_DOCUMENT_LOCK
        if self._reentrant:
            self._reentrant = False
            return
        if self.fd is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None
            if _ACTIVE_DOCUMENT_LOCK is self:
                _ACTIVE_DOCUMENT_LOCK = None


def _documents_version(root: Path, documents: Path) -> tuple[tuple[int, int, int], str] | None:
    identity = _safe_documents_identity(root, documents)
    if identity is None:
        return None
    return identity, _sha256_bytes(documents.read_bytes())


def _documents_before_commit(root: Path, documents: Path) -> None:
    """Testing/coordination hook immediately before the final CAS check."""

    return None

_UTC_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)


def _canonical_repo_path(value: object, *, prefix: str | None = None) -> bool:
    """Return whether a receipt path is a strict canonical POSIX path."""

    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value != value.replace("\\", "/") or value.startswith("/"):
        return False
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        return False
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return False
    if prefix is not None and not value.startswith(prefix):
        return False
    return True


def _is_reparse(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400))


def _inventory_tree(path: Path) -> list[Path]:
    """Inventory regular files without following a symlink/reparse point.

    ``Path.rglob`` follows enough path state between enumeration and stat that
    a nested junction can turn a harmless-looking evidence tree into an escape
    path.  Descriptor-backed ``scandir`` plus ``lstat`` gives every component a
    no-follow check.  Empty directories are deliberately not represented in
    the receipt; the archive contract moves only regular files.
    """

    path = Path(path)
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise OSError(f"cannot inspect archive source {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
        raise OSError(f"archive source contains a symlink/reparse point: {path}")
    if stat.S_ISREG(info.st_mode):
        return [path]
    if not stat.S_ISDIR(info.st_mode):
        raise OSError(f"archive source is not a regular file or directory: {path}")

    result: list[Path] = []
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                children = sorted(entries, key=lambda item: item.name)
                for entry in children:
                    child = Path(entry.path)
                    try:
                        child_info = entry.stat(follow_symlinks=False)
                    except OSError as exc:
                        raise OSError(f"cannot inspect archive source {child}: {exc}") from exc
                    if stat.S_ISLNK(child_info.st_mode) or _is_reparse(child_info):
                        raise OSError(f"archive source contains a symlink/reparse point: {child}")
                    if stat.S_ISDIR(child_info.st_mode):
                        pending.append(child)
                    elif stat.S_ISREG(child_info.st_mode):
                        result.append(child)
                    else:
                        raise OSError(f"archive source contains a non-regular entry: {child}")
        except OSError:
            raise
    return sorted(result, key=lambda item: item.as_posix())


def _validate_utc_timestamp(value: object, label: str) -> None:
    if not isinstance(value, str) or not _UTC_RFC3339_RE.fullmatch(value):
        raise ValueError(f"{label} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{label} must be an RFC3339 UTC timestamp ending in Z") from exc
    if parsed.tzinfo != timezone.utc:
        raise ValueError(f"{label} must be an RFC3339 UTC timestamp ending in Z")


_ARCHIVE_TRANSACTION_SOURCES = {
    "docs/goal/PLAN.md",
    "docs/goal/RUN.md",
    "docs/goal/DECISIONS.md",
    "docs/goal/REFINEMENT_BACKLOG.md",
    "docs/goal/evidence",
    "docs/tasks.md",
}


def _transaction_source_key(source: object) -> str | None:
    if not isinstance(source, str):
        return None
    if source == "docs/goal/evidence" or source.startswith("docs/goal/evidence/"):
        return "docs/goal/evidence"
    return source if source in _ARCHIVE_TRANSACTION_SOURCES else None


def _transaction_destination(archive_path: str, source: str) -> str:
    if source == "docs/goal/evidence":
        return f"{archive_path}/evidence"
    return f"{archive_path}/{Path(source).name}"


def _validate_archive_transaction_moves(
    archive_path: str,
    moves: object,
    *,
    receipt: dict[str, object] | None = None,
) -> list[str]:
    """Validate journal moves before opening or mutating any recovery path."""

    errors: list[str] = []
    if not isinstance(moves, list) or not moves:
        return ["archive transaction journal moves must be a non-empty list"]
    seen_sources: set[str] = set()
    seen_destinations: set[str] = set()
    journal_pairs: set[tuple[str, str]] = set()
    for index, item in enumerate(moves):
        if not isinstance(item, dict) or set(item) != {"source", "destination"}:
            errors.append(f"archive transaction journal move {index} has invalid fields")
            continue
        source = item.get("source")
        destination = item.get("destination")
        source_key = _transaction_source_key(source)
        if source_key is None or not _canonical_repo_path(source_key):
            errors.append(f"archive transaction journal move {index} source is outside the coordination set")
            continue
        if source != source_key:
            errors.append(f"archive transaction journal move {index} source must name a top-level coordination entry")
            continue
        if not _canonical_repo_path(destination, prefix=f"{archive_path}/"):
            errors.append(f"archive transaction journal move {index} destination is outside archive_path")
            continue
        expected_destination = _transaction_destination(archive_path, source_key)
        if destination != expected_destination:
            errors.append(f"archive transaction journal move {index} destination does not match source")
        if source_key in seen_sources:
            errors.append(f"archive transaction journal move {index} duplicates source")
        if destination in seen_destinations:
            errors.append(f"archive transaction journal move {index} duplicates destination")
        seen_sources.add(source_key)
        seen_destinations.add(destination)
        journal_pairs.add((source_key, destination))
    required = {"docs/goal/PLAN.md", "docs/goal/RUN.md"}
    if not required.issubset(seen_sources):
        errors.append("archive transaction journal moves must include PLAN.md and RUN.md")
    if receipt is not None:
        receipt_path = receipt.get("archive_path")
        if receipt_path != archive_path:
            errors.append("archive transaction journal archive_path does not match receipt")
        receipt_moves = receipt.get("moves")
        receipt_pairs: set[tuple[str, str]] = set()
        if isinstance(receipt_moves, list):
            for row in receipt_moves:
                if isinstance(row, dict):
                    source_key = _transaction_source_key(row.get("source"))
                    destination = row.get("destination")
                    if source_key is not None and isinstance(destination, str):
                        receipt_pairs.add((source_key, _transaction_destination(archive_path, source_key)))
        if journal_pairs != receipt_pairs:
            errors.append("archive transaction journal moves do not match receipt coordination sources")
    return errors


def _canonical_branch(value: object) -> str | None:
    """Return a canonical local branch name for bare/full branch values."""

    if not isinstance(value, str) or not value or value != value.strip():
        return None
    branch = value.removeprefix("refs/heads/")
    if not branch or branch.startswith("refs/") or "\\" in branch:
        return None
    if any(part in {"", ".", ".."} for part in branch.split("/")):
        return None
    return branch


def _branch_ref(value: object) -> str | None:
    branch = _canonical_branch(value)
    return None if branch is None else f"refs/heads/{branch}"


def _protected_branch(value: object) -> bool:
    branch = _canonical_branch(value)
    return branch is not None and branch.casefold() in {
        "main", "master", "development", "default"
    }


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _link_component(root: Path, path: Path) -> tuple[Path, str] | None:
    """Return the first symlink/reparse component under ``root``.

    ``Path.resolve`` alone is not a safety check: a link can resolve to another
    path still inside the checkout, including `.git`.  Inspect every existing
    component with ``lstat`` and reject Windows reparse points as well.
    """

    root = root.resolve(strict=False)
    candidate = path if path.is_absolute() else root / path
    candidate = Path(os.path.normpath(str(candidate)))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return candidate, "outside repository root"
    current = root
    for part in relative.parts:
        current /= part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError:
            return current, "unreadable path component"
        if stat.S_ISLNK(info.st_mode):
            return current, "symlink"
        attributes = getattr(info, "st_file_attributes", 0)
        reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
        if attributes & reparse:
            return current, "reparse point"
    return None


def _safe_documents_identity(root: Path, documents: Path) -> tuple[int, int, int] | None:
    """Validate the documents path and return its lstat identity."""

    link = _link_component(root, documents)
    if link is not None:
        component, kind = link
        raise OSError(
            f"{DOCUMENTS_PATH.as_posix()} contains unsafe {kind} component: {component}"
        )
    try:
        info = os.lstat(documents)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise OSError(f"{DOCUMENTS_PATH.as_posix()} is not a regular file")
    return (info.st_dev, info.st_ino, info.st_mode)


def _atomic_write_documents(
    root: Path,
    documents: Path,
    value: bytes,
    *,
    expected_bytes: bytes | None = None,
    _lock_already_held: bool = False,
) -> tuple[int, int, int]:
    """Write DOCUMENTS.md atomically after an immediate identity recheck."""

    if not _lock_already_held and _ACTIVE_DOCUMENT_LOCK is None:
        lock = _DocumentLock(root)
        lock.acquire()
        try:
            return _atomic_write_documents(
                root,
                documents,
                value,
                expected_bytes=expected_bytes,
                _lock_already_held=True,
            )
        finally:
            lock.release()

    initial = _safe_documents_identity(root, documents)
    if initial is None:
        raise OSError(f"{DOCUMENTS_PATH.as_posix()} disappeared before write")
    try:
        initial_bytes = documents.read_bytes()
    except OSError as exc:
        raise OSError(f"cannot read {DOCUMENTS_PATH.as_posix()} before write") from exc
    if expected_bytes is not None and initial_bytes != expected_bytes:
        raise OSError(f"{DOCUMENTS_PATH.as_posix()} content changed before write")
    initial_version = (initial, _sha256_bytes(initial_bytes))
    parent = documents.parent
    parent_fd: int | None = None
    if os.name != "nt":
        parent_fd = os.open(
            parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    fd = -1
    temporary_name: str | None = None
    try:
        if parent_fd is not None:
            temporary_name = f".{documents.name}.{secrets.token_hex(8)}.tmp"
            fd = os.open(
                temporary_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            temporary = Path(temporary_name)
        else:
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{documents.name}.", suffix=".tmp", dir=parent
            )
            temporary = Path(temporary_name)
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        fd = -1
        # The path may have been swapped after preflight.  Never replace a
        # different inode or a newly introduced link.
        current_version = _documents_version(root, documents)
        if current_version != initial_version:
            raise OSError(f"{DOCUMENTS_PATH.as_posix()} version changed before atomic replace")
        _documents_before_commit(root, documents)
        # The hook is intentionally followed by a second token comparison:
        # an injected last-read→replace edit is preserved instead of being
        # overwritten by the transaction's temporary file.
        current_version = _documents_version(root, documents)
        if current_version != initial_version:
            raise OSError(f"{DOCUMENTS_PATH.as_posix()} version changed at commit boundary")
        if parent_fd is not None:
            os.replace(
                temporary_name,
                documents.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
        else:
            os.replace(temporary, documents)
        identity = _safe_documents_identity(root, documents)
        if identity is None:
            raise OSError(f"{DOCUMENTS_PATH.as_posix()} disappeared after atomic replace")
        return identity
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        if temporary_name is not None:
            try:
                if parent_fd is not None:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                else:
                    Path(temporary_name).unlink()
            except FileNotFoundError:
                pass
        if parent_fd is not None:
            os.close(parent_fd)


def _git_filtered_bytes(
    root: Path,
    destination: Path,
    *,
    source: Path | None = None,
    value: bytes | None = None,
) -> bytes:
    """Read the exact Git blob bytes after destination-path filters apply."""

    destination_arg = destination.relative_to(root).as_posix() if destination.is_absolute() else destination.as_posix()
    if source is not None:
        link = _link_component(root, source)
        if link is not None:
            component, kind = link
            raise OSError(f"cannot hash unsafe archive source {component}: {kind}")
    # ``hash-object -w`` is required to apply Git's path filters, but writing
    # into the checkout's object database makes a supposedly read-only archive
    # preflight mutate .git/objects.  Give Git a temporary object store with
    # the real store as a read-only alternate and remove it after cat-file.
    try:
        reject_object_substitution(root)
        objects_result = run_git(root, "rev-parse", "--git-path", "objects", timeout=10)
        if objects_result.returncode != 0:
            raise OSError("cannot resolve Git object store")
        objects = Path(str(objects_result.stdout).strip())
        if not objects.is_absolute():
            objects = (root / objects).resolve()
        with tempfile.TemporaryDirectory(prefix="harness-filtered-objects-") as isolated:
            isolated_objects = Path(isolated) / "objects"
            isolated_objects.mkdir()
            environment = git_environment()
            environment["GIT_OBJECT_DIRECTORY"] = str(isolated_objects)
            environment["GIT_ALTERNATE_OBJECT_DIRECTORIES"] = str(objects)
            executable = git_executable(environment)
            argv = [executable, "--no-replace-objects", "hash-object", "-w", f"--path={destination_arg}"]
            if source is not None:
                argv.extend(("--", str(source)))
                input_data: bytes | None = None
            else:
                argv.append("--stdin")
                input_data = value or b""
            hashed = subprocess.run(
                argv,
                cwd=root,
                capture_output=True,
                text=False,
                timeout=10,
                env=environment,
                input=input_data,
            )
            if hashed.returncode != 0:
                detail = bytes(hashed.stderr).decode(errors="replace").strip()
                raise OSError(detail or "git hash-object failed")
            oid = bytes(hashed.stdout).decode("ascii").strip()
            blob = subprocess.run(
                [executable, "--no-replace-objects", "cat-file", "blob", oid],
                cwd=root,
                capture_output=True,
                text=False,
                timeout=10,
                env=environment,
            )
    except (OSError, subprocess.SubprocessError) as exc:
        if isinstance(exc, OSError) and str(exc):
            raise
        raise OSError("git filtered blob read failed") from exc
    if blob.returncode != 0:
        raise OSError("git cat-file failed while reading filtered blob")
    return bytes(blob.stdout)


def _documents_after_bytes(value: bytes | None) -> bytes | None:
    if value is None:
        return None
    text = value.decode("utf-8")
    if "docs/goal/archived/" in text:
        return value
    lines = text.splitlines(keepends=True)
    insert_at = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].lstrip().startswith("|"):
            insert_at = index + 1
            break
    newline = "\r\n" if "\r\n" in text else "\n"
    lines.insert(insert_at, DOCUMENTS_ROW + newline)
    return "".join(lines).encode("utf-8")


def _archive_file_moves(root: Path, moves: list[Path], target: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for source in moves:
        source_path = root / source
        destination = target / source.name
        archived_source = target / source.name
        # A caller may build a receipt after manually moving the files (the
        # historical test helper does this).  Prefer the live source, but use
        # the already-created archive copy when the source is absent.  The
        # receipt remains authoritative for the bytes and never derives them
        # from candidate C.
        if source_path.exists():
            files = _inventory_tree(source_path)
        else:
            archived_source = target / source.name
            files = _inventory_tree(archived_source) if archived_source.exists() else []
        for path in files:
            base = source_path if source_path.is_dir() else target / source.name
            relative = path.relative_to(base).as_posix() if base.is_dir() else path.name
            destination_path = destination / relative if source_path.is_dir() else destination
            if not source_path.exists() and archived_source.is_dir():
                destination_path = target / source.name / path.relative_to(archived_source).as_posix()
            entries.append({
                "source": (source / relative).as_posix() if source_path.is_dir() or archived_source.is_dir() else source.as_posix(),
                "destination": destination_path.relative_to(root).as_posix(),
                "type": "file",
                "sha256": _sha256_bytes(_git_filtered_bytes(root, destination_path, source=path)),
            })
    return sorted(entries, key=lambda item: (str(item["source"]), str(item["destination"])))


def _build_archive_receipt(
    root: Path,
    plan: dict[str, object],
    run: dict[str, object],
    moves: list[Path],
    target: Path,
    *,
    expected_main: str | None,
    main_ref: str | None,
    stamp: str,
    anchor_path: Path | None = None,
    anchor_nonce: str | None = None,
) -> dict[str, object]:
    integration = run.get("integration") if isinstance(run.get("integration"), dict) else {}
    branch = _canonical_branch(integration.get("branch"))
    candidate_c = integration.get("integration_head_sha")
    branch_ref = _branch_ref(branch)
    documents_path = root / DOCUMENTS_PATH
    before = documents_path.read_bytes() if documents_path.is_file() else None
    after = _documents_after_bytes(before)
    before_for_git = _git_filtered_bytes(root, documents_path, value=before) if before is not None else None
    after_for_git = _git_filtered_bytes(root, documents_path, value=after) if after is not None else None
    receipt: dict[str, object] = {
        "protocol": ARCHIVE_RECEIPT_PROTOCOL,
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "candidate_c": candidate_c,
        "branch": branch,
        "branch_ref": branch_ref,
        "expected_main": expected_main,
        "main_ref": main_ref,
        "stamp": stamp,
        "archive_path": target.relative_to(root).as_posix(),
        "moves": _archive_file_moves(root, moves, target),
        "documents_before_sha256": _sha256_bytes(before_for_git) if before_for_git is not None else None,
        "documents_after_sha256": _sha256_bytes(after_for_git) if after_for_git is not None else None,
        "anchor_path": str(anchor_path.resolve()) if anchor_path is not None else None,
        "anchor_path_sha256": _sha256_bytes(str(anchor_path.resolve()).encode()) if anchor_path is not None else None,
        "anchor_nonce": anchor_nonce,
    }
    receipt["receipt_sha256"] = _sha256_bytes(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return receipt


def _write_archive_receipt(path: Path, receipt: dict[str, object]) -> None:
    if set(receipt) != ARCHIVE_RECEIPT_KEYS:
        raise RuntimeError("archive receipt has an invalid schema")
    _write_atomic_exclusive_json(path, receipt)


def validate_archive_receipt(receipt: object) -> list[str]:
    """Validate the closed receipt shape without consulting Git.

    The push protocol calls this before every side effect.  Keep this helper
    deliberately strict: JSON type coercion must never turn a malformed
    receipt into authority.
    """

    errors: list[str] = []
    if not isinstance(receipt, dict):
        return ["archive receipt must be an object"]
    if set(receipt) != ARCHIVE_RECEIPT_KEYS:
        errors.append("archive receipt has missing or extra fields")
    if receipt.get("protocol") != ARCHIVE_RECEIPT_PROTOCOL:
        errors.append("archive receipt protocol is invalid")
    for key in ("run_id", "plan_id", "archive_path", "branch", "branch_ref", "stamp"):
        if not isinstance(receipt.get(key), str) or not str(receipt.get(key)).strip():
            errors.append(f"archive receipt {key} must be a non-empty string")
    if not isinstance(receipt.get("plan_revision"), int) or isinstance(receipt.get("plan_revision"), bool) or receipt.get("plan_revision", 0) < 1:
        errors.append("archive receipt plan_revision must be a positive integer")
    for key in ("plan_digest_sha256", "documents_before_sha256", "documents_after_sha256"):
        value = receipt.get(key)
        if value is not None and (not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None):
            errors.append(f"archive receipt {key} must be lowercase SHA-256 or null")
    for key in ("candidate_c",):
        value = receipt.get(key)
        if not isinstance(value, str) or FULL_SHA_RE.fullmatch(value) is None:
            errors.append(f"archive receipt {key} must be a lowercase full Git SHA")
    expected_main = receipt.get("expected_main")
    if not isinstance(expected_main, str) or FULL_SHA_RE.fullmatch(expected_main) is None:
        errors.append("archive receipt expected_main must be a lowercase full Git SHA")
    main_ref = receipt.get("main_ref")
    if not isinstance(main_ref, str) or MAIN_REF_RE.fullmatch(main_ref) is None:
        errors.append("archive receipt main_ref must be a canonical main ref")
    branch = _canonical_branch(receipt.get("branch"))
    if branch is None or _protected_branch(branch):
        errors.append("archive receipt branch is invalid or protected")
    if receipt.get("branch_ref") != _branch_ref(branch):
        errors.append("archive receipt branch_ref is not canonical")
    archive_path = receipt.get("archive_path")
    stamp = receipt.get("stamp")
    if not isinstance(stamp, str) or re.fullmatch(r"\d{8}-\d{6}", stamp) is None or not isinstance(archive_path, str) or not archive_path.startswith(f"docs/goal/archived/{stamp}-"):
        errors.append("archive receipt stamp is invalid")
    if not _canonical_repo_path(archive_path, prefix="docs/goal/archived/"):
        errors.append("archive receipt archive_path must be a repository-relative archive path")
    elif len(Path(archive_path).parts) != 4:
        errors.append("archive receipt archive_path must name one archive directory")
    moves = receipt.get("moves")
    if not isinstance(moves, list) or not moves:
        errors.append("archive receipt moves must be a non-empty list")
    else:
        seen_sources: set[str] = set()
        seen_destinations: set[str] = set()
        allowed_optional = {"docs/goal/DECISIONS.md", "docs/goal/REFINEMENT_BACKLOG.md", "docs/tasks.md"}
        for index, move in enumerate(moves):
            if not isinstance(move, dict) or set(move) != {"source", "destination", "type", "sha256"}:
                errors.append(f"archive receipt moves[{index}] has invalid fields")
                continue
            source = move.get("source")
            destination = move.get("destination")
            move_type = move.get("type")
            digest = move.get("sha256")
            valid_source = (
                _canonical_repo_path(source)
                and (
                    source in {"docs/goal/PLAN.md", "docs/goal/RUN.md"}
                    or source in allowed_optional
                    or source.startswith("docs/goal/evidence/")
                )
            )
            valid_destination = _canonical_repo_path(
                destination, prefix=f"{archive_path}/"
            )
            if not valid_source:
                errors.append(f"archive receipt moves[{index}] source is outside the coordination set")
            if not valid_destination:
                errors.append(f"archive receipt moves[{index}] destination is outside archive_path")
            elif isinstance(source, str):
                if source == "docs/tasks.md":
                    expected_destination = f"{archive_path}/tasks.md"
                elif source.startswith("docs/goal/evidence/"):
                    expected_destination = f"{archive_path}/evidence/{source.removeprefix('docs/goal/evidence/')}"
                else:
                    expected_destination = f"{archive_path}/{Path(source).name}"
                if destination != expected_destination:
                    errors.append(f"archive receipt moves[{index}] destination does not match source")
            if move_type != "file":
                errors.append(f"archive receipt moves[{index}] type must be file")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                errors.append(f"archive receipt moves[{index}] sha256 is invalid")
            if isinstance(source, str):
                if source in seen_sources:
                    errors.append(f"archive receipt moves[{index}] duplicates source")
                seen_sources.add(source)
            if isinstance(destination, str):
                if destination in seen_destinations:
                    errors.append(f"archive receipt moves[{index}] duplicates destination")
                seen_destinations.add(destination)
        if "docs/goal/PLAN.md" not in seen_sources or "docs/goal/RUN.md" not in seen_sources:
            errors.append("archive receipt moves must include PLAN.md and RUN.md")
    if not isinstance(receipt.get("receipt_sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("receipt_sha256"))) is None:
        errors.append("archive receipt receipt_sha256 is invalid")
    else:
        unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if receipt["receipt_sha256"] != _sha256_bytes(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")):
            errors.append("archive receipt digest mismatch")
    return errors


def _canonical_external_path(value: object, *, root: Path, label: str) -> Path:
    if isinstance(value, str):
        path = Path(value)
    elif isinstance(value, Path):
        path = value
    else:
        raise ValueError(f"{label} must be an absolute path")
    resolved = path.resolve(strict=False)
    if not resolved.is_absolute() or str(path) != str(resolved):
        raise ValueError(f"{label} must be a canonical absolute path")
    if resolved.is_relative_to(root.resolve()):
        raise ValueError(f"{label} must be outside the repository root")
    return resolved


def _anchor_digest(value: dict[str, object]) -> str:
    unsigned = {key: item for key, item in value.items() if key != "anchor_sha256"}
    return _sha256_bytes(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def validate_archive_anchor(anchor: object, *, root: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not isinstance(anchor, dict):
        return ["archive anchor must be an object"]
    if set(anchor) != ARCHIVE_ANCHOR_KEYS:
        errors.append("archive anchor has missing or extra fields")
    if anchor.get("protocol") != ARCHIVE_ANCHOR_PROTOCOL:
        errors.append("archive anchor protocol is invalid")
    for key in ("run_id", "plan_id", "archive_path", "branch", "branch_ref", "stamp", "anchor_path"):
        if not isinstance(anchor.get(key), str) or not str(anchor.get(key)).strip():
            errors.append(f"archive anchor {key} must be a non-empty string")
    if isinstance(anchor.get("anchor_path"), str) and root is not None:
        try:
            _canonical_external_path(anchor["anchor_path"], root=root, label="anchor_path")
        except ValueError as exc:
            errors.append(str(exc))
    if not isinstance(anchor.get("anchor_path_sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", str(anchor.get("anchor_path_sha256"))) is None:
        errors.append("archive anchor anchor_path_sha256 is invalid")
    elif isinstance(anchor.get("anchor_path"), str) and _sha256_bytes(str(Path(anchor["anchor_path"]).resolve()).encode()) != anchor["anchor_path_sha256"]:
        errors.append("archive anchor anchor_path_sha256 does not match path")
    nonce = anchor.get("anchor_nonce")
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
        errors.append("archive anchor anchor_nonce is invalid")
    for key in ("plan_digest_sha256", "receipt_sha256", "moves_sha256"):
        if not isinstance(anchor.get(key), str) or re.fullmatch(r"[0-9a-f]{64}", str(anchor.get(key))) is None:
            errors.append(f"archive anchor {key} is invalid")
    for key in ("candidate_c", "expected_main"):
        value = anchor.get(key)
        if not isinstance(value, str) or FULL_SHA_RE.fullmatch(value) is None:
            errors.append(f"archive anchor {key} must be a lowercase full Git SHA")
    branch = _canonical_branch(anchor.get("branch"))
    if branch is None or _protected_branch(branch) or anchor.get("branch_ref") != _branch_ref(branch):
        errors.append("archive anchor branch/ref is invalid")
    if not isinstance(anchor.get("plan_revision"), int) or isinstance(anchor.get("plan_revision"), bool) or anchor.get("plan_revision", 0) < 1:
        errors.append("archive anchor plan_revision must be positive")
    if not isinstance(anchor.get("source_inventory"), list) or not anchor["source_inventory"]:
        errors.append("archive anchor source_inventory must be a non-empty list")
    else:
        for row in anchor["source_inventory"]:
            if not isinstance(row, dict) or set(row) != {"source", "destination", "type", "sha256"}:
                errors.append("archive anchor source_inventory row is invalid")
    created = anchor.get("created_at")
    try:
        _validate_utc_timestamp(created, "archive anchor created_at")
    except ValueError as exc:
        errors.append(str(exc))
    if not isinstance(anchor.get("anchor_sha256"), str) or re.fullmatch(r"[0-9a-f]{64}", str(anchor.get("anchor_sha256"))) is None:
        errors.append("archive anchor anchor_sha256 is invalid")
    elif anchor["anchor_sha256"] != _anchor_digest(anchor):
        errors.append("archive anchor digest mismatch")
    return errors


def _build_archive_anchor(
    root: Path,
    receipt: dict[str, object],
    *,
    anchor_path: Path,
    nonce: str,
    created_at: str | None = None,
) -> dict[str, object]:
    canonical = _canonical_external_path(anchor_path, root=root, label="anchor_path")
    moves = receipt["moves"]
    if not isinstance(moves, list):
        raise ValueError("receipt moves must be a list")
    anchor: dict[str, object] = {
        "protocol": ARCHIVE_ANCHOR_PROTOCOL,
        "anchor_path": str(canonical),
        "anchor_path_sha256": _sha256_bytes(str(canonical).encode()),
        "anchor_nonce": nonce,
        "receipt_sha256": receipt["receipt_sha256"],
        "run_id": receipt["run_id"],
        "plan_id": receipt["plan_id"],
        "plan_revision": receipt["plan_revision"],
        "plan_digest_sha256": receipt["plan_digest_sha256"],
        "candidate_c": receipt["candidate_c"],
        "branch": receipt["branch"],
        "branch_ref": receipt["branch_ref"],
        "expected_main": receipt["expected_main"],
        "main_ref": receipt["main_ref"],
        "stamp": receipt["stamp"],
        "archive_path": receipt["archive_path"],
        "source_inventory": moves,
        "moves_sha256": _sha256_bytes(json.dumps(moves, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
        "created_at": created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    anchor["anchor_sha256"] = _anchor_digest(anchor)
    return anchor


def _write_atomic_exclusive_json(
    path: Path,
    value: dict[str, object],
    *,
    dir_fd: int | None = None,
    replace: bool = False,
) -> None:
    """Publish a closed JSON record with fsync and no-replace semantics."""

    payload = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    parent = path.parent
    if dir_fd is not None:
        temporary_name = f".{path.name}.{secrets.token_hex(8)}.tmp"
        fd = os.open(
            temporary_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=dir_fd,
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if replace:
                os.replace(
                    temporary_name,
                    path.name,
                    src_dir_fd=dir_fd,
                    dst_dir_fd=dir_fd,
                )
            else:
                os.link(
                    temporary_name,
                    path.name,
                    src_dir_fd=dir_fd,
                    dst_dir_fd=dir_fd,
                    follow_symlinks=False,
                )
            os.fsync(dir_fd)
        finally:
            try:
                os.unlink(temporary_name, dir_fd=dir_fd)
            except FileNotFoundError:
                pass
        return

    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard-link publish is atomic and refuses to replace an existing
        # destination on POSIX and NTFS.  If a filesystem has no link support,
        # fail closed instead of falling back to an overwriting replace.
        if replace:
            os.replace(temporary_name, path)
        else:
            os.link(temporary_name, path)
        try:
            parent_fd = os.open(
                parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            )
        except OSError:
            parent_fd = None
        if parent_fd is not None:
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
    except FileExistsError:
        raise
    except OSError as exc:
        raise OSError(f"cannot publish closed JSON record atomically: {exc}") from exc
    finally:
        try:
            Path(temporary_name).unlink()
        except FileNotFoundError:
            pass


def _write_closed_anchor(path: Path, anchor: dict[str, object], root: Path) -> None:
    if path.resolve().is_relative_to(root.resolve()):
        raise ValueError("archive anchor must be outside checkout")
    if path.exists():
        raise FileExistsError("archive anchor path already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic_exclusive_json(path, anchor)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"


def _completed_run_ok(run: dict[str, object]) -> list[str]:
    problems: list[str] = []
    if run.get("status") != "complete":
        problems.append(
            f"run status is {run.get('status')!r}; only a complete run may be archived"
        )
    final_gates = run.get("final_gate_results")
    if final_gates is not None:
        if not isinstance(final_gates, list):
            problems.append("run.final_gate_results must be a list")
        else:
            for gate in final_gates:
                if isinstance(gate, dict) and gate.get("status") != "PASS":
                    problems.append(
                        f"final gate {gate.get('id')!r} is {gate.get('status')!r}; "
                        "every final gate must PASS before archival"
                    )
    return problems


def plan_moves(root: Path) -> tuple[list[Path], list[str]]:
    """Return repo-relative sources to move, and missing required paths."""

    moves: list[Path] = []
    missing_required: list[str] = []
    sources: list[tuple[Path, bool]] = [
        (GOAL_DIR / name, True) for name in REQUIRED_FILES
    ]
    sources.extend((GOAL_DIR / name, False) for name in OPTIONAL_FILES)
    sources.append((GOAL_DIR / "evidence", False))
    sources.append((Path("docs/tasks.md"), False))
    for source, required in sources:
        candidate = root / source
        if candidate.exists() and source == GOAL_DIR / "evidence":
            # Empty optional directories have no receipt rows and are
            # deliberately skipped.  This keeps the archive contract typed as
            # regular-file moves only instead of silently moving an
            # unrepresented directory.
            try:
                if not _inventory_tree(candidate):
                    continue
            except OSError:
                # Keep unsafe trees in the move list so preflight/guard emits
                # the precise symlink/reparse or non-regular finding.
                pass
        if candidate.exists():
            moves.append(source)
        elif required:
            missing_required.append(source.as_posix())
    return moves, missing_required


def _resolved_inside(root: Path, path: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root)
        return resolved
    except (OSError, ValueError):
        return None


def _preflight_archive_paths(
    root: Path, moves: list[Path], target: Path
) -> list[str]:
    """Check every source and destination before creating anything."""

    problems: list[str] = []
    root = root.resolve()
    resolved_target = _resolved_inside(root, target)
    if resolved_target is None:
        return [f"archive target resolves outside the repository root: {target}"]
    for label, path in (
        ("archive target", target),
        ("documents path", root / DOCUMENTS_PATH),
    ):
        link = _link_component(root, path)
        if link is not None:
            component, kind = link
            problems.append(f"{label} contains unsafe {kind} component: {component}")
    if target.exists():
        problems.append(f"archive target already exists: {target}")
    if target.parent.exists() and not target.parent.is_dir():
        problems.append(
            f"archive destination parent is not a directory: {target.parent}"
        )

    destinations: set[Path] = set()
    for source in moves:
        source_path = root / source
        link = _link_component(root, source_path)
        if link is not None:
            component, kind = link
            problems.append(
                f"source {source.as_posix()} contains unsafe {kind} component: {component}"
            )
            continue
        resolved_source = _resolved_inside(root, source_path)
        if resolved_source is None:
            problems.append(f"source resolves outside the repository root: {source}")
            continue
        if not source_path.exists():
            # plan_moves reports required files; optional paths may be absent.
            continue
        destination = resolved_target / source.name
        link = _link_component(root, destination)
        if link is not None:
            component, kind = link
            problems.append(
                f"destination {destination} contains unsafe {kind} component: {component}"
            )
        if destination in destinations:
            problems.append(f"duplicate archive destination: {destination}")
        destinations.add(destination)
        if destination.exists():
            problems.append(f"archive destination already exists: {destination}")

    documents = root / DOCUMENTS_PATH
    if documents.parent.exists() and not documents.parent.is_dir():
        problems.append(
            f"documents destination parent is not a directory: {documents.parent}"
        )
    if documents.exists():
        try:
            _safe_documents_identity(root, documents)
        except OSError as exc:
            problems.append(str(exc))
    resolved_documents = _resolved_inside(root, documents)
    if documents.exists() and resolved_documents is None:
        problems.append(
            f"documents destination resolves outside the repository root: {DOCUMENTS_PATH}"
        )
    return problems


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return run_git(root, *args, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None


def _live_head_problems(
    run: dict[str, object],
    root: Path,
    expected_main: str | None,
    main_ref: str | None,
    allowed_dirty_roots: list[Path],
) -> list[str]:
    """Bind pre-promotion archival to the exact run branch and observed main."""

    problems: list[str] = []
    if expected_main is None:
        return ["--expected-main is required with --apply"]
    if not FULL_SHA_RE.fullmatch(expected_main):
        return [f"--expected-main {expected_main!r} must be a full lowercase SHA"]
    if main_ref is None:
        return ["--main-ref is required with --apply"]
    if not MAIN_REF_RE.fullmatch(main_ref) or ".." in main_ref:
        return [
            "--main-ref must be refs/heads/main or refs/remotes/<remote>/main"
        ]

    observed_main = _git(root, "rev-parse", "--verify", f"{main_ref}^{{commit}}")
    if observed_main is None:
        return [f"could not resolve the observed main ref {main_ref}"]
    if observed_main.returncode != 0:
        reason = observed_main.stderr.strip() or (
            f"git rev-parse exited {observed_main.returncode}"
        )
        return [f"could not resolve the observed main ref {main_ref}: {reason}"]
    observed_main_sha = observed_main.stdout.strip()
    if observed_main_sha != expected_main:
        return [
            f"observed main ref {main_ref} is {observed_main_sha}, not the "
            f"authorized/read-back SHA {expected_main}"
        ]

    integration = run.get("integration")
    recorded_branch = (
        _canonical_branch(integration.get("branch")) if isinstance(integration, dict) else None
    )
    if recorded_branch is None:
        problems.append("RUN integration.branch must be a canonical named branch")
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch is None:
        return ["could not read the current Git branch"]
    if branch.returncode != 0:
        return ["archive apply requires a named run branch; detached HEAD is refused"]
    live_branch = _canonical_branch(branch.stdout.strip())
    if live_branch is None:
        problems.append("current Git branch is not a canonical branch name")
        return problems
    if _protected_branch(live_branch):
        problems.append(
            f"archive apply is forbidden on protected branch {live_branch!r}"
        )
    if recorded_branch is not None and live_branch != recorded_branch:
        problems.append(
            f"current branch {live_branch!r} does not match run integration branch "
            f"{recorded_branch!r}"
        )

    head = _git(root, "rev-parse", "HEAD")
    if head is None:
        return ["could not read the live Git HEAD"]
    if head.returncode != 0:
        reason = head.stderr.strip() or f"git rev-parse exited {head.returncode}"
        return [f"could not read the live Git HEAD: {reason}"]
    live_head = head.stdout.strip()
    recorded_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    if live_head != recorded_head:
        problems.append(
            f"live HEAD {live_head} does not match run integration head {recorded_head}"
        )

    ancestry = _git(root, "merge-base", "--is-ancestor", expected_main, live_head)
    if ancestry is None:
        problems.append("could not verify live HEAD ancestry")
    elif ancestry.returncode != 0:
        problems.append(
            f"live HEAD {live_head} does not descend from expected main/base {expected_main}"
        )

    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if status is None:
        problems.append("could not read the live checkout status")
    elif status.returncode != 0:
        reason = status.stderr.strip() or f"git status exited {status.returncode}"
        problems.append(f"could not read the live checkout status: {reason}")
    else:
        allowed = [path.as_posix().rstrip("/") for path in allowed_dirty_roots]
        entries = status.stdout.split("\0")
        index = 0
        while index < len(entries):
            entry = entries[index]
            index += 1
            if not entry:
                continue
            code = entry[:2]
            dirty_path = entry[3:].replace("\\", "/")
            if "R" in code or "C" in code:
                # In porcelain -z mode a rename/copy has a second path field.
                if index < len(entries) and entries[index]:
                    dirty_path = f"{dirty_path} -> {entries[index]}"
                    index += 1
                problems.append(
                    f"archive apply refuses renamed/copied dirty path: {dirty_path}"
                )
                continue
            if not any(
                dirty_path == root_path or dirty_path.startswith(root_path + "/")
                for root_path in allowed
            ):
                problems.append(
                    f"archive apply found unrelated dirty path: {dirty_path}"
                )
    return problems


def _move_entry(source: Path, destination: Path) -> None:
    if destination.exists():
        raise FileExistsError(f"archive destination already exists: {destination}")
    shutil.move(str(source), str(destination))


class _ArchiveMutationGuard:
    """Bind archive parent/source identities for the whole mutation window.

    Windows holds no-delete directory handles with OPEN_REPARSE_POINT, which
    prevents a concurrent rename/junction replacement while path operations
    run.  POSIX uses O_DIRECTORY|O_NOFOLLOW descriptors and descriptor-relative
    rename/mkdir calls.  If either primitive cannot be established, archival
    fails closed before writing a receipt or moving a source.
    """

    def __init__(self, root: Path, moves: list[Path], target: Path, anchor_path: Path | None = None) -> None:
        self.root = root.resolve()
        self.moves = moves
        self.target = target
        self.anchor_path = anchor_path.resolve() if anchor_path is not None else None
        self.handles: list[object] = []
        self.parent_handles: dict[Path, object] = {}
        self.parent_identities: dict[Path, tuple[int, int, int]] = {}
        self.source_parent_fds: dict[Path, int] = {}
        self.archived_parent: Path = target.parent
        self.target_handle: object | None = None
        self.target_fd: int | None = None
        self.anchor_parent_fd: int | None = None
        self.archived_created = False
        self.documents_lock = _DocumentLock(self.root)
        try:
            self.documents_lock.acquire()
            self._prepare()
        except Exception:
            if self.archived_created:
                try:
                    self.remove_archived_parent()
                except OSError:
                    # The original failure is authoritative; leave a visible
                    # empty parent only when the OS cannot safely remove it.
                    pass
            self.close()
            raise

    def _prepare(self) -> None:
        if os.name == "nt":
            self._prepare_windows()
        else:
            self._prepare_posix()

    def _check_posix_identities(self) -> None:
        if os.name == "nt":
            return
        for relative, fd in self.source_parent_fds.items():
            path = relative if relative.is_absolute() else self.root / relative
            current = os.stat(path, follow_symlinks=False)
            held = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (held.st_dev, held.st_ino):
                raise OSError(f"archive directory identity changed: {path}")

    def _reject_tree_reparse(self, path: Path) -> None:
        _inventory_tree(path)

    def _prepare_posix(self) -> None:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        root_fd = os.open(self.root, flags)
        self.source_parent_fds[Path(".")] = root_fd
        docs_fd = os.open("docs", flags, dir_fd=root_fd)
        self.source_parent_fds[Path("docs")] = docs_fd
        goal_fd = os.open("goal", flags, dir_fd=docs_fd)
        self.source_parent_fds[Path("docs/goal")] = goal_fd
        try:
            archived_fd = os.open("archived", flags, dir_fd=goal_fd)
        except FileNotFoundError:
            os.mkdir("archived", dir_fd=goal_fd)
            self.archived_created = True
            archived_fd = os.open("archived", flags, dir_fd=goal_fd)
        self.source_parent_fds[Path("docs/goal/archived")] = archived_fd
        archived = self.root / "docs/goal/archived"
        self.archived_parent = archived
        if self.anchor_path is not None:
            self.anchor_parent_fd = os.open(self.anchor_path.parent, flags)
            self.source_parent_fds[self.anchor_path.parent] = self.anchor_parent_fd
        for source in self.moves:
            source_path = self.root / source
            if source_path.exists():
                self._reject_tree_reparse(source_path)
        self.target_fd = None

    def _windows_handle(self, path: Path, *, directory: bool, delete_access: bool = False) -> object:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.GetFileAttributesW.restype = wintypes.DWORD
        attrs = kernel32.GetFileAttributesW(str(path))
        invalid_attrs = wintypes.DWORD(-1).value
        if attrs == invalid_attrs:
            raise OSError(ctypes.get_last_error(), f"cannot inspect archive path: {path}")
        if attrs & 0x400:
            raise OSError(f"archive path is a reparse point: {path}")
        flags = 0x02000000 | (0x00200000 if directory else 0)
        desired = 0x80000000 | (0x00010000 if delete_access else 0)
        handle = kernel32.CreateFileW(str(path), desired, 0x00000001 | 0x00000002, None, 3, flags, None)
        if handle in (None, wintypes.HANDLE(-1).value):
            raise OSError(ctypes.get_last_error(), f"cannot hold archive path: {path}")
        self.handles.append((kernel32, handle))
        return handle

    def _windows_identity(self, handle: object) -> tuple[int, int, int]:
        import ctypes

        class FileInfo(ctypes.Structure):
            _fields_ = [
                ("attributes", ctypes.c_uint32),
                ("created_low", ctypes.c_uint32), ("created_high", ctypes.c_uint32),
                ("accessed_low", ctypes.c_uint32), ("accessed_high", ctypes.c_uint32),
                ("written_low", ctypes.c_uint32), ("written_high", ctypes.c_uint32),
                ("volume", ctypes.c_uint32), ("size_high", ctypes.c_uint32),
                ("size_low", ctypes.c_uint32), ("links", ctypes.c_uint32),
                ("index_high", ctypes.c_uint32), ("index_low", ctypes.c_uint32),
            ]
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        info = FileInfo()
        if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise OSError(ctypes.get_last_error(), "cannot read archive handle identity")
        return (int(info.volume), int(info.index_high), int(info.index_low))

    def _windows_rename_bound(self, source: Path, destination: Path) -> None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
        source_handle = kernel32.CreateFileW(
            str(source), 0x80000000 | 0x00010000,
            0x00000001 | 0x00000002, None, 3,
            # BACKUP_SEMANTICS opens directories; OPEN_REPARSE_POINT is
            # unconditional so a leaf swapped to a link is renamed as that
            # link and never followed to an external target.
            0x02000000 | 0x00200000, None,
        )
        if source_handle in (None, wintypes.HANDLE(-1).value):
            raise OSError(ctypes.get_last_error(), f"cannot hold source for handle-bound rename: {source}")
        try:
            destination_parent = destination.parent
            destination_handle = (
                self.target_handle
                if destination_parent == self.target
                else self.parent_handles.get(destination_parent)
            )
            if destination_handle is None:
                raise OSError(f"destination parent is not held: {destination_parent}")
            # FILE_RENAME_INFO rejects RootDirectory+basename for this handle
            # combination on supported Windows runners (ERROR_INVALID_PARAMETER).
            # Every destination ancestor is already held without FILE_SHARE_DELETE
            # and identity-checked, so the absolute name cannot be redirected by
            # renaming or replacing its parent while this operation is in flight.
            name_bytes = str(destination).encode("utf-16-le")
            class RenameInfo(ctypes.Structure):
                _fields_ = [
                    ("replace", wintypes.BOOLEAN),
                    ("root", wintypes.HANDLE),
                    ("length", wintypes.DWORD),
                    ("name", wintypes.WCHAR * 1),
                ]
            name_offset = RenameInfo.name.offset
            buffer = ctypes.create_string_buffer(name_offset + len(name_bytes) + ctypes.sizeof(wintypes.WCHAR))
            info = ctypes.cast(buffer, ctypes.POINTER(RenameInfo)).contents
            info.replace = 0
            info.root = None
            info.length = len(name_bytes)
            ctypes.memmove(ctypes.addressof(buffer) + name_offset, name_bytes, len(name_bytes))
            if not kernel32.SetFileInformationByHandle(
                source_handle, 3, ctypes.byref(buffer), ctypes.sizeof(buffer)
            ):
                raise OSError(ctypes.get_last_error(), f"handle-bound rename failed: {source}")
        finally:
            kernel32.CloseHandle(source_handle)

    def _check_windows_identities(self) -> None:
        if os.name != "nt":
            return
        for path, held in self.parent_handles.items():
            current = self._windows_handle(path, directory=True)
            identity = self._windows_identity(current)
            kernel32, handle = self.handles.pop()
            kernel32.CloseHandle(handle)
            if identity != self.parent_identities[path]:
                raise OSError(f"archive directory identity changed: {path}")

    def _prepare_windows(self) -> None:
        self.parent_handles[self.root] = self._windows_handle(self.root, directory=True)
        self.parent_identities[self.root] = self._windows_identity(self.parent_handles[self.root])
        docs = self.root / "docs"
        self.parent_handles[docs] = self._windows_handle(docs, directory=True)
        self.parent_identities[docs] = self._windows_identity(self.parent_handles[docs])
        goal = self.root / GOAL_DIR
        self.parent_handles[goal] = self._windows_handle(goal, directory=True)
        self.parent_identities[goal] = self._windows_identity(self.parent_handles[goal])
        archived = goal / "archived"
        if not archived.exists():
            archived.mkdir()
            self.archived_created = True
        self.parent_handles[archived] = self._windows_handle(archived, directory=True)
        self.parent_identities[archived] = self._windows_identity(self.parent_handles[archived])
        self.archived_parent = archived
        if self.anchor_path is not None:
            self.parent_handles[self.anchor_path.parent] = self._windows_handle(self.anchor_path.parent, directory=True)
            self.parent_identities[self.anchor_path.parent] = self._windows_identity(self.parent_handles[self.anchor_path.parent])
        for source in self.moves:
            source_path = self.root / source
            if source_path.exists():
                self._reject_tree_reparse(source_path)
            parent = source_path.parent.resolve()
            if parent not in self.parent_handles:
                self.parent_handles[parent] = self._windows_handle(parent, directory=True)
                self.parent_identities[parent] = self._windows_identity(self.parent_handles[parent])

    def create_target(self) -> None:
        self._check_windows_identities()
        self._check_posix_identities()
        if self.target.exists():
            raise FileExistsError(f"archive destination already exists: {self.target}")
        if os.name == "nt":
            self.target.mkdir()
            self.target_handle = self._windows_handle(self.target, directory=True, delete_access=True)
        else:
            archived_fd = self.source_parent_fds[Path("docs/goal/archived")]
            os.mkdir(self.target.name, dir_fd=archived_fd)
            self.target_fd = os.open(
                self.target.name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=archived_fd,
            )

    def bind_existing_target(self) -> None:
        """Bind an existing archive target for crash recovery/rollback."""

        if os.name == "nt":
            self.target_handle = self._windows_handle(self.target, directory=True, delete_access=True)
        else:
            archived_fd = self.source_parent_fds[Path("docs/goal/archived")]
            self.target_fd = os.open(
                self.target.name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=archived_fd,
            )

    def move(self, source: Path, destination: Path) -> None:
        if os.name == "nt":
            self._check_windows_identities()
            self._reject_tree_reparse(source)
            self._windows_rename_bound(source, destination)
            return
        self._check_posix_identities()
        self._reject_tree_reparse(source)
        source_rel = source.relative_to(self.root).parent
        destination_rel = destination.relative_to(self.root).parent
        source_fd = self.target_fd if source == self.target / source.name else self.source_parent_fds.get(source_rel)
        destination_fd = self.target_fd if destination.parent == self.target else self.source_parent_fds.get(destination_rel)
        if source_fd is None or destination_fd is None:
            raise OSError("archive target descriptor is not held")
        os.rename(source.name, destination.name, src_dir_fd=source_fd, dst_dir_fd=destination_fd)

    def write_receipt(self, root: Path, receipt: dict[str, object]) -> None:
        if os.name == "nt" or self.target_fd is None:
            _write_archive_receipt(self.target / ARCHIVE_RECEIPT_NAME, receipt)
            return
        self._check_posix_identities()
        _write_atomic_exclusive_json(
            self.target / ARCHIVE_RECEIPT_NAME,
            receipt,
            dir_fd=self.target_fd,
        )

    def write_anchor(self, anchor: dict[str, object]) -> None:
        if self.anchor_path is None:
            raise OSError("archive anchor path is not bound")
        if os.name == "nt" or self.anchor_parent_fd is None:
            _write_closed_anchor(self.anchor_path, anchor, self.root)
            return
        self._check_posix_identities()
        _write_atomic_exclusive_json(
            self.anchor_path,
            anchor,
            dir_fd=self.anchor_parent_fd,
        )

    def write_journal(self, journal: dict[str, object]) -> None:
        if self.target_fd is None and os.name != "nt":
            raise OSError("archive target descriptor is not held")
        if os.name == "nt":
            _write_atomic_exclusive_json(
                self.target / ARCHIVE_JOURNAL_NAME,
                journal,
                replace=True,
            )
        else:
            # Journal updates use an atomic same-directory replace after the
            # new bytes are durable.  The target remains handle-bound.
            if self.target_fd is not None:
                _write_atomic_exclusive_json(
                    self.target / ARCHIVE_JOURNAL_NAME,
                    journal,
                    dir_fd=self.target_fd,
                    replace=True,
                )

    def remove_journal(self) -> None:
        if os.name == "nt":
            path = self.target / ARCHIVE_JOURNAL_NAME
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            return
        if self.target_fd is not None:
            try:
                os.unlink(ARCHIVE_JOURNAL_NAME, dir_fd=self.target_fd)
            except FileNotFoundError:
                pass

    def remove_anchor(self) -> None:
        if self.anchor_path is None:
            return
        if os.name == "nt" or self.anchor_parent_fd is None:
            try:
                self.anchor_path.unlink()
            except FileNotFoundError:
                pass
            return
        try:
            os.unlink(self.anchor_path.name, dir_fd=self.anchor_parent_fd)
        except FileNotFoundError:
            pass

    def remove_archived_parent(self) -> None:
        if not self.archived_created:
            return
        if os.name == "nt":
            # Windows cannot remove a directory while its no-delete handle is
            # open.  Identity was checked immediately before this call; close
            # only the exact archived-parent handle, then remove that empty
            # directory.  We never touch a pre-existing parent.
            held = self.parent_handles.get(self.archived_parent)
            if held is not None:
                for index, item in enumerate(self.handles):
                    kernel32, handle = item
                    if handle == held:
                        kernel32.CloseHandle(handle)
                        self.handles.pop(index)
                        break
                self.parent_handles.pop(self.archived_parent, None)
            try:
                self.archived_parent.rmdir()
            except FileNotFoundError:
                pass
            return
        goal_fd = self.source_parent_fds.get(Path("docs/goal"))
        if goal_fd is None:
            raise OSError("docs/goal descriptor is not held")
        try:
            os.rmdir("archived", dir_fd=goal_fd)
        except FileNotFoundError:
            pass

    def release_target_handle(self) -> None:
        if os.name != "nt" or self.target_handle is None:
            return
        remaining: list[object] = []
        for kernel32, handle in self.handles:
            if handle == self.target_handle:
                kernel32.CloseHandle(handle)
            else:
                remaining.append((kernel32, handle))
        self.handles = remaining
        self.target_handle = None

    def remove_target(self) -> None:
        if os.name == "nt":
            if self.target_handle is None:
                raise OSError("archive target handle is not held")
            receipt_path = self.target / ARCHIVE_RECEIPT_NAME
            if receipt_path.exists():
                receipt_path.unlink()
            journal_path = self.target / ARCHIVE_JOURNAL_NAME
            if journal_path.exists():
                journal_path.unlink()
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            class Disposition(ctypes.Structure):
                _fields_ = [("delete", wintypes.BOOLEAN)]
            info = Disposition(1)
            if not kernel32.SetFileInformationByHandle(
                self.target_handle, 4, ctypes.byref(info), ctypes.sizeof(info)
            ):
                raise OSError(ctypes.get_last_error(), "handle-bound archive target removal failed")
            for kernel, handle in self.handles:
                if handle == self.target_handle:
                    kernel.CloseHandle(handle)
            self.handles = [(kernel, handle) for kernel, handle in self.handles if handle != self.target_handle]
            self.target_handle = None
            return
        if self.target_fd is None:
            raise OSError("archive target descriptor is not held")
        for name in (ARCHIVE_RECEIPT_NAME, ARCHIVE_JOURNAL_NAME):
            try:
                os.unlink(name, dir_fd=self.target_fd)
            except FileNotFoundError:
                pass
        archived_fd = self.source_parent_fds[Path("docs/goal/archived")]
        os.rmdir(self.target.name, dir_fd=archived_fd)

    def close(self) -> None:
        if os.name == "nt":
            for kernel32, handle in reversed(self.handles):
                kernel32.CloseHandle(handle)
            self.handles.clear()
        else:
            for fd in reversed(list(self.source_parent_fds.values())):
                try:
                    os.close(fd)
                except OSError:
                    pass
            self.source_parent_fds.clear()
            if self.target_fd is not None:
                try:
                    os.close(self.target_fd)
                except OSError:
                    pass
                self.target_fd = None
        self.documents_lock.release()


def _rollback_archive(
    root: Path,
    moved: list[tuple[Path, Path]],
    documents_snapshot: bytes | None,
    target: Path,
    anchor_path: Path | None = None,
    mutation_guard: _ArchiveMutationGuard | None = None,
    documents_write_state: dict[str, object] | None = None,
) -> list[str]:
    """Restore the pre-archive layout; retain archive copies only if a restore fails."""

    problems: list[str] = []
    documents_path = root / DOCUMENTS_PATH
    # Restore DOCUMENTS only when its identity and bytes still equal the
    # transaction's own output.  A concurrent writer gets preserved and a
    # recovery message instead of being silently clobbered.
    expected_after = (
        documents_write_state.get("bytes")
        if documents_write_state is not None
        else _documents_after_bytes(documents_snapshot)
    )
    expected_identity = (
        documents_write_state.get("identity")
        if documents_write_state is not None
        else None
    )
    try:
        current_identity = _safe_documents_identity(root, documents_path)
    except OSError as exc:
        problems.append(f"could not inspect {DOCUMENTS_PATH.as_posix()} during rollback: {exc}")
        current_identity = None
    current_bytes: bytes | None = None
    if current_identity is not None:
        try:
            current_bytes = documents_path.read_bytes()
        except OSError as exc:
            problems.append(f"could not read {DOCUMENTS_PATH.as_posix()} during rollback: {exc}")
    if documents_snapshot is not None:
        owns_output = (
            current_identity is not None
            and current_bytes == expected_after
            and expected_identity is not None
            and current_identity == expected_identity
        )
        unchanged = current_identity is not None and current_bytes == documents_snapshot
        if owns_output:
            try:
                _atomic_write_documents(
                    root,
                    documents_path,
                    documents_snapshot,
                    expected_bytes=expected_after,
                )
            except OSError as exc:
                problems.append(
                    f"could not restore {DOCUMENTS_PATH.as_posix()}: {exc}; "
                    "the original bytes were not replaced"
                )
        elif not unchanged:
            problems.append(
                f"preserved concurrent or unowned {DOCUMENTS_PATH.as_posix()}; "
                "manual recovery is required"
            )
    elif current_identity is not None:
        owns_created = (
            current_bytes == expected_after
            and expected_identity is not None
            and current_identity == expected_identity
        )
        if owns_created:
            try:
                documents_path.unlink()
            except OSError as exc:
                problems.append(
                    f"could not remove transaction-created {DOCUMENTS_PATH.as_posix()}: {exc}"
                )
        else:
            problems.append(
                f"preserved concurrent or unowned {DOCUMENTS_PATH.as_posix()}; "
                "manual recovery is required"
            )
    for source, destination in reversed(moved):
        try:
            if not destination.exists():
                problems.append(f"rolled-back entry is absent: {destination}")
            elif source.exists():
                problems.append(
                    f"cannot restore {source.as_posix()} because the source path reappeared"
                )
            else:
                if mutation_guard is not None:
                    mutation_guard.move(destination, source)
                else:
                    shutil.move(str(destination), str(source))
        except OSError as exc:
            problems.append(
                f"could not restore {source.as_posix()}; recoverable copy retained at "
                f"{destination}: {exc}"
            )
    if mutation_guard is not None:
        archived_parent = mutation_guard.archived_parent
        archived_created = mutation_guard.archived_created
    else:
        archived_parent = None
        archived_created = False
    if not problems and target.exists():
        try:
            if mutation_guard is not None:
                mutation_guard.remove_target()
            else:
                receipt_path = target / ARCHIVE_RECEIPT_NAME
                if receipt_path.exists():
                    receipt_path.unlink()
                target.rmdir()
        except OSError as exc:
            problems.append(f"could not remove the empty failed archive target: {exc}")
    if not problems and anchor_path is not None and anchor_path.exists():
        try:
            if mutation_guard is not None:
                mutation_guard.remove_anchor()
            else:
                anchor_path.unlink()
        except OSError as exc:
            problems.append(f"could not remove newly created archive anchor: {exc}")
    if not problems and archived_created and archived_parent is not None and archived_parent.exists():
        try:
            if mutation_guard is not None:
                mutation_guard.remove_archived_parent()
            else:
                archived_parent.rmdir()
        except OSError as exc:
            problems.append(f"could not remove newly created archive parent: {exc}")
    if mutation_guard is not None:
        mutation_guard.close()
    return problems


def recover_archive(root: Path, target: Path | None = None) -> int:
    """Recover an interrupted archive transaction safely and idempotently.

    A journal is written before the first move and after every move.  Recovery
    only reverses a destination when its source is still absent; if both sides
    exist or either side has been replaced, it preserves the data and returns
    a non-zero result for manual recovery.  A fully committed transaction only
    needs its stale journal removed.
    """

    root = root.resolve()
    archived = root / GOAL_DIR / "archived"
    if target is not None:
        candidates = [target.resolve()]
    elif archived.is_dir():
        candidates = sorted(
            path for path in archived.iterdir()
            if path.is_dir() and (path / ARCHIVE_JOURNAL_NAME).is_file()
        )
    else:
        candidates = []
    if not candidates:
        return 0
    failures = 0
    for current_target in candidates:
        journal_path = current_target / ARCHIVE_JOURNAL_NAME
        if not journal_path.exists() and not current_target.exists():
            # A prior recovery already completed the transaction.  Recovery
            # is intentionally idempotent and treats the absent target as a
            # successful no-op.
            continue
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            if not isinstance(journal, dict) or journal.get("protocol") != ARCHIVE_JOURNAL_PROTOCOL:
                raise ValueError("archive transaction journal protocol is invalid")
            archive_rel = journal.get("archive_path")
            if not _canonical_repo_path(archive_rel, prefix="docs/goal/archived/"):
                raise ValueError("archive transaction journal path is not canonical")
            if (root / archive_rel).resolve() != current_target:
                raise ValueError("archive transaction journal target does not match")
            moves = journal.get("moves")
            if not isinstance(moves, list) or not moves:
                raise ValueError("archive transaction journal moves are missing")
            receipt_value: dict[str, object] | None = None
            receipt_path = current_target / ARCHIVE_RECEIPT_NAME
            if receipt_path.exists():
                receipt_value = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt_errors = validate_archive_receipt(receipt_value)
                if receipt_errors:
                    raise ValueError(
                        "archive transaction receipt is invalid: " + "; ".join(receipt_errors)
                    )
            move_errors = _validate_archive_transaction_moves(
                archive_rel,
                moves,
                receipt=receipt_value,
            )
            if move_errors:
                raise ValueError("; ".join(move_errors))
            move_paths: list[Path] = []
            for item in moves:
                move_paths.append(Path(str(item["source"])))
            anchor_value = journal.get("anchor_path")
            anchor_candidate = None
            if isinstance(anchor_value, str) and anchor_value:
                anchor_candidate = _canonical_external_path(
                    anchor_value,
                    root=root,
                    label="archive transaction anchor_path",
                )
            guard = _ArchiveMutationGuard(
                root,
                move_paths,
                current_target,
                anchor_candidate,
            )
            guard.bind_existing_target()
            phase = journal.get("phase")
            if phase == "documents_written":
                guard.remove_journal()
                guard.close()
                continue
            conflict = False
            for item in moves:
                source_path = root / str(item["source"])
                destination_path = root / str(item["destination"])
                source_exists = source_path.exists()
                destination_exists = destination_path.exists()
                if source_exists and destination_exists:
                    conflict = True
                    print(
                        f"recovery preserved conflicting archive paths: {source_path} and {destination_path}",
                        file=sys.stderr,
                    )
                elif not source_exists and destination_exists:
                    guard.move(destination_path, source_path)
                elif not source_exists and not destination_exists:
                    conflict = True
                    print(
                        f"recovery cannot locate either side of archive move: {source_path}",
                        file=sys.stderr,
                    )
            if conflict:
                failures += 1
                guard.close()
                continue
            guard.remove_target()
            if anchor_candidate is not None:
                guard.remove_anchor()
            guard.remove_archived_parent()
            guard.close()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failures += 1
            print(f"archive recovery failed for {current_target}: {exc}", file=sys.stderr)
    return 1 if failures else 0


def archive(
    root: Path,
    *,
    slug: str,
    apply: bool,
    stamp: str | None = None,
    expected_main: str | None = None,
    main_ref: str | None = None,
    anchor_out: Path | None = None,
) -> int:
    root = root.resolve()
    try:
        reject_object_substitution(root)
    except GitMetadataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    run_path = root / GOAL_DIR / "RUN.md"
    if not run_path.is_file():
        print(f"error: {run_path} does not exist", file=sys.stderr)
        return 1
    try:
        run = load_run(run_path)
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        print(f"error: cannot read RUN manifest: {exc}", file=sys.stderr)
        return 1

    problems = _completed_run_ok(run)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    moves, missing_required = plan_moves(root)
    if missing_required:
        for name in missing_required:
            print(f"error: required coordination file missing: {name}", file=sys.stderr)
        return 1
    if not moves:
        print("error: nothing to archive", file=sys.stderr)
        return 1

    try:
        plan = load_plan(root / GOAL_DIR / "PLAN.md")
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        print(f"error: cannot read PLAN manifest: {exc}", file=sys.stderr)
        return 1
    validation_errors = validate_current_plan_run(plan, run, repo_root=root)
    if validation_errors:
        print(
            "error: run validation failed; fix RUN/PLAN before archival:",
            file=sys.stderr,
        )
        for error in validation_errors[:5]:
            print(f"error: {error}", file=sys.stderr)
        return 1

    if stamp is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    elif not re.fullmatch(r"\d{8}-\d{6}", stamp):
        print(
            f"error: --stamp {stamp!r} must look like YYYYMMDD-HHMMSS",
            file=sys.stderr,
        )
        return 2
    target = root / GOAL_DIR / "archived" / f"{stamp}-{_slugify(slug)}"
    if target.exists():
        print(
            f"error: archive target already exists: {target}", file=sys.stderr
        )
        return 1
    preflight_problems = _preflight_archive_paths(root, moves, target)
    if preflight_problems:
        for problem in preflight_problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    live_head_problems = (
        _live_head_problems(run, root, expected_main, main_ref, moves)
        if apply
        else []
    )
    if live_head_problems:
        for problem in live_head_problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    requires_anchor = archive_first_required(run)
    anchor_path: Path | None = None
    if anchor_out is not None:
        try:
            anchor_path = _canonical_external_path(anchor_out, root=root, label="anchor-out")
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if anchor_path.exists():
            print(f"error: archive anchor path already exists: {anchor_path}", file=sys.stderr)
            return 1
    if requires_anchor and anchor_path is None:
        print("error: --anchor-out is required for Harness 0.38 archive-first archival", file=sys.stderr)
        return 1

    print(f"archive target: {target.relative_to(root).as_posix()}")
    for source in moves:
        print(f"move: {source.as_posix()}")
    print(
        f"create: {(target / ARCHIVE_RECEIPT_NAME).relative_to(root).as_posix()} "
        "(closed ARCHIVE_RECEIPT)"
    )
    if anchor_path is not None:
        print(f"create: {anchor_path} (closed ARCHIVE_ANCHOR)")
    print(f"documents row: {DOCUMENTS_ROW}")
    if not apply:
        print("dry run only; pass --apply to move these exact paths")
        return 0

    documents_path = root / DOCUMENTS_PATH
    documents_snapshot: bytes | None = None
    documents_initial_identity: tuple[int, int, int] | None = None
    global _LAST_DOCUMENT_WRITE_STATE
    _LAST_DOCUMENT_WRITE_STATE = None
    moved: list[tuple[Path, Path]] = []
    mutation_guard: _ArchiveMutationGuard | None = None
    try:
        mutation_guard = _ArchiveMutationGuard(root, moves, target, anchor_path)
    except Exception as exc:  # noqa: BLE001 - fail closed before any mutation
        print(f"error: archive filesystem identity guard failed: {exc}", file=sys.stderr)
        return 1
    # Capture DOCUMENTS only after the transaction-wide lock is held.  Every
    # compliant writer therefore serializes on this same destination token.
    documents_initial_identity = _safe_documents_identity(root, documents_path)
    documents_snapshot = (
        documents_path.read_bytes() if documents_initial_identity is not None else None
    )
    # The first preflight was only a snapshot.  Re-read branch, HEAD, main,
    # ancestry, and cleanliness while directory identities are held and just
    # before any anchor/target write.  A concurrent ref update therefore fails
    # closed instead of producing a stale archive receipt.
    final_live_head_problems = _live_head_problems(
        run, root, expected_main, main_ref, moves
    )
    if final_live_head_problems:
        for problem in final_live_head_problems:
            print(f"error: {problem}", file=sys.stderr)
        try:
            mutation_guard.remove_archived_parent()
        except OSError:
            pass
        mutation_guard.close()
        return 1
    anchor_nonce = secrets.token_hex(32) if anchor_path is not None else None
    try:
        archive_receipt = _build_archive_receipt(
            root, plan, run, moves, target,
            expected_main=expected_main,
            main_ref=main_ref,
            stamp=stamp,
            anchor_path=anchor_path,
            anchor_nonce=anchor_nonce,
        )
    except Exception as exc:  # noqa: BLE001 - fail closed before any mutation
        print(f"error: cannot build archive receipt: {exc}", file=sys.stderr)
        try:
            mutation_guard.remove_archived_parent()
        except OSError:
            pass
        mutation_guard.close()
        return 1
    receipt_errors = validate_archive_receipt(archive_receipt)
    if receipt_errors:
        for problem in receipt_errors:
            print(f"error: {problem}", file=sys.stderr)
        try:
            mutation_guard.remove_archived_parent()
        except OSError:
            pass
        mutation_guard.close()
        return 1
    try:
        archive_anchor = (
            _build_archive_anchor(root, archive_receipt, anchor_path=anchor_path, nonce=anchor_nonce)
            if anchor_path is not None and anchor_nonce is not None
            else None
        )
    except Exception as exc:  # noqa: BLE001 - fail closed before any mutation
        print(f"error: cannot build archive anchor: {exc}", file=sys.stderr)
        try:
            mutation_guard.remove_archived_parent()
        except OSError:
            pass
        mutation_guard.close()
        return 1
    if archive_anchor is not None:
        anchor_errors = validate_archive_anchor(archive_anchor, root=root)
        if anchor_errors:
            for problem in anchor_errors:
                print(f"error: {problem}", file=sys.stderr)
            try:
                mutation_guard.remove_archived_parent()
            except OSError:
                pass
            mutation_guard.close()
            return 1
    anchor_created = False
    journal = {
        "protocol": ARCHIVE_JOURNAL_PROTOCOL,
        "phase": "prepared",
        "archive_path": target.relative_to(root).as_posix(),
        "moves": [
            {
                "source": source.as_posix(),
                "destination": (target / source.name).relative_to(root).as_posix(),
            }
            for source in moves
        ],
        "moved": [],
        "documents_before_b64": base64.b64encode(documents_snapshot or b"").decode("ascii")
        if documents_snapshot is not None
        else None,
        "documents_before_identity": documents_initial_identity,
        "archived_parent_created": mutation_guard.archived_created,
        "anchor_path": str(anchor_path) if anchor_path is not None else None,
    }
    try:
        mutation_guard.create_target()
        mutation_guard.write_journal(journal)
        journal["phase"] = "receipt_pending"
        mutation_guard.write_journal(journal)
        mutation_guard.write_receipt(root, archive_receipt)
        journal["phase"] = "receipt_written"
        mutation_guard.write_journal(journal)
        if archive_anchor is not None and anchor_path is not None:
            mutation_guard.write_anchor(archive_anchor)
            anchor_created = True
        for source in moves:
            source_path = root / source
            destination_path = target / source.name
            mutation_guard.move(source_path, destination_path)
            moved.append((source_path, destination_path))
            # Re-scan the renamed tree after the descriptor-bound move.  POSIX
            # cannot lock descendants against every concurrent mutation; a
            # newly introduced nested link therefore fails closed and leaves
            # the archive copy for explicit recovery.
            mutation_guard._reject_tree_reparse(destination_path)
            journal["moved"] = [
                {"source": item[0].relative_to(root).as_posix(), "destination": item[1].relative_to(root).as_posix()}
                for item in moved
            ]
            journal["phase"] = "moving"
            mutation_guard.write_journal(journal)
        _update_documents(root)
        journal["phase"] = "documents_written"
        journal["documents_after_b64"] = base64.b64encode(
            _documents_after_bytes(documents_snapshot) or b""
        ).decode("ascii") if documents_snapshot is not None else None
        journal["documents_after_identity"] = (
            _LAST_DOCUMENT_WRITE_STATE.get("identity")
            if _LAST_DOCUMENT_WRITE_STATE is not None
            else None
        )
        mutation_guard.write_journal(journal)
        mutation_guard.remove_journal()
    except Exception as exc:  # noqa: BLE001 - every apply failure must roll back
        print(f"error: archival failed: {exc}", file=sys.stderr)
        rollback_problems = _rollback_archive(
            root, moved, documents_snapshot, target,
            anchor_path if anchor_created else None,
            mutation_guard,
            _LAST_DOCUMENT_WRITE_STATE,
        )
        if rollback_problems:
            for problem in rollback_problems:
                print(f"error: {problem}", file=sys.stderr)
        else:
            print(
                "rolled back every moved entry after the failure",
                file=sys.stderr,
            )
        mutation_guard.close()
        return 1

    mutation_guard.close()

    print(f"archived {len(moves)} entries; never deleted anything")
    return 0


def _update_documents(root: Path) -> None:
    if _ACTIVE_DOCUMENT_LOCK is None:
        lock = _DocumentLock(root)
        lock.acquire()
        try:
            return _update_documents(root)
        finally:
            lock.release()
    global _LAST_DOCUMENT_WRITE_STATE
    _LAST_DOCUMENT_WRITE_STATE = None
    documents = root / DOCUMENTS_PATH
    if not documents.exists():
        print(f"note: {DOCUMENTS_PATH.as_posix()} absent; row not recorded")
        return
    _safe_documents_identity(root, documents)
    before = documents.read_bytes()
    after = _documents_after_bytes(before)
    if after == before:
        return
    identity = _atomic_write_documents(
        root,
        documents,
        after or b"",
        expected_bytes=before,
    )
    _LAST_DOCUMENT_WRITE_STATE = {"identity": identity, "bytes": after or b""}
    print(f"documents row recorded in {DOCUMENTS_PATH.as_posix()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="target repository root (default: current directory)",
    )
    parser.add_argument(
        "--slug",
        help="initiative slug for the archive directory name "
        "(default: the run id)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the listed moves; default is a dry run",
    )
    parser.add_argument(
        "--stamp",
        help="pin the archive directory timestamp as YYYYMMDD-HHMMSS "
        "(default: now; deterministic re-runs and tests)",
    )
    parser.add_argument(
        "--expected-main",
        help="full current main SHA read back immediately before pre-promotion archival; "
        "required with --apply",
    )
    parser.add_argument(
        "--main-ref",
        help="fully qualified local or remote-tracking main ref whose current value "
        "must equal --expected-main; required with --apply",
    )
    parser.add_argument(
        "--anchor-out",
        type=Path,
        help="external absolute path for the closed ARCHIVE_ANCHOR; required for Harness 0.38 apply",
    )
    parser.add_argument(
        "--recover",
        type=Path,
        help="recover one interrupted archive target from its transaction journal; no new archive is created",
    )
    args = parser.parse_args(argv)
    if args.recover is not None:
        recovery_target = args.recover
        if not recovery_target.is_absolute():
            recovery_target = args.repo_root / recovery_target
        return recover_archive(args.repo_root, recovery_target)
    run_path = args.repo_root / GOAL_DIR / "RUN.md"
    slug = args.slug
    if slug is None:
        try:
            slug = str(load_run(run_path).get("run_id") or "run")
        except Exception:  # noqa: BLE001 - slug falls back below
            slug = "run"
    return archive(
        args.repo_root,
        slug=slug,
        apply=args.apply,
        stamp=args.stamp,
        expected_main=args.expected_main,
        main_ref=args.main_ref,
        anchor_out=args.anchor_out,
    )


if __name__ == "__main__":
    raise SystemExit(main())
