#!/usr/bin/env python3
"""Push one reserved integration head and retain an immutable receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from harness_core import ManifestError, _normalized_branch, is_full_sha
from harness_schema import archive_first_required, required_harness_version
from harness_authorization import authorization_covers
from harness_manifest import (
    canonical_json,
    load_plan,
    load_run,
    plan_digest,
    validate_current_plan_run,
)


PUSH_PROTOCOL = "harness-push-request-v1"
RECEIPT_PROTOCOL = "harness-push-receipt-v1"


def _git(
    root: Path, *arguments: str, text: bool = True
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=text,
        timeout=30,
        check=False,
    )


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _safe_remote(value: Any, *, configured_name: bool = False) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ManifestError("push remote must be a non-empty exact string")
    if value.startswith("-") or value in {"--", ".", ".."}:
        if configured_name:
            raise ManifestError("current push requires a simple configured remote name")
        raise ManifestError("push remote must not be option-like")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ManifestError("push remote contains forbidden control characters")
    if configured_name and _REMOTE_NAME_RE.fullmatch(value) is None:
        raise ManifestError(
            "current push requires a simple configured remote name, not a URL, ext:: transport, or path"
        )
    return value


def _safe_push_url(value: Any) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ManifestError("configured push URL must be a non-empty exact string")
    if "?" in value or "#" in value:
        raise ManifestError(
            "configured push URL must not contain userinfo, query, or fragment data"
        )
    if any(char.isspace() for char in value) or any(
        char in value for char in ("\x00", "\r", "\n", "!")
    ):
        raise ManifestError("configured push URL contains unsafe whitespace/control/helper syntax")
    lowered = value.lower()
    if lowered.startswith("ext::") or value.startswith("-"):
        raise ManifestError("configured push URL uses an unsafe transport or option")
    if any(token in lowered for token in ("--upload-pack", "--receive-pack", "git-receive-pack")):
        raise ManifestError("configured push URL contains an unsafe helper or option")
    if re.fullmatch(r"[A-Za-z]:[\\/][^\s]+", value) or value.startswith("/"):
        return value
    parts = urlsplit(value)
    if parts.scheme:
        if parts.password or parts.query or parts.fragment:
            raise ManifestError(
                "configured push URL must not contain userinfo, query, or fragment data"
            )
        if parts.username and parts.scheme != "ssh":
            raise ManifestError("configured push URL user identity is allowed only for passwordless ssh")
        if lowered.startswith(("http://", "https://", "ssh://", "git://", "file://")):
            if parts.scheme == "file" and not parts.path:
                raise ManifestError("configured file push URL must include a path")
            return value
        raise ManifestError("configured push URL uses an unsafe scheme")
    if re.fullmatch(r"[A-Za-z0-9._-]+@[^:/\\]+:[^\s]+", value):
        return value
    raise ManifestError("configured push URL is not a supported safe URL/path")


def _push_url_metadata(value: str) -> dict[str, str]:
    """Return non-sensitive identity metadata; never persist the URL itself."""

    digest = _sha256_text(value)
    if re.fullmatch(r"[A-Za-z]:[\\/][^\s]+", value) or value.startswith("/"):
        kind = "file_path"
        summary = "file://<redacted-path>"
    elif re.fullmatch(r"[A-Za-z0-9._-]+@[^:/\\]+:[^\s]+", value):
        kind = "scp"
        summary = "scp://<redacted-host>/<redacted-path>"
    else:
        parts = urlsplit(value)
        if not parts.scheme:
            kind = "file_path"
            summary = "file://<redacted-path>"
        else:
            kind = parts.scheme.lower()
            summary = f"{kind}://<redacted-host>/<redacted-path>"
    return {
        "push_endpoint_kind": kind,
        "push_endpoint_summary": summary,
        "push_url_sha256": digest,
    }


def _configured_push_url(root: Path, remote: str) -> str:
    checked = _safe_remote(remote, configured_name=True)
    result = _git(root, "remote", "get-url", "--push", "--all", checked)
    if result.returncode != 0:
        raise ManifestError(f"configured Git remote {checked!r} does not exist")
    urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(urls) != 1:
        raise ManifestError(
            f"configured Git remote {checked!r} must expose exactly one push URL"
        )
    return _safe_push_url(urls[0])


def _verify_configured_remote(root: Path, remote: str) -> tuple[str, str]:
    checked = _safe_remote(remote, configured_name=True)
    return checked, _configured_push_url(root, checked)


def _root(path: Path) -> Path:
    resolved = path.resolve()
    top = _git(resolved, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise ManifestError(f"--repo-root {resolved} is not a Git checkout")
    actual = Path(top.stdout.strip()).resolve()
    if actual != resolved:
        raise ManifestError(
            f"--repo-root {path} must be the repository root, not a subdirectory"
        )
    return resolved


def _outside_checkout(path: Path, checkout: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(checkout.resolve())
    except ValueError:
        return resolved
    raise ManifestError(f"{label} must live outside the reviewed checkout")


def _status_paths(root: Path) -> list[str]:
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "-z",
        text=False,
    )
    if status.returncode != 0:
        detail = status.stderr.decode(errors="replace").strip()
        raise ManifestError(f"git status failed while validating push checkout: {detail}")
    output = status.stdout
    assert isinstance(output, bytes)
    tokens = [item for item in output.split(b"\0") if item]
    paths: list[str] = []
    index = 0
    while index < len(tokens):
        record = tokens[index].decode("utf-8", errors="replace")
        index += 1
        if len(record) < 3:
            continue
        status_code = record[:2]
        paths.append(record[3:].replace("\\", "/"))
        if status_code[:1] in {"R", "C"} and index < len(tokens):
            paths.append(tokens[index].decode("utf-8", errors="replace").replace("\\", "/"))
            index += 1
    return sorted(set(paths))


def _coordination_dirty_paths(run: dict[str, Any], root: Path) -> list[str]:
    integration = run.get("integration")
    paths = integration.get("coordination_paths") if isinstance(integration, dict) else None
    if not isinstance(paths, list) or any(
        not isinstance(item, str) or not item for item in paths
    ):
        raise ManifestError("run.integration.coordination_paths must be recorded before push")
    allowed = {item.replace("\\", "/").lstrip("./") for item in paths}
    dirty = _status_paths(root)
    unrelated = [path for path in dirty if path not in allowed]
    if unrelated:
        raise ManifestError(
            "push checkout is dirty outside recorded coordination paths: "
            + ", ".join(unrelated)
        )
    return dirty


def _attempt(run: dict[str, Any], node_id: str, attempt_id: str) -> dict[str, Any]:
    matches = [
        item
        for item in run.get("attempt_log", [])
        if isinstance(item, dict)
        and item.get("kind") == "node_attempt"
        and item.get("node_id") == node_id
        and item.get("attempt_id") == attempt_id
    ]
    if len(matches) != 1:
        raise ManifestError(
            f"push requires one matching reserved node/attempt ({node_id!r}, {attempt_id!r})"
        )
    if matches[0].get("result") != "reserved":
        raise ManifestError("push reservation is no longer active")
    dispatch = matches[0].get("node_dispatch")
    if not isinstance(dispatch, dict) or not isinstance(dispatch.get("push_request"), dict):
        raise ManifestError("push reservation has no immutable push request")
    return matches[0]


def _validate_current_request_binding(
    plan: dict[str, Any],
    run: dict[str, Any],
    root: Path,
    request: dict[str, Any],
    dispatch: dict[str, Any],
    *,
    node_id: str,
    attempt_id: str,
) -> None:
    """Revalidate the live current pair and the reserved immutable identity."""

    errors = validate_current_plan_run(plan, run, repo_root=root)
    if errors:
        raise ManifestError(
            "current PLAN/RUN changed or is no longer valid before push:\n"
            + "\n".join(f"- {error}" for error in errors)
        )
    expected = {
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "node_id": node_id,
        "attempt_id": attempt_id,
        "branch": dispatch.get("branch"),
        "branch_ref": dispatch.get("branch_ref"),
        "head_sha": dispatch.get("authorized_head_sha"),
        "remote": run.get("landing", {}).get("remote"),
        "remote_ref": dispatch.get("branch_ref"),
    }
    _, configured_url = _verify_configured_remote(root, str(expected["remote"]))
    expected.update(_push_url_metadata(configured_url))
    for key, value in expected.items():
        if request.get(key) != value:
            raise ManifestError(
                f"reserved push request {key} no longer matches the current PLAN/RUN"
            )
    if dispatch.get("request_sha256") != _sha256(request):
        raise ManifestError("reserved push request digest no longer matches the current request")


def _live_target(run: dict[str, Any], repo_root: Path, authorized_head_sha: str) -> dict[str, str]:
    root = _root(repo_root)
    integration = run.get("integration")
    raw_branch = integration.get("branch") if isinstance(integration, dict) else None
    branch = _normalized_branch(raw_branch)
    if branch is None:
        raise ManifestError("run.integration.branch must name a branch")
    if branch.lower() in {"main", "development"}:
        raise ManifestError("integration branch is protected or retired")
    if not is_full_sha(authorized_head_sha):
        raise ManifestError("push authorization requires a full authorized head SHA")
    if integration.get("integration_head_sha") != authorized_head_sha:
        raise ManifestError(
            "push authorized_head_sha must equal integration.integration_head_sha"
        )
    head_result = _git(root, "rev-parse", "HEAD")
    branch_result = _git(root, "rev-parse", "--verify", f"refs/heads/{branch}")
    current_branch_result = _git(root, "branch", "--show-current")
    if head_result.returncode != 0 or branch_result.returncode != 0:
        raise ManifestError("could not read the live integration branch and HEAD")
    live_head = head_result.stdout.strip()
    branch_head = branch_result.stdout.strip()
    live_branch = current_branch_result.stdout.strip()
    if _normalized_branch(live_branch) != branch:
        raise ManifestError(
            f"--repo-root is on branch {live_branch!r}, not integration branch {branch!r}"
        )
    if live_head != authorized_head_sha or branch_head != authorized_head_sha:
        raise ManifestError(
            f"integration branch HEAD is {branch_head}, checkout HEAD is {live_head}; "
            f"push requires authorized head {authorized_head_sha}"
        )
    return {"branch": branch, "branch_ref": f"refs/heads/{branch}", "head_sha": live_head}


def validate_push_target(
    run: dict[str, Any], repo_root: Path, authorized_head_sha: str
) -> dict[str, str]:
    """Validate the live exact candidate and every current push grant."""

    target = _live_target(run, repo_root, authorized_head_sha)
    requested = f"branch:{target['branch_ref']}"
    mission_ids = sorted(run.get("mission_states", {}))
    if not mission_ids or any(
        not authorization_covers(
            run,
            "push",
            mission_id,
            requested,
            required_head_sha=authorized_head_sha,
        )
        for mission_id in mission_ids
    ):
        raise ManifestError(
            "push authorization does not cover every mission, branch, and authorized head"
        )
    return target


def make_push_request(
    plan: dict[str, Any],
    run: dict[str, Any],
    repo_root: Path,
    *,
    node_id: str,
    attempt_id: str,
    authorized_head_sha: str,
) -> dict[str, Any]:
    """Build the canonical request persisted by reserve-node-attempt."""

    root = _root(repo_root)
    target = validate_push_target(run, root, authorized_head_sha)
    landing = run.get("landing")
    remote = _safe_remote(
        landing.get("remote") if isinstance(landing, dict) else None,
        configured_name=True,
    )
    _, push_url = _verify_configured_remote(root, remote)
    endpoint_meta = _push_url_metadata(push_url)
    dirty_paths = _coordination_dirty_paths(run, root)
    coordination_paths = run["integration"]["coordination_paths"]
    return {
        "protocol": PUSH_PROTOCOL,
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "node_id": node_id,
        "attempt_id": attempt_id,
        "branch": target["branch"],
        "branch_ref": target["branch_ref"],
        "head_sha": target["head_sha"],
        "remote": remote,
        **endpoint_meta,
        "remote_ref": target["branch_ref"],
        "coordination_paths": sorted(
            {
                item.replace("\\", "/").lstrip("./")
                for item in coordination_paths
            }
        ),
        "dirty_paths_at_reservation": dirty_paths,
        "checkout_root": str(root),
    }


def _read_request(path: Path, root: Path) -> tuple[dict[str, Any], str]:
    _outside_checkout(path, root, "push request")
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read push request: {exc}") from exc
    if not isinstance(request, dict) or request.get("protocol") != PUSH_PROTOCOL:
        raise ManifestError("push request has an unsupported protocol")
    return request, _sha256(request)


def _write_exclusive(path: Path, value: dict[str, Any], root: Path, label: str) -> None:
    _outside_checkout(path, root, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, ensure_ascii=False)
            handle.write("\n")
    except FileExistsError as exc:
        raise ManifestError(f"refusing to overwrite existing {label}: {path}") from exc


def _remote_readback(root: Path, push_url: str, branch_ref: str) -> str:
    result = _git(root, "ls-remote", "--", push_url, branch_ref)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git ls-remote error"
        raise ManifestError(f"git ls-remote frozen push URL {branch_ref} failed: {detail}")
    rows = result.stdout.strip().splitlines()
    fields = rows[0].split() if len(rows) == 1 else []
    if len(fields) != 2 or fields[1] != branch_ref:
        raise ManifestError("remote integration ref read-back is missing or malformed")
    return fields[0]


def validate_push_receipt(
    plan: dict[str, Any],
    run: dict[str, Any],
    repo_root: Path,
    *,
    node_id: str,
    attempt_id: str,
    receipt_path: Path,
) -> dict[str, Any]:
    """Validate a receipt and perform the mandatory fresh remote read-back."""

    root = _root(repo_root)
    attempt = _attempt(run, node_id, attempt_id)
    dispatch = attempt["node_dispatch"]
    request = dispatch["push_request"]
    _outside_checkout(receipt_path, root, "push receipt")
    try:
        value = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read push receipt: {exc}") from exc
    if not isinstance(value, dict) or value.get("protocol") != RECEIPT_PROTOCOL:
        raise ManifestError("push receipt has an unsupported protocol")
    if value.get("status") != "PASS":
        raise ManifestError("push receipt must record PASS")
    if value.get("request_sha256") != dispatch.get("request_sha256"):
        raise ManifestError("push receipt request digest does not match reservation")
    expected_plan = {
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
    }
    for key in (
        "run_id",
        "plan_id",
        "plan_revision",
        "plan_digest_sha256",
        "node_id",
        "attempt_id",
        "branch",
        "branch_ref",
        "head_sha",
        "remote",
        "remote_ref",
        "push_endpoint_kind",
        "push_endpoint_summary",
        "push_url_sha256",
    ):
        expected = expected_plan[key] if key in expected_plan else request.get(key)
        if value.get(key) != expected:
            raise ManifestError(f"push receipt {key} does not match reservation")
    remote = _safe_remote(request.get("remote"), configured_name=True)
    _, push_url = _verify_configured_remote(root, remote)
    endpoint_meta = _push_url_metadata(push_url)
    if any(request.get(key) != value for key, value in endpoint_meta.items()):
        raise ManifestError("configured push URL changed after the push")
    _coordination_dirty_paths(run, root)
    readback = _remote_readback(root, push_url, request["remote_ref"])
    if readback != request["head_sha"] or value.get("readback_head_sha") != readback:
        raise ManifestError("fresh remote read-back does not equal the authorized head")
    return value


def push_authorized_head(
    plan: dict[str, Any],
    run: dict[str, Any],
    repo_root: Path,
    remote: str | None = None,
    *,
    node_id: str | None = None,
    attempt_id: str | None = None,
    request_path: Path | None = None,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    """Execute one reserved push and write its immutable receipt."""

    root = _root(repo_root)
    current = run.get("schema_version") == 11
    if current and required_harness_version(run) is None:
        raise ManifestError(
            "RUN schema 11 push requires an explicit valid required_harness_version pin"
        )
    if current and archive_first_required(run):
        raise ManifestError(
            "RUN pins archive-first promotion (Harness >=0.38); use push_archived_candidate.py"
        )
    if not current:
        raise ManifestError(
            "push side effects require RUN schema 11; legacy runs are read-only recovery"
        )
    entry = run.get("authorizations", {}).get("push")
    authorized_head = entry.get("authorized_head_sha") if isinstance(entry, dict) else None
    if not isinstance(authorized_head, str):
        raise ManifestError("run has no push authorized_head_sha")
    request: dict[str, Any] | None = None
    dispatch: dict[str, Any] | None = None
    if current:
        if not isinstance(node_id, str) or not node_id or not isinstance(attempt_id, str) or not attempt_id:
            raise ManifestError("current push requires matching reserved node and attempt")
        if request_path is None or receipt_path is None:
            raise ManifestError("current push requires an immutable request and receipt path")
        attempt = _attempt(run, node_id, attempt_id)
        dispatch = attempt["node_dispatch"]
        request, request_sha = _read_request(request_path, root)
        if dispatch.get("request_sha256") != request_sha or dispatch.get("push_request") != request:
            raise ManifestError("push request does not match the reserved node attempt")
        if request.get("run_id") != run.get("run_id") or request.get("node_id") != node_id or request.get("attempt_id") != attempt_id:
            raise ManifestError("push request identity does not match the reserved node attempt")
        expected_remote = _safe_remote(
            run.get("landing", {}).get("remote"), configured_name=True
        )
        _, push_url = _verify_configured_remote(root, expected_remote)
        endpoint_meta = _push_url_metadata(push_url)
        if remote is not None and remote != expected_remote:
            raise ManifestError("push remote does not match the recorded landing.remote")
        remote = expected_remote
        if request.get("remote") != remote:
            raise ManifestError("push request remote does not match the recorded landing.remote")
        if any(request.get(key) != value for key, value in endpoint_meta.items()):
            raise ManifestError("reserved push URL does not match the configured remote")
        _validate_current_request_binding(
            plan,
            run,
            root,
            request,
            dispatch,
            node_id=node_id,
            attempt_id=attempt_id,
        )
    target = validate_push_target(run, root, authorized_head)
    dirty = _coordination_dirty_paths(run, root) if current else []
    if current and request is not None:
        allowed = set(request.get("coordination_paths", []))
        if any(path not in allowed for path in dirty):
            raise ManifestError("push checkout gained an unrelated dirty path after reservation")
        # Re-read the immutable request immediately before the side effect so a
        # changed PLAN/RUN/request cannot race the remote write.
        assert request_path is not None
        latest_request, latest_digest = _read_request(request_path, root)
        if latest_digest != dispatch.get("request_sha256") or latest_request != request:
            raise ManifestError("push request changed before the remote write")
        _validate_current_request_binding(
            plan,
            run,
            root,
            latest_request,
            dispatch,
            node_id=node_id,
            attempt_id=attempt_id,
        )
        _, latest_push_url = _verify_configured_remote(root, remote)
        if _push_url_metadata(latest_push_url) != {
            key: request.get(key) for key in _push_url_metadata(latest_push_url)
        }:
            raise ManifestError("configured push URL changed before the remote write")

    refspec = f"{target['head_sha']}:{target['branch_ref']}"
    push = _git(root, "push", "--", push_url, refspec)
    if push.returncode != 0:
        detail = push.stderr.strip() or push.stdout.strip() or "unknown git push error"
        raise ManifestError(f"git push frozen URL {refspec} failed: {detail}")
    readback = _remote_readback(root, push_url, target["branch_ref"])
    if readback != target["head_sha"]:
        raise ManifestError("remote integration ref read-back does not equal the authorized head")
    receipt = {
        "protocol": RECEIPT_PROTOCOL,
        "status": "PASS",
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "node_id": node_id,
        "attempt_id": attempt_id,
        "request_sha256": dispatch.get("request_sha256") if dispatch else None,
        "branch": target["branch"],
        "branch_ref": target["branch_ref"],
        "head_sha": target["head_sha"],
        "remote": remote,
        **_push_url_metadata(push_url),
        "remote_ref": target["branch_ref"],
        "readback_head_sha": readback,
        "dirty_paths": dirty,
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if current:
        assert receipt_path is not None
        _write_exclusive(receipt_path, receipt, root, "push receipt")
    return {**receipt, "receipt_path": str(receipt_path) if receipt_path is not None else None}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--remote")
    parser.add_argument("--node-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--receipt-out", type=Path)
    args = parser.parse_args(argv)
    try:
        result = push_authorized_head(
            load_plan(args.plan),
            load_run(args.run),
            args.repo_root,
            args.remote,
            node_id=args.node_id,
            attempt_id=args.attempt_id,
            request_path=args.request,
            receipt_path=args.receipt_out,
        )
    except (OSError, ManifestError, ValueError) as exc:
        sys.stdout.write(canonical_json({"errors": [str(exc)], "status": "ERROR"}))
        return 2
    sys.stdout.write(canonical_json({**result, "status": "PASS"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
