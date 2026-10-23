#!/usr/bin/env python3
"""Prepare and verify an exact-SHA publication of archive-only candidate A.

``prepare`` verifies A, writes one request outside the checkout and prints the
no-force ``git push`` argv. It never contacts the network and never pushes.
The parent runs the argv only after the owner's exact instruction naming the
SHA and branch. ``verify-receipt`` reads the remote ref back and passes only
when it equals A.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from harness_core import ManifestError, extract_json_manifest_text, is_full_sha, plan_digest
from harness_git import (
    GitMetadataError,
    git_environment,
    git_executable,
    reject_object_substitution,
    run_git,
)
from harness_schema import PLAN_HEADING, RUN_HEADING, archive_first_required
from harness_manifest import validate_plan, validate_run
from harness_contract_join import validate_frozen_contract_joins
from harness_ui_evidence import validate_ui_evidence_files
from archive_run import (
    ARCHIVE_RECEIPT_NAME,
    DOCUMENTS_PATH,
    _canonical_branch,
    _canonical_repo_path,
    _documents_after_bytes,
    _protected_branch,
    validate_archive_receipt,
)
from branch_policy import archive_ancestry_base, branch_policy_required


REQUEST_PROTOCOL = "harness-archive-push-request-v4"
REQUEST_KEYS = {
    "protocol", "plan_id", "run_id", "archive_path", "archive_receipt_sha256",
    "candidate_c", "candidate_a", "replacement_base", "run_branch", "branch_ref",
    "remote", "push_url", "push_argv", "created_at", "request_sha256",
}
COORDINATION_NAMES = ("PLAN.md", "RUN.md", "DECISIONS.md", "REFINEMENT_BACKLOG.md")
COORDINATION_DIR = Path("docs/goal")
_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _git(root: Path, *args: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return run_git(root, *args, capture_output=True, text=text, timeout=30, check=False)


def _out(root: Path, *args: str) -> str:
    result = _git(root, *args)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _safe_push_url(value: Any) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ManifestError("configured push URL must be a non-empty exact string")
    lowered = value.lower()
    if (
        "?" in value
        or "#" in value
        or any(char.isspace() for char in value)
        or any(char in value for char in ("\x00", "!"))
        or lowered.startswith("ext::")
        or value.startswith("-")
        or any(token in lowered for token in ("--upload-pack", "--receive-pack", "git-receive-pack"))
    ):
        raise ManifestError("configured push URL is unsafe: query, fragment, whitespace, helper or option syntax")
    if re.fullmatch(r"[A-Za-z]:[\\/][^\s]+", value) or value.startswith("/"):
        return value
    parts = urlsplit(value)
    if parts.scheme:
        if parts.password or parts.query or parts.fragment:
            raise ManifestError("configured push URL must not contain userinfo, query, or fragment data")
        if parts.username and parts.scheme != "ssh":
            raise ManifestError("configured push URL user identity is allowed only for passwordless ssh")
        if parts.scheme in {"http", "https", "ssh", "git", "file"}:
            return value
        raise ManifestError("configured push URL uses an unsafe scheme")
    if re.fullmatch(r"[A-Za-z0-9._-]+@[^:/\\]+:[^\s]+", value):
        return value
    raise ManifestError("configured push URL is not a supported safe URL/path")


def _configured_push_url(root: Path, remote: str) -> str:
    if not isinstance(remote, str) or _REMOTE_NAME_RE.fullmatch(remote) is None:
        raise ManifestError("push requires a simple configured remote name, not a URL or path")
    result = _git(root, "remote", "get-url", "--push", "--all", remote)
    urls = [line.strip() for line in result.stdout.splitlines() if line.strip()] if result.returncode == 0 else []
    if len(urls) != 1:
        raise ManifestError(f"configured Git remote {remote!r} must exist and expose exactly one push URL")
    return _safe_push_url(urls[0])


def _push_argv(url: str, candidate_a: str, branch_ref: str) -> list[str]:
    """The only publication argv: a plain push, so the remote can only fast-forward."""

    return ["git", "--no-replace-objects", "push", "--no-force", "--", url, f"{candidate_a}:{branch_ref}"]


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
    result = _git(root, "ls-tree", "-r", "-z", revision, "--", prefix, text=False)
    if result.returncode != 0:
        raise ManifestError("cannot inspect archived Git tree")
    files: dict[str, str] = {}
    for raw in bytes(result.stdout).split(b"\0"):
        if not raw:
            continue
        try:
            header, encoded_name = raw.split(b"\t", 1)
            mode, object_type, object_id = header.split()
            name = encoded_name.decode("utf-8")
            mode_text = mode.decode("ascii")
            type_text = object_type.decode("ascii")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ManifestError("archived Git tree entry is malformed") from exc
        if type_text != "blob" or mode_text not in {"100644", "100755"}:
            raise ManifestError(
                f"archived Git tree contains a non-regular entry: {name} ({mode_text} {type_text})"
            )
        if not _canonical_repo_path(name):
            raise ManifestError("archived Git tree path is not canonical")
        files[name] = hashlib.sha256(_blob(root, revision, name)).hexdigest()
    return files


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


def _canonical_archive_path(value: object) -> bool:
    return (
        _canonical_repo_path(value, prefix="docs/goal/archived/")
        and len(str(value).split("/")) == 4
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


def _replacement_base_from_plan(
    root: Path,
    plan: dict[str, Any],
    *,
    branch: str,
    candidate_c: str,
    expected_main: str,
    run: dict[str, Any] | None = None,
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
    if _canonical_branch(prior_receipt.get("branch")) != branch:
        raise ManifestError("prior archive candidate belongs to another run branch")
    if branch_policy_required(run):
        prior_directory = str(Path(location).parent).replace("\\", "/")
        prior_plan = _manifest(root, revision, prior_directory + "/PLAN.md", PLAN_HEADING, "harness_plan")
        prior_run = _manifest(root, revision, prior_directory + "/RUN.md", RUN_HEADING, "harness_run")
        for name in ("PLAN.md", "RUN.md"):
            prior_path = prior_directory + "/" + name
            move = next((item for item in prior_receipt["moves"] if item.get("destination") == prior_path), None)
            if move is None or hashlib.sha256(_blob(root, revision, prior_path)).hexdigest() != move.get("sha256"):
                raise ManifestError("prior frozen policy inputs do not match archive receipt")
        if (not branch_policy_required(prior_run)
                or plan_digest(prior_plan) != prior_receipt.get("plan_digest_sha256")
                or archive_ancestry_base(prior_plan, prior_run, prior_receipt.get("expected_main"))
                != archive_ancestry_base(plan, run, expected_main)
                or prior_plan.get("branch_policy") != plan.get("branch_policy")):
            raise ManifestError("correction archive must retain the prior frozen branch policy")
    elif prior_receipt.get("expected_main") != expected_main:
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


def _has_receipt_bound_archive(root: Path, revision: str) -> bool:
    """Return whether a revision is an archive-only candidate with a receipt."""

    if not is_full_sha(revision):
        return False
    result = _git(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        revision,
        "--",
        "docs/goal/archived",
    )
    if result.returncode != 0:
        return False
    for name in result.stdout.splitlines():
        if not name.endswith("/" + ARCHIVE_RECEIPT_NAME):
            continue
        try:
            receipt = _read_receipt(root, revision, name)
        except ManifestError:
            continue
        if receipt.get("candidate_c") and receipt.get("branch_ref"):
            parents = _out(root, "rev-list", "--parents", "-n", "1", revision).split()
            if len(parents) == 2 and receipt.get("candidate_c") == parents[1]:
                return True
    return False


def _archive_lineage_candidates(
    root: Path,
    candidate_c: str,
    expected_main: str,
) -> list[str]:
    """List receipt-bound archive candidates after the recorded main base."""

    result = _git(
        root,
        "rev-list",
        "--first-parent",
        candidate_c,
        "--not",
        expected_main,
    )
    if result.returncode != 0:
        raise ManifestError("cannot inspect candidate first-parent lineage")
    return [
        revision
        for revision in result.stdout.splitlines()
        if is_full_sha(revision) and _has_receipt_bound_archive(root, revision)
    ]


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
    prior_sources = [
        source
        for source in plan.get("sources", [])
        if isinstance(source, dict)
        and " ".join(str(source.get("kind", "")).replace("_", " ").split()).casefold()
        == "prior archive candidate"
    ]
    lineage_archives = _archive_lineage_candidates(
        root,
        candidate_c,
        archive_ancestry_base(plan, run, receipt.get("expected_main")),
    )
    if lineage_archives and len(prior_sources) != 1:
        raise ManifestError(
            "correction candidate descends from a receipt-bound archive A and "
            "must include exactly one prior archive candidate source"
        )
    replacement_base = _replacement_base_from_plan(
        root,
        plan,
        branch=branch,
        candidate_c=candidate_c,
        expected_main=receipt.get("expected_main"),
        run=run,
    )
    if lineage_archives and replacement_base != lineage_archives[0]:
        raise ManifestError(
            "prior archive candidate source must bind the latest receipt-bound archive A"
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
    if not isinstance(stamp, str) or not rel.name.startswith(stamp + "-"):
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
    c_files = _coordination_files(root, candidate_c)
    # PLAN/RUN are intentionally allowed to be the closeout working-tree
    # coordination inputs (C can predate the manifests); every other file
    # must be exactly the immutable candidate-C coordination inventory.
    expected_source_names = set(c_files) | {"docs/goal/PLAN.md", "docs/goal/RUN.md"}
    if not expected_source_names.issubset(source_names):
        missing = sorted(expected_source_names - source_names)
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        raise ManifestError(
            "archive receipt moves must cover every coordination file in candidate C"
            + (" (" + "; ".join(detail) + ")" if detail else "")
        )
    for move in moves:
        source = move["source"]
        if source in {"docs/goal/PLAN.md", "docs/goal/RUN.md"}:
            continue
        if source not in c_files or move["sha256"] != c_files[source]:
            raise ManifestError(f"archive receipt source does not match candidate C: {source}")
    # A inherits C's review, security and gate evidence only through this allowlist.
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
    expected_docs = _documents_after_bytes(c_docs)
    if a_docs != expected_docs:
        raise ManifestError("DOCUMENTS.md is not the deterministic archive_run transformation")
    if receipt.get("documents_before_sha256") != (hashlib.sha256(c_docs).hexdigest() if c_docs is not None else None):
        raise ManifestError("ARCHIVE_RECEIPT documents_before_sha256 is incorrect")
    if receipt.get("documents_after_sha256") != (hashlib.sha256(expected_docs).hexdigest() if expected_docs is not None else None):
        raise ManifestError("ARCHIVE_RECEIPT documents_after_sha256 is incorrect")
    expected_main = receipt.get("expected_main")
    main_ref = receipt.get("main_ref")
    if not branch_policy_required(run):
        observed_main = _out(root, "rev-parse", "--verify", f"{main_ref}^{{commit}}")
        if observed_main != expected_main:
            raise ManifestError("archive receipt main_ref no longer resolves to expected_main")
    ancestry_base = archive_ancestry_base(plan, run, expected_main)
    ancestry = _git(root, "merge-base", "--is-ancestor", ancestry_base, candidate_c)
    if ancestry.returncode != 0:
        raise ManifestError("archive base is not an ancestor of candidate C")
    return {
        **expected_authority,
        "run_branch": branch,
        "candidate_a": candidate_a,
        "replacement_base": replacement_base,
        "archive_receipt_sha256": hashlib.sha256(_blob(root, candidate_a, receipt_path)).hexdigest(),
    }


def _remote_state(url: str, branch_ref: str) -> str | None:
    """Read the exact remote ref from an empty directory, so no repository config applies.

    System and user Git config still apply, so the machine's own credential
    helper works for a private remote.
    """

    url = _safe_push_url(url)
    environment = git_environment()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    with tempfile.TemporaryDirectory(prefix="harness-readback-") as isolated:
        environment["GIT_CEILING_DIRECTORIES"] = isolated
        try:
            result = subprocess.run(
                [git_executable(environment), "--no-replace-objects", "ls-remote", "--", url, branch_ref],
                cwd=isolated,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.SubprocessError, GitMetadataError) as exc:
            raise ManifestError(f"remote readback failed: {exc}") from exc
    if result.returncode != 0:
        raise ManifestError("remote readback failed")
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    fields = lines[0].split()
    if len(lines) != 1 or len(fields) != 2 or fields[1] != branch_ref or not is_full_sha(fields[0]):
        raise ManifestError("remote readback is malformed")
    return fields[0]


def prepare(
    root: Path,
    *,
    archive_path: Path,
    remote: str,
    request_path: Path,
) -> dict[str, Any]:
    root = _root(root)
    request_path = request_path.resolve(strict=False)
    if request_path.is_relative_to(root):
        raise ManifestError("request_path must live outside the reviewed checkout")
    if request_path.exists():
        raise ManifestError("request_path is already consumed")
    candidate_a = _out(root, "rev-parse", "HEAD")
    verified = verify_archive_candidate(root, archive_path=archive_path, candidate_a=candidate_a)
    run = _manifest(root, candidate_a, f"{verified['archive_path']}/RUN.md", RUN_HEADING, "harness_run")
    if not archive_first_required(run):
        raise ManifestError("archive-first prepare requires a valid >=0.38 RUN pin")
    url = _configured_push_url(root, remote)
    request = {
        "protocol": REQUEST_PROTOCOL,
        "plan_id": verified["plan_id"],
        "run_id": verified["run_id"],
        "archive_path": verified["archive_path"],
        "archive_receipt_sha256": verified["archive_receipt_sha256"],
        "candidate_c": verified["candidate_c"],
        "candidate_a": candidate_a,
        "replacement_base": verified["replacement_base"],
        "run_branch": verified["run_branch"],
        "branch_ref": verified["branch_ref"],
        "remote": remote,
        "push_url": url,
        "push_argv": _push_argv(url, candidate_a, verified["branch_ref"]),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    request["request_sha256"] = _digest(request)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with request_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(request, handle, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise ManifestError("request_path is already consumed") from exc
    return {"status": "PREPARED", "request_path": str(request_path), **request}


def _load_request(path: Path) -> dict[str, Any]:
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read request: {exc}") from exc
    if not isinstance(request, dict) or request.get("protocol") != REQUEST_PROTOCOL or set(request) != REQUEST_KEYS:
        raise ManifestError("request has missing or extra fields")
    if request["request_sha256"] != _digest({k: v for k, v in request.items() if k != "request_sha256"}):
        raise ManifestError("request digest mismatch")
    return request


def verify_receipt(root: Path, *, request_path: Path) -> dict[str, Any]:
    """Pass only when the checkout is still the verified A and the remote ref equals A."""

    root = _root(root)
    request = _load_request(request_path)
    verified = verify_archive_candidate(root, archive_path=root / request["archive_path"], candidate_a=request["candidate_a"])
    for key in ("plan_id", "run_id", "archive_path", "archive_receipt_sha256", "candidate_c", "replacement_base", "run_branch", "branch_ref"):
        if verified[key] != request[key]:
            raise ManifestError(f"request archive authority mismatch: {key}")
    if request["push_argv"] != _push_argv(request["push_url"], request["candidate_a"], request["branch_ref"]):
        raise ManifestError("request push argv does not match the exact URL, A and branch ref")
    if _configured_push_url(root, request["remote"]) != request["push_url"]:
        raise ManifestError("configured push URL changed after prepare")
    readback = _remote_state(request["push_url"], request["branch_ref"])
    if readback != request["candidate_a"]:
        raise ManifestError("fresh readback does not equal A")
    return {
        "status": "PASS",
        "candidate_a": request["candidate_a"],
        "branch_ref": request["branch_ref"],
        "readback_head_sha": readback,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--repo-root", required=True, type=Path)
    prepare_parser.add_argument("--archive", required=True, type=Path)
    prepare_parser.add_argument("--remote", required=True)
    prepare_parser.add_argument("--request-out", required=True, type=Path)
    verify_parser = sub.add_parser("verify-receipt")
    verify_parser.add_argument("--repo-root", required=True, type=Path)
    verify_parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            value = prepare(
                args.repo_root,
                archive_path=args.archive,
                remote=args.remote,
                request_path=args.request_out,
            )
        else:
            value = verify_receipt(args.repo_root, request_path=args.request)
    except (OSError, ManifestError, ValueError, KeyError, GitMetadataError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True))
        return 2
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
