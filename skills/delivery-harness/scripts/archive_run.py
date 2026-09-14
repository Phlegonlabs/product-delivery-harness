#!/usr/bin/env python3
"""Archive a completed run's coordination set under docs/goal/archived/.

The script refuses anything but a completed run whose PLAN/RUN pair
passes full manifest validation with every final gate PASS, lists every
exact move first (dry run by default), and moves — never deletes — the
coordination set into one timestamped archive directory. It performs no
Git operations; committing the archival stays with the parent under its
ordinary create_local_commits authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import load_plan, load_run  # noqa: E402
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
ARCHIVE_ANCHOR_PROTOCOL = "harness-archive-anchor-v1"
ARCHIVE_ANCHOR_KEYS = {
    "protocol", "anchor_path", "anchor_path_sha256", "anchor_nonce", "receipt_sha256",
    "run_id", "plan_id", "plan_revision", "plan_digest_sha256", "candidate_c",
    "branch", "branch_ref", "expected_main", "main_ref", "stamp", "archive_path",
    "source_inventory", "moves_sha256", "anchor_sha256", "created_at",
}


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


def _git_filtered_bytes(
    root: Path,
    destination: Path,
    *,
    source: Path | None = None,
    value: bytes | None = None,
) -> bytes:
    """Read the exact Git blob bytes after destination-path filters apply."""

    destination_arg = destination.relative_to(root).as_posix() if destination.is_absolute() else destination.as_posix()
    command = ["git", "hash-object", "-w", f"--path={destination_arg}"]
    if source is not None:
        command.extend(["--", str(source)])
        hashed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=10)
    else:
        command.append("--stdin")
        hashed = subprocess.run(command, cwd=root, input=value or b"", capture_output=True, text=False, timeout=10)
    if hashed.returncode != 0:
        raise OSError(hashed.stderr.strip() if isinstance(hashed.stderr, str) else "git hash-object failed")
    oid = hashed.stdout.strip() if isinstance(hashed.stdout, str) else bytes(hashed.stdout).decode("ascii").strip()
    blob = subprocess.run(["git", "cat-file", "blob", oid], cwd=root, capture_output=True, text=False, timeout=10)
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
        if source_path.is_file():
            files = [source_path]
        elif source_path.is_dir():
            files = sorted(path for path in source_path.rglob("*") if path.is_file())
        else:
            archived_source = target / source.name
            if archived_source.is_file():
                files = [archived_source]
            elif archived_source.is_dir():
                files = sorted(path for path in archived_source.rglob("*") if path.is_file())
            else:
                files = []
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
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, sort_keys=True, indent=2, ensure_ascii=False)
        handle.write("\n")


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
    if not isinstance(archive_path, str) or archive_path != archive_path.replace("\\", "/") or archive_path.startswith("/") or ".." in archive_path.split("/") or not archive_path.startswith("docs/goal/archived/"):
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
            valid_source = isinstance(source, str) and source == source.strip() and source == source.replace("\\", "/") and not source.startswith("/") and ".." not in source.split("/") and (source in {"docs/goal/PLAN.md", "docs/goal/RUN.md"} or source in allowed_optional or source.startswith("docs/goal/evidence/"))
            valid_destination = isinstance(destination, str) and destination == destination.strip() and destination == destination.replace("\\", "/") and destination.startswith(f"{archive_path}/") and ".." not in destination.split("/")
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
    if not isinstance(created, str) or not created.endswith("Z"):
        errors.append("archive anchor created_at is invalid")
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


def _write_closed_anchor(path: Path, anchor: dict[str, object], root: Path) -> None:
    if path.resolve().is_relative_to(root.resolve()):
        raise ValueError("archive anchor must be outside checkout")
    if path.exists():
        raise FileExistsError("archive anchor path already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(anchor, handle, sort_keys=True, indent=2, ensure_ascii=False)
        handle.write("\n")


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
        if (root / source).exists():
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
    if target.exists():
        problems.append(f"archive target already exists: {target}")
    if target.parent.exists() and not target.parent.is_dir():
        problems.append(
            f"archive destination parent is not a directory: {target.parent}"
        )

    destinations: set[Path] = set()
    for source in moves:
        source_path = root / source
        resolved_source = _resolved_inside(root, source_path)
        if resolved_source is None:
            problems.append(f"source resolves outside the repository root: {source}")
            continue
        if not source_path.exists():
            # plan_moves reports required files; optional paths may be absent.
            continue
        destination = resolved_target / source.name
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
    if documents.exists() and not documents.is_file():
        problems.append(f"documents destination is not a file: {DOCUMENTS_PATH}")
    resolved_documents = _resolved_inside(root, documents)
    if documents.exists() and resolved_documents is None:
        problems.append(
            f"documents destination resolves outside the repository root: {DOCUMENTS_PATH}"
        )
    return problems


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
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


def _rollback_archive(
    root: Path,
    moved: list[tuple[Path, Path]],
    documents_snapshot: bytes | None,
    target: Path,
    anchor_path: Path | None = None,
) -> list[str]:
    """Restore the pre-archive layout; retain archive copies only if a restore fails."""

    problems: list[str] = []
    documents_path = root / DOCUMENTS_PATH
    if documents_snapshot is not None:
        try:
            documents_path.write_bytes(documents_snapshot)
        except OSError as exc:
            problems.append(
                f"could not restore {DOCUMENTS_PATH.as_posix()}: {exc}; "
                "the original bytes were not replaced"
            )
    elif documents_path.exists():
        try:
            if documents_path.is_file():
                documents_path.unlink()
            else:
                problems.append(
                    f"cannot remove newly created {DOCUMENTS_PATH.as_posix()}: "
                    "the path is no longer a file"
                )
        except OSError as exc:
            problems.append(
                f"could not remove newly created {DOCUMENTS_PATH.as_posix()}: {exc}"
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
                shutil.move(str(destination), str(source))
        except OSError as exc:
            problems.append(
                f"could not restore {source.as_posix()}; recoverable copy retained at "
                f"{destination}: {exc}"
            )
    if not problems and target.exists():
        try:
            receipt_path = target / ARCHIVE_RECEIPT_NAME
            if receipt_path.exists():
                receipt_path.unlink()
            target.rmdir()
        except OSError as exc:
            problems.append(f"could not remove the empty failed archive target: {exc}")
    if not problems and target.parent.exists():
        try:
            target.parent.rmdir()
        except OSError:
            # A non-empty parent may retain unrelated archives; only the empty
            # directory chain created for this failed attempt is safe to undo.
            pass
    if not problems and anchor_path is not None and anchor_path.exists():
        try:
            anchor_path.unlink()
        except OSError as exc:
            problems.append(f"could not remove newly created archive anchor: {exc}")
    return problems


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
    documents_snapshot = (
        documents_path.read_bytes() if documents_path.is_file() else None
    )
    moved: list[tuple[Path, Path]] = []
    anchor_nonce = secrets.token_hex(32) if anchor_path is not None else None
    archive_receipt = _build_archive_receipt(
        root, plan, run, moves, target,
        expected_main=expected_main,
        main_ref=main_ref,
        stamp=stamp,
        anchor_path=anchor_path,
        anchor_nonce=anchor_nonce,
    )
    receipt_errors = validate_archive_receipt(archive_receipt)
    if receipt_errors:
        for problem in receipt_errors:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    archive_anchor = (
        _build_archive_anchor(root, archive_receipt, anchor_path=anchor_path, nonce=anchor_nonce)
        if anchor_path is not None and anchor_nonce is not None
        else None
    )
    if archive_anchor is not None:
        anchor_errors = validate_archive_anchor(archive_anchor, root=root)
        if anchor_errors:
            for problem in anchor_errors:
                print(f"error: {problem}", file=sys.stderr)
            return 1
    anchor_created = False
    try:
        if archive_anchor is not None and anchor_path is not None:
            _write_closed_anchor(anchor_path, archive_anchor, root)
            anchor_created = True
        target.mkdir(parents=True)
        _write_archive_receipt(target / ARCHIVE_RECEIPT_NAME, archive_receipt)
        for source in moves:
            source_path = root / source
            destination_path = target / source.name
            _move_entry(source_path, destination_path)
            moved.append((source_path, destination_path))
        _update_documents(root)
    except Exception as exc:  # noqa: BLE001 - every apply failure must roll back
        print(f"error: archival failed: {exc}", file=sys.stderr)
        rollback_problems = _rollback_archive(
            root, moved, documents_snapshot, target,
            anchor_path if anchor_created else None,
        )
        if rollback_problems:
            for problem in rollback_problems:
                print(f"error: {problem}", file=sys.stderr)
        else:
            print(
                "rolled back every moved entry after the failure",
                file=sys.stderr,
            )
        return 1

    print(f"archived {len(moves)} entries; never deleted anything")
    return 0


def _update_documents(root: Path) -> None:
    documents = root / DOCUMENTS_PATH
    if not documents.is_file():
        print(f"note: {DOCUMENTS_PATH.as_posix()} absent; row not recorded")
        return
    before = documents.read_bytes()
    after = _documents_after_bytes(before)
    if after == before:
        return
    documents.write_bytes(after or b"")
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
        anchor_out=args.anchor_out,
    )


if __name__ == "__main__":
    raise SystemExit(main())
