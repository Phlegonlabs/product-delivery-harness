#!/usr/bin/env python3
"""Prepare and verify an archive-first exact-SHA publication handoff.

This local tool never invokes ``git push``.  It writes closed immutable
request/attempt records, returns a safe no-force argv for a human or trusted
host, and closes the receipt only after recovery reads back the exact SHA.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_core import ManifestError, extract_json_manifest_text, is_full_sha, plan_digest
from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_schema import PLAN_HEADING, RUN_HEADING, archive_first_required
from harness_manifest import validate_plan, validate_run
from harness_contract_join import validate_frozen_contract_joins
from harness_ui_evidence import validate_ui_evidence_files
from push_integration_branch import _push_url_metadata, _safe_remote, _verify_configured_remote
from archive_run import _documents_after_bytes, validate_archive_receipt
from archive_run import validate_archive_anchor

REQUEST_PROTOCOL = "harness-archive-push-request-v2"
RECEIPT_PROTOCOL = "harness-archive-push-receipt-v2"
ATTEMPT_PROTOCOL = "harness-archive-push-attempt-v1"
LOCAL_AUTHORIZATION_SOURCE = "external-human-or-trusted-host"
LOCAL_AUTHORIZATION_REF = "not-authorized-by-local-executor"
PENDING_TRUSTED_HOST_STATUS = "PENDING_TRUSTED_HOST_PUBLICATION"
REQUEST_KEYS = {
    "protocol", "authorization_source", "authorization_ref", "plan_id", "plan_revision",
    "plan_digest_sha256", "run_id", "run_schema_version", "archive_path", "archive_hashes",
    "moves", "archive_receipt_sha256", "expected_main", "main_ref", "stamp",
    "documents_before_sha256", "documents_after_sha256",
    "anchor_path", "anchor_path_sha256", "anchor_nonce",
    "candidate_c", "candidate_a", "replacement_base", "run_branch", "branch_ref", "remote",
    "push_endpoint_kind", "push_endpoint_summary", "push_url_sha256", "remote_pre_push_head",
    "request_path", "request_path_sha256", "receipt_path", "receipt_path_sha256",
    "execution_nonce", "created_at", "request_sha256", "attempt_path", "attempt_path_sha256",
}
RECEIPT_KEYS = {
    "protocol", "status", "request_sha256", "attempt_path", "attempt_path_sha256", "receipt_path", "receipt_path_sha256",
    "execution_nonce", "candidate_a", "branch_ref", "remote", "push_endpoint_kind",
    "push_endpoint_summary", "push_url_sha256", "remote_pre_push_head", "readback_head_sha",
    "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
    "archive_path", "archive_hashes", "moves", "archive_receipt_sha256", "candidate_c",
    "run_branch", "replacement_base", "expected_main", "main_ref", "stamp", "documents_before_sha256",
    "documents_after_sha256", "receipt_sha256",
    "anchor_path", "anchor_path_sha256", "anchor_nonce",
}
ATTEMPT_KEYS = {
    "protocol", "request_sha256", "attempt_path", "attempt_path_sha256",
    "execution_nonce", "candidate_a", "replacement_base", "branch_ref", "remote", "started_at",
    "push_mode", "push_endpoint_kind", "push_endpoint_summary", "push_url_sha256",
    "remote_pre_push_head", "attempt_sha256",
}
COORDINATION_NAMES = ("PLAN.md", "RUN.md", "DECISIONS.md", "REFINEMENT_BACKLOG.md")
COORDINATION_DIR = Path("docs/goal")
DOCUMENTS_PATH = Path("docs/DOCUMENTS.md")
ARCHIVE_RECEIPT_NAME = "ARCHIVE_RECEIPT.json"
ARCHIVE_RECEIPT_PROTOCOL = "harness-archive-receipt-v1"
ARCHIVE_RECEIPT_KEYS = {
    "protocol", "run_id", "plan_id", "plan_revision", "plan_digest_sha256", "candidate_c",
    "branch", "branch_ref", "expected_main", "main_ref", "stamp", "archive_path", "moves",
    "documents_before_sha256", "documents_after_sha256", "receipt_sha256",
}


def _git(root: Path, *args: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return run_git(root, *args, capture_output=True, text=text, timeout=30, check=False)


def _out(root: Path, *args: str) -> str:
    result = _git(root, *args)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _path_digest(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()


def _require_sha(value: object, *, length: int = 40, label: str = "SHA") -> None:
    if not isinstance(value, str) or len(value) != length or any(char not in "0123456789abcdef" for char in value):
        raise ManifestError(f"{label} must be lowercase hexadecimal SHA-{length * 4}")


def _require_nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ManifestError(f"{label} must be a non-empty exact string")
    return value


def _canonical_external_path(value: object, *, label: str, root: Path) -> str:
    if isinstance(value, Path):
        value = str(value)
    raw = _require_nonempty(value, label)
    resolved = Path(raw).resolve(strict=False)
    if raw != str(resolved):
        raise ManifestError(f"{label} must be a canonical absolute path")
    if resolved.is_relative_to(root.resolve()):
        raise ManifestError(f"{label} must live outside the reviewed checkout")
    return raw


def _validate_timestamp(value: object, label: str) -> None:
    if not isinstance(value, str) or value != value.strip() or not value.endswith("Z"):
        raise ManifestError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ManifestError(f"{label} must be an RFC3339 UTC timestamp") from exc


def _validate_endpoint(metadata: dict[str, Any]) -> None:
    _require_nonempty(metadata.get("push_endpoint_kind"), "push_endpoint_kind")
    _require_nonempty(metadata.get("push_endpoint_summary"), "push_endpoint_summary")
    _require_sha(metadata.get("push_url_sha256"), length=64, label="push_url_sha256")


def _validate_archive_authority(authority: dict[str, Any]) -> None:
    for key in ("plan_id", "run_id", "archive_path", "run_branch", "branch_ref", "candidate_c", "candidate_a"):
        _require_nonempty(authority.get(key), key)
    _require_sha(authority["plan_digest_sha256"], length=64, label="plan_digest_sha256")
    _require_sha(authority["candidate_c"], label="candidate_c")
    _require_sha(authority["candidate_a"], label="candidate_a")
    replacement_base = authority.get("replacement_base")
    if replacement_base is not None:
        _require_sha(replacement_base, label="replacement_base")
        if replacement_base in {authority["candidate_c"], authority["candidate_a"]}:
            raise ManifestError("replacement_base must identify the prior candidate, not C or A")
    branch = _canonical_branch(authority["run_branch"])
    if branch is None or _protected_branch(branch) or authority["branch_ref"] != f"refs/heads/{branch}":
        raise ManifestError("archive branch/ref is not canonical or is protected")
    if not _canonical_archive_path(authority["archive_path"]):
        raise ManifestError("archive_path is not canonical")
    if not isinstance(authority.get("run_schema_version"), int) or isinstance(authority.get("run_schema_version"), bool):
        raise ManifestError("run_schema_version must be an integer")
    if not isinstance(authority.get("archive_hashes"), dict) or not authority["archive_hashes"]:
        raise ManifestError("archive_hashes must be a non-empty object")
    for path, digest in authority["archive_hashes"].items():
        if not isinstance(path, str) or not path.startswith(authority["archive_path"] + "/"):
            raise ManifestError("archive_hashes contains a path outside archive_path")
        _require_sha(digest, length=64, label=f"archive_hashes[{path}]")
    if not isinstance(authority.get("moves"), list) or not authority["moves"]:
        raise ManifestError("moves must be a non-empty list")
    for move in authority["moves"]:
        if not isinstance(move, dict) or set(move) != {"source", "destination", "type", "sha256"}:
            raise ManifestError("moves contains an invalid row")
        _require_nonempty(move.get("source"), "move.source")
        _require_nonempty(move.get("destination"), "move.destination")
        if move["type"] != "file":
            raise ManifestError("move.type must be file")
        _require_sha(move.get("sha256"), length=64, label="move.sha256")
    receipt_digest = authority.get("archive_receipt_sha256")
    _require_sha(receipt_digest, length=64, label="archive_receipt_sha256")
    stamp = authority.get("stamp")
    if not isinstance(stamp, str) or re.fullmatch(r"\d{8}-\d{6}", stamp) is None:
        raise ManifestError("stamp is invalid")
    for key in ("documents_before_sha256", "documents_after_sha256"):
        value = authority.get(key)
        if value is not None:
            _require_sha(value, length=64, label=key)
    anchor_path = authority.get("anchor_path")
    anchor_nonce = authority.get("anchor_nonce")
    if not isinstance(anchor_path, str) or not Path(anchor_path).is_absolute():
        raise ManifestError("anchor_path must be an absolute external path")
    _require_sha(authority.get("anchor_path_sha256"), length=64, label="anchor_path_sha256")
    if _path_digest(Path(anchor_path)) != authority["anchor_path_sha256"]:
        raise ManifestError("anchor_path_sha256 does not match canonical path")
    if not isinstance(anchor_nonce, str) or re.fullmatch(r"[0-9a-f]{64}", anchor_nonce) is None:
        raise ManifestError("anchor_nonce must be 64 lowercase hex characters")


def _validate_request_values(request: dict[str, Any], root: Path, request_path: Path) -> None:
    if set(request) != REQUEST_KEYS - {"request_sha256"} and set(request) != REQUEST_KEYS:
        raise ManifestError("request has missing or extra fields before digest")
    if request.get("protocol") != REQUEST_PROTOCOL:
        raise ManifestError("request protocol is invalid")
    if request.get("authorization_source") != LOCAL_AUTHORIZATION_SOURCE:
        raise ManifestError(
            "caller-supplied authorization prose/ref cannot authorize archive publication"
        )
    if request.get("authorization_ref") != LOCAL_AUTHORIZATION_REF:
        raise ManifestError(
            "caller-supplied authorization prose/ref cannot authorize archive publication"
        )
    _validate_archive_authority(request)
    _require_nonempty(request.get("remote"), "remote")
    _validate_endpoint(request)
    pre = request.get("remote_pre_push_head")
    if pre is not None:
        _require_sha(pre, label="remote_pre_push_head")
    for key in ("request_path", "attempt_path", "receipt_path"):
        _canonical_external_path(request.get(key), label=key, root=root)
        digest_key = key + "_sha256"
        if request[digest_key] != _path_digest(Path(request[key])):
            raise ManifestError(f"{key} digest does not match canonical path")
    if len({request["request_path"], request["attempt_path"], request["receipt_path"]}) != 3:
        raise ManifestError("request, attempt, and receipt paths must be pairwise distinct")
    if request["request_path"] != str(request_path.resolve()):
        raise ManifestError("request_path does not match the loaded request path")
    _canonical_external_path(request.get("anchor_path"), label="anchor_path", root=root)
    nonce = request.get("execution_nonce")
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{64}", nonce) is None:
        raise ManifestError("execution_nonce must be 64 lowercase hex characters")
    _validate_timestamp(request.get("created_at"), "created_at")


def _root(root: Path) -> Path:
    root = root.resolve()
    if Path(_out(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ManifestError("--repo-root must be the repository root")
    try:
        reject_object_substitution(root)
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    return root


def _blob(root: Path, revision: str, path: str) -> bytes:
    result = _git(root, "show", "--format=", f"{revision}:{path}", text=False)
    if result.returncode != 0:
        raise ManifestError(f"missing immutable Git blob {revision}:{path}")
    return bytes(result.stdout)


def _manifest(root: Path, revision: str, path: str, heading: str, wrapper: str) -> dict[str, Any]:
    payload = extract_json_manifest_text(_blob(root, revision, path).decode("utf-8"), heading, wrapper, source=f"{revision}:{path}")
    return payload if isinstance(payload, dict) else json.loads(payload)


def _archive_rel(root: Path, archive: Path) -> Path:
    try:
        rel = archive.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ManifestError("archive must be inside the repository root") from exc
    if len(rel.parts) != 4 or rel.parts[:3] != ("docs", "goal", "archived"):
        raise ManifestError("archive must be docs/goal/archived/<stamp-run>")
    if any(part in {"", ".", ".."} for part in rel.parts) or any(char in rel.name for char in "\\\0\r\n"):
        raise ManifestError("archive path is not canonical")
    return rel


def _tree_files(root: Path, revision: str, prefix: str) -> dict[str, str]:
    result = _git(root, "ls-tree", "-r", "-z", "--name-only", revision, "--", prefix, text=False)
    if result.returncode != 0:
        raise ManifestError("cannot inspect archived Git tree")
    names = [item.decode("utf-8") for item in bytes(result.stdout).split(b"\0") if item]
    return {name: hashlib.sha256(_blob(root, revision, name)).hexdigest() for name in names}


def _coordination_files(root: Path, revision: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for name in COORDINATION_NAMES:
        path = (COORDINATION_DIR / name).as_posix()
        try:
            files[path] = hashlib.sha256(_blob(root, revision, path)).hexdigest()
        except ManifestError:
            pass
    files.update(_tree_files(root, revision, "docs/goal/evidence"))
    try:
        files["docs/tasks.md"] = hashlib.sha256(_blob(root, revision, "docs/tasks.md")).hexdigest()
    except ManifestError:
        pass
    return files


def _documents_after_archive(value: bytes | None) -> bytes | None:
    return _documents_after_bytes(value)


def _canonical_branch(value: object) -> str | None:
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    branch = value.removeprefix("refs/heads/")
    if not branch or branch.startswith("refs/") or "\\" in branch:
        return None
    if any(part in {"", ".", ".."} for part in branch.split("/")):
        return None
    return branch


def _protected_branch(value: object) -> bool:
    branch = _canonical_branch(value)
    return branch is not None and branch.casefold() in {"main", "master", "development", "default"}


def _canonical_archive_path(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and value == value.replace("\\", "/")
        and value.startswith("docs/goal/archived/")
        and len(Path(value).parts) == 4
        and all(part not in {"", ".", ".."} for part in Path(value).parts)
    )


def _read_receipt(root: Path, revision: str, receipt_path: str) -> dict[str, Any]:
    try:
        value = json.loads(_blob(root, revision, receipt_path).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ManifestError("archive receipt is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ManifestError("archive receipt must be an object")
    errors = validate_archive_receipt(value)
    if errors:
        raise ManifestError("; ".join(errors))
    return value


def _read_archive_anchor(root: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    path_value = receipt.get("anchor_path")
    if not isinstance(path_value, str):
        raise ManifestError("archive receipt is missing external anchor_path")
    anchor_path = Path(path_value).resolve(strict=False)
    if str(anchor_path) != path_value or anchor_path.is_relative_to(root.resolve()):
        raise ManifestError("archive anchor path is not canonical and external")
    if not anchor_path.is_file():
        raise ManifestError("archive anchor file is missing")
    try:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError("archive anchor is not valid JSON") from exc
    errors = validate_archive_anchor(anchor, root=root)
    if errors:
        raise ManifestError("; ".join(errors))
    if anchor.get("anchor_path") != path_value or anchor.get("anchor_path_sha256") != receipt.get("anchor_path_sha256"):
        raise ManifestError("archive anchor path identity does not match receipt")
    if anchor.get("receipt_sha256") != receipt.get("receipt_sha256") or anchor.get("anchor_nonce") != receipt.get("anchor_nonce"):
        raise ManifestError("archive anchor receipt or nonce does not match")
    for key in ("run_id", "plan_id", "plan_revision", "plan_digest_sha256", "candidate_c", "branch", "branch_ref", "expected_main", "main_ref", "stamp", "archive_path"):
        if anchor.get(key) != receipt.get(key):
            raise ManifestError(f"archive anchor authority does not match receipt: {key}")
    if anchor.get("source_inventory") != receipt.get("moves"):
        raise ManifestError("archive anchor source inventory does not match receipt moves")
    moves = receipt.get("moves")
    expected_moves_digest = hashlib.sha256(json.dumps(moves, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if anchor.get("moves_sha256") != expected_moves_digest:
        raise ManifestError("archive anchor moves digest does not match receipt")
    return anchor


def _replacement_base_from_plan(
    root: Path,
    plan: dict[str, Any],
    *,
    branch: str,
    candidate_c: str,
    expected_main: str,
) -> str | None:
    """Resolve an explicit prior archive candidate for a correction RUN."""

    sources = [
        source
        for source in plan.get("sources", [])
        if isinstance(source, dict)
        and " ".join(
            str(source.get("kind", "")).replace("_", " ").split()
        ).casefold()
        == "prior archive candidate"
    ]
    if not sources:
        return None
    if len(sources) != 1:
        raise ManifestError(
            "correction RUN requires exactly one prior archive candidate source"
        )
    source = sources[0]
    revision = source.get("source_revision")
    location = source.get("location")
    content_sha256 = source.get("content_sha256")
    if not is_full_sha(revision):
        raise ManifestError(
            "prior archive candidate source_revision must be exact A"
        )
    if (
        not isinstance(location, str)
        or not _canonical_archive_path(str(Path(location).parent).replace("\\", "/"))
        or Path(location).name != ARCHIVE_RECEIPT_NAME
    ):
        raise ManifestError(
            "prior archive candidate source must name its archived ARCHIVE_RECEIPT.json"
        )
    receipt_bytes = _blob(root, revision, location)
    if (
        not isinstance(content_sha256, str)
        or hashlib.sha256(receipt_bytes).hexdigest() != content_sha256
    ):
        raise ManifestError("prior archive candidate source hash does not match exact A")
    prior_receipt = _read_receipt(root, revision, location)
    _read_archive_anchor(root, prior_receipt)
    if _canonical_branch(prior_receipt.get("branch")) != branch:
        raise ManifestError("prior archive candidate belongs to another run branch")
    if prior_receipt.get("expected_main") != expected_main:
        raise ManifestError("prior archive candidate records another main base")
    parents = _out(root, "rev-list", "--parents", "-n", "1", revision).split()
    if (
        len(parents) != 2
        or parents[1] != prior_receipt.get("candidate_c")
    ):
        raise ManifestError("prior archive candidate is not its receipt-bound archive A")
    if _git(root, "merge-base", "--is-ancestor", revision, candidate_c).returncode != 0:
        raise ManifestError("prior archive candidate is not an ancestor of correction C2")
    return revision


def verify_archive_candidate(root: Path, *, archive_path: Path, candidate_a: str) -> dict[str, Any]:
    """Verify archive-only candidate A using the receipt as byte authority."""

    root = _root(root)
    if not is_full_sha(candidate_a):
        raise ManifestError("candidate A must be a lowercase full Git SHA")
    rel = _archive_rel(root, archive_path)
    branch = _canonical_branch(_out(root, "branch", "--show-current"))
    if branch is None or _protected_branch(branch):
        raise ManifestError("archive candidate requires a named non-protected branch")
    if _out(root, "rev-parse", "HEAD") != candidate_a:
        raise ManifestError("live HEAD is not archive candidate A")
    if _out(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ManifestError("archive candidate checkout must be clean")
    parents = _out(root, "rev-list", "--parents", "-n", "1", candidate_a).split()
    if len(parents) != 2 or not is_full_sha(parents[1]):
        raise ManifestError("archive A must be a direct non-merge child of C")
    candidate_c = parents[1]
    archive_prefix = rel.as_posix()
    receipt_path = f"{archive_prefix}/{ARCHIVE_RECEIPT_NAME}"
    plan_path = f"{archive_prefix}/PLAN.md"
    run_path = f"{archive_prefix}/RUN.md"
    plan = _manifest(root, candidate_a, plan_path, PLAN_HEADING, "harness_plan")
    run = _manifest(root, candidate_a, run_path, RUN_HEADING, "harness_run")
    receipt = _read_receipt(root, candidate_a, receipt_path)
    if archive_first_required(run):
        _read_archive_anchor(root, receipt)

    validation_errors = []
    validation_errors.extend(validate_plan(plan, repo_root=root))
    validation_errors.extend(validate_run(plan, run))
    validation_errors.extend(validate_frozen_contract_joins(plan, root, run=run))
    validation_errors.extend(validate_ui_evidence_files(plan, run, root))
    if validation_errors:
        raise ManifestError("archived PLAN/RUN validation failed: " + "; ".join(validation_errors[:8]))

    integration = run.get("integration")
    if not isinstance(integration, dict):
        raise ManifestError("archived RUN integration is missing")
    archived_branch = _canonical_branch(integration.get("branch"))
    if archived_branch is None or archived_branch != branch:
        raise ManifestError("archived integration.branch does not match the live run branch")
    if run.get("status") != "complete" or integration.get("integration_head_sha") != candidate_c:
        raise ManifestError("archived RUN must be complete and record candidate C")
    replacement_base = _replacement_base_from_plan(
        root,
        plan,
        branch=branch,
        candidate_c=candidate_c,
        expected_main=receipt.get("expected_main"),
    )
    if run.get("plan", {}).get("id") != plan.get("plan_id") or run.get("plan", {}).get("revision") != plan.get("revision") or run.get("plan", {}).get("digest_sha256") != plan_digest(plan):
        raise ManifestError("archived PLAN/RUN identity or digest mismatch")
    expected_authority = {
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "candidate_c": candidate_c,
        "archive_path": archive_prefix,
        "branch_ref": f"refs/heads/{branch}",
    }
    for key, expected in expected_authority.items():
        if receipt.get(key) != expected:
            raise ManifestError(f"archive receipt authority does not match archived PLAN/RUN/A: {key}")
    if _canonical_branch(receipt.get("branch")) != branch:
        raise ManifestError("archive receipt branch does not match the live run branch")
    stamp = receipt.get("stamp")
    if (receipt.get("expected_main") is not None or receipt.get("main_ref") is not None) and (not isinstance(stamp, str) or not rel.name.startswith(stamp + "-")):
        raise ManifestError("archive receipt stamp does not match archive path")

    moves = receipt.get("moves")
    if not isinstance(moves, list):
        raise ManifestError("archive receipt moves are malformed")
    move_map = {str(item["destination"]): item for item in moves if isinstance(item, dict) and isinstance(item.get("destination"), str)}
    actual_archive = _tree_files(root, candidate_a, archive_prefix)
    expected_destinations = set(move_map)
    if set(actual_archive) != expected_destinations | {receipt_path}:
        raise ManifestError("archive tree has extra or missing files")
    for destination, move in move_map.items():
        if actual_archive[destination] != move["sha256"]:
            raise ManifestError(f"archive blob does not match receipt move: {destination}")
        source = str(move["source"])
        if _git(root, "cat-file", "-e", f"{candidate_a}:{source}").returncode == 0:
            raise ManifestError(f"live coordination path remains in A: {source}")

    source_names = {str(item["source"]) for item in moves if isinstance(item, dict)}
    if "docs/goal/PLAN.md" not in source_names or "docs/goal/RUN.md" not in source_names:
        raise ManifestError("archive receipt moves must include PLAN.md and RUN.md")
    c_files = _coordination_files(root, candidate_c)
    allowed_changes = set(c_files) | source_names | expected_destinations | {receipt_path, DOCUMENTS_PATH.as_posix()}
    changed = set(filter(None, _out(root, "diff", "--name-only", candidate_c, candidate_a).splitlines()))
    if not changed.issubset(allowed_changes):
        raise ManifestError("C->A changed files include an unauthorized path")
    c_docs = None
    try:
        c_docs = _blob(root, candidate_c, DOCUMENTS_PATH.as_posix())
    except ManifestError:
        pass
    try:
        a_docs = _blob(root, candidate_a, DOCUMENTS_PATH.as_posix())
    except ManifestError:
        a_docs = None
    expected_docs = _documents_after_archive(c_docs)
    if a_docs != expected_docs:
        raise ManifestError("DOCUMENTS.md is not the deterministic archive_run transformation")
    if receipt.get("documents_before_sha256") != (hashlib.sha256(c_docs).hexdigest() if c_docs is not None else None):
        raise ManifestError("ARCHIVE_RECEIPT documents_before_sha256 is incorrect")
    if receipt.get("documents_after_sha256") != (hashlib.sha256(expected_docs).hexdigest() if expected_docs is not None else None):
        raise ManifestError("ARCHIVE_RECEIPT documents_after_sha256 is incorrect")
    expected_main = receipt.get("expected_main")
    main_ref = receipt.get("main_ref")
    observed_main = _out(root, "rev-parse", "--verify", f"{main_ref}^{{commit}}")
    if observed_main != expected_main:
        raise ManifestError("archive receipt main_ref no longer resolves to expected_main")
    ancestry = _git(root, "merge-base", "--is-ancestor", expected_main, candidate_c)
    if ancestry.returncode != 0:
        raise ManifestError("expected_main is not an ancestor of candidate C")
    receipt_digest = hashlib.sha256(_blob(root, candidate_a, receipt_path)).hexdigest()
    archive_hashes = {path: digest for path, digest in actual_archive.items()}
    return {
        **expected_authority,
        "run_schema_version": run.get("schema_version"),
        "run_branch": branch,
        "candidate_a": candidate_a,
        "replacement_base": replacement_base,
        "archive_path": archive_prefix,
        "archive_hashes": archive_hashes,
        "moves": moves,
        "archive_receipt_sha256": receipt_digest,
        "expected_main": receipt.get("expected_main"),
        "main_ref": receipt.get("main_ref"),
        "stamp": stamp,
        "documents_before_sha256": receipt.get("documents_before_sha256"),
        "documents_after_sha256": receipt.get("documents_after_sha256"),
        "anchor_path": receipt.get("anchor_path"),
        "anchor_path_sha256": receipt.get("anchor_path_sha256"),
        "anchor_nonce": receipt.get("anchor_nonce"),
    }


def _read_closed(path: Path, protocol: str, keys: set[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read immutable artifact: {exc}") from exc
    if not isinstance(value, dict) or value.get("protocol") != protocol or set(value) != keys:
        raise ManifestError("immutable artifact has missing or extra fields")
    return value


def _write_closed(path: Path, value: dict[str, Any], root: Path) -> None:
    if path.resolve().is_relative_to(root.resolve()):
        raise ManifestError("immutable request/receipt must be outside checkout")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise ManifestError("immutable request/receipt path is already consumed") from exc


def _remote_state(root: Path, remote: str, branch_ref: str) -> str | None:
    checked = _safe_remote(remote, configured_name=True)
    _, url = _verify_configured_remote(root, checked)
    result = _git(root, "ls-remote", "--", url, branch_ref)
    if result.returncode != 0:
        raise ManifestError("configured remote readback failed")
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != branch_ref or not is_full_sha(fields[0]):
        raise ManifestError("remote readback is malformed")
    return fields[0]


def prepare(root: Path, *, archive_path: Path, remote: str, request_path: Path, attempt_path: Path, receipt_path: Path, archive_anchor: Path | None = None, authorization_source: str | None = None, authorization_ref: str | None = None) -> dict[str, Any]:
    root = _root(root)
    if authorization_source is not None or authorization_ref is not None:
        raise ManifestError(
            "caller-supplied authorization prose/ref is rejected; prepare only creates a trusted-host handoff"
        )
    request_path = Path(_canonical_external_path(request_path, label="request_path", root=root))
    attempt_path = Path(_canonical_external_path(attempt_path, label="attempt_path", root=root))
    receipt_path = Path(_canonical_external_path(receipt_path, label="receipt_path", root=root))
    if len({request_path, attempt_path, receipt_path}) != 3:
        raise ManifestError("request_path, attempt_path, and receipt_path must be pairwise distinct")
    if request_path.exists() or attempt_path.exists() or receipt_path.exists():
        raise ManifestError("request/attempt/receipt paths must be unused")
    candidate_a = _out(root, "rev-parse", "HEAD")
    verified = verify_archive_candidate(root, archive_path=archive_path, candidate_a=candidate_a)
    _manifest(root, candidate_a, f"{verified['archive_path']}/PLAN.md", PLAN_HEADING, "harness_plan")
    run = _manifest(root, candidate_a, f"{verified['archive_path']}/RUN.md", RUN_HEADING, "harness_run")
    if not archive_first_required(run):
        raise ManifestError("archive-first prepare requires a valid >=0.38 RUN pin")
    _validate_archive_authority(verified)
    if archive_anchor is None:
        raise ManifestError("prepare requires --archive-anchor for archive-first candidates")
    if archive_anchor is not None and str(Path(archive_anchor).resolve()) != verified["anchor_path"]:
        raise ManifestError("--archive-anchor does not match ARCHIVE_RECEIPT anchor_path")
    checked = _safe_remote(remote, configured_name=True)
    _, url = _verify_configured_remote(root, checked)
    pre = _remote_state(root, checked, verified["branch_ref"])
    replacement_base = verified.get("replacement_base")
    allowed_pre = (
        {None, replacement_base}
        if replacement_base is not None
        else {None, verified["candidate_c"]}
    )
    if pre not in allowed_pre:
        expectation = (
            "absent or the exact replacement base"
            if replacement_base is not None
            else "absent or C"
        )
        raise ManifestError(
            f"remote pre-state must be {expectation}"
        )
    metadata = _push_url_metadata(url)
    request = {
        "protocol": REQUEST_PROTOCOL,
        "authorization_source": LOCAL_AUTHORIZATION_SOURCE,
        "authorization_ref": LOCAL_AUTHORIZATION_REF,
        "plan_id": verified["plan_id"],
        "plan_revision": verified["plan_revision"],
        "plan_digest_sha256": verified["plan_digest_sha256"],
        "run_id": verified["run_id"],
        "run_schema_version": verified["run_schema_version"],
        "archive_path": verified["archive_path"],
        "archive_hashes": verified["archive_hashes"],
        "moves": verified["moves"],
        "archive_receipt_sha256": verified["archive_receipt_sha256"],
        "expected_main": verified["expected_main"],
        "main_ref": verified["main_ref"],
        "stamp": verified["stamp"],
        "documents_before_sha256": verified["documents_before_sha256"],
        "documents_after_sha256": verified["documents_after_sha256"],
        "anchor_path": verified["anchor_path"],
        "anchor_path_sha256": verified["anchor_path_sha256"],
        "anchor_nonce": verified["anchor_nonce"],
        "candidate_c": verified["candidate_c"],
        "replacement_base": verified.get("replacement_base"),
        "candidate_a": verified["candidate_a"],
        "run_branch": verified["run_branch"],
        "branch_ref": verified["branch_ref"],
        "remote": checked,
        **metadata,
        "remote_pre_push_head": pre,
        "request_path": str(request_path),
        "request_path_sha256": _path_digest(request_path),
        "attempt_path": str(attempt_path),
        "attempt_path_sha256": _path_digest(attempt_path),
        "receipt_path": str(receipt_path),
        "receipt_path_sha256": _path_digest(receipt_path),
        "execution_nonce": secrets.token_hex(32),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _validate_request_values(request, root, request_path)
    request["request_sha256"] = _digest(request)
    _write_closed(request_path, request, root)
    return request


def _load_request(path: Path, root: Path) -> dict[str, Any]:
    request = _read_closed(path, REQUEST_PROTOCOL, REQUEST_KEYS)
    loaded_path = path.resolve(strict=False)
    if request.get("request_path") != str(loaded_path):
        raise ManifestError("request was copied or moved; request_path does not match")
    if request["request_sha256"] != _digest({k: v for k, v in request.items() if k != "request_sha256"}):
        raise ManifestError("request digest mismatch")
    _validate_request_values(request, root, loaded_path)
    return request


def _request_matches_authority(request: dict[str, Any], authority: dict[str, Any]) -> None:
    # Every archive identity field is compared, including nested move rows and
    # deterministic DOCUMENTS hashes.  Recomputing request_sha256 cannot turn
    # a semantic edit into a valid side effect.
    for key in (
        "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
        "archive_path", "archive_hashes", "moves", "archive_receipt_sha256",
        "expected_main", "main_ref", "stamp", "documents_before_sha256",
        "documents_after_sha256", "candidate_c", "candidate_a", "replacement_base", "run_branch", "branch_ref",
        "anchor_path", "anchor_path_sha256", "anchor_nonce",
    ):
        if request.get(key) != authority.get(key):
            raise ManifestError(f"request archive authority mismatch: {key}")


def _configured_endpoint(root: Path, request: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
    checked, url = _verify_configured_remote(root, request["remote"])
    metadata = _push_url_metadata(url)
    _validate_endpoint(metadata)
    if checked != request["remote"] or metadata != {key: request[key] for key in metadata}:
        raise ManifestError("configured push endpoint does not match the request")
    return checked, url, metadata


def _validate_receipt_values(receipt: dict[str, Any], root: Path) -> None:
    if receipt.get("status") != "PASS":
        raise ManifestError("receipt status must be PASS")
    _require_sha(receipt.get("request_sha256"), length=64, label="receipt.request_sha256")
    _require_sha(receipt.get("readback_head_sha"), label="receipt.readback_head_sha")
    _require_sha(receipt.get("candidate_a"), label="receipt.candidate_a")
    _require_sha(receipt.get("candidate_c"), label="receipt.candidate_c")
    _require_nonempty(receipt.get("remote"), "receipt.remote")
    _validate_endpoint(receipt)
    _canonical_external_path(receipt.get("attempt_path"), label="receipt.attempt_path", root=root)
    _canonical_external_path(receipt.get("receipt_path"), label="receipt.receipt_path", root=root)
    for key in ("attempt_path_sha256", "receipt_path_sha256"):
        _require_sha(receipt.get(key), length=64, label=f"receipt.{key}")
    _validate_archive_authority(receipt)
    if receipt.get("readback_head_sha") != receipt.get("candidate_a"):
        raise ManifestError("receipt readback_head_sha must equal candidate_a")


def _pre_push_recheck(root: Path, request: dict[str, Any], authority: dict[str, Any]) -> tuple[str, str]:
    fresh = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, fresh)
    branch = _out(root, "branch", "--show-current")
    if branch != request["run_branch"]:
        raise ManifestError("branch changed before archive push")
    if _out(root, "rev-parse", "HEAD") != request["candidate_a"]:
        raise ManifestError("HEAD changed before archive push")
    if _out(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ManifestError("checkout became dirty before archive push")
    _, url, _ = _configured_endpoint(root, request)
    if _remote_state(root, request["remote"], request["branch_ref"]) != request["remote_pre_push_head"]:
        raise ManifestError("remote pre-state changed before archive push")
    return request["remote"], url


def begin_handoff(root: Path, *, request_path: Path) -> dict[str, Any]:
    root = _root(root)
    request = _load_request(request_path, root)
    attempt_path = Path(request["attempt_path"])
    if attempt_path.exists():
        raise ManifestError("attempt already exists; recover or verify instead of replaying execute")
    receipt_path = Path(request["receipt_path"])
    if receipt_path.exists():
        raise ManifestError("request already consumed by a receipt")
    verified = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, verified)
    _configured_endpoint(root, request)
    if _remote_state(root, request["remote"], request["branch_ref"]) != request["remote_pre_push_head"]:
        raise ManifestError("remote pre-state drifted before archive push")
    endpoint_kind = request["push_endpoint_kind"]
    endpoint_summary = request["push_endpoint_summary"]
    endpoint_digest = request["push_url_sha256"]
    remote_pre_push_head = request.get("remote_pre_push_head")
    attempt = {
        "protocol": ATTEMPT_PROTOCOL,
        "request_sha256": request["request_sha256"],
        "attempt_path": request["attempt_path"],
        "attempt_path_sha256": request["attempt_path_sha256"],
        "execution_nonce": request["execution_nonce"],
        "candidate_a": request["candidate_a"],
        "replacement_base": request.get("replacement_base"),
        "branch_ref": request["branch_ref"],
        "remote": request["remote"],
        "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "push_mode": "no_force",
        "push_endpoint_kind": endpoint_kind,
        "push_endpoint_summary": endpoint_summary,
        "push_url_sha256": endpoint_digest,
        "remote_pre_push_head": remote_pre_push_head,
    }
    attempt["attempt_sha256"] = _digest(attempt)
    _write_closed(attempt_path, attempt, root)
    # Recheck endpoint, branch, candidate, and remote pre-state immediately
    # after writing the attempt.  The local tool never performs publication:
    # a human or trusted host must execute the exact no-force push, then call
    # ``recover``/``verify-receipt`` for read-back and receipt closure.
    remote_name, _ = _pre_push_recheck(root, request, verified)
    return {
        "status": PENDING_TRUSTED_HOST_STATUS,
        "request_sha256": request["request_sha256"],
        "attempt_path": request["attempt_path"],
        "attempt_path_sha256": request["attempt_path_sha256"],
        "execution_nonce": request["execution_nonce"],
        "candidate_a": request["candidate_a"],
        "branch_ref": request["branch_ref"],
        "remote": request["remote"],
        "push_mode": "no_force",
        "push_endpoint_kind": endpoint_kind,
        "push_endpoint_summary": endpoint_summary,
        "push_url_sha256": endpoint_digest,
        "remote_pre_push_head": remote_pre_push_head,
        "receipt_path": request["receipt_path"],
        "receipt_path_sha256": request["receipt_path_sha256"],
        "push_argv": [
            "git",
            "--no-replace-objects",
            "push",
            "--",
            remote_name,
            f"{request['candidate_a']}:{request['branch_ref']}",
        ],
        "message": "trusted host or human must execute the exact no-force push; local executor did not push",
    }


def execute(root: Path, *, request_path: Path) -> dict[str, Any]:
    """Compatibility alias for :func:`begin_handoff`; never invokes Git push."""

    return begin_handoff(root, request_path=request_path)


def _load_attempt(request: dict[str, Any], root: Path) -> dict[str, Any]:
    attempt = _read_closed(Path(request["attempt_path"]), ATTEMPT_PROTOCOL, ATTEMPT_KEYS)
    if attempt["attempt_sha256"] != _digest({k: v for k, v in attempt.items() if k != "attempt_sha256"}):
        raise ManifestError("attempt digest mismatch")
    _canonical_external_path(attempt.get("attempt_path"), label="attempt_path", root=root)
    if attempt.get("attempt_path") != request.get("attempt_path") or attempt.get("attempt_path_sha256") != request.get("attempt_path_sha256"):
        raise ManifestError("attempt path identity does not match request")
    if attempt.get("started_at") is None:
        raise ManifestError("attempt started_at is missing")
    _validate_timestamp(attempt.get("started_at"), "attempt.started_at")
    _require_sha(attempt.get("request_sha256"), length=64, label="attempt.request_sha256")
    _require_sha(attempt.get("candidate_a"), label="attempt.candidate_a")
    if attempt.get("push_mode") != "no_force":
        raise ManifestError("attempt push_mode must be no_force")
    _validate_endpoint(attempt)
    pre = attempt.get("remote_pre_push_head")
    if pre is not None:
        _require_sha(pre, label="attempt.remote_pre_push_head")
    for key in ("request_sha256", "attempt_path", "attempt_path_sha256", "execution_nonce", "candidate_a", "replacement_base", "branch_ref", "remote"):
        if attempt.get(key) != request.get(key):
            raise ManifestError("attempt identity does not match request")
    for key in ("push_endpoint_kind", "push_endpoint_summary", "push_url_sha256", "remote_pre_push_head"):
        if attempt.get(key) != request.get(key):
            raise ManifestError("attempt endpoint identity does not match request")
    return attempt


def verify_receipt(root: Path, *, request_path: Path) -> dict[str, Any]:
    root = _root(root)
    request = _load_request(request_path, root)
    _load_attempt(request, root)
    receipt = _read_closed(Path(request["receipt_path"]), RECEIPT_PROTOCOL, RECEIPT_KEYS)
    _validate_receipt_values(receipt, root)
    if receipt["receipt_sha256"] != _digest({k: v for k, v in receipt.items() if k != "receipt_sha256"}):
        raise ManifestError("receipt digest mismatch")
    if any(receipt.get(k) != request.get(k) for k in ("request_sha256", "attempt_path", "attempt_path_sha256", "receipt_path", "receipt_path_sha256", "execution_nonce", "candidate_a", "replacement_base", "branch_ref", "remote", "remote_pre_push_head")):
        raise ManifestError("receipt identity does not match request")
    if any(receipt.get(k) != request.get(k) for k in (
        "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
        "archive_path", "archive_hashes", "moves", "archive_receipt_sha256", "candidate_c",
        "run_branch", "replacement_base", "expected_main", "main_ref", "stamp", "documents_before_sha256",
        "documents_after_sha256",
        "anchor_path", "anchor_path_sha256", "anchor_nonce",
    )):
        raise ManifestError("receipt archive authority does not match request")
    _, _, metadata = _configured_endpoint(root, request)
    if metadata != {key: receipt[key] for key in metadata}:
        raise ManifestError("configured push endpoint does not match receipt")
    authority = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, authority)
    if _remote_state(root, request["remote"], request["branch_ref"]) != request["candidate_a"]:
        raise ManifestError("fresh readback does not equal A")
    return receipt


def recover_uncertain(root: Path, *, request_path: Path) -> dict[str, Any]:
    root = _root(root)
    request = _load_request(request_path, root)
    _load_attempt(request, root)
    receipt_path = Path(request["receipt_path"])
    if receipt_path.exists():
        return verify_receipt(root, request_path=request_path)
    authority = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    _request_matches_authority(request, authority)
    if _remote_state(root, request["remote"], request["branch_ref"]) != request["candidate_a"]:
        raise ManifestError("recovery refuses to push; remote does not already equal A")
    _, _, metadata = _configured_endpoint(root, request)
    receipt = {
        "protocol": RECEIPT_PROTOCOL,
        "status": "PASS",
        "request_sha256": request["request_sha256"],
        "attempt_path": request["attempt_path"],
        "attempt_path_sha256": request["attempt_path_sha256"],
        "receipt_path": request["receipt_path"],
        "receipt_path_sha256": request["receipt_path_sha256"],
        "execution_nonce": request["execution_nonce"],
        "candidate_a": request["candidate_a"],
        "branch_ref": request["branch_ref"],
        "remote": request["remote"],
        **metadata,
        "remote_pre_push_head": request["remote_pre_push_head"],
        "readback_head_sha": request["candidate_a"],
        **{key: request[key] for key in (
            "plan_id", "plan_revision", "plan_digest_sha256", "run_id", "run_schema_version",
            "archive_path", "archive_hashes", "moves", "archive_receipt_sha256", "candidate_c",
            "run_branch", "replacement_base", "expected_main", "main_ref", "stamp", "documents_before_sha256",
            "documents_after_sha256",
            "anchor_path", "anchor_path_sha256", "anchor_nonce",
        )},
    }
    receipt["receipt_sha256"] = _digest(receipt)
    _write_closed(receipt_path, receipt, root)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--repo-root", required=True, type=Path)
    prepare_parser.add_argument("--archive", required=True, type=Path)
    prepare_parser.add_argument("--remote", required=True)
    prepare_parser.add_argument("--request-out", required=True, type=Path)
    prepare_parser.add_argument("--attempt-path", required=True, type=Path)
    prepare_parser.add_argument("--receipt-path", required=True, type=Path)
    prepare_parser.add_argument("--archive-anchor", required=True, type=Path)
    for name in ("begin-handoff", "execute", "verify-receipt", "recover"):
        current = sub.add_parser(name)
        current.add_argument("--repo-root", required=True, type=Path)
        current.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare(args.repo_root, archive_path=args.archive, remote=args.remote, request_path=args.request_out, attempt_path=args.attempt_path, receipt_path=args.receipt_path, archive_anchor=args.archive_anchor)
        elif args.command in {"begin-handoff", "execute"}:
            value = begin_handoff(args.repo_root, request_path=args.request)
        elif args.command == "verify-receipt":
            value = verify_receipt(args.repo_root, request_path=args.request)
        else:
            value = recover_uncertain(args.repo_root, request_path=args.request)
    except (OSError, ManifestError, ValueError, KeyError, GitMetadataError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True))
        return 2
    payload = dict(value)
    payload.setdefault("status", "PASS")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
