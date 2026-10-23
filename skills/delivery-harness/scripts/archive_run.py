#!/usr/bin/env python3
"""Archive a completed run's coordination set under docs/goal/archived/.

The script refuses anything but a completed run whose PLAN/RUN pair
passes full manifest validation with every final gate PASS, lists every
exact move first (dry run by default), and moves — never deletes — the
coordination set into one timestamped archive directory with a closed
ARCHIVE_RECEIPT.json. It performs no Git ref or commit writes; hardened Git
metadata/blob reads stay read-only from the parent's perspective, and
committing the archival remains with the parent under its ordinary
create_local_commits authorization. A failed apply preserves every remaining
source and moved entry for parent-led recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import ManifestError, load_plan, load_run  # noqa: E402
from harness_git import (  # noqa: E402
    GitMetadataError,
    git_environment,
    git_executable,
    reject_object_substitution,
    run_git,
)
from harness_manifest import plan_digest  # noqa: E402
from harness_manifest import validate_current_plan_run  # noqa: E402

GOAL_DIR = Path("docs/goal")
REQUIRED_FILES = ("PLAN.md", "RUN.md")
OPTIONAL_FILES = ("DECISIONS.md", "REFINEMENT_BACKLOG.md")
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
    "receipt_sha256",
}
# Receipts archived before 0.66 also name an external anchor. They stay valid;
# new receipts omit these keys.
ARCHIVE_RECEIPT_LEGACY_ANCHOR_KEYS = {"anchor_path", "anchor_path_sha256", "anchor_nonce"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")


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
    path.  ``scandir`` plus ``lstat`` gives every component a no-follow check.
    Empty directories are deliberately not represented in the receipt; the
    archive contract moves only regular files.
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
        with os.scandir(current) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
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
    return sorted(result, key=lambda item: item.as_posix())


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
        if _is_reparse(info):
            return current, "reparse point"
    return None


def _check_documents_path(root: Path, documents: Path) -> None:
    """Refuse a DOCUMENTS path that is linked or not a regular file."""

    link = _link_component(root, documents)
    if link is not None:
        component, kind = link
        raise OSError(
            f"{DOCUMENTS_PATH.as_posix()} contains unsafe {kind} component: {component}"
        )
    try:
        info = os.lstat(documents)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(info.st_mode):
        raise OSError(f"{DOCUMENTS_PATH.as_posix()} is not a regular file")


def _write_documents(documents: Path, value: bytes, *, expected: bytes) -> None:
    """Preserve displaced owner bytes if DOCUMENTS changes at replacement."""
    from document_write import replace_existing_bytes

    replace_existing_bytes(documents, value, expected)


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
        for path in _inventory_tree(source_path):
            relative = path.relative_to(source_path).as_posix() if source_path.is_dir() else None
            destination = target / source.name
            if relative is not None:
                destination = destination / relative
            entries.append({
                "source": (source / relative).as_posix() if relative is not None else source.as_posix(),
                "destination": destination.relative_to(root).as_posix(),
                "type": "file",
                "sha256": _sha256_bytes(_git_filtered_bytes(root, destination, source=path)),
            })
    return sorted(entries, key=lambda item: (str(item["source"]), str(item["destination"])))


def _receipt_digest(receipt: dict[str, object]) -> str:
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return _sha256_bytes(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


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
) -> dict[str, object]:
    integration = run.get("integration") if isinstance(run.get("integration"), dict) else {}
    branch = _canonical_branch(integration.get("branch"))
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
        "candidate_c": integration.get("integration_head_sha"),
        "branch": branch,
        "branch_ref": _branch_ref(branch),
        "expected_main": expected_main,
        "main_ref": main_ref,
        "stamp": stamp,
        "archive_path": target.relative_to(root).as_posix(),
        "moves": _archive_file_moves(root, moves, target),
        "documents_before_sha256": _sha256_bytes(before_for_git) if before_for_git is not None else None,
        "documents_after_sha256": _sha256_bytes(after_for_git) if after_for_git is not None else None,
    }
    receipt["receipt_sha256"] = _receipt_digest(receipt)
    return receipt


def _write_archive_receipt(path: Path, receipt: dict[str, object]) -> None:
    if set(receipt) != ARCHIVE_RECEIPT_KEYS:
        raise RuntimeError("archive receipt has an invalid schema")
    payload = (json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def validate_archive_receipt(receipt: object) -> list[str]:
    """Validate the closed receipt shape without consulting Git.

    The push helper calls this before preparing a handoff.  Keep this helper
    deliberately strict: JSON type coercion must never turn a malformed
    receipt into authority.
    """

    errors: list[str] = []
    if not isinstance(receipt, dict):
        return ["archive receipt must be an object"]
    legacy = set(receipt) & ARCHIVE_RECEIPT_LEGACY_ANCHOR_KEYS
    if legacy not in (set(), ARCHIVE_RECEIPT_LEGACY_ANCHOR_KEYS) or set(receipt) - legacy != ARCHIVE_RECEIPT_KEYS:
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
        if value is not None and (not isinstance(value, str) or SHA256_RE.fullmatch(value) is None):
            errors.append(f"archive receipt {key} must be lowercase SHA-256 or null")
    value = receipt.get("candidate_c")
    if not isinstance(value, str) or FULL_SHA_RE.fullmatch(value) is None:
        errors.append("archive receipt candidate_c must be a lowercase full Git SHA")
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
            if move.get("type") != "file":
                errors.append(f"archive receipt moves[{index}] type must be file")
            if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
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
    if not isinstance(receipt.get("receipt_sha256"), str) or SHA256_RE.fullmatch(str(receipt.get("receipt_sha256"))) is None:
        errors.append("archive receipt receipt_sha256 is invalid")
    elif receipt["receipt_sha256"] != _receipt_digest(receipt):
        errors.append("archive receipt digest mismatch")
    return errors


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
                # Keep unsafe trees in the move list so preflight emits the
                # precise symlink/reparse or non-regular finding.
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
        if _resolved_inside(root, source_path) is None:
            problems.append(f"source resolves outside the repository root: {source}")
            continue
        if not source_path.exists():
            # plan_moves reports required files; optional paths may be absent.
            continue
        try:
            _inventory_tree(source_path)
        except OSError as exc:
            problems.append(str(exc))
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
            _check_documents_path(root, documents)
        except OSError as exc:
            problems.append(str(exc))
        if _resolved_inside(root, documents) is None:
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
    plan: dict[str, object] | None = None,
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

    from branch_policy import archive_ancestry_base

    try:
        ancestry_base = archive_ancestry_base(plan, run, expected_main)
    except ManifestError as exc:
        return [*problems, str(exc)]
    ancestry = _git(root, "merge-base", "--is-ancestor", ancestry_base, live_head)
    if ancestry is None:
        problems.append("could not verify live HEAD ancestry")
    elif ancestry.returncode != 0:
        problems.append(
            f"live HEAD {live_head} does not descend from archive base {ancestry_base}"
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


def archive(
    root: Path,
    *,
    slug: str,
    apply: bool,
    stamp: str | None = None,
    expected_main: str | None = None,
    main_ref: str | None = None,
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
        _live_head_problems(run, root, expected_main, main_ref, moves, plan)
        if apply
        else []
    )
    if live_head_problems:
        for problem in live_head_problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    print(f"archive target: {target.relative_to(root).as_posix()}")
    for source in moves:
        print(f"move: {source.as_posix()}")
    print(
        f"create: {(target / ARCHIVE_RECEIPT_NAME).relative_to(root).as_posix()} "
        "(closed ARCHIVE_RECEIPT)"
    )
    print(f"documents row: {DOCUMENTS_ROW}")
    if not apply:
        print("dry run only; pass --apply to move these exact paths")
        return 0

    try:
        archive_receipt = _build_archive_receipt(
            root, plan, run, moves, target,
            expected_main=expected_main,
            main_ref=main_ref,
            stamp=stamp,
        )
    except Exception as exc:  # noqa: BLE001 - fail closed before any mutation
        print(f"error: cannot build archive receipt: {exc}", file=sys.stderr)
        return 1
    receipt_errors = validate_archive_receipt(archive_receipt)
    if receipt_errors:
        for problem in receipt_errors:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()
        _write_archive_receipt(target / ARCHIVE_RECEIPT_NAME, archive_receipt)
        for source in moves:
            destination = target / source.name
            _move_entry(root / source, destination)
            # A link introduced while the tree moved fails closed here.
            _inventory_tree(destination)
        _update_documents(root)
    except Exception as exc:  # noqa: BLE001 - preserve partial moves for recovery
        print(f"error: archival failed: {exc}", file=sys.stderr)
        print(
            f"partial archive retained at {target}; inspect sources and destinations "
            "before manual recovery; nothing was deleted",
            file=sys.stderr,
        )
        return 1

    print(f"archived {len(moves)} entries; never deleted anything")
    return 0


def _update_documents(root: Path) -> None:
    documents = root / DOCUMENTS_PATH
    if not documents.exists():
        print(f"note: {DOCUMENTS_PATH.as_posix()} absent; row not recorded")
        return
    _check_documents_path(root, documents)
    before = documents.read_bytes()
    after = _documents_after_bytes(before)
    if after == before:
        return
    _write_documents(documents, after or b"", expected=before)
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
    args = parser.parse_args(argv)
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
    )


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
